# Operative selection

## What this module is

**Operative selection** applies Pareto deprioritization, risk-constrained winners (\(R \leq R_{\max}\)), and dual-purpose bundles. **Cross-purpose regret** quantifies utility loss when one purpose's winner is reused for another.

## Paper connection

Maps to **§4.5 Operative Selection** and Figure cross-purpose regret matrix.

## Current implementation

Code:

- `src/eval/operative_selection.py` — Pareto, risk-constrained, bundle selectors
- `src/eval/dual_purpose.py` — dual-purpose bundles; `plot_operative_regret_focal()` (purpose regret at \(R_{\max}\))
- `src/eval/advisor_figures.py` — `build_cross_purpose_regret_matrix()`, `plot_cross_purpose_regret_matrix()`, `write_cross_purpose_regret_table()`
- `src/eval/operative_figures.py` — operative figure helpers
- `eval/run_operative_selection.py` — CLI entrypoint
- `eval/run_figures.py` — invokes regret matrix generation

Data:

- `outputs/pilot_v2/metrics.json` (input)
- `outputs/pilot_v2/analytics_metrics.json` (input)

Outputs:

- `outputs/pilot_v2/operative_selection/operative_selection.json`
- `outputs/pilot_v2/operative_selection/risk_constrained.csv`
- `outputs/pilot_v2/operative_selection/operative_selection_report.md`
- `outputs/pilot_v2/operative_selection/operative_boundary_bundle_v0.json`
- `outputs/pilot_v2/figures/cross_purpose_regret_matrix.png`
- `outputs/pilot_v2/figures/tables/cross_purpose_regret_matrix.csv`
- `outputs/pilot_v2/figures/tables/cross_purpose_regret_meta.json`
- `outputs/pilot_v2/figures/operative_regret_focal.png`
- `outputs/pilot_v2/dual_purpose_snapshot.json`

## Reproduce

```bash
make repro-smoke
make operative-selection CONFIG=configs/pilot_v0.1.1.yaml
make figures CONFIG=configs/pilot_v0.1.1.yaml
```

Verify cross-purpose regret artifact:

```bash
test -f outputs/pilot_v2/figures/cross_purpose_regret_matrix.png && echo OK
head -3 outputs/pilot_v2/figures/tables/cross_purpose_regret_matrix.csv
```

## Extend

New selector rule → `src/eval/operative_selection.py`. New regret visualization → `src/eval/advisor_figures.py` or `dual_purpose.py`.

## Not claimed

Automated selectors are exploratory; purpose-split exports may be the honest deployment path.
