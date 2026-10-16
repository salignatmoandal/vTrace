//! Analysis errors — distinct from validation errors.

use thiserror::Error;

/// Errors produced while building or querying the causal graph.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum AnalysisError {
    #[error("cycle detected involving event {event_id}")]
    Cycle { event_id: String },

    #[error("cross-domain path: {from_domain} → {to_domain}")]
    CrossDomain {
        from_domain: String,
        to_domain: String,
    },
}
