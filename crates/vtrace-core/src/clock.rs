//! Clock abstraction — monotonic time with an explicit domain.
//!
//! See spec 0004. Durations are computed within a single clock domain;
//! cross-domain subtraction is a validation error. Timestamps cross
//! the FFI as `i64` ns + `clock_domain` string, never a raw `Instant`
//! (spec 0001, spec 0004).

use std::sync::atomic::{AtomicI64, Ordering};
use std::time::Instant;

/// A source of monotonic nanosecond timestamps within a named domain.
///
/// The domain string identifies the clock so that consumers can reject
/// cross-domain duration computation (spec 0004 invariant).
pub trait Clock {
    /// Current time in nanoseconds within this clock's domain.
    fn now_ns(&self) -> i64;

    /// The name of this clock's domain (e.g. `"mono:main"`, `"manual:turn-42"`).
    fn domain(&self) -> &str;
}

/// A real monotonic clock backed by `std::time::Instant`.
///
/// `now_ns()` returns nanoseconds elapsed since the clock was created.
/// If the system clock goes backwards (extremely rare), the last known
/// value is returned — we never panic (spec 0005: record must not panic).
pub struct MonotonicClock {
    domain: String,
    start: Instant,
    last_ns: AtomicI64,
}

impl MonotonicClock {
    /// Create a new monotonic clock with the given domain name.
    pub fn new(domain: impl Into<String>) -> Self {
        Self {
            domain: domain.into(),
            start: Instant::now(),
            last_ns: AtomicI64::new(0),
        }
    }
}

impl Clock for MonotonicClock {
    fn now_ns(&self) -> i64 {
        // Instant::now() is later than self.start (normal case).
        // checked_duration_since returns None only if the clock went
        // backwards; we return the last known value rather than panic.
        let elapsed = Instant::now().checked_duration_since(self.start);
        let ns = match elapsed {
            Some(dur) => dur.as_nanos() as i64,
            None => self.last_ns.load(Ordering::Relaxed),
        };
        self.last_ns.store(ns, Ordering::Relaxed);
        ns
    }

    fn domain(&self) -> &str {
        &self.domain
    }
}

/// A deterministic manual clock for tests.
///
/// `now_ns()` returns the current value and advances by a fixed step
/// (default 1 ns). Thread-safe via atomics so it can be shared across
/// producers in concurrency tests (spec 0008).
pub struct ManualClock {
    domain: String,
    next_ns: AtomicI64,
    step_ns: i64,
}

impl ManualClock {
    /// Create a manual clock starting at `start_ns`, advancing by
    /// `step_ns` on each call.
    pub fn new(domain: impl Into<String>, start_ns: i64, step_ns: i64) -> Self {
        Self {
            domain: domain.into(),
            next_ns: AtomicI64::new(start_ns),
            step_ns,
        }
    }

    /// Create a manual clock starting at 0, advancing by 1 ns per call.
    pub fn starting_at_zero(domain: impl Into<String>) -> Self {
        Self::new(domain, 0, 1)
    }

    /// Set the next timestamp without advancing. For test setup.
    pub fn set(&self, ns: i64) {
        self.next_ns.store(ns, Ordering::Relaxed);
    }
}

impl Clock for ManualClock {
    fn now_ns(&self) -> i64 {
        self.next_ns.fetch_add(self.step_ns, Ordering::Relaxed)
    }

    fn domain(&self) -> &str {
        &self.domain
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manual_clock_advances_by_step() {
        let clock = ManualClock::new("manual:test", 1000, 500);
        assert_eq!(clock.now_ns(), 1000);
        assert_eq!(clock.now_ns(), 1500);
        assert_eq!(clock.now_ns(), 2000);
    }

    #[test]
    fn manual_clock_domain() {
        let clock = ManualClock::starting_at_zero("manual:turn-1");
        assert_eq!(clock.domain(), "manual:turn-1");
    }

    #[test]
    fn monotonic_clock_is_non_decreasing() {
        let clock = MonotonicClock::new("mono:test");
        let a = clock.now_ns();
        let b = clock.now_ns();
        assert!(b >= a, "monotonic clock must not go backwards");
    }
}
