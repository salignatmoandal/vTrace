//! vtrace-python — PyO3 bindings exposing the typed contract to Python.
//!
//! L2: may depend on vtrace-core and vtrace-analysis. Nothing below
//! L2 may depend on PyO3 (enforced by `cargo xtask layers`).
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
// PyO3 macros trigger clippy::useless_conversion on pyfunction return
// types. See https://github.com/PyO3/pyo3/issues/4828 (same as polars).
#![allow(clippy::useless_conversion)]

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use vtrace_analysis::critical_paths as analysis_critical_paths;
use vtrace_core::{parse_and_validate, Clock};
use vtrace_core::{ManualClock as CoreManualClock, MonotonicClock as CoreMonotonicClock};

/// A real monotonic clock backed by `std::time::Instant`.
///
/// `now_ns()` returns nanoseconds elapsed since creation. The domain
/// string identifies the clock so consumers can reject cross-domain
/// duration computation (spec 0004).
#[pyclass(name = "MonotonicClock", module = "vtrace")]
struct PyMonotonicClock {
    inner: CoreMonotonicClock,
}

#[pymethods]
impl PyMonotonicClock {
    #[new]
    fn new(domain: String) -> Self {
        Self {
            inner: CoreMonotonicClock::new(domain),
        }
    }

    /// Current time in nanoseconds within this clock's domain.
    fn now_ns(&self) -> i64 {
        self.inner.now_ns()
    }

    /// The name of this clock's domain.
    #[getter]
    fn domain(&self) -> &str {
        self.inner.domain()
    }
}

/// A deterministic manual clock for tests.
///
/// `now_ns()` returns the current value and advances by a fixed step.
#[pyclass(name = "ManualClock", module = "vtrace")]
struct PyManualClock {
    inner: CoreManualClock,
}

#[pymethods]
impl PyManualClock {
    #[new]
    #[pyo3(signature = (domain, start_ns=0, step_ns=1))]
    fn new(domain: String, start_ns: i64, step_ns: i64) -> Self {
        Self {
            inner: CoreManualClock::new(domain, start_ns, step_ns),
        }
    }

    /// Current time in nanoseconds; advances by step_ns on each call.
    fn now_ns(&self) -> i64 {
        self.inner.now_ns()
    }

    /// The name of this clock's domain.
    #[getter]
    fn domain(&self) -> &str {
        self.inner.domain()
    }

    /// Set the next timestamp without advancing. For test setup.
    fn set(&self, ns: i64) {
        self.inner.set(ns);
    }

    /// Advance the clock by one step and return the previous value.
    fn tick(&self) -> i64 {
        self.inner.now_ns()
    }
}

/// Validate a trace document (JSON string) against the structural
/// invariants. Raises `ValueError` on failure.
///
/// This is the Rust twin of `vtrace.validate.validate_document`.
/// Both check the same invariants against the same fixture.
#[pyfunction]
fn validate(json: &str) -> PyResult<()> {
    match parse_and_validate(json) {
        Ok(_) => Ok(()),
        Err(e) => Err(PyValueError::new_err(e.to_string())),
    }
}

/// Validate a trace document and return it as a dict.
/// Raises `ValueError` on failure.
#[pyfunction]
fn parse(json: &str) -> PyResult<PyObject> {
    let doc = parse_and_validate(json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let serialized =
        serde_json::to_string(&doc).map_err(|e| PyValueError::new_err(e.to_string()))?;
    Python::with_gil(|py| {
        let builtins = py.import_bound("builtins")?;
        let json_mod = py.import_bound("json")?;
        let result = json_mod.call_method1("loads", (serialized,))?;
        let _ = builtins; // suppress unused warning
        Ok(result.unbind())
    })
}

/// Compute per-objective critical paths (spec 0007).
///
/// Returns a list of path result dicts. Raises `ValueError` on a cycle
/// or cross-domain path. Missing edges yield `partial` / `unavailable`
/// — never a fabricated path (decision 0005).
#[pyfunction]
fn critical_paths(json: &str) -> PyResult<PyObject> {
    let doc = parse_and_validate(json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let paths = analysis_critical_paths(&doc).map_err(|e| PyValueError::new_err(e.to_string()))?;
    let serialized =
        serde_json::to_string(&paths).map_err(|e| PyValueError::new_err(e.to_string()))?;
    Python::with_gil(|py| {
        let json_mod = py.import_bound("json")?;
        let result = json_mod.call_method1("loads", (serialized,))?;
        Ok(result.unbind())
    })
}

/// The vTrace native extension module.
#[pymodule]
fn _vtrace(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_function(wrap_pyfunction!(critical_paths, m)?)?;
    m.add_class::<PyMonotonicClock>()?;
    m.add_class::<PyManualClock>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manual_clock_wraps_core() {
        let clock = PyManualClock {
            inner: CoreManualClock::new("manual:test", 100, 10),
        };
        assert_eq!(clock.now_ns(), 100);
        assert_eq!(clock.now_ns(), 110);
    }
}
