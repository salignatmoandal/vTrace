# MCP tool usage policy — vTrace

This policy governs when an authoring agent (working *on* vTrace) may
reach for MCP tools. It does not describe vTrace's own MCP server,
which is deferred to P5/P6 (see `docs/roadmap.md`).

## Principles

- Prefer local file tools (Read, Grep, Glob) over network tools for
  anything inside the repo.
- Use an external MCP only when the information is genuinely outside
  the repo and cannot be obtained locally.
- Never invent measurements, traces, or benchmark results. An MCP
  that returns external data is evidence, not a substitute for running
  vTrace.
- Cite the source (URL, repo, file) for any external fact brought in.

## When to use which MCP

| MCP | Use for | Do not use for |
|---|---|---|
| `user-github` | Reading upstream repos (e.g. `huggingface/speech-to-speech` at P6), opening PRs, reading issues | Anything readable from the local checkout |
| `user-arxiv` | Citing prior art for a design decision | Replacing a benchmark (P5) |
| `user-firecrawl-mcp` | Auditing an external codebase or docs not on local disk | Re-reading a repo already cloned |
| `user-hf-mcp-server` | Finding models/datasets for the P6 integration, or a reference pipeline | Claiming a model's latency without running it |

## Hard rules

1. No performance number from an MCP. Performance is measured by
   vTrace in P5, never fetched.
2. No causal claim sourced from an MCP. Causality comes from explicit
   edges (decision 0005), never from external narrative.
3. An external fact used in a spec/decision must be cited to its
   source.
4. vTrace's own MCP server (when it exists) will confine file access
   with read-root/write-root flags, borrowed from the SoundCraft
   model.

## vTrace's own MCP server (deferred)

Not built in P0 or P1. When built (P5/P6), it will:

- Expose `vtrace report`, `vtrace validate`, and trace inspection over
  MCP.
- Confine file access to explicit read/write roots.
- Be a consumer of the trace document (decision 0006), not a source of
  truth.
