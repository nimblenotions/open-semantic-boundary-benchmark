# Purpose-specific linkage audit

**Question.** What happens if linkage is evaluated on the same purpose-specific export that is scored for utility, rather than pairing purpose-specific \(U(T,z_{c,T})\) with observability-only \(R(z_{c,T_o})\)?

**Status.** Supporting audit for the final CIKM 2026 protocol. The published protocol adopts purpose-specific linkage \(R(z_{c,T})\); this report records the audit that established its material effects.

**Commit at run.** `985295c`  
**Outputs.** `outputs/post_acceptance_experiments/purpose_specific_linkage/`  
**Historical artifacts not modified.** `outputs/pilot_v2/`, policies, schemas, transforms, utility caches.

**Protocol.** Train-only character n-gram TF-IDF (`char_wb`, 1–3, max 5,000 features), fitted on training export strings only, applied unchanged to held-out exports. Same Trial4 adversaries as the observability instrument (attribute LR, persona leave-one-out cosine top-1, longitudinal pair AUC). Combined

\[
R(z)=\frac{R_{\mathrm{persona}}+R_{\mathrm{attribute}}+R_{\mathrm{longitudinal}}}{3}.
\]

Token recovery is reported separately and is **not** a fourth term in \(R\).

**Utility.** Frozen Qwen scores reused. No new inference. \(T_a\)-5 uses the published assessor-symmetric construction, not mixed export-train / assessor-test scoring.

**Schema JSON note.** The first Trial4 dump wrote empty `ana_only_fields` because of a set-difference typo (`ana_k - ana_k`). That field was regenerated from the frozen exports without rerunning Trial4. The file is `semantic_schemas.json`.

---

## 1. Experimental question

For each lattice condition \(c\) and purpose \(T\), evaluate \((U(T,z_{c,T}), R(z_{c,T}))\).

Compare train-only observability linkage \(R(z_{c,T_o})\) with analytics-surface evaluation \(R(z_{c,T_a})\).

The question is whether the distinction is **material**. The published protocol uses purpose-specific \(R(z_{c,T})\); the measurements below record where the two surfaces diverge.

---

## 2. Frozen instrument

Confirmed in `instrument.json` and `identity.json`.

| Quantity | Expected (frozen) | Observed |
|---|---:|---:|
| Synthetic corpus events \(W\) | 3,894 | 3,894 |
| Train events (persona 70/10/20, seed 42) | 2,777 | 2,777 |
| Val events | — | 487 |
| Held-out test events | 630 | 630 |
| Test personas | 20 | 20 |
| Lattice conditions | 9 | 9 |
| Event-ID alignment `transformed/{c}` ↔ `transformed_analytics/{c}` | equal | equal on all 9 (`symmetric_diff = 0`) |

TF-IDF / adversary / combined-\(R\) / provenance gate are the existing Trial4 implementations. The only intended difference is the released representation supplied to the adversary: \(z_{c,T_o}\) vs \(z_{c,T_a}\).

Train-only vs frozen **transductive** observability \(R\) is small (largest \(|\Delta|\): `redact_tokenize` \(-0.010\), `redact_surrogate` \(+0.008\)). It does **not** change 0.40/0.45 feasibility relative to the frozen observability table.

`instrument_counts_match: true`.

---

## 3. Text-condition sanity check (positive control)

The six raw / redaction / LLM conditions are supposed to copy the same released text across purposes. They do.

For every text arm (`raw`, `redact_bracket`, `redact_tokenize`, `redact_surrogate`, `redact_llm_substitute`, `redact_llm_rephrase`):

- \(z\) is **byte-for-byte identical** across 3,894 events (`z_byte_identical: true`).
- Trial4 canonical embedding strings are identical (`embed_text_identical: true`).
- Provenance \(r\) is **not** identical: `consumer_id` and `purpose_id` differ. That is expected and is **not** an input to Trial4 text.
- Train-only linkage is **identical** on all four channels, including token recovery (`text_linkage_identical: true`, \(\Delta R = 0\)).

**Control check.** Text-arm linkage matched. Semantic \(\Delta R\) can be interpreted as a payload difference, not as a silent protocol bug.

---

## 4. Semantic-condition payload audit (descriptive)

No fields were removed. No policies or transforms were changed. `cohort_segment` remains in analytics `sem_fine`.

### `sem_coarse`

| | Fields |
|---|---|
| Observability | `adherence_barrier`, `risk_level`, `side_effect` |
| Analytics | `adherence_friction_present`, `risk_band`, `side_effect_present` |
| Common names | *(none — renamed boolean/band schema)* |
| Persona/attr flags | none of the flagged keys |

