//! vtrace-python — PyO3 bindings exposing `Clock` and `record()` to Python.
//!
//! SCAFFOLD ONLY (phase P1). L2: may depend on vtrace-core and
//! vtrace-analysis. Nothing below L2 may depend on PyO3 (enforced by
//! `cargo xtask layers`).
//!
//! FFI timestamp rule (spec 0001, spec 0004): timestamps cross the
//! boundary as `i64` ns + `clock_domain` string, never a raw `Instant`.
#![deny(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::unimplemented,
    clippy::todo,
    clippy::unreachable
)]
