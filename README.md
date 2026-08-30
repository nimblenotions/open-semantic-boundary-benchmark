# Open Semantic Boundary Benchmark

This is the **CIKM 2026 artifact** for
[Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure](https://doi.org/10.1145/3799682.3840076)
(paper **4405**).

Sensitive traces are often useful to more than one downstream team, and those teams do not need the same information. **Open-SBB** holds the underlying events fixed and scores candidate **exports** on two axes: how well a purpose can still do its job (\(U\)), and how much residual linkage remains (\(R\)).

The paper studies a synthetic medication-adherence pilot: 100 personas, 630 held-out events, observability and analytics consumers, and nine reference export methods.

```text
Sensitive source event
        │
        ├── raw
        ├── bracket redaction
        ├── surrogate substitution
        ├── tokenization
        ├── LLM rewrite
        └── semantic coarse / medium / fine
                │
                ▼
        purpose-specific consumer
                │
         ┌──────┴───────┐
         ▼              ▼
      utility         linkage
         │              │
         └──────┬───────┘
                ▼
     feasible winner at a linkage ceiling
```

**What this study found**

- Different downstream purposes can prefer different exports.
- Removing recoverable tokens does not necessarily remove linkage risk.
- Semantic exports are not universally better than redaction.
- A single global export can cost a lot of utility for some purposes.

There is no unofficial aggregate “Open-SBB score.” Cite the paper for the science, and this tag for the exact code and numbers.

## Try it

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

No Ollama. That check confirms Table 3 at \(R_{\max}=0.45\), the tokenize-vs-persona result, and the three figure checksums.

## Paper assets

| From the paper | Open here |
|----------------|-----------|
| **Table 3 — operative winners** | [`releases/cikm-2026/table3_operative_grid.md`](releases/cikm-2026/table3_operative_grid.md) |
| **Figure 2 — linkage decomposition** | [`releases/cikm-2026/figures/linkage_decomposition.pdf`](releases/cikm-2026/figures/linkage_decomposition.pdf) |
| **Figure 3 — utility matrix** | [`releases/cikm-2026/figures/utility_matrix_heatmap.pdf`](releases/cikm-2026/figures/utility_matrix_heatmap.pdf) |
| **Figure 4 — cross-purpose regret** | [`releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf`](releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| **Camera-ready protocol** | [`releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](releases/cikm-2026/CAMERA_READY_PROTOCOL.md) |

The nine reference baselines are `raw`, `redact_bracket`, `redact_tokenize`, `redact_surrogate`, `sem_coarse`, `sem_medium`, `sem_fine`, `redact_llm_substitute`, and `redact_llm_rephrase`.

## What to cite

| | |
|--|--|
| **Science** | The CIKM 2026 paper ([DOI 10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076)) |
| **This artifact** | Git tag `cikm-2026`, folder [`releases/cikm-2026/`](releases/cikm-2026/). A Zenodo version of this tag is the archival copy (see [`docs/releases/opensbb-cikm-2026.md`](docs/releases/opensbb-cikm-2026.md)). |
| **Older software** | Zenodo [v0.1.2](https://doi.org/10.5281/zenodo.21071088) and `outputs/pilot_v2/` are the **pre-camera-ready** snapshot. They are not the paper default. |

## Read next

| If you want to… | Read |
|-----------------|------|
| Understand the idea | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| Find paper tables and code | [`docs/paper_to_repo.md`](docs/paper_to_repo.md) |
| Reproduce more deeply, or extend | [`docs/adoption_path.md`](docs/adoption_path.md) |

A later release will add a plug-in interface so you can score an external disclosure method without forking this experiment. That work is not on this frozen tag. ([Issues #1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues).)

## License

Apache-2.0 — [`LICENSE`](LICENSE). [`CITATION.cff`](CITATION.cff).
