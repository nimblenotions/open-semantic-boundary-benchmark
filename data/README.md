# Data

This directory contains the frozen data artifacts used by the CIKM 2026 Semantic Boundary Benchmark pilot.

* `raw/` — synthetic medication-adherence observations.
* `ground_truth/` — persona splits, labels, simulator ground truth, and the frozen split manifest.
* `policies/` — disclosure policies for the registered observability and analytics purposes.
* `schemas/` — semantic-export, provenance, and label schemas.
* `transformed/` — committed observability-purpose exports for the nine lattice conditions.
* `transformed_analytics/` — committed analytics-purpose exports for the same lattice conditions.
* `llm_transform_cache/` — cached outputs for the LLM substitution and rephrasing conditions.
* `eval_cache/` — frozen observability assessor predictions.
* `eval_cache_analytics/` — frozen analytics assessor predictions.

The supported CIKM verification path uses these committed artifacts and does not regenerate LLM transformations or assessor inference:

```bash
make repro-cikm-2026
```

For the scientific protocol, see [`../releases/cikm-2026/`](../releases/cikm-2026/). For the relationship between paper concepts and repository paths, see [`../docs/paper_to_repo.md`](../docs/paper_to_repo.md).
