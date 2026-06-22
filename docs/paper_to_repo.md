# Paper to repository map

Maps the arXiv long paper **§4 Open Semantic Boundary Benchmark** to this repository.

## Section index

| Paper § | Title | Protocol folder | Primary artifacts |
|---------|-------|-----------------|-------------------|
| §4.1 | Export lattice | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md) | `data/transformed/`, Table export-lattice |
| §4.2 | Registered consumers & policies | [`open-sbb/policies/`](../open-sbb/policies/README.md), [`open-sbb/consumers/`](../open-sbb/consumers/README.md) | `data/policies/`, `data/schemas/`, `data/eval_cache*` |
| §4.3 | Synthetic pilot | [`open-sbb/synthetic_pilot_data/`](../open-sbb/synthetic_pilot_data/README.md) | `data/raw/`, `data/ground_truth/`, seed 42 |
| §4.4 | Utility & linkage | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md), [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md) | `metrics.json`, linkage figures |
| §4.5 | Operative selection | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md) | `operative_selection/`, regret matrix |
| §4.6 | Transformation provenance | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md) | `verify`, `boundary_bundle_v0.json` |

## Results (§5–§6)

| Paper asset | Repo path |
|-------------|-----------|
| Headline utility + linkage table | `outputs/pilot_v2/metrics.json`, `analytics_metrics.json` |
| Bootstrap CIs | `outputs/pilot_v2/bootstrap_cis/` |
| Linkage decomposition figure | `outputs/pilot_v2/figures/linkage_decomposition.*` |
| Utility matrix heatmap | `outputs/pilot_v2/figures/utility_matrix_heatmap.*` |
| Cross-purpose regret | `outputs/pilot_v2/figures/cross_purpose_regret_matrix.*` |
| Granularity stacked (Trial4) | `outputs/pilot_v2/additional_analyses/aa_trial4_sem_granularity_stacked.*` |

## Reproduction commands cited in paper spirit

```bash
uv pip install -e ".[dev]"
make repro-smoke
make eval
make figures
make bootstrap-cis
make operative-selection
```

Teams verifying published numbers can run `make repro-smoke` without Ollama. Full regen uses `make pipeline` (optional, heavy).

## What the paper is vs what the repo is

| | Paper | Repo |
|---|-------|------|
| Role | Explains protocol & pilot findings | Runnable benchmark + frozen artifacts |
| LaTeX | Yes | **Not included** |
| Product / Policy Studio | Mentioned as future | **Out of scope** v0.1.1 |

See [`adoption_path.md`](adoption_path.md) for practitioner onboarding.
