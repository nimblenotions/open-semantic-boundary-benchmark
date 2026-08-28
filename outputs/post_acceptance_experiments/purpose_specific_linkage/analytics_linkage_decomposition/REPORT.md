# Purpose-specific linkage decomposition (two surfaces)

Audit artifact only. Paper Fig 2 remains the observability-surface heatmap under `outputs/pilot_v2_camera_ready/figures/linkage_decomposition.pdf`.

## Protocol lock

- Frozen corpus and whole-persona split (unchanged)
- Train-only character n-gram TF-IDF adversary (Trial4 channels)
- Row order: `PRIMARY_LATTICE` (same as camera-ready Fig 2)
- **Two figures:** one per released purpose surface (not per utility task)

## Figures

| surface | tasks sharing this \(R(z_{c,T})\) | files |
| --- | --- | --- |
| observability | $T_o$-1, $T_o$-2 | `linkage_decomposition_observability_surface.{pdf,png}` |
| analytics | $T_a$-1, $T_a$-2, $T_a$-3, $T_a$-5 | `linkage_decomposition_analytics_surface.{pdf,png}` |

## Text / LLM conditions (six arms)

All six text/LLM conditions are **obs–ana identical** for every linkage channel and combined \(R(z)\). Byte-identical \(z\) and embed text on the shared event corpus (`text_z_equality.json`); per-channel equality confirmed in `text_linkage_sanity.json`.

| condition | ΔR | z identical | embed identical |
| --- | ---: | :---: | :---: |
| raw | 0 | ✓ | ✓ |
| redact_bracket | 0 | ✓ | ✓ |
| redact_llm_rephrase | 0 | ✓ | ✓ |
| redact_llm_substitute | 0 | ✓ | ✓ |
| redact_surrogate | 0 | ✓ | ✓ |
| redact_tokenize | 0 | ✓ | ✓ |

## Semantic schema arms (purpose-specific surface)

Structured analytics exports differ from observability JSON; linkage can diverge:

| condition | R_obs | R_ana | ΔR | Δpersona | Δattr | Δlong |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sem_coarse | 0.3095 | 0.3135 | 0.004 | 0.0 | 0.0 | 0.012 |
| sem_medium | 0.4867 | 0.6118 | 0.1251 | 0.3222 | -0.0084 | 0.0615 |
| sem_fine | 0.7524 | 0.7615 | 0.0091 | 0.1667 | -0.2426 | 0.1033 |

## Camera-ready cross-check

Observability figure matches frozen Fig 2 table `outputs/pilot_v2_camera_ready/figures/tables/linkage_decomposition.csv`.
