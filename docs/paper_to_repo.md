# Paper to repository map

You read the CIKM 2026 paper. This page says where each piece lives in the artifact.

**Science:** [*Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*](https://doi.org/10.1145/3799682.3840076) (paper **4405**).  
**Start here:** [`../releases/cikm-2026/`](../releases/cikm-2026/).

Section numbers below are those of the **CIKM short paper**, not an older long manuscript.

## Results (§5)

| Paper asset | Open here |
|-------------|-----------|
| Table 3 — operative winners | [`../releases/cikm-2026/table3_operative_grid.md`](../releases/cikm-2026/table3_operative_grid.md) |
| Fig. 2 linkage decomposition | [`../releases/cikm-2026/figures/linkage_decomposition.pdf`](../releases/cikm-2026/figures/linkage_decomposition.pdf) |
| Fig. 3 utility matrix | [`../releases/cikm-2026/figures/utility_matrix_heatmap.pdf`](../releases/cikm-2026/figures/utility_matrix_heatmap.pdf) |
| Fig. 4 cross-purpose regret | [`../releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf`](../releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| Protocol assertion | [`../releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](../releases/cikm-2026/CAMERA_READY_PROTOCOL.md) |

The metric trees behind those files are `outputs/pilot_v2_camera_ready/` (train-only TF-IDF, purpose-specific linkage) and `outputs/post_acceptance_experiments/` (Track C Ta-5). You do not need them to read the paper.

## Verify

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

No Ollama. That command checks Table 3 at \(R_{\max}=0.45\), tokenize vs persona on `redact_tokenize`, and SHA256 of Figs. 2–4.

Optional replay (writes only under `outputs/post_acceptance_experiments/`):

```bash
python eval/run_purpose_specific_linkage_audit.py
python eval/run_ta5_cohort_audit.py --score-track-c-only
```

## Framework and protocol (§2–§4)

The short paper compresses the protocol. The folders below are the full detail that would not fit in four pages.

| In the paper | Protocol folder | On disk |
|--------------|-----------------|--------|
| Export conditions / lattice | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md) | `data/transformed/` |
| Purposes, policies, consumers | [`open-sbb/policies/`](../open-sbb/policies/README.md), [`open-sbb/consumers/`](../open-sbb/consumers/README.md) | `data/policies/`, `data/schemas/`, `data/eval_cache*` |
| Synthetic pilot | [`open-sbb/synthetic_pilot_data/`](../open-sbb/synthetic_pilot_data/README.md) | `data/raw/`, `data/ground_truth/`, seed 42 |
| Utility and linkage | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md), [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md) | camera-ready + post-acceptance metrics; Figs. 2–3 |
| Operative selection | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md) | Table 3, Fig. 4 |
| Provenance / verify | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md) | `verify`, `boundary_bundle_v0.json` |

## Paper vs this repo

| | Paper | This repo |
|---|-------|-----------|
| Role | Explains the protocol and the pilot findings | Runnable benchmark plus frozen artifacts |
| LaTeX | Yes | Not included |
| Product / Policy Studio | Mentioned as future | Out of scope |

`outputs/pilot_v2/` is the **pre-repair** snapshot (older TF-IDF fit, mixed Ta-5, shared observability linkage). Same bundle: Zenodo [v0.1.2](https://doi.org/10.5281/zenodo.21071088). See [`../outputs/pilot_v2/HISTORICAL.md`](../outputs/pilot_v2/HISTORICAL.md). Do not quote it as the CIKM result.

To run or extend the harness, see [`adoption_path.md`](adoption_path.md).
