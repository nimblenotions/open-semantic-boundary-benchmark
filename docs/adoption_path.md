# Adoption path

Structured onboarding for reviewers, practitioners, and contributors.

## 1-minute path

1. Read [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md) — framework vs Open SBB.
2. Read the [root README](../README.md) — what this repo measures.
3. Skim [`open-sbb/README.md`](../open-sbb/README.md) — protocol flow.
4. Run `make repro-smoke` after `uv pip install -e ".[dev]"`.

## 5-minute path

1. Complete 1-minute path.
2. Read [`examples/README.md`](../examples/README.md) — when to use Open SBB.
3. Inspect headline numbers:

```bash
# observability T_o-1 macro-F1 (JSON key tier1 in metrics.json)
python -c "import json; print(json.load(open('outputs/pilot_v2/metrics.json'))['conditions']['raw']['tier1']['failure_mode_macro_f1'])"
```

## 30-minute path

1. Complete 5-minute path.
2. Read [`open-sbb/export_lattice/README.md`](../open-sbb/export_lattice/README.md) and [`open-sbb/utility_assessment/README.md`](../open-sbb/utility_assessment/README.md).
3. Inspect one lattice arm:

```bash
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

4. Open `outputs/pilot_v2/figures/utility_matrix_heatmap.png` (if present) or regenerate with `make figures`.

## 1-hour path

1. Complete 30-minute path.
2. Read [`examples/bring_your_own/README.md`](../examples/bring_your_own/README.md).
3. Compare `data/policies/obs_policy_v1.json` with [`examples/provenance/`](../examples/provenance/).
4. Run `make eval` (uses cached LLM consumer predictions; no Ollama if caches present).

## Contributor path

1. Read [`extension_points.md`](extension_points.md) and [`repo_map.md`](repo_map.md).
2. Run `make test`.
3. Follow [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Reviewer path (paper ↔ repo)

1. [`paper_to_repo.md`](paper_to_repo.md)
2. `make repro-smoke` + spot-check §4 module READMEs under `open-sbb/`

## Strategic framing

| Layer | Role |
|-------|------|
| **Paper** | Establishes the idea and pilot evidence |
| **This repo** | Establishes the **benchmark** — run, reproduce, extend |
| **Product / deployment** | Future commercial stack (out of scope here) |

Goal: a practitioner can say *“I can test my own semantic exports here.”*
