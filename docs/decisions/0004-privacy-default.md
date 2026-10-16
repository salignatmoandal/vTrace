# Decision 0004 — Voice content excluded by default

- **Status:** Accepted
- **Date:** 2026-10-16
- **Related specs:** [spec 0003](../specs/0003-event-schema.md)
- **Replaces:** —

## Context

A voice profiler can, by accident, capture raw audio, transcriptions,
prompts, or model responses. These are sensitive data, and their capture
is unnecessary for latency analysis.

## Decision

By default, vTrace does not collect voice content: no raw audio, no
transcription, no prompt, no model response. An explicit flag would be
required later to authorize this capture; it is not in the MVP.

## Consequences

Traces are shareable without content leakage. The cost is reduced
visibility into content; acceptable, since vTrace measures durations,
not content.

## Alternatives

- **Capture enabled by default with opt-out.** Rejected: the safe
  default is no capture.

## Related specs

spec 0003 (event schema; non-sensitive `attributes`).
