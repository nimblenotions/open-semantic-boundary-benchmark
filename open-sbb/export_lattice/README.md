# Export lattice

## What this module is

The **export lattice** is a finite, frozen set of transform conditions \(\mathcal{C}\). Each condition materializes export \(z\) (and provenance \(r\) when applicable) from the same trusted observation \(x\).

v0.1.1 ships **nine primary arms**: `raw`, `redact_bracket`, `redact_tokenize`, `redact_surrogate`, `redact_llm_substitute`, `redact_llm_rephrase`, `sem_coarse`, `sem_medium`, `sem_fine`.

## Paper connection

Maps to **§4.1 Export Lattice** (Table: export-lattice).

## Current implementation

Code:

- `src/transform/run_transforms.py` — materialize observability lattice
- `src/transform/run_analytics_transforms.py` — analytics-purpose lattice
- `src/transform/redact.py`, `tokenize.py`, `surrogate.py`, `semantic_map.py`, `llm_sanitize.py`
- `src/transform/lattice.py` — condition registry
- `eval/run_obs_study.py` — reads committed transforms for scoring

Data:

- `data/transformed/raw/events.jsonl` … `data/transformed/sem_fine/events.jsonl`
- `data/transformed_analytics/raw/events.jsonl` … (parallel analytics arms)
- `data/llm_transform_cache/redact_llm_substitute/cache.jsonl`
- `data/llm_transform_cache/redact_llm_rephrase/cache.jsonl`

Outputs:

- Per-condition scores in `outputs/pilot_v2/metrics.json` → `conditions[*]`
- Per-condition analytics scores in `outputs/pilot_v2/analytics_metrics.json`

## Reproduce

```bash
make repro-smoke
make transform CONFIG=configs/pilot_v0.1.1.yaml
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

## Extend

Add condition ID in `configs/pilot_v0.1.1.yaml` → implement in `src/transform/` → materialize under `data/transformed/{condition}/`. See [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

Lattice arms are benchmark comparators, not vendor reproductions. Semantic arms are representation upper bounds, not learned extractor SOTA.
