# Evaluation snapshots

This directory holds committed evaluation outputs for the CIKM 2026 Semantic Boundary Benchmark pilot. It is not the citeable artifact.

**Paper** (DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076)) is the canonical scientific record. The frozen supporting artifact — protocol statement, Table 3 excerpt, Figures 2–4, and checksums — is under [`../releases/cikm-2026/`](../releases/cikm-2026/). Verify with `make repro-cikm-2026`.

The three subdirectories here have distinct roles. Their filesystem names are historical implementation labels; the scientific labels are:

| Directory | Role |
| --- | --- |
| [`pilot_v2_camera_ready/`](pilot_v2_camera_ready/) | **Published result snapshot.** Train-only TF-IDF linkage and the paper figure sources underlying [`../releases/cikm-2026/`](../releases/cikm-2026/). |
| [`post_acceptance_experiments/`](post_acceptance_experiments/) | **Supporting protocol audits.** Purpose-specific linkage and assessor-symmetric \(T_a\)-5 evaluations used in the published protocol. |
| [`pilot_v2/`](pilot_v2/) | **Historical development snapshot.** An earlier experimental run retained for provenance. Not the published protocol. See [`pilot_v2/HISTORICAL.md`](pilot_v2/HISTORICAL.md). |

Do not treat any of these directories as independently canonical. The published protocol is declared in `configs/cikm_v0.1.yaml` (`paper_protocol`) and documented under `releases/cikm-2026/`.
