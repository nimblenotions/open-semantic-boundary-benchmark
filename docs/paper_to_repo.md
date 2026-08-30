# Paper to repository map

You read the CIKM 2026 paper. This page maps its sections and assets onto this artifact.

Gaurav Baruah, [*Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*](https://doi.org/10.1145/3799682.3840076), CIKM 2026. Frozen results: [`../releases/cikm-2026/`](../releases/cikm-2026/).

Section numbers are those of the short paper.

## Results (§5)

| Paper | This artifact |
|-------|----------------|
| Table 3 — risk-constrained winners | [`../releases/cikm-2026/table3_operative_grid.md`](../releases/cikm-2026/table3_operative_grid.md) |
| Figure 2 — linkage decomposition | [`../releases/cikm-2026/figures/linkage_decomposition.pdf`](../releases/cikm-2026/figures/linkage_decomposition.pdf) |
| Figure 3 — utility matrix | [`../releases/cikm-2026/figures/utility_matrix_heatmap.pdf`](../releases/cikm-2026/figures/utility_matrix_heatmap.pdf) |
| Figure 4 — cross-task regret | [`../releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf`](../releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| Protocol used for those numbers | [`../releases/cikm-2026/experimental_protocol.md`](../releases/cikm-2026/experimental_protocol.md) |

Implementation trees (not required to read the paper): `outputs/pilot_v2_camera_ready/` and `outputs/post_acceptance_experiments/`.

## Verify

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

No Ollama. Checks Table 3 at \(R_{\max}=0.45\), token recovery versus persona linkage on `redact_tokenize` (`red_tokenize` in the paper), and SHA256 of Figures 2–4.

## Framework and protocol (§2–§4)

The short paper compresses the protocol. These folders hold the detail that does not fit in four pages.

| In the paper | Protocol folder | On disk |
|--------------|-----------------|--------|
| Frozen lattice \(\mathcal{C}\) | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md) | `data/transformed/` |
| Registered purposes, policies, consumers | [`open-sbb/policies/`](../open-sbb/policies/README.md), [`open-sbb/consumers/`](../open-sbb/consumers/README.md) | `data/policies/`, `data/schemas/`, `data/eval_cache*` |
| Synthetic pilot corpus | [`open-sbb/synthetic_pilot_data/`](../open-sbb/synthetic_pilot_data/README.md) | `data/raw/`, `data/ground_truth/`, seed 42 |
| Utility \(U\) and linkage \(R\) | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md), [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md) | camera-ready and post-acceptance metrics; Figs. 2–3 |
| Operative selection | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md) | Table 3, Fig. 4 |
| Provenance \(r\) and `verify` | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md) | `verify`, `boundary_bundle_v0.json` |

## Lattice identifiers

| Paper (Table 2) | Repository |
|-----------------|------------|
| `raw` | `raw` |
| `red_bracket` | `redact_bracket` |
| `red_tokenize` | `redact_tokenize` |
| `red_surrogate` | `redact_surrogate` |
| `red_llm_substitute` | `redact_llm_substitute` |
| `red_llm_rephrase` | `redact_llm_rephrase` |
| `sem_coarse` / `sem_medium` / `sem_fine` | same |

## Paper vs this repository

| | Paper | This repository |
|---|-------|-----------------|
| Role | Framework, SBB protocol, and pilot findings | Runnable artifact and frozen results |
| LaTeX | Yes | Not included |

`outputs/pilot_v2/` is a pre-camera-ready snapshot (older TF-IDF fit and Ta-5 scoring). Same bundle: Zenodo [v0.1.2](https://doi.org/10.5281/zenodo.21071088). See [`../outputs/pilot_v2/HISTORICAL.md`](../outputs/pilot_v2/HISTORICAL.md). Do not quote it as the CIKM result.

To inspect or extend the artifact, see [`adoption_path.md`](adoption_path.md).
