//! Event model — the typed version of the trace document contract.
//!
//! See spec 0003 and `docs/schema/trace.schema.json`. Field names use
//! snake_case to match the JSON schema exactly.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Pipeline component that emitted the event.
///
/// Matches the `component` enum in the JSON schema. Adding a variant
/// is a contract change (decision 0002).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Component {
    Vad,
    Stt,
    Llm,
    Tts,
    Playback,
    Turn,
    Collector,
}

/// A single observed event in a voice turn.
///
/// Required fields are non-optional; optional fields use `Option`.
/// `sequence` is a producer-local tie-breaker, **not** causality
/// (spec 0003, decision 0005).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Event {
    pub schema_version: String,
    pub event_id: String,
    pub session_id: String,
    pub turn_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub response_id: Option<String>,
    pub span_id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_span_id: Option<String>,
    pub component: Component,
    pub name: String,
    pub timestamp_ns: i64,
    pub clock_domain: String,
    pub sequence: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub producer_id: Option<String>,
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub attributes: HashMap<String, serde_json::Value>,
}
