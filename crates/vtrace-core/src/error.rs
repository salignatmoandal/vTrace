//! Validation errors for the trace document contract.
//!
//! Errors are returned, never panicked (spec 0005, the `#![deny]` wall).

use thiserror::Error;

/// A violation of the trace document contract.
#[derive(Debug, Clone, PartialEq, Error)]
pub enum ValidationError {
    #[error("schema_version mismatch: document says {document_version}, event {event_id} says {event_version}")]
    SchemaVersionMismatch {
        document_version: String,
        event_id: String,
        event_version: String,
    },

    #[error("event {event_id} uses clock_domain {clock_domain:?} not listed in clock_domains")]
    UnknownClockDomain {
        event_id: String,
        clock_domain: String,
    },

    #[error(
        "events in domain {domain:?} are not in (timestamp_ns, sequence) order at index {index}"
    )]
    OrderingViolation { domain: String, index: usize },

    #[error("dropped_critical is {dropped} but completeness is complete")]
    InconsistentCompleteness { dropped: i64 },

    #[error("JSON error: {0}")]
    Json(String),
}

impl From<serde_json::Error> for ValidationError {
    fn from(e: serde_json::Error) -> Self {
        ValidationError::Json(e.to_string())
    }
}
