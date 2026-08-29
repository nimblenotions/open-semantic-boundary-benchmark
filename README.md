# Open Semantic Boundary Benchmark

**CIKM 2026 artifact** for
[Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure](https://doi.org/10.1145/3799682.3840076)
(paper **4405**).

## What Open-SBB evaluates

**Open-SBB** is the evaluation instrument for that paper. It holds sensitive events fixed and scores candidate **information exports** for different downstream purposes on two axes:

- purpose-specific utility \(U(T,z)\)
- residual linkage risk \(R(z)\)

The CIKM 2026 pilot uses synthetic medication-adherence journals, observability and analytics consumers, and nine reference export conditions.

```text
Sensitive source event x
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
      U(T,z)           R(z)
         │              │
         └──────┬───────┘
                ▼
     feasible winner @ Rmax
```

**Headline findings**

- Different downstream purposes can prefer different exports.
- Removing recoverable tokens does not necessarily remove linkage risk.
- Semantic exports are not universally better than redaction.
- A single global export can incur substantial cross-purpose regret.

## Paper in 60 seconds

**Problem.** Sensitive traces may be useful to several downstream consumers, but they do not necessarily require the same information.

**Benchmark.** Open-SBB holds the underlying events fixed and evaluates nine candidate export conditions for purpose-specific utility and residual linkage risk.

**Pilot.** Synthetic medication-adherence journals; 100 personas; 630 held-out events; observability and analytics consumers.

**Selection.** At each declared linkage ceiling \(R_{\max}\), select the feasible export with the best utility for each purpose.

**Result.** Winners differ across purposes; surface redaction can outperform richer exports under tight constraints, while semantic exports can dominate for other tasks. Token removal alone does not eliminate persona linkage.

## Table 3 and figures

| From the paper | Open here |
|----------------|-----------|
| **Table 3 — operative winners** | [`releases/cikm-2026/table3_operative_grid.md`](releases/cikm-2026/table3_operative_grid.md) |
| **Figure 2 — linkage decomposition** | [`figures/linkage_decomposition.pdf`](releases/cikm-2026/figures/linkage_decomposition.pdf) |
| **Figure 3 — utility matrix** | [`figures/utility_matrix_heatmap.pdf`](releases/cikm-2026/figures/utility_matrix_heatmap.pdf) |
| **Figure 4 — cross-purpose regret** | [`figures/cross_purpose_regret_matrix.pdf`](releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| **Camera-ready protocol** | [`CAMERA_READY_PROTOCOL.md`](releases/cikm-2026/CAMERA_READY_PROTOCOL.md) |

Cite: evaluated on Open SBB tag `cikm-2026`; see [`releases/cikm-2026/`](releases/cikm-2026/). Do not report an unofficial aggregate “Open-SBB score.”

## Reproduce

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

No Ollama. That command checks Table 3 at \(R_{\max}=0.45\), the `red_tokenize` token vs persona bite, and the three figure checksums.

For deeper rescoring and full regeneration, see the [adoption guide](docs/adoption_path.md).

## Reference baselines

The nine lattice conditions are **reference baselines** for this pilot:

`raw`, `redact_bracket`, `redact_tokenize`, `redact_surrogate`, `sem_coarse`, `sem_medium`, `sem_fine`, `redact_llm_substitute`, `redact_llm_rephrase`

## Understand / go deeper

| Goal | Read |
|------|------|
| **Understand Semantic Boundary / Open-SBB** | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| **Reproduce the CIKM paper** | [`releases/cikm-2026/`](releases/cikm-2026/) |
| **Map paper concepts to code/data** | [`docs/paper_to_repo.md`](docs/paper_to_repo.md) |
| **Go deeper / contribute** | [`docs/adoption_path.md`](docs/adoption_path.md) |

## Historical note

`outputs/pilot_v2/` and Zenodo [v0.1.2](https://doi.org/10.5281/zenodo.21071088) preserve the pre-camera-ready snapshot and are **not** the CIKM 2026 default. See [`outputs/pilot_v2/HISTORICAL.md`](outputs/pilot_v2/HISTORICAL.md).

## What comes next

Future Open-SBB releases will add a lightweight canonical suite and a plug-in interface for evaluating external disclosure methods. Those changes are intentionally not part of this frozen CIKM artifact. ([Issues #1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues).)

## License & citation

Apache-2.0 — [`LICENSE`](LICENSE). [`CITATION.cff`](CITATION.cff).

**Paper:** Gaurav Baruah. *Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure.* CIKM 2026. DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076).
