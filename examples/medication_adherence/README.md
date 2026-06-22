# Medication adherence pilot (shipped)

This is the **frozen v0.1.1 pilot** described in the paper: synthetic medication-adherence journaling with dual-purpose observability + analytics evaluation.

## What is included

| Asset | Location |
|-------|----------|
| Corpus + split | `data/raw/`, `data/ground_truth/` (100 personas, seed 42, 630 test events) |
| Nine export conditions | `data/transformed/`, `data/transformed_analytics/` |
| Published metrics | `outputs/pilot_v2/metrics.json`, `analytics_metrics.json` |
| Paper figures | `outputs/pilot_v2/figures/` |

## Reproduce

```bash
make repro-smoke
make figures
```

Full pipeline regen (optional):

```bash
make pipeline CONFIG=configs/pilot_v0.1.1.yaml
```

## Protocol map

See [`../open-sbb/synthetic_pilot_data/README.md`](../open-sbb/synthetic_pilot_data/README.md) and [`../open-sbb/export_lattice/README.md`](../open-sbb/export_lattice/README.md).

## Not claimed

Synthetic personas are not real patients. Oracle semantic exports are upper bounds, not clinical deployment recommendations.
