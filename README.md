# Open Semantic Boundary Benchmark

Supporting artifact for the CIKM 2026 short paper
[*Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*](https://doi.org/10.1145/3799682.3840076)
(Gaurav Baruah, *Proc. CIKM '26*, DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076)).

**The Semantic Boundary Benchmark (SBB) evaluates what representation should cross a system boundary for a declared purpose.** Sensitive user and operational traces — journals, conversations, tool-use records, logs — can support several downstream purposes, but those purposes may require different information to perform their tasks. Rather than assuming that one transformed representation is appropriate for every consumer, the benchmark compares candidate exports by the utility they preserve for a particular task, \(U(T,z_{c,T})\), and the residual linkage associated with that export, \(R(z_{c,T})\).

This repository is the public artifact of the SBB pilot reported in the paper. The CIKM 2026 study instantiates the trade-off on synthetic medication-adherence journals and two registered consumer families: observability (\(T_o\)) and analytics (\(T_a\)). Nine lattice conditions range from surface redaction and surrogate substitution to semantic exports at different granularities. Under a declared linkage tolerance \(R_{\max}\), operative selection identifies which feasible condition best preserves utility for each registered task.

The experiments show that the preferred transformation can change with both purpose and linkage constraint. Surface transformations can be competitive under tight ceilings, while richer semantic exports can better support some analytics tasks. Token removal alone does not necessarily prevent persona linkage, and forcing one lattice condition — a single privacy-preserving or disclosure-controlled export — across registered purposes can incur substantial utility regret.

**If you are here from the paper**, Table 3, Figures 2–4, the protocol declaration, and a one-command check are in [`releases/cikm-2026/`](releases/cikm-2026/).

## How the benchmark works

A trusted observation \(x\) is transformed under a registered purpose \(T\) and disclosure policy \(\pi\) into an export \(z\) with provenance \(r\), then checked by `verify` before release. SBB applies a frozen set of lattice conditions \(\mathcal{C}\) to the same events, scores each purpose-conditioned export, and selects among feasible conditions at \(R_{\max}\).

```text
observation x  (trusted collection context)
        │
        │  lattice condition c ∈ C
        ▼
purpose-conditioned export z_{c,T}  (+ provenance r)
        │
        ├── utility   U(T, z_{c,T})
        └── linkage   R(z_{c,T})
                │
                ▼
     risk-constrained winner at R_max
```

Semantic Boundary is the framework for that crossing (`declare`, `cross`, `verify`). SBB is the counterfactual lattice that makes alternative disclosure strategies comparable. Neither is a new privacy algorithm.

## Paper artifacts

| In the paper | In this artifact |
|--------------|------------------|
| Table 3 — risk-constrained winners | [`releases/cikm-2026/table3_operative_grid.md`](releases/cikm-2026/table3_operative_grid.md) |
| Figure 2 — linkage decomposition | [`releases/cikm-2026/figures/linkage_decomposition.pdf`](releases/cikm-2026/figures/linkage_decomposition.pdf) |
| Figure 3 — utility matrix | [`releases/cikm-2026/figures/utility_matrix_heatmap.pdf`](releases/cikm-2026/figures/utility_matrix_heatmap.pdf) |
| Figure 4 — cross-task regret | [`releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf`](releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| Protocol declaration | [`releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](releases/cikm-2026/CAMERA_READY_PROTOCOL.md) |

## Reproduce

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

No Ollama. The command checks Table 3 at \(R_{\max}=0.45\), token recovery versus persona linkage on the tokenize condition, and SHA256 of Figures 2–4.

## Reference transformations

Nine frozen lattice conditions (paper Table 2). Repository identifiers use a `redact_` prefix where the paper uses `red_`.

| Paper | This repo | Export rule |
|-------|-----------|-------------|
| `raw` | `raw` | Raw journal and assistant text |
| `red_bracket` | `redact_bracket` | Bracket placeholders (`[MEDICATION]`-style) |
| `red_tokenize` | `redact_tokenize` | Persona-scoped stable pseudonyms |
| `red_surrogate` | `redact_surrogate` | i2b2-style surrogate replacements |
| `red_llm_substitute` | `redact_llm_substitute` | LLM entity substitution |
| `red_llm_rephrase` | `redact_llm_rephrase` | LLM passage rewrite |
| `sem_coarse` | `sem_coarse` | Coarse semantic export (boolean slots) |
| `sem_medium` | `sem_medium` | Medium semantic export (typed task fields) |
| `sem_fine` | `sem_fine` | Fine semantic export (richer typed attributes) |

Semantic conditions use simulator ground truth rather than learned extraction, isolating representation choice from extraction error.

## Documentation

| If you want to… | Read |
|-----------------|------|
| Understand the framework | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| Map paper sections to files | [`docs/paper_to_repo.md`](docs/paper_to_repo.md) |
| Inspect, reproduce further, or extend | [`docs/adoption_path.md`](docs/adoption_path.md) |

## Citation

Cite the **paper** for the science. Cite this **artifact** (git tag `cikm-2026`, and a Zenodo version of this tag when published) for the exact code and frozen results. See [`CITATION.cff`](CITATION.cff).

Zenodo [v0.1.2](https://doi.org/10.5281/zenodo.21071088) and `outputs/pilot_v2/` are a pre-camera-ready software snapshot, not the paper default.

## License

Apache-2.0 — [`LICENSE`](LICENSE).
