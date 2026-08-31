# Medication adherence (CIKM 2026 study)

This folder is the **published evaluation** in this artifact: the synthetic medication-adherence pilot in the CIKM 2026 paper.

The corpus, purpose-conditioned exports, and frozen assessor caches live under [`../../data/`](../../data/README.md). Protocol and figures: [`../../releases/cikm-2026/`](../../releases/cikm-2026/).

## What is included

| Asset | Location |
|-------|----------|
| Corpus and split | `data/raw/`, `data/ground_truth/` (100 personas, seed 42, 630 test events) |
| Nine lattice conditions | `data/transformed/` (observability), `data/transformed_analytics/` (analytics) |
| Frozen protocol and figures | [`../../releases/cikm-2026/`](../../releases/cikm-2026/) |

## Verify

```bash
make repro-cikm-2026
```

That command uses committed artifacts. It does not regenerate LLM transformations or assessor inference.

Regenerating the corpus or lattice is development work, not reproduction of the published study. See [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Protocol map

- [`../../open-sbb/synthetic_pilot_data/README.md`](../../open-sbb/synthetic_pilot_data/README.md)
- [`../../open-sbb/export_lattice/README.md`](../../open-sbb/export_lattice/README.md)

## Not claimed

Synthetic personas are not real patients. Oracle semantic exports are representation upper bounds, not production extraction estimates or clinical recommendations.
