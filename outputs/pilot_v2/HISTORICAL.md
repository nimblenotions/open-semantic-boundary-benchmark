# Historical development snapshot — not the CIKM 2026 protocol

This directory preserves an earlier experimental run used during development of the benchmark. It is retained for provenance and regression/audit purposes and is not the result set reported by the final CIKM 2026 paper.

The final CIKM protocol and citeable supporting artifact are documented under [`../../releases/cikm-2026/`](../../releases/cikm-2026/). The corresponding result snapshot is under [`../pilot_v2_camera_ready/`](../pilot_v2_camera_ready/).

Relative to the published protocol, this snapshot used:

* TF-IDF fitted on train and test export strings together, rather than train-only fitting;
* a shared observability linkage surface, rather than purpose-specific residual linkage \(R(z_{c,T})\);
* mixed \(T_a\)-5 cohort scoring (export features on train, assessor outputs on test), rather than assessor-symmetric cohort features.

Utility scores stored here were copied, not recomputed, when assembling the result snapshot under `outputs/pilot_v2_camera_ready/`. Linkage and cohort-task numbers in this directory are not those of the published paper.

This tree matches git tag `opensbb-v0.1.2`. `make repro-smoke` checks numbers from this earlier snapshot. The CIKM artifact is a later software version (`cikm-2026` / v0.1.3).
