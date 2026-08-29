# Paper to repository map

Maps **CIKM 2026** paper 4405
([*Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*](https://doi.org/10.1145/3799682.3840076))
to this repository.

**Cite surface (start here):** [`../releases/cikm-2026/`](../releases/cikm-2026/).  
A longer technical report remains forthcoming; it does **not** replace the CIKM paper as the canonical cite.

## Results (CIKM §§5–6)

| Paper asset | Open here |
|-------------|-----------|
| Table 3 — operative winners | [`../releases/cikm-2026/table3_operative_grid.md`](../releases/cikm-2026/table3_operative_grid.md) |
| Fig. 2 linkage decomposition | [`../releases/cikm-2026/figures/linkage_decomposition.pdf`](../releases/cikm-2026/figures/linkage_decomposition.pdf) |
| Fig. 3 utility matrix | [`../releases/cikm-2026/figures/utility_matrix_heatmap.pdf`](../releases/cikm-2026/figures/utility_matrix_heatmap.pdf) |
| Fig. 4 cross-purpose regret | [`../releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf`](../releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| Protocol assertion | [`../releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](../releases/cikm-2026/CAMERA_READY_PROTOCOL.md) |

Canonical metric trees (implementation detail): `outputs/pilot_v2_camera_ready/` and `outputs/post_acceptance_experiments/` (purpose-specific linkage + Track C Ta-5 snapshot).

## Reproduction

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

That command verifies Table 3 at \(R_{\max}=0.45\), the `red_tokenize` token vs persona bite, and SHA256 of Figs. 2–4. **No Ollama.**

Optional paper-protocol replay (writes only under `outputs/post_acceptance_experiments/`):

```bash
python eval/run_purpose_specific_linkage_audit.py
python eval/run_ta5_cohort_audit.py --score-track-c-only
```

### Historical v0.1.1 / Zenodo

`outputs/pilot_v2/` and `make repro-smoke` audit the **pre-repair** snapshot (transductive TF-IDF, mixed Ta-5, shared observability \(R\)). Same bundle: Zenodo [10.5281/zenodo.21071088](https://doi.org/10.5281/zenodo.21071088). See [`../outputs/pilot_v2/HISTORICAL.md`](../outputs/pilot_v2/HISTORICAL.md). **Not** the CIKM default.

## Section index (framework ↔ protocol folders)

Section numbers below follow the forthcoming long-form write-up (same framework as the CIKM short paper).

| Topic | Protocol folder | Primary artifacts |
|-------|-----------------|-------------------|
| Export lattice | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md) | `data/transformed/` |
| Registered consumers & policies | [`open-sbb/policies/`](../open-sbb/policies/README.md), [`open-sbb/consumers/`](../open-sbb/consumers/README.md) | `data/policies/`, `data/schemas/`, `data/eval_cache*` |
| Synthetic pilot | [`open-sbb/synthetic_pilot_data/`](../open-sbb/synthetic_pilot_data/README.md) | `data/raw/`, `data/ground_truth/`, seed 42 |
| Utility & linkage | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md), [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md) | camera-ready + post-acceptance metrics; Figs. 2–3 |
| Operative selection | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md) | Table 3, Fig. 4 |
| Transformation provenance | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md) | `verify`, `boundary_bundle_v0.json` |

## What the paper is vs what the repo is

| | Paper | Repo |
|---|-------|------|
| Role | Explains protocol & pilot findings | Runnable benchmark + frozen artifacts |
| LaTeX | Yes | **Not included** |
| Product / Policy Studio | Mentioned as future | **Out of scope** |

See [`adoption_path.md`](adoption_path.md) for practitioner onboarding.
