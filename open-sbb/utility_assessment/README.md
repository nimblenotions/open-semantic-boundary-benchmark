# Utility assessment

Utility \(U\) is scored on the purpose-conditioned export \(z_{c,T}\) for a **registered downstream task**. Purpose \(T\) and task are not the same object: tasks under one purpose share \(z_{c,T}\) and its linkage \(R(z_{c,T})\), but retain task-specific utility.

The published tasks (paper Table 1) are:

| Task | Metric | Grain |
|------|--------|-------|
| \(T_o\)-1 Failure mode | macro-F1 | event |
| \(T_o\)-2 Error stage | accuracy | event |
| \(T_a\)-1 Medication class | macro-F1 | event |
| \(T_a\)-2 Side-effect signal | macro-F1 | event |
| \(T_a\)-3 Adherence barrier | macro-F1 | event |
| \(T_a\)-5 Behavioural cohort | macro-F1 | persona (30-day) |

Table 3 reports risk-constrained winners for \(T_o\)-1, \(T_a\)-1, \(T_a\)-2, \(T_a\)-3, and \(T_a\)-5. There is no \(T_a\)-4 in the published table.

Event-level tasks are scored on all 630 held-out events. For \(T_a\)-5, medication-class, side-effect, and adherence **assessor** predictions are aggregated per persona; a random forest then predicts the behavioural cohort (logging \(\times\) engagement) for the 20 test personas, trained on the same assessor aggregates from the train split (**assessor-symmetric**).

The frozen utility assessor is `qwen3:8b` (temperature 0, seed 42). It receives \(z_{c,T}\) only, never raw \(x\). See [`../consumers/README.md`](../consumers/README.md).

## Implementation

- `src/eval/observability_task.py`
- `src/eval/analytics_task.py`
- `src/eval/analytics_cohort.py` — \(T_a\)-5 assessor-symmetric cohort evaluation
- `src/eval/tier1_consumer.py` (`triage_v1`)
- `src/eval/tier1_analytics_consumer.py` (`analytics_triage_v1`)

Frozen predictions: `data/eval_cache/qwen3_8b/`, `data/eval_cache_analytics/qwen3_8b/`.

Published utility presentation: Figure 3 under [`../../releases/cikm-2026/`](../../releases/cikm-2026/). Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Verify

```bash
make repro-cikm-2026
```

That command checks the frozen protocol and the focal Table 3 utilities at \(R_{\max}=0.45\). It does not re-run the LLM assessor.

## Extend

New task: [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

High utility on semantic conditions reflects structured simulator fields, not extraction from redacted prose. Utility scores are not a ranking of production sanitizers.