Disjoint names, aligned semantics. Combined \(\Delta R = +0.004\) (longitudinal 0.499 → 0.511). Not material.

### `sem_medium`

| | Fields |
|---|---|
| Common | `medication_class`, `symptom_categories` |
| Observability-only | `error_stage`, `failure_mode`, `input_semantic_type`, `policy_action` |
| Analytics-only | `adherence_signal`, `side_effect_signal`, `time_bucket` |
| Flags | `failure_mode`, `medication_class`, `symptom_categories`, **`time_bucket`** |

Analytics medium adds a time bucket and drops observability failure-mode fields. This is the condition whose linkage **moves**.

### `sem_fine`

| | Fields |
|---|---|
| Observability-only | `failure_mode`, `occupation_sector`, `specific_medication`, `symptoms` |
| Analytics-only | `adherence_signal`, **`cohort_segment`**, `engagement_trend`, `medication_class`, `side_effect_signal`, `symptom_categories` |
| Common names | *(none)* |
| Flags | `cohort_segment`, `engagement_trend`, `failure_mode`, `medication_class`, `occupation_sector`, `specific_medication`, `symptoms`, `symptom_categories` |

Analytics fine uniquely releases `cohort_segment` (and `engagement_trend`). Observability fine uniquely releases occupation / specific-medication / symptom strings that Trial4's **attribute** heads are defined on.

**Channel mix, left as measured.** Analytics `sem_fine` **attribute** F1 *falls* (0.843 → 0.600) while persona *rises* (0.641 → 0.808) and longitudinal *rises* (0.773 → 0.876). Combined \(R\) barely moves (\(+0.009\)). The adversary was **not** retargeted onto `cohort_segment`; that would have been a protocol change. The drop is consistent with scoring observability-contracted attribute heads against an analytics JSON that does not contain those fields.

---

## 5. Primary linkage comparison

Train-only TF-IDF. Combined \(R = \mathrm{mean}(R_{\mathrm{persona}}, R_{\mathrm{attr}}, R_{\mathrm{long}})\). Source: `linkage_comparison.csv`.

| Condition | \(R_{\mathrm{pers}}^{\mathrm{obs}}\) | \(R_{\mathrm{pers}}^{\mathrm{ana}}\) | \(R_{\mathrm{attr}}^{\mathrm{obs}}\) | \(R_{\mathrm{attr}}^{\mathrm{ana}}\) | \(R_{\mathrm{long}}^{\mathrm{obs}}\) | \(R_{\mathrm{long}}^{\mathrm{ana}}\) | \(R^{\mathrm{obs}}\) | \(R^{\mathrm{ana}}\) | \(\Delta R\) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| raw | 0.324 | 0.324 | 0.561 | 0.561 | 0.565 | 0.565 | 0.483 | 0.483 | 0 |
| redact_bracket | 0.054 | 0.054 | 0.490 | 0.490 | 0.526 | 0.526 | 0.357 | 0.357 | 0 |
| redact_tokenize | 0.837 | 0.837 | 0.463 | 0.463 | 0.657 | 0.657 | 0.652 | 0.652 | 0 |
| redact_surrogate | 0.216 | 0.216 | 0.518 | 0.518 | 0.561 | 0.561 | 0.432 | 0.432 | 0 |
| sem_coarse | 0.027 | 0.027 | 0.402 | 0.402 | 0.499 | 0.511 | 0.310 | 0.314 | +0.004 |
| **sem_medium** | **0.167** | **0.489** | 0.606 | 0.598 | 0.687 | 0.749 | **0.487** | **0.612** | **+0.125** |
| sem_fine | 0.641 | 0.808 | 0.843 | 0.600 | 0.773 | 0.876 | 0.752 | 0.762 | +0.009 |
| redact_llm_substitute | 0.527 | 0.527 | 0.470 | 0.470 | 0.584 | 0.584 | 0.527 | 0.527 | 0 |
| redact_llm_rephrase | 0.576 | 0.576 | 0.474 | 0.474 | 0.567 | 0.567 | 0.539 | 0.539 | 0 |

### Token recovery (separate)

| Condition | Token obs | Token ana |
|---|---:|---:|
| raw | 1.000 | 1.000 |
| redact_bracket | 0.033 | 0.033 |
| redact_tokenize | 0.008 | 0.008 |
| redact_surrogate | 0.029 | 0.029 |
| sem_* | 0.000 | 0.000 |
| redact_llm_substitute | 0.409 | 0.409 |
| redact_llm_rephrase | 0.563 | 0.563 |

