# Open Semantic Boundary Benchmark

*Supporting artifact for the CIKM 2026 short paper [**Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure**](https://doi.org/10.1145/3799682.3840076).*

The **Semantic Boundary Benchmark (SBB)** evaluates what representation should cross a system boundary for a declared purpose. Sensitive user and operational traces — such as journals, conversations, tool-use records, and logs — can support several downstream purposes, but those purposes may require different information to perform their respective tasks.

In practice, raw traces are often transformed before they leave a trusted context to suppress, replace, or abstract private and sensitive information. A transformation that is appropriate for one downstream purpose, however, may remove information needed by another or retain information that the other does not need. The question is therefore not only whether a trace should be transformed, but **which representation should cross for a particular purpose**.

SBB makes this trade-off measurable. For a registered purpose \(T\) and candidate export \(z_{c,T}\), SBB evaluates the utility preserved for that purpose, \(U(T,z_{c,T})\), together with the residual linkage associated with the exported representation, \(R(z_{c,T})\). Candidate transformations can then be compared under a declared linkage ceiling \(R_{\max}\).

The CIKM 2026 study instantiates this framework using synthetic medication-adherence journals and two downstream consumer families: observability and analytics. It evaluates a fixed **export lattice** \(\mathcal{C}\): nine alternative transformation conditions applied to the same underlying events, ranging from raw text and surface redaction to surrogate replacement, LLM-based transformations, and semantic exports at different granularities.

The experiments show that the preferred transformation can change with both purpose and linkage constraint. Surface transformations can be competitive under tight linkage ceilings, while richer semantic exports can better support some analytics tasks. Removing recoverable sensitive tokens does not necessarily prevent persona linkage, and applying a single privacy-transformed export across purposes can incur substantial utility regret.

**If you are here from the paper:** the frozen Table 3 results, Figures 2–4, protocol declaration, and reproduction check are collected in [`releases/cikm-2026/`](releases/cikm-2026/).

## Contents

- [How the benchmark works](#how-the-benchmark-works)
- [Paper artifacts](#paper-artifacts)
- [Reproduce the reported artifact](#reproduce-the-reported-artifact)
- [Reference transformations](#reference-transformations)
- [Documentation](#documentation)
- [Citation](#citation)
- [License](#license)

## How the benchmark works

**Semantic Boundary** models disclosure as a governed crossing from a trusted collection context to a registered downstream consumer. An observation \(x\) is transformed under a declared purpose \(T\) and disclosure policy \(\pi\), into an export \(z\), accompanied by provenance \(r\), before release to the consumer.

SBB evaluates alternative ways of performing that crossing. Each condition \(c \in \mathcal{C}\) defines a candidate transformation in the export lattice. Applying a condition for purpose \(T\) produces the purpose-conditioned export \(z_{c,T}\). The benchmark measures the utility and residual linkage of that exported representation and, for a declared linkage ceiling \(R_{\max}\), identifies the feasible condition that best preserves task utility.

```text
source observation x
        │
        │  transformation condition c ∈ C
        ▼
purpose-conditioned export z_{c,T}
        │
        ├── purpose-specific utility       U(T, z_{c,T})
        │
        └── residual linkage   R(z_{c,T})
        │
        ▼
feasible conditions under R_max
        │
        ▼
utility-maximizing feasible condition for purpose T
```

The **Semantic Boundary** framework defines the broader `declare`–`cross`–`verify` contract for governing such crossings. **SBB** provides the evaluation protocol for comparing alternative disclosure strategies under that contract. Neither is itself a new privacy algorithm.

For a more detailed introduction to the framework and terminology, see [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md).

## Paper artifacts

The `cikm-2026` tag freezes the code, protocol, and reported results associated with the CIKM 2026 short paper.

| In the paper                           | In this artifact                                                                                                           |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Table 3 — risk-constrained winners** | [`releases/cikm-2026/experimental_protocol.md`](releases/cikm-2026/experimental_protocol.md)                               |
| **Figure 2 — linkage decomposition**   | [`releases/cikm-2026/figures/linkage_decomposition.pdf`](releases/cikm-2026/figures/linkage_decomposition.pdf)             |
| **Figure 3 — utility matrix**          | [`releases/cikm-2026/figures/utility_matrix_heatmap.pdf`](releases/cikm-2026/figures/utility_matrix_heatmap.pdf)           |
| **Figure 4 — cross-task regret** | [`releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf`](releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| **Experimental protocol**              | [`releases/cikm-2026/experimental_protocol.md`](releases/cikm-2026/experimental_protocol.md)                               |

The paper-to-repository map in [`docs/paper_to_repo.md`](docs/paper_to_repo.md) links the experimental components described in the paper to their corresponding configurations, code, data, and frozen outputs.

## Reproduce the reported artifact

Create the environment and run the frozen reproduction check:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

This check uses the committed evaluation artifacts; it does **not** regenerate the LLM-based transformations. It verifies the focal Table 3 results at \(R_{\max}=0.45\), the reported contrast between token recovery and persona linkage for the tokenization condition, and the checksums of Figures 2–4.

For rescoring, full regeneration, and other ways to inspect or extend the artifact, see [`docs/adoption_path.md`](docs/adoption_path.md).

## Reference transformations

The CIKM pilot compares nine frozen transformation conditions. Together, these form the export lattice \(\mathcal{C}\) used in the reported experiments.

| Paper condition      | Repository identifier   | Transformation                                                               |
| -------------------- | ----------------------- | ---------------------------------------------------------------------------- |
| `raw`                | `raw`                   | Untransformed journal and assistant text                                     |
| `red_bracket`        | `redact_bracket`        | Sensitive entities replaced by typed bracket placeholders                    |
| `red_tokenize`       | `redact_tokenize`       | Sensitive entities replaced by stable persona-scoped tokens                  |
| `red_surrogate`      | `redact_surrogate`      | Sensitive entities replaced by plausible surrogate values                    |
| `red_llm_substitute` | `redact_llm_substitute` | LLM-based substitution of sensitive entities                                 |
| `red_llm_rephrase`   | `redact_llm_rephrase`   | LLM-based rewriting of the passage                                           |
| `sem_coarse`         | `sem_coarse`            | Coarse semantic representation                                               |
| `sem_medium`         | `sem_medium`            | Intermediate semantic representation with additional task-relevant structure |
| `sem_fine`           | `sem_fine`              | Fine-grained semantic representation with richer typed attributes            |

The three semantic conditions use fields from the synthetic data generator rather than a learned semantic extractor. This deliberately isolates the effect of **representation choice** from extraction error; the reported semantic conditions should therefore not be interpreted as estimates of production extraction performance.

Repository identifiers retain the longer `redact_` prefix for several text transformations, while the paper uses the shorter `red_` condition names.

## Documentation

If you are approaching the repository from the paper, the following paths are the most useful:

| Goal                                                            | Start here                                                               |
| --------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Understand Semantic Boundary and SBB**                        | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| **Find the implementation of something described in the paper** | [`docs/paper_to_repo.md`](docs/paper_to_repo.md)                         |
| **Inspect, reproduce, rescore, or extend the artifact**         | [`docs/adoption_path.md`](docs/adoption_path.md)                         |
| **Inspect the frozen CIKM results directly**                    | [`releases/cikm-2026/`](releases/cikm-2026/)                             |

The `open-sbb/` directory provides a more detailed protocol map for readers who want to inspect individual components of the benchmark.

## Citation

### Paper

Please cite the CIKM 2026 paper for the framework, benchmark methodology,
experiments, and scientific findings:

> Gaurav Baruah. 2026. *Semantic Boundary: A Framework and Benchmark for
> Policy-Constrained Semantic Disclosure.* In **Proceedings of the 35th ACM
> International Conference on Information and Knowledge Management
> (CIKM '26)**. ACM. https://doi.org/10.1145/3799682.3840076

### Supporting artifact

The frozen supporting artifact for the CIKM 2026 paper corresponds to the
`cikm-2026` tag in this repository. Citation metadata is provided in
[`CITATION.cff`](CITATION.cff).

## License

Open-SBB is released under the Apache License 2.0. See [`LICENSE`](LICENSE).
