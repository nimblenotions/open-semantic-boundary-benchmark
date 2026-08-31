# Ta-5 cohort-utility protocol audit

This supporting audit compares historical mixed and export-symmetric cohort constructions with the assessor-symmetric construction used in the final CIKM 2026 protocol.

**Commit at audit start:** `641610d`  
**Outputs:** `outputs/post_acceptance_experiments/ta5_cohort_audit/`  
**Historical artifacts not modified:** `outputs/pilot_v2/`, `data/eval_cache_analytics/`

Assessor-symmetric scoring finished 2026-08-19T12:03Z (~5.4 h, 24,963 new train-side `qwen3:8b` calls into the audit cache only). Coverage is complete (2,777 train + 630 test predictions on all 9 conditions).

---

## 1. Historical mixed pipeline (Track A)

The mixed \(T_a\)-5 score stored in `outputs/pilot_v2` is `conditions.*.tier1_cohort.cohort_segment_macro_f1` from `eval/run_cohort_tier1.py` → `evaluate_cohort_from_tier1_predictions`. It is **not** the published protocol.

| Piece | Mixed construction |
|---|---|
| Target | `cohort_segment = logging_propensity + "_" + clinical_engagement` (9-way) |
| Metric | macro-F1 |
| Classifier | `RandomForestClassifier(n_estimators=50, class_weight="balanced", random_state=42)` + `DictVectorizer` |
| Split | whole-persona 70/10/20, seed 42. **Val unused.** Train 70 personas (9 classes), test 20 personas (**7 classes**; two missing) |
| Train \(X\) | `_persona_features` on **export \(z\)** |
| Test \(X\) | `_persona_features_from_predictions` on **test-only** Qwen analytics outputs (`medication_class`, `side_effect_signal`, `adherence_signal`) |
| Repro | Track A re-run matches the historical JSON to machine precision on all 9 conditions |

Logging propensity has **non-overlapping** event-count ranges (low 10–15, medium 25–40, high 60–100). `event_count` identifies the logging half of the target **exactly**, and is **identical across conditions** (same events, 3894 each).

### Train-side keys by family

Text / LLM (`raw`, bracket, tokenize, surrogate, llm_*): \(z\) is `{journal_text, assistant_text}`. Train vectors collapse to `event_count` plus **identically zero** `side_effect_rate` / `adherence_barrier_rate`.

`sem_coarse`: `event_count`, oracle `side_effect_rate`, `adherence_barrier_rate` (from `*_present` booleans). No `med_*` / `sym_*` / `time_*`.

`sem_medium` / `sem_fine`: those rates plus `med_*`, `sym_*`, and (medium only) `time_*`. **`sem_fine` oracle \(z\) contains `cohort_segment` and `engagement_trend`; `_persona_features` never reads them.**

### Test-side keys

Always: `event_count`, assessor `side_effect_rate`, `adherence_barrier_rate`, `med_*`. No `sym_*` / `time_*`.

### Schema mismatch (mixed Track A)

| Family | Train-only keys | Test-only keys dropped | Effect |
|---|---|---|---|
| Text / LLM | none | all `med_*` (~57–63% of test keys) | Train rates are constant 0, so RF never splits on them; test assessor rates are unused. **Effective model = event_count.** |
| `sem_coarse` | none | `med_*` (40%) | Rates aligned (oracle vs assessor); med dropped |
| `sem_medium` | `sym_*`, `time_*` (7/13 dims **always zero at test**) | none | Train-only compositional features become zeros at test |
| `sem_fine` | `sym_*` (no time in \(z\)) | none | same pattern, 40% of train dims zero at test |

Track B (`evaluate_cohort_tasks` / `cohort` in the historical JSON) is the **export/export** construction.

---

## 2–4. Condition-level results

Primary metric: `cohort_segment_macro_f1`.

