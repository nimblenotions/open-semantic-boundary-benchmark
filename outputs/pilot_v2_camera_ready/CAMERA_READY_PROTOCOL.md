# Camera-ready train-only TF-IDF linkage protocol

Generated: 2026-08-19T06:52:08.265026+00:00
Git commit: `b2a9c0d09d62d7dd0abd9a761fae35ed8fda7a8b`

Canonical CIKM setting: `eval.trial4.tfidf_fit_scope: train_only`.
Utility scores copied from frozen `outputs/pilot_v2`; no LLM inference.
The earlier train+test (transductive) fit was incorrect; those numbers stay in
`outputs/pilot_v2` and `outputs/pilot_v2_tfidf_train_test` for audit only.

## Paper figures

- `outputs/pilot_v2_camera_ready/figures/linkage_decomposition.pdf`
- `outputs/pilot_v2_camera_ready/figures/utility_matrix_heatmap.pdf`
- `outputs/pilot_v2_camera_ready/figures/cross_purpose_regret_matrix.pdf`

## Operative verification

- Table 3 winners at 0.45 match paper: **True**
- R_max boundary crossings vs transductive: `none`
- Dual-purpose floors empty at 0.45: **True**
- `red_tokenize` near-zero token / high persona: **True** (token=0.0079, persona=0.837)