`redact_tokenize` still shows near-zero token recovery (0.008) with high persona linkage (0.837). Unchanged.

### Rankings (lowest → highest combined \(R\))

- **Observability:** coarse < bracket < surrogate < raw < **medium** < llm_sub < llm_reph < tokenize < fine
- **Analytics:** coarse < bracket < surrogate < raw < **llm_sub < llm_reph < medium** < tokenize < fine

**Ranking change:** `sem_medium` jumps past both LLM arms on the analytics surface (5th → 7th). No other condition changes rank.

### Threshold crossings (obs vs ana train-only)

Only `sem_medium`:

- At \(R_{\max}\in\{0.50,0.55\}\): **feasible on observability** (\(R=0.487\)), **infeasible on analytics** (\(R=0.612\)).
- At \(R_{\max}\in\{0.40,0.45\}\): **no crossings.** Medium is infeasible on both surfaces at 0.45.

---

## 6. Purpose-specific operative selection

Utility held fixed. Winners below use purpose-specific residual linkage as in the published protocol:

- \(c^*(T_o)=\arg\max_c U(T_o,z_{c,T_o})\) s.t. \(R(z_{c,T_o})\le R_{\max}\)
- \(c^*(T_a)=\arg\max_c U(T_a,z_{c,T_a})\) s.t. \(R(z_{c,T_a})\le R_{\max}\)
- \(T_a\)-5 = Track C assessor/assessor (not mixed Track A)

Machine-readable: `mixed_protocol_winners.json`.

| \(R_{\max}\) | Feasible \(T_o\) | Feasible \(T_a\) | \(T_o\)-1 | \(T_o\)-2 | \(T_a\)-1 | \(T_a\)-2 | \(T_a\)-3 | \(T_a\)-5 Track C |
|---|---|---|---|---|---|---|---|---|
| 0.40 | bracket, coarse | bracket, coarse | bracket | bracket | bracket | coarse | coarse | bracket |
| **0.45** | bracket, surrogate, coarse | **same** | **bracket** | bracket | **surrogate** | **coarse** | **coarse** | **surrogate** |
| 0.50 | raw, bracket, surrogate, coarse, **medium** | raw, bracket, surrogate, coarse (**no medium**) | medium | medium | **raw** | coarse | coarse | surrogate |
| 0.55 | + llm_sub, llm_reph | + llm_sub, llm_reph (**still no medium**) | medium | medium | **raw** | coarse | coarse | surrogate |

### Differences from shared observability \(R\) (including frozen transductive)

**At focal 0.45: none.** Same feasible set, same winners as train-only shared obs \(R\) and as frozen transductive obs \(R\) *on this Track C grid*.

**At 0.50 / 0.55: material.** Shared obs \(R\) lets `sem_medium` in, so \(T_a\)-1 winner is `sem_medium` (\(U=1.0\)). Purpose-specific analytics \(R\) keeps medium out, so \(T_a\)-1 winner is `raw` (\(U=0.547\)). \(T_o\)-1 remains `sem_medium` because observability \(R\) is unchanged for that purpose.

This also means that, under purpose-specific \(R\), risk-constrained winners **diverge** at \(0.50\) and \(0.55\) (\(T_o\)-1 medium vs \(T_a\)-1 raw). They still **agree** at \(0.40\) and still **diverge** at the focal \(0.45\).

The published \(T_a\)-5 path is assessor-symmetric. This audit consumes those scores; the linkage-surface change is separate from the cohort-construction choice. At the same 0.45 feasible set, assessor-symmetric scoring selects `redact_surrogate` (0.264 vs bracket 0.261).

---

## 7. Pareto membership

Unconstrained Pareto on \((R(z_{c,T}), U(T,z_{c,T}))\) vs shared frozen obs \(R\) as the x-axis: **no condition enters or leaves any registered-task frontier** (`pareto.json` `enter`/`leave` all empty).

| Purpose | Frontier (unchanged) |
|---|---|
| observability | bracket, coarse, medium |
| analytics_med | raw, bracket, surrogate, coarse, medium |
| analytics_side | coarse |
| analytics_adherence | coarse |
| analytics_cohort (Track C) | bracket, surrogate, coarse, fine |

`sem_medium` stays on the analytics-med frontier even after \(R\) jumps to 0.612, because \(U=1.0\) is not dominated. Risk-constrained **selection** still drops it at 0.50/0.55. Pareto membership and operative winners are different statements.

---

## 8. Dual-purpose bundle

Existing illustrative floors preserved: \(U(T_o)\ge 0.6\), \(U(T_a,\mathrm{med})\ge 0.5\). Not retuned.

Purpose-specific test: a single condition ID \(c\) must satisfy **both**

