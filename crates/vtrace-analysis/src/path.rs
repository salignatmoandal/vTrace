//! Per-objective critical paths (spec 0007).
//!
//! Distinct objectives yield distinct paths. Missing edges →
//! `partial` / `unavailable`, never a fabricated path (decision 0005).

use std::collections::HashMap;

use serde::Serialize;
use vtrace_core::{Event, TraceDocument};

use crate::error::AnalysisError;
use crate::graph::{adjacency, build_graph, missing_queue_reasons, topo_order, Graph};

/// Latency objective for a critical-path query.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Objective {
    /// Ends at `llm.first_token`.
    Ttft,
    /// Ends at `tts.first_audio`.
    Ttfa,
    /// Ends at `playback.started` (requires audible evidence).
    TimeToAudible,
    /// Ends at `turn.completed` (or other turn terminal).
    TurnCompletion,
}

impl Objective {
    fn target_names(self) -> &'static [&'static str] {
        match self {
            Self::Ttft => &["llm.first_token"],
            Self::Ttfa => &["tts.first_audio"],
            Self::TimeToAudible => &["playback.started"],
            Self::TurnCompletion => &[
                "turn.completed",
                "turn.failed",
                "turn.cancelled",
                "turn.timed_out",
            ],
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Ttft => "ttft",
            Self::Ttfa => "ttfa",
            Self::TimeToAudible => "time_to_audible",
            Self::TurnCompletion => "turn_completion",
        }
    }
}

/// Confidence of a critical-path result.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum PathConfidence {
    Complete,
    Partial,
    Unavailable,
}

/// One hop on a critical path.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PathHop {
    pub event_id: String,
    pub name: String,
    pub timestamp_ns: i64,
}

/// Result of `critical_path` for one objective.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PathResult {
    pub objective: Objective,
    pub confidence: PathConfidence,
    pub hops: Vec<PathHop>,
    pub duration_ns: Option<i64>,
    pub reasons: Vec<String>,
}

/// Compute the critical path for a single objective.
pub fn critical_path(
    doc: &TraceDocument,
    objective: Objective,
) -> Result<PathResult, AnalysisError> {
    let graph = build_graph(doc)?;
    critical_path_on_graph(doc, &graph, objective)
}

fn critical_path_on_graph(
    doc: &TraceDocument,
    graph: &Graph,
    objective: Objective,
) -> Result<PathResult, AnalysisError> {
    let by_id: HashMap<&str, &Event> = doc
        .events
        .iter()
        .map(|e| (e.event_id.as_str(), e))
        .collect();

    // Cross-domain: all events on the path must share one domain.
    // Checked after we find a path.

    let target = find_target(doc, objective);
    let Some(target_ev) = target else {
        return Ok(PathResult {
            objective,
            confidence: PathConfidence::Unavailable,
            hops: Vec::new(),
            duration_ns: None,
            reasons: vec![format!(
                "no target event for {} ({})",
                objective.as_str(),
                objective.target_names().join(" | ")
            )],
        });
    };

    // Special case: time_to_audible also needs vad.speech_ended as start
    // evidence — without it the metric is unavailable (spec 0004).
    if objective == Objective::TimeToAudible {
        let has_vad_end = doc.events.iter().any(|e| e.name == "vad.speech_ended");
        if !has_vad_end {
            return Ok(PathResult {
                objective,
                confidence: PathConfidence::Unavailable,
                hops: Vec::new(),
                duration_ns: None,
                reasons: vec!["unavailable (no vad.speech_ended)".into()],
            });
        }
    }

    let adj = adjacency(graph);
    let order = topo_order(graph);

    // Longest path (by duration along timestamps) ending at target.
    // dist[v] = max cumulative duration from any source to v.
    // pred[v] = predecessor on that path.
    let mut dist: HashMap<&str, i64> = HashMap::new();
    let mut pred: HashMap<&str, &str> = HashMap::new();
    for id in &graph.event_ids {
        dist.insert(id.as_str(), 0);
    }

    for &u in &order {
        let Some(u_ev) = by_id.get(u) else {
            continue;
        };
        let Some(neis) = adj.get(u) else {
            continue;
        };
        for &v in neis {
            let Some(v_ev) = by_id.get(v) else {
                continue;
            };
            // Edge weight = time delta (non-negative within domain).
            if u_ev.clock_domain != v_ev.clock_domain {
                return Err(AnalysisError::CrossDomain {
                    from_domain: u_ev.clock_domain.clone(),
                    to_domain: v_ev.clock_domain.clone(),
                });
            }
            let delta = v_ev.timestamp_ns.saturating_sub(u_ev.timestamp_ns);
            let cand = dist.get(u).copied().unwrap_or(0).saturating_add(delta);
            let cur = dist.get(v).copied().unwrap_or(0);
            if cand >= cur {
                // Prefer longer (or equal with a predecessor set) so we
                // actually chain; on equal keep first discovered.
                if cand > cur || !pred.contains_key(v) {
                    dist.insert(v, cand);
                    pred.insert(v, u);
                }
            }
        }
    }

    // Reconstruct path ending at target. If target has no predecessor and
    // is not a source with self-path, still allow single-node path.
    let mut chain_ids: Vec<&str> = Vec::new();
    let mut cur = target_ev.event_id.as_str();
    let mut guard = 0usize;
    loop {
        chain_ids.push(cur);
        guard += 1;
        if guard > graph.event_ids.len() + 1 {
            return Err(AnalysisError::Cycle {
                event_id: cur.to_string(),
            });
        }
        match pred.get(cur) {
            Some(p) => cur = p,
            None => break,
        }
    }
    chain_ids.reverse();

    // If the target was unreachable from any other node, chain is [target]
    // only — still a trivial path, but mark partial/unavailable based on gaps.
    let hops: Vec<PathHop> = chain_ids
        .iter()
        .filter_map(|id| {
            by_id.get(id).map(|e| PathHop {
                event_id: e.event_id.clone(),
                name: e.name.clone(),
                timestamp_ns: e.timestamp_ns,
            })
        })
        .collect();

    let duration_ns = if hops.len() >= 2 {
        Some(hops[hops.len() - 1].timestamp_ns - hops[0].timestamp_ns)
    } else if hops.len() == 1 {
        Some(0)
    } else {
        None
    };

    let mut reasons = missing_queue_reasons(doc, graph);

    // Path that is only the target (no incoming edges used) while earlier
    // stages exist → incomplete evidence.
    if hops.len() <= 1 && doc.events.len() > 1 {
        reasons.push("path has no upstream explicit edges to target".into());
    }

    let confidence = if reasons.is_empty() {
        PathConfidence::Complete
    } else {
        PathConfidence::Partial
    };

    Ok(PathResult {
        objective,
        confidence,
        hops,
        duration_ns,
        reasons,
    })
}

fn find_target(doc: &TraceDocument, objective: Objective) -> Option<&Event> {
    let names = objective.target_names();
    // First matching event in document order (earliest terminal for turn).
    doc.events.iter().find(|e| names.contains(&e.name.as_str()))
}

/// Compute critical paths for all standard objectives.
pub fn critical_paths(doc: &TraceDocument) -> Result<Vec<PathResult>, AnalysisError> {
    let graph = build_graph(doc)?;
    let objectives = [
        Objective::Ttft,
        Objective::Ttfa,
        Objective::TimeToAudible,
        Objective::TurnCompletion,
    ];
    let mut out = Vec::with_capacity(objectives.len());
    for obj in objectives {
        out.push(critical_path_on_graph(doc, &graph, obj)?);
    }
    Ok(out)
}
