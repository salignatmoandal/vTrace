//! Trace document validation — structural invariants beyond the schema.
//!
//! See spec 0003 and `vtrace/validate.py` (the Python twin). Both
//! validators check the same invariants against the same fixture, so
//! the contract has two implementations and one truth.

use std::collections::HashMap;

use crate::document::TraceDocument;
use crate::error::ValidationError;

/// Validate a trace document against the structural invariants.
///
/// Checks invariants that the JSON schema alone cannot express:
/// 1. Every event's `clock_domain` is listed in `clock_domains`.
/// 2. Within each domain, events are ordered by `(timestamp_ns, sequence)`.
/// 3. `completeness: complete` is inconsistent with `dropped_critical > 0`.
/// 4. All events share the document's `schema_version`.
pub fn validate(doc: &TraceDocument) -> Result<(), ValidationError> {
    let known_domains: HashMap<&str, ()> =
        doc.clock_domains.iter().map(|d| (d.as_str(), ())).collect();

    // Invariant 3: completeness vs dropped_critical.
    if doc.completeness == crate::document::Completeness::Complete && doc.dropped_critical > 0 {
        return Err(ValidationError::InconsistentCompleteness {
            dropped: doc.dropped_critical,
        });
    }

    // Group events by domain, preserving document order.
    let mut by_domain: HashMap<&str, Vec<&crate::event::Event>> = HashMap::new();

    for ev in &doc.events {
        // Invariant 1: clock_domain must be declared.
        if !known_domains.contains_key(ev.clock_domain.as_str()) {
            return Err(ValidationError::UnknownClockDomain {
                event_id: ev.event_id.clone(),
                clock_domain: ev.clock_domain.clone(),
            });
        }

        // Invariant 4: schema_version must match the document.
        if ev.schema_version != doc.schema_version {
            return Err(ValidationError::SchemaVersionMismatch {
                document_version: doc.schema_version.clone(),
                event_id: ev.event_id.clone(),
                event_version: ev.schema_version.clone(),
            });
        }

        by_domain
            .entry(ev.clock_domain.as_str())
            .or_default()
            .push(ev);
    }

    // Invariant 2: within each domain, (timestamp_ns, sequence) is
    // non-decreasing. sequence breaks ties, not causality (spec 0003).
    for (domain, evs) in &by_domain {
        for i in 1..evs.len() {
            let prev = evs[i - 1];
            let curr = evs[i];
            if (curr.timestamp_ns, curr.sequence) < (prev.timestamp_ns, prev.sequence) {
                return Err(ValidationError::OrderingViolation {
                    domain: domain.to_string(),
                    index: i,
                });
            }
        }
    }

    Ok(())
}

/// Parse a JSON string into a `TraceDocument` and validate it.
///
/// Convenience wrapper: deserialize then `validate`.
#[allow(dead_code)] // Used by vtrace-python bindings and CLI (P1-2/P1-3).
pub fn parse_and_validate(json: &str) -> Result<TraceDocument, ValidationError> {
    let doc: TraceDocument = serde_json::from_str(json)?;
    validate(&doc)?;
    Ok(doc)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::document::Completeness;
    use crate::event::{Component, Event};

    fn valid_doc() -> TraceDocument {
        TraceDocument {
            schema_version: "1.0".to_string(),
            clock_domains: vec!["manual:test".to_string()],
            completeness: Completeness::Complete,
            dropped_total: 0,
            dropped_critical: 0,
            session_metadata: HashMap::new(),
            events: vec![
                Event {
                    schema_version: "1.0".into(),
                    event_id: "e1".into(),
                    session_id: "s1".into(),
                    turn_id: "t1".into(),
                    response_id: None,
                    span_id: "sp1".into(),
                    parent_span_id: None,
                    component: Component::Turn,
                    name: "turn.started".into(),
                    timestamp_ns: 0,
                    clock_domain: "manual:test".into(),
                    sequence: 0,
                    attributes: HashMap::new(),
                },
                Event {
                    schema_version: "1.0".into(),
                    event_id: "e2".into(),
                    session_id: "s1".into(),
                    turn_id: "t1".into(),
                    response_id: None,
                    span_id: "sp1".into(),
                    parent_span_id: None,
                    component: Component::Turn,
                    name: "turn.completed".into(),
                    timestamp_ns: 100,
                    clock_domain: "manual:test".into(),
                    sequence: 1,
                    attributes: HashMap::new(),
                },
            ],
        }
    }

    #[test]
    fn valid_document_passes() {
        let doc = valid_doc();
        assert!(validate(&doc).is_ok());
    }

    #[test]
    fn unknown_clock_domain_rejected() {
        let mut doc = valid_doc();
        doc.events[0].clock_domain = "unknown:domain".into();
        let err = validate(&doc);
        assert!(err.is_err());
    }

    #[test]
    fn ordering_violation_rejected() {
        let mut doc = valid_doc();
        // Swap timestamps: second event earlier than first.
        doc.events[1].timestamp_ns = -1;
        assert!(validate(&doc).is_err());
    }

    #[test]
    fn inconsistent_completeness_rejected() {
        let mut doc = valid_doc();
        doc.dropped_critical = 1;
        // completeness is Complete, dropped_critical > 0 => error.
        assert!(validate(&doc).is_err());
    }

    #[test]
    fn schema_version_mismatch_rejected() {
        let mut doc = valid_doc();
        doc.events[0].schema_version = "2.0".into();
        assert!(validate(&doc).is_err());
    }

    #[test]
    fn fixture_json_parses_and_validates() {
        let json = include_str!("../../../fixtures/traces/one-turn.json");
        let result = parse_and_validate(json);
        assert!(
            result.is_ok(),
            "fixture must parse and validate: {:?}",
            result.err()
        );
        if let Ok(doc) = result {
            assert_eq!(doc.events.len(), 9);
            assert_eq!(doc.completeness, Completeness::Complete);
        }
    }
}