\[
R(z_{c,T_o})\le R_{\max},\qquad R(z_{c,T_a})\le R_{\max}
\]

and both utility floors.

| \(R_{\max}\) | Satisfying \(c\) |
|---|---|
| 0.40 | none |
| **0.45** | **none** (`no_single_condition_at_0.45: true`) |
| 0.50 | **raw only** |
| 0.55 | **raw only** |

`sem_medium` has \(U=1/1\) but analytics \(R=0.612\), so it fails the purpose-specific bundle at every listed \(R_{\max}\). Under **shared obs \(R\)** the registry exemplar at \(R_{\max}=0.50\) had `{raw, sem_medium}`. Purpose-specific linkage **removes medium** from that 0.50 bundle.

The paper's displayed claim — no single condition satisfies the illustrative dual-purpose bundle at **\(R_{\max}=0.45\)** — **remains true**.

---

## 9. Cross-purpose regret

The existing formula (advisor figures / Figure 3) assumes **one shared feasible set**

\[
\mathcal{F}(R_{\max})=\{c:R(z_c)\le R_{\max}\}
\]

and then

\[
\mathrm{Regret}_{i\to j}=U_j(c_j^*)-U_j(c_i^*),\qquad c_i^*,c_j^*\in\mathcal{F}.
\]

That is **not well-defined** once each purpose has its own feasible set \(\mathcal{F}_T=\{c:R(z_{c,T})\le R_{\max}\}\). Silently reusing the shared formula would treat `sem_medium` as a legal company-wide reuse at 0.50 even though analytics \(R\) exceeds \(R_{\max}\).

**Minimal correct formulation (used here, not a silent rewrite of the old matrix):**

1. One common condition ID \(c\).
2. Purpose-specific exports \(z_{c,T_o}\) and \(z_{c,T_a}\).
3. \(c_T^*=\arg\max_{c\in\mathcal{F}_T} U(T,z_{c,T})\).
4. Forcing \(c_i^*\) onto purpose \(j\) is **infeasible** if \(c_i^*\notin\mathcal{F}_j\) (report as infeasible, not as a numeric regret).
5. Otherwise \(\mathrm{Regret}_{i\to j}=U_j(c_j^*)-U_j(c_i^*)\).

At **focal 0.45**, \(\mathcal{F}_{T_o}=\mathcal{F}_{T_a}=\{\)bracket, surrogate, coarse\(\}\). Every winner is feasible on every other surface, so the numeric matrix is well-defined and the legacy shared-\(R\) assumption happens to hold.

Winners at 0.45: \(T_o\)=bracket, Ta-1=surrogate, Ta-2=Ta-3=coarse, Ta-5=surrogate.

Selected regrets (F1 points):

| Force ↓ / On → | \(T_o\)-1 | Ta-1 | Ta-2 | Ta-3 | Ta-5 |
|---|---:|---:|---:|---:|---:|
| \(T_o\) winner (bracket) | 0 | 0.248 | 0.438 | 0.281 | 0.004 |
| Ta-1 winner (surrogate) | 0.016 | 0 | 0.134 | 0.265 | 0 |
| Ta-2/3 winner (coarse) | 0.508 | 0.317 | 0 | 0 | 0.028 |

Measurable cross-purpose utility regret is still present. `infeasible_reuses` is empty **at 0.45**.

At 0.50 the formulation **does** bite: forcing \(T_o\)'s winner (`sem_medium`) onto any analytics task is **infeasible** under analytics \(R\). That cell must not be reported as regret 0.

---

## 10. Headline-claim audit at focal \(R_{\max}=0.45\)

Distinguish: unchanged / numeric only / winner-ranking / weakened / invalidated / strengthened.

