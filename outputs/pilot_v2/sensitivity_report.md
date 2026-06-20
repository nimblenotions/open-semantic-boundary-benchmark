# Tier-1 sensitivity report (pilot_v2)

Generated: 2026-06-06T00:41:22.170627+00:00

Same frozen prompts (`triage_v1`, `analytics_triage_v1`); temperature 0; seed 42; test split only (630 events). Primary consumer: **qwen3:8b**; sensitivity: **llama3.1:8b**, **gemma4:latest**.

## Headline (decision robustness)

- At **R_max = 0.45**, observability risk-constrained winner: qwen3:8b → `redact_bracket`, llama3.1:8b → `redact_bracket`, gemma4:latest → `redact_bracket` (**stable**).
- Analytics composite winner at same budget: qwen3:8b → `sem_coarse`, llama3.1:8b → `sem_coarse`, gemma4:latest → `sem_coarse` (**stable**).
- **Lattice ordering is model-robust** for semantic arms: `sem_medium` / `sem_fine` hit utility ceiling on all three models; `sem_coarse` fails on all three.
- **Purpose conflict persists**: no model picks the same transform for obs and analytics at this budget; absolute F1 shifts but the operative story does not collapse to “one transform wins everything.”

## Observability — failure_mode macro-F1

| Condition | Trial4 R | qwen3:8b | llama3.1:8b | gemma4:latest |
|---|---|---|---|---|
| raw | 0.481 | 0.626 | 0.542 | 0.653 |
| redact_bracket | 0.358 | 0.673 | 0.556 | 0.647 |
| redact_tokenize | 0.662 | 0.662 | 0.494 | 0.526 |
| redact_surrogate | 0.424 | 0.657 | 0.552 | 0.603 |
| sem_coarse | 0.310 | 0.165 | 0.224 | 0.213 |
| sem_medium | 0.483 | 1.000 | 1.000 | 0.997 |
| sem_fine | 0.752 | 1.000 | 1.000 | 1.000 |
| redact_llm_substitute | 0.525 | 0.599 | 0.494 | 0.638 |
| redact_llm_rephrase | 0.537 | 0.583 | 0.432 | 0.599 |

## Analytics — composite utility (mean Ta-1/2/3)

| Condition | qwen3:8b | llama3.1:8b | gemma4:latest |
|---|---|---|---|
| raw | 0.727 | 0.462 | 0.392 |
| redact_bracket | 0.493 | 0.380 | 0.405 |
| redact_tokenize | 0.625 | 0.406 | 0.293 |
| redact_surrogate | 0.682 | 0.415 | 0.316 |
| sem_coarse | 0.709 | 0.626 | 0.666 |
| sem_medium | 0.998 | 0.998 | 1.000 |
| sem_fine | 0.994 | 0.998 | 1.000 |
| redact_llm_substitute | 0.618 | 0.375 | 0.311 |
| redact_llm_rephrase | 0.664 | 0.496 | 0.326 |

## Paper prose (paste-ready)

> We hold exports and linkage fixed and swap only the open-weight Tier-1 consumer (qwen3:8b primary; llama3.1:8b and gemma4:latest on the test holdout). Absolute macro-F1 shifts by model, but the qualitative lattice ordering holds: coarse semantic exports fail triage, medium/fine oracle fields saturate utility, and purpose-specific risk-constrained winners at R_max=0.45 agree across consumers — supporting operative selection as a decision method rather than a single-model artifact.

