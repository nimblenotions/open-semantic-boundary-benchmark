# Acceptance checklist — adoption-first documentation pass

Use this list before tagging **Open SBB v0.1.1** or exporting the public repo.

## Reviewer path

- [ ] Read paper **§4.5 Operative Selection** → open [`open-sbb/operative_selection/README.md`](../open-sbb/operative_selection/README.md)
- [ ] Instantly find cross-purpose regret implementation:
  - `src/eval/advisor_figures.py` — `build_cross_purpose_regret_matrix()`
  - `src/eval/dual_purpose.py` — `plot_operative_regret_focal()`
  - `outputs/pilot_v2/figures/cross_purpose_regret_matrix.png`

## Linkage path (§4.4)

- [ ] Open [`open-sbb/linkage_assessment/README.md`](../open-sbb/linkage_assessment/README.md)
- [ ] Find persona top-1, attribute F1, longitudinal AUC in:
  - `src/eval/adversary_trial4.py`
  - `outputs/pilot_v2/metrics.json` → `conditions[*].trial4_adversary`
  - `outputs/pilot_v2/figures/linkage_decomposition.png`

## Repro trust (clean sandbox)

- [ ] Fresh clone + `uv pip install -e ".[dev]"` (or `pip install -e ".[dev]"`)
- [ ] `make repro-smoke` exits 0 **without Ollama, GPU, or network**
- [ ] Output includes: `repro-smoke: OK`

```bash
make repro-smoke
```

## Code stability (documentation pass)

- [ ] **No Python package moves** under `open-sbb/*/src/` (not implemented v0.1.1)
- [ ] Core layout unchanged: `src/`, `eval/`, `data/`, `outputs/`, `tests/`
- [ ] Documentation-only changes in `open-sbb/`, `examples/`, `docs/`, root `README.md`

To verify no unintended `src/` edits since a baseline:

```bash
git diff --stat -- src/ tests/
```

## Adopter path

- [ ] Root README → `open-sbb/README.md` → module README in < 2 minutes
- [ ] [`examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) maps paper Figure 1 fields to `z` / `r`
- [ ] [`docs/adoption_path.md`](adoption_path.md) covers 1 min / 5 min / 30 min paths

## Naming alias documented

- [ ] `outputs/pilot_v2/` documented as **Open SBB v0.1.1 published run**
- [ ] `configs/pilot_v0.1.1.yaml` documented as primary config

## Strategic framing

| Layer | Role |
|-------|------|
| Paper | Establishes the idea |
| This repo | Establishes the **benchmark** |
| Product | Future deployment (out of scope) |

Goal: *"I can test my own semantic exports here."*
