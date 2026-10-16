# vTrace — single entry point for all agents and CI.
# `just ci` is the one command an agent runs before declaring a task done.

default:
    @just --list

# Everything: Rust gates + Python gates + schema validation.
ci:
    cargo xtask ci
    cd py-vtrace && uv run ruff check .
    cd py-vtrace && uv run ruff format --check .
    cd py-vtrace && uv run pyright
    cd py-vtrace && uv run pytest -q
    just validate

# Rust only: fmt, clippy -D warnings, test, layers, schema-validate.
rust-ci:
    cargo xtask ci

# Python only.
py-ci:
    cd py-vtrace && uv run ruff check .
    cd py-vtrace && uv run ruff format --check .
    cd py-vtrace && uv run pyright
    cd py-vtrace && uv run pytest -q

# Enforce the Rust layer table (no upward deps, no Python/UI below L2).
layers:
    cargo xtask layers

# Regenerate derived docs from the schema.
docgen:
    cargo xtask docgen

# Validate the acceptance fixture against the trace schema.
validate:
    cd py-vtrace && uv run python -m vtrace.validate ../fixtures/traces/one-turn.json

# Run the CLI report on the acceptance fixture (demonstrable deliverable).
report:
    cd py-vtrace && uv run vtrace report ../fixtures/traces/one-turn.json
