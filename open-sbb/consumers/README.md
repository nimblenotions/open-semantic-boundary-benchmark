# Consumers

## What this module is

**Consumers** emulate downstream workflows on released export \(z\). **Assessors** are frozen scoring procedures: Tier-0 (sklearn/TF-IDF) and Tier-1 (LLM prompts, `qwen3:8b` primary).

## Paper connection

Maps to **§4.2 Registered Consumers and Policies** (consumer half) and Table registered-tasks.

## Current implementation

Code:

- `src/eval/tier0_consumer.py`
- `src/eval/tier1_consumer.py` — observability triage (`failure_mode`, `error_stage`)
- `src/eval/tier1_analytics_consumer.py` — analytics tasks
- `src/eval/observability_task.py`
- `src/eval/analytics_task.py`
- `src/eval/analytics_cohort.py`
- `eval/run_obs_study.py`
- `eval/run_analytics_study.py`
- `eval/run_cohort_tier1.py`

Data:

- `data/eval_cache/qwen3_8b/raw/predictions.jsonl` (and per-condition dirs)
- `data/eval_cache/qwen3_8b/redact_bracket/predictions.jsonl`
- `data/eval_cache_analytics/qwen3_8b/sem_coarse/predictions.jsonl`
- `data/eval_cache/llama3.1_8b/` — sensitivity models
- `data/eval_cache/gemma4_latest/` — sensitivity models

Outputs:

- `outputs/pilot_v2/metrics.json` → `conditions[*].tier1`
- `outputs/pilot_v2/analytics_metrics.json` → `conditions[*].tier1`
- `outputs/pilot_v2/sensitivity_report.md`

## Reproduce

```bash
make repro-smoke
make eval CONFIG=configs/pilot_v0.1.1.yaml
make eval-analytics CONFIG=configs/pilot_v0.1.1.yaml
```

## Extend

New task → add prompt/vocab in `src/eval/` + hook in `eval/run_*_study.py`.

## Not claimed

Tier-1 consumers are frozen benchmark instruments, not production model recommendations.
