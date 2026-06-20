# Agent observability (conceptual)

## Use case

Tool-using agents produce **traces** (planner steps, tool I/O, failures) that observability vendors need for triage — without exporting raw user content or secrets.

Open SBB registers **evaluation** (\(T_e\)) and **agent-trace** (\(T_{ag}\)) consumer slots on the same API; **v0.1.1 scores observability \(T_o\) and analytics \(T_a\) only** on the medication pilot.

## What v0.1.1 provides today

- Observability tasks \(T_o\)-1/2 on journal-like exports — see shipped pilot
- Protocol hooks for future agent trace schema in `data/schemas/`

## v0.2 direction (planned)

- **SBB-Agent** slice: tool-call traces, multi-hop provenance
- Example lattice arms for trace redaction vs semantic summary

## Start from shipped pilot

```bash
make repro-smoke
open-sbb/consumers/README.md
```

## Not claimed

This folder is a **roadmap placeholder**, not a second frozen benchmark in v0.1.1.
