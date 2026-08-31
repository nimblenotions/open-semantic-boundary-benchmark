# Consumers

**Consumers** are registered downstream workflows that receive a verified export under a declared purpose. **Assessors** are frozen scoring procedures that evaluate that export on the held-out split; they never see the raw observation \(x\).

This artifact registers two purposes:

| Purpose | Role | Policy | Assessor |
|---------|------|--------|----------|
| Observability \(T_o\) | Triage-style monitoring | `data/policies/obs_policy_v1.json` | Frozen `qwen3:8b` prompt in `src/eval/tier1_consumer.py` (`PROMPT_VERSION = "triage_v1"`) |
| Analytics \(T_a\) | Pharmacologic analytics | `data/policies/analytics_policy_v1.json` | Frozen `qwen3:8b` prompt in `src/eval/tier1_analytics_consumer.py` (`PROMPT_VERSION = "analytics_triage_v1"`) |

The observability prompt predicts `failure_mode` and `error_stage`. The analytics prompt predicts medication class, side-effect, and adherence from the fixed vocabularies. Predictions are scored against simulator ground truth. The model and prompts proxy registered consumers; they are not the boundary transformer.

The same `qwen3:8b` tag is also used for LLM lattice conditions. That is a separate protocol choice from the utility assessor.

## Implementation

- `src/eval/tier1_consumer.py` — observability utility assessor
- `src/eval/tier1_analytics_consumer.py` — analytics utility assessor
- `src/eval/observability_task.py`, `src/eval/analytics_task.py`, `src/eval/analytics_cohort.py`
- Vocabularies: `data/schemas/obs_labels_v1.json`, `data/ground_truth/labels.jsonl`

Committed assessor predictions (not live inference):

- `data/eval_cache/qwen3_8b/`
- `data/eval_cache_analytics/qwen3_8b/`

Classical sklearn pipelines in `src/eval/tier0_consumer.py` are diagnostics. They are not the published utility numbers.

Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md). Task list: [`../utility_assessment/README.md`](../utility_assessment/README.md).

## Verify

```bash
make repro-cikm-2026
head -1 data/eval_cache/qwen3_8b/raw/predictions.jsonl | python -m json.tool
```

`make repro-cikm-2026` uses committed artifacts and does not call Ollama. Re-running live assessor inference is development, not CIKM verification.

## Extend

New purpose or assessor: [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

Frozen LLM assessors are benchmark instruments, not production model recommendations.