| # | Question | Answer | Status |
|---|---|---|---|
| 1 | Do observability and analytics still prefer different conditions? | Yes. \(T_o\)-1 = `redact_bracket`, Ta-1 = `redact_surrogate`, Ta-2/3 = `sem_coarse`. | **Unchanged** |
| 2 | Do different analytics tasks still prefer different conditions? | Yes. Med-class/cohort (assessor-symmetric) vs side/adherence. | **Unchanged** |
| 3 | Does `red_tokenize` still show near-zero token recovery with high persona linkage? | Yes. Token 0.008, persona 0.837. Identical on both surfaces. | **Unchanged** |
| 4 | Does a single condition still fail the illustrative dual-purpose bundle? | Yes at 0.45. | **Unchanged** |
| 5 | Is measurable cross-purpose utility regret still present? | Yes. Forcing bracket onto Ta-1 ≈ 0.25 F1; onto Ta-3 ≈ 0.28 F1. Well-defined at 0.45. | **Unchanged** |
| 6 | Do semantic conditions remain competitive for some analytics tasks? | Yes. `sem_coarse` still saturates Ta-2/Ta-3 at every listed \(R_{\max}\). `sem_medium` remains an unconstrained Pareto point for med-class / \(T_o\), but is **not** analytics-feasible at 0.50/0.55. | **Unchanged at 0.45**; **changed winner/ranking at 0.50–0.55** under purpose-specific \(R\) |
| 7 | Does any one condition now dominate the registered tasks? | No. | **Unchanged** |
| 8 | Does the central conclusion still hold (optimal disclosure depends on downstream purpose and linkage tolerance)? | Yes at 0.45. Under purpose-specific \(R\), the 0.50/0.55 winners **diverge** (To=medium, Ta-1=raw), which **strengthens** purpose-dependence at looser budgets. | **Unchanged at focal 0.45**; **changed numeric/feasibility at 0.50–0.55** |

The distinction **is material** (`sem_medium` \(\Delta R=+0.125\), persona 0.167→0.489, rank change vs LLM arms). It does **not** overturn the focal 0.45 published results.

---

## 11. Implications for the published protocol

Shared observability \(R(c)\), purpose-specific \(R(z_{c,T})\), and a dual-purpose bundle that requires both purpose-conditioned exports to meet \(R_{\max}\) answer different questions. The published CIKM protocol uses purpose-specific residual linkage \(R(z_{c,T})\) as the risk of the representation each consumer actually receives.

At focal \(R_{\max}=0.45\) the shared and purpose-specific grids **agree**. The distinction is localized to semantic payloads, especially `sem_medium` (\(\Delta R=+0.125\)). Under purpose-specific \(R\), \(T_a\)-1 at \(0.50/0.55\) is `raw` rather than `sem_medium`, and the 0.50 dual-purpose bundle retains `{raw}` rather than `{raw, sem_medium}`.

The 0.45 operative winners, token-recovery contrast, dual-purpose failure at 0.45, and the central conclusion (purpose and \(R_{\max}\) jointly determine the winner) are unchanged. Utility scores were not rerun.

### Reproducibility

| Item | Location |
|---|---|
| Protocol lock | `configs/cikm_v0.1.yaml` → `paper_protocol` |
| Snapshot | `paper_protocol_snapshot.json` (this directory) |
| Seed | 42 |
| TF-IDF | `char_wb`, ngram (1,3), max_features 5000, fit = train export strings only |
| Adversary | `evaluate_trial4_adversary` + `train_only_tfidf_embedder` |
| Obs exports | `data/transformed/{c}` |
| Ana exports | `data/transformed_analytics/{c}` |
| Utility | `outputs/pilot_v2/metrics.json`, `outputs/pilot_v2/analytics_metrics.json` (copied, not recomputed) |
| Assessor-symmetric \(T_a\)-5 | `outputs/post_acceptance_experiments/ta5_cohort_audit/track_c_scores.json` |
| Runner | `eval/run_purpose_specific_linkage_audit.py` |
| Verification | `make repro-cikm-2026` |
| Manifest | `run_manifest.json` (`text_z_embed_identical`, `text_linkage_identical`, `instrument_counts_match` all true) |

Machine-readable outputs in this directory: `instrument.json`, `identity.json`, `text_z_equality.json`, `text_linkage_sanity.json`, `semantic_schemas.json`, `linkage_train_only.json`, `linkage_comparison.{csv,json}`, `ranks.json`, `threshold_crossings.json`, `operative_selection.json`, `mixed_protocol_winners.json`, `pareto.json`, `dual_purpose_bundle.json`, `regret_purpose_specific.json`, `run_manifest.json`.

---

## 12. Recorded inconsistencies

1. **First-run `ana_only_fields` empty.** Typo in schema helper; regenerated. Trial4 numbers were not recomputed for that fix.
2. **Provenance \(r\) differs on text arms** (`consumer_id`, `purpose_id`) while \(z\) and embed text do not. Expected. Not a linkage bug.
3. **Analytics `sem_fine` attribute F1 drops** while persona/longitudinal rise. Combined \(R\) hides a channel swap. Adversary heads were left on the observability attribute contract.
4. **Historical `outputs/pilot_v2` linkage** used train-and-test TF-IDF fitting. This audit implements the published train-only embedder.
5. **Pareto IDs unchanged** even though `sem_medium` analytics \(R\) moves by 0.125. Empty enter/leave does not mean the distinction is immaterial; operative feasibility at 0.50/0.55 is where it matters.
