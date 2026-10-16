//! Causal DAG from explicit edges only (spec 0007, decision 0005).
//!
//! No edge is inferred from timestamp proximity. Sources:
//! - `parent_span_id` → parent span's started (or earliest) event
//! - same-span lifecycle chain (`started` → `first_*` → terminal)
//! - `*.queued` → `*.started` (same span)
//! - `cancel.requested` → `*.cancelled` / `turn.cancelled`

use std::collections::{HashMap, HashSet, VecDeque};

use vtrace_core::{Event, TraceDocument};

use crate::error::AnalysisError;

/// Kind of an explicit causal edge.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EdgeKind {
    Parent,
    SameSpanLifecycle,
    QueueHandoff,
    Cancellation,
}

/// A directed edge: `from` must precede `to` on a dependency path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Edge {
    pub from: String,
    pub to: String,
    pub kind: EdgeKind,
}

/// Explicit-edge DAG over event_ids.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Graph {
    pub event_ids: Vec<String>,
    pub edges: Vec<Edge>,
}

/// Build the causal graph from a validated trace document.
pub fn build_graph(doc: &TraceDocument) -> Result<Graph, AnalysisError> {
    let events = &doc.events;
    let mut edges: Vec<Edge> = Vec::new();

    let by_id: HashMap<&str, &Event> = events.iter().map(|e| (e.event_id.as_str(), e)).collect();
    let mut by_span: HashMap<&str, Vec<&Event>> = HashMap::new();
    for ev in events {
        by_span.entry(ev.span_id.as_str()).or_default().push(ev);
    }
    for list in by_span.values_mut() {
        list.sort_by_key(|e| (e.timestamp_ns, e.sequence));
    }

    // --- Parent edges: parent span started → child span entry ----------
    // Only *.queued / *.started carry a parent edge. Intermediate events
    // (first_token, completed, …) depend on the span entry via the
    // same-span lifecycle chain — otherwise every child event would get
    // a direct edge from the parent and short-circuit the path.
    for ev in events {
        let Some(ref parent_span) = ev.parent_span_id else {
            continue;
        };
        if !(ev.name.ends_with(".started") || ev.name.ends_with(".queued")) {
            continue;
        }
        let Some(parent_events) = by_span.get(parent_span.as_str()) else {
            continue;
        };
        // Prefer *.started on the parent span; else earliest event.
        let parent_anchor = parent_events
            .iter()
            .find(|e| e.name.ends_with(".started"))
            .or_else(|| parent_events.first());
        if let Some(anchor) = parent_anchor {
            if anchor.event_id != ev.event_id {
                edges.push(Edge {
                    from: anchor.event_id.clone(),
                    to: ev.event_id.clone(),
                    kind: EdgeKind::Parent,
                });
            }
        }
    }

    // --- Same-span lifecycle + queued→started --------------------------
    for list in by_span.values() {
        let lifecycle: Vec<&Event> = list
            .iter()
            .copied()
            .filter(|e| is_lifecycle_event(e))
            .collect();
        for window in lifecycle.windows(2) {
            let a = window[0];
            let b = window[1];
            let kind = if a.name.ends_with(".queued") && b.name.ends_with(".started") {
                EdgeKind::QueueHandoff
            } else {
                EdgeKind::SameSpanLifecycle
            };
            edges.push(Edge {
                from: a.event_id.clone(),
                to: b.event_id.clone(),
                kind,
            });
        }
    }

    // --- Cancellation: cancel.requested → *.cancelled ------------------
    let cancel_req: Vec<&Event> = events
        .iter()
        .filter(|e| e.name == "cancel.requested")
        .collect();
    let cancelled: Vec<&Event> = events
        .iter()
        .filter(|e| e.name.ends_with(".cancelled") || e.name == "turn.cancelled")
        .collect();
    for req in &cancel_req {
        for term in &cancelled {
            if (term.timestamp_ns, term.sequence) >= (req.timestamp_ns, req.sequence) {
                edges.push(Edge {
                    from: req.event_id.clone(),
                    to: term.event_id.clone(),
                    kind: EdgeKind::Cancellation,
                });
            }
        }
    }

    // Deduplicate identical edges.
    edges.sort_by(|a, b| (&a.from, &a.to).cmp(&(&b.from, &b.to)));
    edges.dedup_by(|a, b| a.from == b.from && a.to == b.to);

    let event_ids: Vec<String> = events.iter().map(|e| e.event_id.clone()).collect();

    // Cycle check.
    detect_cycle(&event_ids, &edges)?;

    // Sanity: every edge endpoint exists.
    for e in &edges {
        if !by_id.contains_key(e.from.as_str()) || !by_id.contains_key(e.to.as_str()) {
            // Should not happen with our construction; skip rather than panic.
            continue;
        }
    }

    Ok(Graph { event_ids, edges })
}

