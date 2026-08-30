# CIKM 2026 camera-ready protocol

**Paper:** Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure  
**Venue:** CIKM 2026  
**DOI:** [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076)  
**Tag:** `cikm-2026` (Full paper package — not Open-SBB Core)

Declared in `configs/cikm_v0.1.yaml` → `paper_protocol` (locked 2026-08-19).

## Protocol locks

| Dimension | This tag (canonical) | Historical `outputs/pilot_v2/` |
|-----------|----------------------|--------------------------------|
| Linkage TF-IDF | **train-only** `char_wb` ngram (1, 3), 5000 features | transductive train+test fit |
| Risk surface | **purpose-specific** \(R(z_{c,T})\) | shared observability \(R(z_{c,T_o})\) |
| Ta-5 cohort | **Track C** `assessor_symmetric` | mixed Track A |

Do **not** overwrite `outputs/pilot_v2/`. Verify with `make repro-cikm-2026` (no Ollama).

## Table 3 at \(R_{\max}=0.45\) (Track C)

| \(T_o\)-1 | \(T_a\)-1 | \(T_a\)-2 | \(T_a\)-3 | \(T_a\)-5 |
|-----------|-----------|-----------|-----------|-----------|
| bracket (0.67) | surrogate (0.45) | coarse (1.00) | coarse (1.00) | **surrogate (0.26)** |

Full grid: [`table3_operative_grid.md`](table3_operative_grid.md).

## Token vs persona (`red_tokenize`)

Near-zero token recovery with high persona linkage:

- token recovery rate = **0.0079**
- persona top-1 = **0.837**

## Paper figures

Flattened copies in [`figures/`](figures/); originals stay under `outputs/` so protocol paths still resolve.

| Paper | Cite path | Source |
|-------|-----------|--------|
| Fig. 2 | `figures/linkage_decomposition.pdf` | purpose-specific observability surface |
| Fig. 3 | `figures/utility_matrix_heatmap.pdf` | Track C Ta-5 column |
| Fig. 4 | `figures/cross_purpose_regret_matrix.pdf` | purpose-specific \(R\) at 0.45 |

Figure checksums: [`checksums.sha256`](checksums.sha256).

## Split manifest

Canonical JSON uses `sort_keys=True` and compact separators (`,` `:`).

| Artifact | Path | SHA256 |
|----------|------|--------|
| Split manifest v0 | `data/ground_truth/split_manifest_v0.json` | `b15f4cebc5570a36171eb18ddca5d65d109ad18cb334268d45f43f84e15cfac0` |
