# Historical frozen run (not the CIKM 2026 default)

`outputs/pilot_v2/` is the **pre-repair** published snapshot:

- TF-IDF linkage fit on **train+test** (transductive)
- shared observability risk surface \(R(z_{c,T_o})\)
- mixed Track A Ta-5 cohort scoring

It remains on this tag so `make repro-smoke` can audit the older v0.1.1 headlines.

Canonical CIKM 2026 protocol lives in `configs/cikm_v0.1.yaml` → `paper_protocol`, with cite artifacts under `releases/cikm-2026/` and metrics under `outputs/pilot_v2_camera_ready/` plus `outputs/post_acceptance_experiments/`. This tree matches git tag `opensbb-v0.1.2`. The CIKM artifact is a later software version (`cikm-2026` / v0.1.3).
