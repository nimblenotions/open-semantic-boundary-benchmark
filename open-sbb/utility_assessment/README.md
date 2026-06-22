# Utility assessment

## What this module is

**Utility assessment** — `assess_utility(T, z)` → \(U(T,z)\) on the held-out split.

- **Observability:** `failure_mode` macro-F1 (triage task)
- **Analytics:** medication-class macro-F1 (+ tasks 2–5 in full matrix)

## Paper connection

Maps to **§4.4 Utility and Linkage Assessment** (utility half) and headline results tables.

## Current implementation

Code:

- `src/eval/observability_task.py`
- `src/eval/analytics_task.py`
- `src/eval/study.py`
- `src/eval/sensitivity_merge.py`
- `eval/run_obs_study.py`
- `eval/run_analytics_study.py`
- `eval/run_bootstrap_cis.py`
- `eval/run_figures.py` — utility matrix plots
- `src/eval/figures.py`

Data:

- `data/transformed/` (reads exports)
- `data/eval_cache/` and `data/eval_cache_analytics/` (frozen LLM consumer predictions)

Outputs:

- `outputs/pilot_v2/metrics.json`
- `outputs/pilot_v2/analytics_metrics.json`
- `outputs/pilot_v2/figures/utility_matrix_heatmap.png`
- `outputs/pilot_v2/figures/tables/utility_matrix.csv`
- `outputs/pilot_v2/bootstrap_cis/bootstrap_cis.tex`
- `outputs/pilot_v2/sensitivity_report.md` — consumer sensitivity across open-weight models ([`../consumers/README.md`](../consumers/README.md#paper--code-naming))

## Reproduce

```bash
make repro-smoke
make eval CONFIG=configs/pilot_v0.1.1.yaml
make eval-analytics CONFIG=configs/pilot_v0.1.1.yaml
make bootstrap-cis CONFIG=configs/pilot_v0.1.1.yaml
```

Headline spot-check (`raw` observability failure_mode macro-F1 ≈ 0.63; JSON key `tier1` in metrics):

```bash
python -c "import json; print(json.load(open('outputs/pilot_v2/metrics.json'))['conditions']['raw']['tier1']['failure_mode_macro_f1'])"
```

## Extend

New task → `src/eval/*_task.py` + policies/consumers. See [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

High utility on `sem_medium` reflects structured oracle fields, not inference from redacted prose alone.
