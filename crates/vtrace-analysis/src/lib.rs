//! vtrace-analysis — explicit-edge dependency graph, per-objective paths.
//!
//! L1: may depend on `vtrace-core`. Reads a trace document and never
//! mutates it. No causal edge is inferred from timestamp proximity
//! (decision 0005): only `parent_span_id`, same-span lifecycle pairs,
//! `queued`/`started`, and cancellation pairs count as edges.
//!
//! Spec 0007. Graph is computed on demand; the document remains the
//! contract (decision 0006).

#![deny(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::unimplemented,
    clippy::todo,
    clippy::unreachable
)]

mod error;
mod graph;
mod path;

pub use error::AnalysisError;
pub use graph::{build_graph, Edge, EdgeKind, Graph};
pub use path::{critical_path, critical_paths, Objective, PathConfidence, PathHop, PathResult};

#[cfg(test)]
mod tests;
