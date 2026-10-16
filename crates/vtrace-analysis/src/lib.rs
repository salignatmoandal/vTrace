//! vtrace-analysis — explicit-edge dependency graph, per-objective paths.
//!
//! SCAFFOLD ONLY (phase P3). Reads a trace document and never mutates
//! it. No causal edge is inferred from timestamp proximity (decision 0005):
//! only `parent_span_id` and explicit pairs count as edges.
#![deny(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::unimplemented,
    clippy::todo,
    clippy::unreachable
)]

// L1: may depend on vtrace-core. Enforced by `cargo xtask layers`.
