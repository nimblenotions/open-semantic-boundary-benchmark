# Adoption path

Structured onboarding for reviewers, practitioners, and contributors.

Time labels below are **realistic wall-clock estimates** for someone new to the repo (clone, venv, reading, one command). Skimming is faster; understanding the protocol takes longer.

## Quick repro (~15–30 min)

**Goal:** verify the frozen pilot matches published headline metrics.

1. Clone the repo and create a venv (`uv venv`, `uv pip install -e ".[dev]"`) — **~5–10 min** (depends on network and clone size).
2. Skim [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md) and the [root README](../README.md) — **~10 min**.
3. Run `make repro-smoke` — **seconds** (no Ollama). Checks observability **and** analytics headline **tier1** F1 plus linkage **R(z)** against the paper table.

Optional: skim [`open-sbb/README.md`](../open-sbb/README.md) for protocol flow — add **~10 min**.

## Paper numbers spot-check (~30–45 min)

1. Complete quick repro path.
2. Read [`examples/README.md`](../examples/README.md) — **~10 min**.
3. Inspect headline numbers (or trust `make repro-smoke` from the step above):

```bash
# observability failure_mode macro-F1 (JSON key tier1 in metrics.json)
python -c "import json; print(json.load(open('outputs/pilot_v2/metrics.json'))['conditions']['raw']['tier1']['failure_mode_macro_f1'])"
```

4. Optional: open pre-committed figures under `outputs/pilot_v2/figures/` — **~5 min**.

## Understand the protocol (~1–2 hours)

1. Complete paper numbers spot-check.
2. Read [`open-sbb/export_lattice/README.md`](../open-sbb/export_lattice/README.md) and [`open-sbb/utility_assessment/README.md`](../open-sbb/utility_assessment/README.md) — **~30–45 min**.
3. Inspect one export condition:

```bash
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

4. Browse `outputs/pilot_v2/figures/utility_matrix_heatmap.png` (committed) or regenerate with `make figures` — **~5–15 min** if regenerating.

## Rescore the committed pilot (~2–3 hours total)

For early enthusiasts who want to **run assessors**, not just read frozen outputs.

1. Complete understand-the-protocol path.
2. Read [`examples/provenance/`](../examples/provenance/README.md) — `(z, r)` shape — **~15 min**.
3. Run rescoring on cached LLM consumer predictions (no Ollama if caches present). **Both commands** needed for the full paper utility table:

```bash
make eval CONFIG=configs/pilot_v0.1.1.yaml          # observability lattice — typically a few minutes
make eval-analytics CONFIG=configs/pilot_v0.1.1.yaml
```

4. **Optional / advanced:** [`examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) — manual BYO on pilot labels (**YMMV**; productized path is v0.2). Add **hours to days** depending on your export tooling.

## Contributor path (~half day first time)

1. Read [`extension_points.md`](extension_points.md) and [`repo_map.md`](repo_map.md) — **~30 min**.
2. Run `make test` and `make lint` — **~1–2 min** after install.
3. Follow [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Reviewer path (paper ↔ repo) (~30–60 min)

1. [`paper_to_repo.md`](paper_to_repo.md) — **~20–30 min**.
2. `make repro-smoke` + spot-check §4 module READMEs under `open-sbb/` — **~15–30 min**.

## Strategic framing

| Layer | Role |
|-------|------|
| **Paper** | Establishes the idea and pilot evidence (companion preprint submitted; ID pending) |
| **This repo** | Establishes the **benchmark** — run, reproduce, extend |
| **Product / deployment** | Future commercial stack (out of scope here) |

Goal for v0.1.1: reproduce the frozen pilot and understand the protocol. Goal for v0.2+: *“I can test my own semantic exports here”* with less manual wiring.

> **Early development — YMMV** outside the committed pilot and headline metrics.
