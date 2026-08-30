# Export lattice

> **CIKM numbers:** [`releases/cikm-2026/`](../../releases/cikm-2026/). Paths under `outputs/pilot_v2/` below are the pre-repair snapshot. Do not quote them as paper results.

## What this module is

The **export lattice** is a finite, frozen set of transform conditions \(\mathcal{C}\). Each condition materializes export \(z\) (and provenance \(r\) when applicable) from the same trusted observation \(x\).

v0.1.1 ships **nine primary conditions** (IDs are stable in configs and metrics JSON). Paper Table 2 uses a `red_` prefix where this repo uses `redact_`:

| This repo | Paper | Export rule |
|-----------|-------|-------------|
| `raw` | `raw` | Raw journal and assistant text |
| `redact_bracket` | `red_bracket` | Bracket placeholders (`[MEDICATION]`-style) |
| `redact_tokenize` | `red_tokenize` | Persona-scoped stable pseudonyms |
| `redact_surrogate` | `red_surrogate` | i2b2-style surrogate replacements |
| `redact_llm_substitute` | `red_llm_substitute` | LLM entity substitution |
| `redact_llm_rephrase` | `red_llm_rephrase` | LLM passage rewrite |
| `sem_coarse` | `sem_coarse` | Coarse semantic export (boolean slots) |
| `sem_medium` | `sem_medium` | Medium semantic export (typed task fields) |
| `sem_fine` | `sem_fine` | Fine semantic export (richer typed attributes) |

## Paper connection

The nine conditions in the CIKM paper (§3–§4). Paths: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

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