| Condition | A mixed | B export/export | **C assessor/assessor** | Event-count only | B no count | C no count |
|---|---:|---:|---:|---:|---:|---:|
| raw | 0.389 | 0.389 | **0.187** | 0.389 | 0.014 | 0.126 |
| redact_bracket | 0.389 | 0.389 | **0.261** | 0.389 | 0.014 | 0.163 |
| redact_tokenize | 0.389 | 0.389 | **0.206** | 0.389 | 0.014 | 0.202 |
| redact_surrogate | 0.389 | 0.389 | **0.264** | 0.389 | 0.014 | 0.072 |
| redact_llm_substitute | 0.389 | 0.389 | **0.123** | 0.389 | 0.014 | 0.157 |
| redact_llm_rephrase | 0.389 | 0.389 | **0.259** | 0.389 | 0.014 | 0.037 |
| sem_coarse | 0.228 | 0.228 | **0.236** | 0.389 | 0.244 | 0.132 |
| sem_medium | 0.274 | 0.249 | **0.202** | 0.389 | 0.187 | 0.077 |
| sem_fine | 0.296 | 0.181 | **0.294** | 0.389 | 0.119 | 0.077 |

**All six text/LLM conditions on A/B are identical to the event-count-only baseline.** Track C breaks that tie: the 0.389 is gone once train and test both use Qwen aggregates.

Ranks (best → worst):

- Track A: six-way text/LLM tie 0.389, then fine 0.296, medium 0.274, coarse 0.228
- Track B: same text/LLM tie, then medium 0.249, coarse 0.228, fine 0.181
- **Track C: fine 0.294 > surrogate 0.264 > bracket 0.261 > llm_rephrase 0.259 > coarse 0.236 > tokenize 0.206 > medium 0.202 > raw 0.187 > llm_sub 0.123**
- B, no `event_count`: coarse > medium > fine ≫ all text

---

## 5. Operative selection and regret (other scores held fixed)

`TASK_BUNDLES` constraints are obs / med-class / composite / linkage / provenance. **None include \(u_{\text{cohort}}\).** Dual-purpose bundle is unaffected.

Risk-constrained \(T_a\)-5 winners at \(R_{\max}\in\{0.40,0.45,0.50,0.55\}\):

| Track | 0.40 | 0.45 | 0.50 | 0.55 |
|---|---|---|---|---|
| Mixed A | bracket | bracket | raw | raw |
| Track B | bracket | bracket | raw | raw |
| **Track C (published)** | bracket | **surrogate** | **surrogate** | **surrogate** |
| Track B, no `event_count` | coarse | coarse | coarse | coarse |

This table uses shared observability \(R\) for non-cohort columns. The published purpose-specific grid additionally makes analytics `sem_medium` infeasible at 0.50/0.55 (see `snapshot_track_c/table3_operative_grid.md`).

At \(R_{\max}=0.45\), mixed and export-symmetric scoring leave the cohort row/column on `redact_bracket`. Assessor-symmetric scoring moves both to `redact_surrogate`. Unconstrained Track C best is `sem_fine`, but fine is infeasible at these budgets, so risk-constrained winners stay in the text/redaction family.

Event-level purpose conflict at 0.45 (obs→bracket, med→surrogate, side/adherence→coarse) **survives**. Under assessor-symmetric scoring, cohort agrees with med-class on surrogate rather than independently preferring bracket. Mixed-path “cohort prefers raw at 0.50” does **not** hold under Track C.

---

## 6. Findings

**Q1. Mixed Track A bias?**  
**Scientifically unreliable for cross-condition comparison** of the intended construct, even though operative winners can be stable. Text conditions are an event-count classifier; semantic conditions are a small-\(n\) RF on extra features that *hurts* relative to event-count-only. That is not “how much cohort is in the export.” Schema mismatch further moves `sem_fine` (A 0.296 vs B 0.181 vs shared-keys 0.399).

**Q2. Does export/export preserve the longitudinal story?**  
Text vs semantic ordering is preserved (text 0.389 > all sem). `sem_medium` still trails raw (0.249 vs 0.389). **That gap is not a grain/composition story.** Medium has the same `event_count` as raw; the RF just uses oracle rates/`med_*`/`sym_*`/`time_*` and underperforms the event-count-only model. After removing `event_count`, semantic **beats** text, and coarse > medium > fine.

