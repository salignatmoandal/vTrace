//! vtrace-core — schema, clock, bounded collector, lifecycle, document.
//!
//! The typed contract for vTrace. This crate defines the event model,
//! clock abstraction, trace document, and validator. It depends on no
//! workspace crate (L0). The trace document (JSON, validatable against
//! `docs/schema/trace.schema.json`) is the contract between the
//! collector, the CLI, and future consumers (decision 0006).
//!
//! Contracts implemented here:
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

mod clock;
mod document;
mod error;
mod event;
mod validate;

pub use clock::{Clock, ManualClock, MonotonicClock};
pub use document::{Completeness, TraceDocument};
pub use error::ValidationError;
pub use event::{Component, Event};
pub use validate::validate;
