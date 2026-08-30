# CIKM 2026 Supporting Artifact

This directory contains the frozen results and protocol materials corresponding to the CIKM 2026 short paper [*Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*](https://doi.org/10.1145/3799682.3840076).

It provides a compact path from the published paper to the reported results, figures, protocol declaration, and verification artifacts used for the reported experiments.
For a broader map from the paper to the repository implementation, see [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Contents

| Artifact | Description |
|---|---|
| [`experimental_protocol.md`](experimental_protocol.md) | Human-readable description of the experimental protocol and focal reported results |
| [`experimental_protocol.json`](experimental_protocol.json) | Machine-readable form of the frozen protocol |
| [`table3_operative_grid.md`](table3_operative_grid.md) | Cohort-task audit comparing alternative evaluation paths used during validation |
| [`figures/`](figures/) | Frozen copies of Figures 2–4 |
| [`checksums.sha256`](checksums.sha256) | SHA-256 checksums for the frozen figure files |

## Verify the reported artifact

From the repository root:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

The reproduction check verifies:

1. the frozen experimental protocol;
2. the Table 3 results at the focal linkage tolerance \(R_{\max}=0.45\);
3. the reported contrast between token recovery and persona linkage for the `red_tokenize` condition; and
4. the checksums of Figures 2–4.

The check uses committed evaluation artifacts and does not regenerate the LLM-based transformation outputs.

## Paper results

### Table 3

The focal reported results at \(R_{\max}=0.45\) are reproduced in
[`experimental_protocol.md`](experimental_protocol.md).

The file [`table3_operative_grid.md`](table3_operative_grid.md) preserves
the cohort-task audit used to validate the adopted evaluation path; it should
not be treated as a standalone reproduction of the full published Table 3.

### Figures

* **Figure 2 — linkage decomposition:** [`figures/linkage_decomposition.pdf`](figures/linkage_decomposition.pdf)
* **Figure 3 — utility matrix:** [`figures/utility_matrix_heatmap.pdf`](figures/utility_matrix_heatmap.pdf)
* **Figure 4 — cross-task regret:** [`figures/cross_purpose_regret_matrix.pdf`](figures/cross_purpose_regret_matrix.pdf)