**Q3. Assessor/assessor?**  
**Does not preserve the mixed-path story.** Text 0.389 collapses (raw 0.187, llm_sub 0.123). Unconstrained best is `sem_fine` (0.294), not raw. `sem_medium` (0.202) is about the same as raw, not a distinctive grain failure. Absolute scores are all in a noisy 0.12–0.29 band on 20 personas.

**Q4. How much is `event_count`?**  
**100% of the mixed text/LLM \(T_a\)-5 (0.389).** Semantic scores are *lower* than this floor. The 0.389 is recovery of `logging_propensity` (non-overlapping count ranges) plus whatever engagement the RF guesses on 20 test personas.

**Q5. Removing `event_count`?**  
**Yes, ordering reverses.** Operative \(T_a\)-5 winner becomes `sem_coarse` at every listed \(R_{\max}\).

The published protocol uses the assessor-symmetric construction (Track C): both train and test cohort features are persona-level aggregates of assessor predictions.

---

## 7. Relation to the published protocol

Event-level tasks (\(T_o\)-1/2, \(T_a\)-1/2/3), token-versus-persona linkage, the event-level winner conflict at \(R_{\max}=0.45\), and the dual-purpose bundle test (no cohort constraint) do not depend on this cohort-scoring choice.

Under assessor-symmetric scoring, risk-constrained \(T_a\)-5 at \(R_{\max}\in\{0.45,0.50,0.55\}\) is `redact_surrogate` (~0.26), not mixed-path bracket/raw at 0.39. Absolute scores lie in a noisy 0.12–0.29 band on 20 test personas. The mixed-path grain-mismatch story (semantic arms destroying compositional signal) is not identified by this metric: those arms still have `event_count` and lose to an event-count-only baseline.

---

## 8. Reproducibility

```
outputs/post_acceptance_experiments/ta5_cohort_audit/
  run_manifest.json
  pipeline_reconstruction.json
  tracks_ab_controls.json
  condition_table.csv / .json
  ranks.json
  operative_impact.json
  track_c_estimate.json
  track_c_scores.json / track_c_inference.json
  cache_root/          # 2,777 train predictions × 9 conditions; frozen test cache unused for writes
```

Replay (no LLM):

```bash
.venv/bin/python eval/run_ta5_cohort_audit.py --skip-track-c
```

Assessor-symmetric scoring (does not write the historical eval cache):

```bash
.venv/bin/python eval/run_ta5_cohort_audit.py --run-track-c
```

`cohort_mode` labels: `mixed_frozen` | `export_symmetric` | `assessor_symmetric`. Feature modes: `all` | `event_count_only` | `no_event_count` | `shared`.

---

## Additional methodological caveats

1. **Target includes a feature that is condition-invariant and a deterministic function of a generator knob.** Comparing arms on this task mostly measures whether the RF uses `event_count`.
2. **\(n_{\text{test}}=20\) personas, 7 of 9 classes, macro-F1.** High sampling variance; 0.389 vs 0.274 is 20 labels.
3. **`sem_fine` already exports the label** (`cohort_segment` in oracle \(z\)) and the evaluator ignores it. A representation-level ceiling for fine is ~1.0 if that field were used — the opposite of the reported 0.30/0.18.
4. Historical JSON already stored export/export as `cohort` (raw coincidentally 0.389, same as mixed). `sem_medium`/`sem_fine` already differed (`cohort` 0.249/0.181 vs `tier1_cohort` 0.274/0.296); the mixed path reported `tier1_cohort`.
5. Train-side text rates are constant zero, so mixed A **cannot** use test-side Qwen rates for text arms. The “downstream consumer” story is not implemented on those arms.
6. Val split unused; no calibration of RF depth/`min_samples` despite \(p\) approaching \(n\) on medium/fine.