fn is_lifecycle_event(ev: &Event) -> bool {
    let n = ev.name.as_str();
    n.ends_with(".queued")
        || n.ends_with(".started")
        || n.ends_with(".first_token")
        || n.ends_with(".first_audio")
        || n.ends_with(".completed")
        || n.ends_with(".failed")
        || n.ends_with(".cancelled")
        || n == "turn.timed_out"
}

fn detect_cycle(event_ids: &[String], edges: &[Edge]) -> Result<(), AnalysisError> {
    let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
    for id in event_ids {
        adj.entry(id.as_str()).or_default();
    }
    for e in edges {
        adj.entry(e.from.as_str()).or_default().push(e.to.as_str());
    }

    // 0 = white, 1 = gray, 2 = black
    let mut color: HashMap<&str, u8> = HashMap::new();
    for id in event_ids {
        color.insert(id.as_str(), 0);
    }

    fn dfs<'a>(
        u: &'a str,
        adj: &HashMap<&str, Vec<&'a str>>,
        color: &mut HashMap<&'a str, u8>,
    ) -> Result<(), AnalysisError> {
        color.insert(u, 1);
        if let Some(neis) = adj.get(u) {
            for &v in neis {
                match color.get(v).copied().unwrap_or(0) {
                    1 => {
                        return Err(AnalysisError::Cycle {
                            event_id: v.to_string(),
                        });
                    }
                    0 => dfs(v, adj, color)?,
                    _ => {}
                }
            }
        }
        color.insert(u, 2);
        Ok(())
    }

    for id in event_ids {
        if color.get(id.as_str()).copied().unwrap_or(0) == 0 {
            dfs(id.as_str(), &adj, &mut color)?;
        }
    }
    Ok(())
}

/// Adjacency list for longest-path search.
pub(crate) fn adjacency(graph: &Graph) -> HashMap<&str, Vec<&str>> {
    let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
    for id in &graph.event_ids {
        adj.entry(id.as_str()).or_default();
    }
    for e in &graph.edges {
        adj.entry(e.from.as_str()).or_default().push(e.to.as_str());
    }
    adj
}

/// Topological order (Kahn). Graph is acyclic (checked at build).
pub(crate) fn topo_order(graph: &Graph) -> Vec<&str> {
    let mut indeg: HashMap<&str, usize> = HashMap::new();
    for id in &graph.event_ids {
        indeg.insert(id.as_str(), 0);
    }
    for e in &graph.edges {
        *indeg.entry(e.to.as_str()).or_insert(0) += 1;
    }
    let adj = adjacency(graph);
    let mut q: VecDeque<&str> = indeg
        .iter()
        .filter(|(_, &d)| d == 0)
        .map(|(&id, _)| id)
        .collect();
    let mut order = Vec::new();
    let mut indeg_mut = indeg;
    while let Some(u) = q.pop_front() {
        order.push(u);
        if let Some(neis) = adj.get(u) {
            for &v in neis {
                if let Some(d) = indeg_mut.get_mut(v) {
                    *d = d.saturating_sub(1);
                    if *d == 0 {
                        q.push_back(v);
                    }
                }
            }
        }
    }
    order
}

/// Collect missing queue-handoff reasons between pipeline stages.
pub(crate) fn missing_queue_reasons(doc: &TraceDocument, graph: &Graph) -> Vec<String> {
    let names: HashSet<&str> = doc.events.iter().map(|e| e.name.as_str()).collect();
    let has_queue_edge = graph.edges.iter().any(|e| e.kind == EdgeKind::QueueHandoff);

    let mut reasons = Vec::new();
    // Stage pairs that need an explicit queue edge for a complete path.
    let pairs = [
        ("stt.completed", "llm.started", "stt → llm"),
        ("llm.first_token", "tts.started", "llm → tts"),
        ("llm.completed", "tts.started", "llm → tts"),
        ("tts.first_audio", "playback.started", "tts → playback"),
        ("tts.completed", "playback.started", "tts → playback"),
    ];
    for (up, down, label) in pairs {
        if names.contains(up) && names.contains(down) && !has_queue_edge {
            // No *.queued / queue.* edge anywhere — flag the gap.
            let already = reasons.iter().any(|r: &String| r.contains(label));
            if !already {
                reasons.push(format!("missing queue edge ({label})"));
            }
        }
    }
    // If document has no queued events at all but has multi-stage pipeline:
    let has_queued = doc.events.iter().any(|e| e.name.ends_with(".queued"));
    if !has_queued
        && names.contains("stt.started")
        && names.contains("llm.started")
        && reasons.is_empty()
    {
        reasons.push("missing queue edge (no *.queued events)".into());
    }
    reasons
}
