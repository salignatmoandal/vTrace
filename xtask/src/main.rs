//! `cargo xtask <ci|layers|docgen|validate>` — repository gates.
//!
//! Adapted from the SoundCraft xtask pattern: one entry point that proves
//! the whole repo is correct. `just ci` shells out to this plus the
//! Python gates.

use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn cargo(args: &[&str]) -> Result<(), String> {
    let st = Command::new(std::env::var("CARGO").unwrap_or_else(|_| "cargo".into()))
        .args(args)
        .current_dir(root())
        .status()
        .map_err(|e| e.to_string())?;
    if st.success() {
        Ok(())
    } else {
        Err(format!("cargo {} failed", args.join(" ")))
    }
}

/// Layer table: crate name → layer. xtask and apps are exempt.
const LAYERS: &[(&str, u8)] = &[
    ("vtrace-core", 0),
    ("vtrace-analysis", 1),
    ("vtrace-python", 2),
];

/// Crates that pull in Python/PyO3 or a UI toolkit. Nothing below L2 may
/// depend on these.
const PYTHON_CRATES: &[&str] = &["pyo3", "pyo3-build-config", "pyo3-ffi"];
const EXEMPT: &[&str] = &["xtask", "vtrace-cli"];

fn layers() -> Result<(), String> {
    let out = Command::new("cargo")
        .args(["metadata", "--format-version", "1", "--no-deps"])
        .current_dir(root())
        .output()
        .map_err(|e| e.to_string())?;
    let v: serde_json::Value = serde_json::from_slice(&out.stdout).map_err(|e| e.to_string())?;
    let mut problems = Vec::new();
    for p in v["packages"].as_array().cloned().unwrap_or_default() {
        let name = p["name"].as_str().unwrap_or("").to_string();
        if EXEMPT.contains(&name.as_str()) {
            continue;
        }
        let Some(&(_, layer)) = LAYERS.iter().find(|(n, _)| *n == name.as_str()) else {
            problems.push(format!("{name}: not registered in xtask LAYERS"));
            continue;
        };
        for d in p["dependencies"].as_array().cloned().unwrap_or_default() {
            let dn = d["name"].as_str().unwrap_or("");
            let kind = d["kind"].as_str().unwrap_or("normal");
            if PYTHON_CRATES.contains(&dn) && layer < 2 && kind != "dev" {
                problems.push(format!("{name} (L{layer}) depends on Python crate {dn}"));
            }
            if let Some(&(_, dl)) = LAYERS.iter().find(|(n, _)| *n == dn) {
                if dl > layer && kind != "dev" {
                    problems.push(format!("{name} (L{layer}) depends upward on {dn} (L{dl})"));
                }
            }
        }
    }
    if problems.is_empty() {
        println!("layers: ok");
        Ok(())
    } else {
        Err(problems.join("\n"))
    }
}

fn validate() -> Result<(), String> {
    // Validate the acceptance fixture against the JSON schema.
    // Delegates to the Python validator so there is one source of truth.
    let fixture = root().join("fixtures/traces/one-turn.json");
    if !fixture.exists() {
        // No fixture yet (pre-P1). Not a failure, just nothing to check.
        println!("validate: no fixture yet (skipped)");
        return Ok(());
    }
    let py_dir = root().join("py-vtrace");
    if !py_dir.exists() {
        println!("validate: py-vtrace not found (skipped)");
        return Ok(());
    }
    let st = Command::new("uv")
        .args([
            "run",
            "python",
            "-m",
            "vtrace.validate",
            fixture.to_str().unwrap_or(""),
        ])
        .current_dir(py_dir)
        .status()
        .map_err(|e| e.to_string())?;
    if st.success() {
        Ok(())
    } else {
        Err("vtrace.validate failed".into())
    }
}

fn docgen() -> Result<(), String> {
    // Placeholder: regenerate derived docs from the schema when they exist.
    println!("docgen: nothing to generate yet (skipped)");
    Ok(())
}

fn ci() -> Result<(), String> {
    let steps: Vec<(&str, Box<dyn Fn() -> Result<(), String>>)> = vec![
        (
            "fmt",
            Box::new(|| cargo(&["fmt", "--all", "--", "--check"])),
        ),
        (
            "clippy",
            Box::new(|| {
                cargo(&[
                    "clippy",
                    "--workspace",
                    "--all-targets",
                    "--",
                    "-D",
                    "warnings",
                ])
            }),
        ),
        (
            "test",
            Box::new(|| cargo(&["test", "--workspace", "--exclude", "vtrace-python"])),
        ),
        ("layers", Box::new(layers)),
        ("validate", Box::new(validate)),
    ];
    let mut summary = Vec::new();
    for (name, f) in &steps {
        match f() {
            Ok(()) => summary.push(format!("ok    {name}")),
            Err(e) => {
                summary.push(format!("FAIL  {name}"));
                println!("{}", summary.join("\n"));
                return Err(e);
            }
        }
    }
    println!("{}", summary.join("\n"));
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let r = match args.first().map(String::as_str) {
        Some("ci") => ci(),
        Some("layers") => layers(),
        Some("validate") => validate(),
        Some("docgen") => docgen(),
        _ => Err("usage: cargo xtask <ci|layers|validate|docgen>".into()),
    };
    match r {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("xtask: {e}");
            ExitCode::FAILURE
        }
    }
}
