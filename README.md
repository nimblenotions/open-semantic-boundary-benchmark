# Open Semantic Boundary Benchmark

**CIKM 2026 artifact** for
[Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure](https://doi.org/10.1145/3799682.3840076)
(paper **4405**).

## What this repo demonstrates

**Open-SBB** is the evaluation instrument for that paper. It holds sensitive events fixed and scores candidate **information exports** for different downstream purposes on two axes:

- purpose-specific utility \(U(T,z)\)
- residual linkage risk \(R(z)\)

The CIKM 2026 pilot uses synthetic medication-adherence journals, two purpose families (observability and analytics), and nine **reference** export conditions.

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

[Paper in 60 seconds](#paper-in-60-seconds) · [Table 3 and figures](#from-the-paper) · [Reproduce](#reproduce) · [Understand the benchmark](docs/what-is-semantic-boundary.md)

## Paper in 60 seconds

**Problem.** Sensitive traces may be useful to several downstream consumers, but they do not necessarily require the same information.

**Benchmark.** Open-SBB holds the underlying events fixed and evaluates nine candidate export conditions for purpose-specific utility and residual linkage risk.

**Pilot.** Synthetic medication-adherence journals; 100 personas; 630 held-out events; observability and analytics consumers.

**Selection.** At each declared linkage ceiling \(R_{\max}\), select the feasible export with the best utility for each purpose.

**Result.** Winners differ across purposes; surface redaction can outperform richer exports under tight constraints, while semantic exports can dominate for other tasks. Token removal alone does not eliminate persona linkage.

**Start with [Table 3](releases/cikm-2026/table3_operative_grid.md) → [Figures 2–4](#from-the-paper) → [one-command verify](#reproduce).**

## From the paper

Cite surface: [`releases/cikm-2026/`](releases/cikm-2026/). You do not need the deep `outputs/` trees to inspect the paper.

| From the paper | Open here |
|----------------|-----------|
| **Table 3 — operative winners** | [`releases/cikm-2026/table3_operative_grid.md`](releases/cikm-2026/table3_operative_grid.md) |
| **Figure 2 — linkage decomposition** | [`figures/linkage_decomposition.pdf`](releases/cikm-2026/figures/linkage_decomposition.pdf) |
| **Figure 3 — utility matrix** | [`figures/utility_matrix_heatmap.pdf`](releases/cikm-2026/figures/utility_matrix_heatmap.pdf) |
| **Figure 4 — cross-purpose regret** | [`figures/cross_purpose_regret_matrix.pdf`](releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |
| **Exact camera-ready protocol** | [`CAMERA_READY_PROTOCOL.md`](releases/cikm-2026/CAMERA_READY_PROTOCOL.md) |
| **One-command verification** | `make repro-cikm-2026` |

**Cite:** Evaluated on Open SBB tag `cikm-2026`; see that result card. Do not report an unofficial aggregate “Open-SBB score.”

## Protocol

Declared in `configs/cikm_v0.1.yaml` → `paper_protocol` (locked 2026-08-19).

| What the paper means | How this tag implements it | Not the default |
|----------------------|----------------------------|-----------------|
| Linkage fitted on train exports only | train-only TF-IDF (`char_wb`) | transductive train+test (`outputs/pilot_v2/`) |
| Linkage evaluated on the purpose-specific export \(z_{c,T}\) | purpose-specific \(R(z_{c,T})\) | shared observability \(R\) |
| Cohort task (\(T_a\)-5) | Track C / assessor-symmetric | mixed Track A |

`make repro-cikm-2026` asserts Table 3 at \(R_{\max}=0.45\), the `red_tokenize` token vs persona bite, and SHA256 of Figs. 2–4. Inventory: [`docs/CIKM-2026-RELEASE-NOTES.md`](docs/CIKM-2026-RELEASE-NOTES.md).

## Reproduce

Use a **project virtual environment** (`.venv/`) — do not install into system Python.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

make repro-cikm-2026    # CIKM 2026 protocol + figure checksums; no Ollama
make test
```

`make` still works without activation if `.venv/` exists (it calls `.venv/bin/python` directly).

## Reference baselines

The **nine lattice conditions** in `data/transformed/` are **reference baselines** for the medication-adherence pilot — not “the product”:

`raw`, `redact_bracket`, `redact_tokenize`, `redact_surrogate`, `sem_coarse`, `sem_medium`, `sem_fine`, `redact_llm_substitute`, `redact_llm_rephrase`

Open SBB asks *which meanings may be disclosed for a registered purpose, with what utility and residual linkage risk?* One event can yield **different semantic exports** per purpose; each is scored for utility, linkage, and provenance. [Conceptual overview →](docs/what-is-semantic-boundary.md#multi-purpose-exports)

## Historical `outputs/pilot_v2/`

> **Historical / not the CIKM default.** `outputs/pilot_v2/` is the pre-repair v0.1.1 snapshot (transductive TF-IDF, mixed Ta-5, shared observability \(R\)). `make repro-smoke` still checks those older headlines. Canonical CIKM metrics: `outputs/pilot_v2_camera_ready/` and `outputs/post_acceptance_experiments/`. See [`outputs/pilot_v2/HISTORICAL.md`](outputs/pilot_v2/HISTORICAL.md).

Zenodo [10.5281/zenodo.21071088](https://doi.org/10.5281/zenodo.21071088) (`opensbb-v0.1.2`) archives that same historical bundle. Prefer tag `cikm-2026` for the CIKM paper.

## Versioning note

This tag freezes the **full CIKM 2026 scientific artifact**. Later Open-SBB releases will add a cheaper canonical Core suite and a plug-in transform interface (`opensbb run <suite> --transform …`); those are intentionally **not** part of this frozen paper tag. Transform produces the export; Open SBB produces the evaluation. The system under test must not report its own risk.

Roadmap: [issues #1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues). Not required to reproduce the paper.

## Docs

| You are… | Read |
|----------|------|
| Paper reader | this README + [`releases/cikm-2026/`](releases/cikm-2026/) |
| What is Semantic Boundary? | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| Paper §4 → repo | [`docs/paper_to_repo.md`](docs/paper_to_repo.md) |
| Onboarding tracks | [`docs/adoption_path.md`](docs/adoption_path.md) |
| Protocol map | [`open-sbb/README.md`](open-sbb/README.md) |
| Use cases | [`examples/README.md`](examples/README.md) |
| BYO exports (advanced; YMMV) | [`examples/bring_your_own/README.md`](examples/bring_your_own/README.md) — v0.2 |
| Camera-ready change inventory | [`docs/CIKM-2026-RELEASE-NOTES.md`](docs/CIKM-2026-RELEASE-NOTES.md) |

## Frozen split checksum

Canonical JSON uses `sort_keys=True` and compact separators (`,` `:`).

| Artifact | Path | SHA256 |
|----------|------|--------|
| Split manifest v0 | `data/ground_truth/split_manifest_v0.json` | `b15f4cebc5570a36171eb18ddca5d65d109ad18cb334268d45f43f84e15cfac0` |

### Optional rescore (no live LLM if caches are present)

Headline utility F1 uses the frozen LLM consumer (`qwen3:8b`; JSON key `tier1`).

| Goal | Command |
|------|---------|
| **Verify CIKM protocol** | `make repro-cikm-2026` |
| Historical v0.1.1 headlines | `make repro-smoke` |
| Rescore observability / analytics | `make eval` then `make eval-analytics` + `make cohort-tier1` |
| Full regen | `make pipeline` (needs Ollama + `qwen3:8b`) |

Do not overwrite `outputs/pilot_v2/` when replaying the paper protocol.

## Repository layout

```text
README → releases/cikm-2026/ → docs/paper_to_repo.md → src/ eval/ outputs/
```

**CIKM cite metrics:** `outputs/pilot_v2_camera_ready/`, `outputs/post_acceptance_experiments/`  
**Historical v0.1.1:** `outputs/pilot_v2/`

**In scope:** CIKM 2026 protocol, frozen reference baselines, checksum verify without Ollama.  
**Out of scope:** LaTeX sources, Policy Studio, certification claims, `opensbb run` (v0.2), production runtime.

## License & citation

Apache-2.0 — [`LICENSE`](LICENSE). [`CITATION.cff`](CITATION.cff).

**Paper:** Gaurav Baruah. *Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure.* CIKM 2026. DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076).

**Historical software archive:** Zenodo [10.5281/zenodo.21071088](https://doi.org/10.5281/zenodo.21071088).

[`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CHANGELOG.md`](CHANGELOG.md)
