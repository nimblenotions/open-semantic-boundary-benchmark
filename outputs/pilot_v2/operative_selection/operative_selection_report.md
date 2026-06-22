# Operative selection report — primary analysis

Generated: 2026-06-06T01:03:16.771427+00:00

## 1. Risk-constrained selection — observability ($T_o$)

Choose $\arg\max U_{obs}$ subject to $R \leq R_{\max}$ and provenance gate.

| $R_{max}$ | Winner | $U_{obs}$ | Linkage | # feasible |
| --- | --- | --- | --- | --- |
| 0.35 | sem_coarse | 0.165 | 0.310 | 1 |
| 0.40 | redact_bracket | 0.673 | 0.358 | 2 |
| 0.45 | redact_bracket | 0.673 | 0.358 | 3 |
| 0.50 | sem_medium | 1.000 | 0.483 | 5 |
| 0.55 | sem_medium | 1.000 | 0.483 | 7 |
| 0.60 | sem_medium | 1.000 | 0.483 | 7 |
| 0.65 | sem_medium | 1.000 | 0.483 | 7 |
| 0.70 | sem_medium | 1.000 | 0.483 | 8 |
| 0.75 | sem_medium | 1.000 | 0.483 | 8 |

## 2. Risk-constrained selection — analytics med-class ($T_a$)

| $R_{max}$ | Winner | $U_{med}$ | Linkage | # feasible |
| --- | --- | --- | --- | --- |
| 0.35 | sem_coarse | 0.128 | 0.310 | 1 |
| 0.40 | redact_bracket | 0.197 | 0.358 | 2 |
| 0.45 | redact_surrogate | 0.445 | 0.424 | 3 |
| 0.50 | sem_medium | 1.000 | 0.483 | 5 |
| 0.55 | sem_medium | 1.000 | 0.483 | 7 |
| 0.60 | sem_medium | 1.000 | 0.483 | 7 |
| 0.65 | sem_medium | 1.000 | 0.483 | 7 |
| 0.70 | sem_medium | 1.000 | 0.483 | 8 |
| 0.75 | sem_medium | 1.000 | 0.483 | 8 |

## 2b. All analytics tasks at each $R_{max}$ (med / side / adherence / cohort / composite)

| $R_{max}$ | Obs | Med-class | Side-effect | Adherence | Cohort | Composite |
| --- | --- | --- | --- | --- | --- | --- |
| 0.35 | sem_coarse | sem_coarse (0.13) | sem_coarse (1.00) | sem_coarse (1.00) | sem_coarse (0.23) | sem_coarse (0.71) |
| 0.40 | redact_bracket | redact_bracket (0.20) | sem_coarse (1.00) | sem_coarse (1.00) | redact_bracket (0.39) | sem_coarse (0.71) |
| 0.45 | redact_bracket | redact_surrogate (0.45) | sem_coarse (1.00) | sem_coarse (1.00) | redact_bracket (0.39) | sem_coarse (0.71) |
| 0.50 | sem_medium | sem_medium (1.00) | sem_coarse (1.00) | sem_coarse (1.00) | raw (0.39) | sem_medium (1.00) |
| 0.55 | sem_medium | sem_medium (1.00) | sem_coarse (1.00) | sem_coarse (1.00) | raw (0.39) | sem_medium (1.00) |
| 0.60 | sem_medium | sem_medium (1.00) | sem_coarse (1.00) | sem_coarse (1.00) | raw (0.39) | sem_medium (1.00) |

See `analytics_multi_task_simulation.csv` for machine-readable export.

## 3. Pareto dominance — observability

| Condition | On frontier | Dominated by | Never deploy |
| --- | --- | --- | --- |
| raw | no | redact_bracket, redact_surrogate | yes |
| redact_bracket | yes | — | no |
| redact_tokenize | no | redact_bracket, sem_medium | yes |
| redact_surrogate | no | redact_bracket | yes |
| sem_coarse | yes | — | no |
| sem_medium | yes | — | no |
| sem_fine | no | sem_medium | yes |
| redact_llm_substitute | no | raw, redact_bracket, redact_surrogate, sem_medium | yes |
| redact_llm_rephrase | no | raw, redact_bracket, redact_surrogate, sem_medium, redact_llm_substitute | yes |

## 4. Task-bundle feasibility

| Bundle | # feasible | Feasible conditions |
| --- | --- | --- |
| dual_purpose_balanced | 2 | raw, sem_medium |
| strict_linkage | 0 | *(empty)* |
| observability_first | 3 | redact_bracket, redact_surrogate, sem_medium |
| analytics_med_class | 2 | raw, sem_medium |
| full_dual_composite | 3 | raw, redact_surrogate, sem_medium |

## 5. Operative boundary bundle summary

**Recommended (composite rule):** `sem_medium`

> No single condition wins both purposes at R_max=0.45; dual_purpose_balanced bundle feasible set: ['raw', 'sem_medium']. Selected `sem_medium` (non-dominated semantic arm when available). Consider purpose-split exports or pick from bundle.

