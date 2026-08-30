# CIKM 2026 Experimental Protocol

This document summarizes the frozen experimental protocol and focal verification results for the CIKM 2026 short paper *Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*.

**Venue:** CIKM 2026
**DOI:** [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076)
**Repository release:** `cikm-2026`

The corresponding machine-readable protocol declaration is maintained in `configs/cikm_v0.1.yaml` under `paper_protocol` and is checked by the reproduction workflow described in the release [`README.md`](README.md).

## Frozen protocol

The CIKM study evaluates a fixed export lattice over synthetic medication-adherence journals. Each transformation condition produces a candidate exported representation for a registered downstream purpose. These candidates are compared using purpose-specific utility together with residual linkage risk.

| Dimension              | CIKM 2026 protocol                                               |
| ---------------------- | ---------------------------------------------------------------- |
| Linkage representation | TF-IDF with `char_wb` 1–3 character n-grams and 5,000 features   |
| TF-IDF fitting         | Fit on the training split only for each transformation condition |
| Residual linkage       | Evaluated for the purpose-conditioned export \(R(z_{c,T})\)      |
| Cohort task \(T_a\)-5  | Assessor-symmetric persona-level cohort evaluation               |

For a registered purpose \(T\) and transformation condition \(c\), the benchmark evaluates the utility preserved in the exported representation, \(U(T,z_{c,T})\), together with its residual linkage, \(R(z_{c,T})\). Under a declared linkage tolerance \(R_{\max}\), an operative condition must satisfy the linkage constraint and is selected according to the utility objective for the task under evaluation.

For \(T_a\)-5, both training and test cohort features are constructed from persona-level aggregates of assessor predictions for medication class, side effect, and adherence.

## Focal Table 3 result

At the focal linkage tolerance \(R_{\max}=0.45\), the reported operative selections are:

| \(T_o\)-1      | \(T_a\)-1        | \(T_a\)-2     | \(T_a\)-3     | \(T_a\)-5        |
| -------------- | ---------------- | ------------- | ------------- | ---------------- |
| bracket (0.67) | surrogate (0.45) | coarse (1.00) | coarse (1.00) | surrogate (0.26) |

The paper is the authoritative source for the complete Table 3 across all reported linkage tolerances.

## Token recovery and persona linkage

The `red_tokenize` condition illustrates that suppressing recoverable sensitive tokens does not necessarily prevent linkage through the exported representation.

For the reported evaluation:

* token recovery rate: **0.0079**
* persona top-1 linkage: **0.837**

This is the contrast reported in the paper between near-zero token recovery and high persona re-identification.

## Paper figures

Frozen copies of Figures 2–4 are provided in [`figures/`](figures/).

| Paper figure                     | Artifact                                  |
| -------------------------------- | ----------------------------------------- |
| Figure 2 — linkage decomposition | `figures/linkage_decomposition.pdf`       |
| Figure 3 — utility matrix        | `figures/utility_matrix_heatmap.pdf`      |
| Figure 4 — cross-task regret     | `figures/cross_purpose_regret_matrix.pdf` |

SHA-256 checksums for these files are recorded in [`checksums.sha256`](checksums.sha256).

## Split manifest

The frozen train/test split is recorded in:

`data/ground_truth/split_manifest_v0.json`

Its SHA-256 digest is:

`b15f4cebc5570a36171eb18ddca5d65d109ad18cb334268d45f43f84e15cfac0`

The reproduction workflow verifies the frozen protocol, the focal Table 3 result at \(R_{\max}=0.45\), the reported `red_tokenize` recovery-versus-linkage contrast, and the figure checksums using committed evaluation artifacts. It does not regenerate the LLM-based transformation outputs.
