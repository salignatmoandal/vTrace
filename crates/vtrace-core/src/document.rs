//! Trace document — the top-level contract.
//!
//! See spec 0003 and `docs/schema/trace.schema.json`. The document is
//! the contract between the collector, the CLI, and future consumers
//! (decision 0006). It is validatable, versioned, and self-describing
//! about loss (`completeness`, `dropped_critical`).

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::event::Event;

/// Whether the trace is complete or has lost critical events.
///
/// `partial` means at least one critical event was dropped. This is
/// never silent (invariant 9: visible loss).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Completeness {
    Complete,
    Partial,
}

/// The trace document — the exported contract.
///
/// Consumers depend on this JSON structure, not on internal collector
/// objects (decision 0006).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TraceDocument {
    pub schema_version: String,
    pub clock_domains: Vec<String>,
    pub completeness: Completeness,
    pub dropped_total: i64,
    pub dropped_critical: i64,
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub session_metadata: HashMap<String, serde_json::Value>,
    pub events: Vec<Event>,
}
