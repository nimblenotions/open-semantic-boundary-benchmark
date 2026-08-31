# CIKM 2026 result snapshot

Generated: 2026-08-19T06:52:08.265026+00:00
Git commit: `b2a9c0d09d62d7dd0abd9a761fae35ed8fda7a8b`

This directory is the result snapshot underlying the CIKM 2026 paper. The citeable protocol, Table 3 excerpt, and Figures 2–4 live under `releases/cikm-2026/`.

The snapshot uses train-only TF-IDF fitting as specified by the published protocol. Utility scores were copied from the historical development snapshot under `outputs/pilot_v2/` and were not recomputed with new LLM inference. Earlier development runs that fitted TF-IDF on train and test together are retained separately for provenance and are not part of the published result set.

## Paper figures

- `outputs/pilot_v2_camera_ready/figures/linkage_decomposition.pdf`
- `outputs/pilot_v2_camera_ready/figures/utility_matrix_heatmap.pdf`
- `outputs/pilot_v2_camera_ready/figures/cross_purpose_regret_matrix.pdf`

## Operative verification

- Table 3 winners at 0.45 match paper: **True**
- R_max boundary crossings vs transductive: `none`
- Dual-purpose floors empty at 0.45: **True**
- `red_tokenize` near-zero token / high persona: **True** (token=0.0079, persona=0.837)
