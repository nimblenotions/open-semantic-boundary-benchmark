# Export lattice

## What this module is

The **export lattice** is a finite, frozen set of transform conditions \(\mathcal{C}\). Each condition materializes export \(z\) (and provenance \(r\) when applicable) from the same trusted observation \(x\).

v0.1.1 ships **nine primary conditions** (IDs are stable in configs and metrics JSON):

| Condition ID | Plain meaning |
|--------------|---------------|
| `raw` | No redaction — full observation text |
| `redact_bracket` | Bracket-style span redaction |
| `redact_tokenize` | Token replacement / pseudonymization |
| `redact_surrogate` | Surrogate text replacement |
| `redact_llm_substitute` | LLM substitution (cached oracle run) |
| `redact_llm_rephrase` | LLM rephrase (cached oracle run) |
| `sem_coarse` | Coarse semantic JSON export |
| `sem_medium` | Medium-granularity semantic JSON |
| `sem_fine` | Fine-grained semantic JSON |

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

Lattice conditions are benchmark comparators, not vendor reproductions. Semantic conditions are representation upper bounds, not learned extractor SOTA.
