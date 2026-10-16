//! vtrace-core — schema, clock, bounded collector, lifecycle, document.
//!
//! SCAFFOLD ONLY. This crate is the harness skeleton for P1 (decision 0001).
//! It compiles and carries the lint wall, but contains no production
//! logic yet. P1 implementation is gated on P0 acceptance
//! (AGENTS.md: no production code before P0 is accepted).
//!
//! The contract this crate will implement lives in:
//!   - spec 0003 (event model), spec 0004 (clock), spec 0006 (lifecycle)
//!   - docs/schema/trace.schema.json (the machine-readable contract)
//!   - decision 0006 (the trace document is the contract)
#![deny(
    clippy::unwrap_used,
    clippy::expect_used,
    clippy::panic,
    clippy::unimplemented,
    clippy::todo,
    clippy::unreachable
)]

// L0: depends on no workspace crate. Enforced by `cargo xtask layers`.

#[cfg(test)]
mod scaffold_tests {
    //! Placeholder so `cargo test` has something to run in the skeleton.
    #[test]
    fn crate_compiles() {
        // When P1 lands, this is replaced by real collector tests using a
        // manual clock (spec 0004) asserting completeness and ordering.
        let scaffold_ready = true;
        assert!(scaffold_ready);
    }
}
