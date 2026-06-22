# Consumers

## What this module is

**Consumers** are downstream workflows that receive verified export \(z\) under declared purpose \(T\) (paper §4.2). **Assessors** are frozen scoring procedures that benchmark each released export on a held-out split — they never see raw observation \(x\).

v0.1.1 registers two consumer families:

| Family | Role | Primary implementation |
|--------|------|------------------------|
| **Frozen LLM utility consumer** | Headline \(U(T,z)\) via frozen prompts on export \(z\) | `qwen3:8b` (Ollama); alternate open-weight models for sensitivity |
| **Classical baselines** | Diagnostic sklearn/TF-IDF pipelines (not headline paper numbers) | `tier0_consumer.py` |

Headline utility scores are **not recomputed from live inference** in the default repro path. The repo commits an **evaluation registry** — pre-computed LLM predictions keyed by model, lattice condition, and event — so audits run instantly without Ollama or API cost.

### Paper ↔ code naming

The paper calls the headline assessor the **frozen `qwen3:8b` utility consumer** (§4.2, §6). In repo code and frozen outputs, the same consumer appears under legacy labels:

| Paper | Repo (code / committed artifacts) |
|-------|-------------------------------------|
| Frozen `qwen3:8b` utility consumer | `data/eval_cache/qwen3_8b/` |
| Headline \(U(T,z)\) scores | `metrics.json` → `conditions[*].tier1` |
| Sensitivity narrative | `outputs/pilot_v2/sensitivity_report.md` (“Tier-1” in title = this consumer) |

**Tier-1** in those artifacts is **not** separate jargon — it is the primary `qwen3:8b` consumer from the paper. Alternate open-weight models (`llama3.1:8b`, `gemma4:latest`) use the same prompt contracts under their own cache dirs.

## Paper connection

Maps to **§4.2 Registered Consumers and Policies** (consumer half) and Table registered-tasks.

## Current implementation

Code (module filenames use legacy `tier*` prefixes):

- `src/eval/tier0_consumer.py` — classical baselines
- `src/eval/tier1_consumer.py` — observability LLM consumer (`failure_mode`, `error_stage`)
- `src/eval/tier1_analytics_consumer.py` — analytics LLM consumer
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

### How the evaluation registry works

```text
Lattice export z  ──►  frozen LLM consumer prompt  ──►  prediction JSONL  ──►  metric (F1, etc.)
                              ▲
                              │
                    data/eval_cache/{model}/{condition}/predictions.jsonl
                    (committed at release — v0.1.1 primary: qwen3_8b)
```

- **`make eval`** loads observability caches from `data/eval_cache/` when present; scoring is deterministic given the same exports in `data/transformed/`.
- **`make eval-analytics`** uses `data/eval_cache_analytics/` the same way.
- **Cache miss** → study runner may attempt live Ollama inference (not required for v0.1.1 repro).
- **`make repro-smoke`** does not read caches; it validates committed `outputs/pilot_v2/metrics.json` only.

Inspect one row:

```bash
head -1 data/eval_cache/qwen3_8b/raw/predictions.jsonl | python -m json.tool
```

Outputs (see [Paper ↔ code naming](#paper--code-naming) above):

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

Frozen LLM utility consumers are benchmark instruments, not production model recommendations.
