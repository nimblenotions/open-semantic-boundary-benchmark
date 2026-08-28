# Open Semantic Boundary Benchmark

**Tag `cikm-2026` — CIKM 2026 paper 4405 reproducibility package**

This tag reproduces the submitted protocol for
[Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure](https://doi.org/10.1145/3799682.3840076)
(CIKM 2026, paper **4405**):

- **Linkage:** train-only TF-IDF (`char_wb`)
- **Risk surface:** purpose-specific \(R(z_{c,T})\)
- **Ta-5 cohort:** Track C `assessor_symmetric`

Cite artifacts: [`releases/cikm-2026/`](releases/cikm-2026/).

This tag is the **Full paper package** (scientific repro). It is **not** Open-SBB Core. Core is a later, cheaper default suite and is not what this tag ships.

Public home: [`nimblenotions/open-semantic-boundary-benchmark`](https://github.com/nimblenotions/open-semantic-boundary-benchmark)

## Start here

Use a **project virtual environment** (`.venv/`) — do not install into system Python.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

make repro-cikm-2026    # CIKM 2026 protocol + figure checksums; no Ollama
make repro-smoke        # historical v0.1.1 headlines; no Ollama
make test
```

**Why activate?** Your shell then uses the venv’s `python`, `pytest`, and installed packages. That matters when you run scripts or tests outside `make`.

**Without activation:** `make` targets still work if `.venv/` exists — the `Makefile` calls `.venv/bin/python` and `.venv/bin/pytest` directly.

## Protocol (one screen)

Declared in `configs/cikm_v0.1.yaml` → `paper_protocol` (locked 2026-08-19).

| Dimension | Canonical on this tag | Do not use as default |
|-----------|----------------------|------------------------|
| TF-IDF linkage | train-only fit on that condition’s train exports | transductive train+test (`outputs/pilot_v2/`) |
| Risk \(R\) | purpose-specific \(R(z_{c,T})\) | shared observability \(R\) |
| Ta-5 | Track C assessor-symmetric | mixed Track A |

`make repro-cikm-2026` asserts Table 3 at \(R_{\max}=0.45\), the `red_tokenize` token vs persona bite, and SHA256 of Figs. 2–4. Details: [`releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](releases/cikm-2026/CAMERA_READY_PROTOCOL.md). Change inventory: [`docs/CIKM-2026-RELEASE-NOTES.md`](docs/CIKM-2026-RELEASE-NOTES.md).

**Cite:** Evaluated on Open SBB tag `cikm-2026`; see the result card in `releases/cikm-2026/`. Do not report an unofficial aggregate “Open-SBB score.”

## Reference baselines

The **nine lattice conditions** in `data/transformed/` are **reference baselines** for the medication-adherence pilot — not “the product”:

`raw`, `redact_bracket`, `redact_tokenize`, `redact_surrogate`, `sem_coarse`, `sem_medium`, `sem_fine`, `redact_llm_substitute`, `redact_llm_rephrase`

Open SBB asks *which meanings may be disclosed for a registered purpose, with what utility and residual linkage risk?* — not *which strings should be removed?* One sensitive event can yield **different semantic exports** per downstream purpose; each is scored for utility, linkage, and provenance. [Conceptual overview →](docs/what-is-semantic-boundary.md#multi-purpose-exports)

## Historical `outputs/pilot_v2/`

> **Historical / not the CIKM default.** `outputs/pilot_v2/` is the pre-repair v0.1.1 snapshot: transductive TF-IDF, mixed Ta-5, shared observability \(R\). `make repro-smoke` still checks those older headlines. Canonical CIKM metrics live under `outputs/pilot_v2_camera_ready/` and `outputs/post_acceptance_experiments/`. See [`outputs/pilot_v2/HISTORICAL.md`](outputs/pilot_v2/HISTORICAL.md).

**Zenodo v0.1.2** ([10.5281/zenodo.21071088](https://doi.org/10.5281/zenodo.21071088)) archives that same historical frozen bundle. Prefer this GitHub tag when reproducing the CIKM paper.

## What comes next (v0.2)

v0.2 will invert the harness to `opensbb run <suite> --transform …` so you can score *your* method against this suite. **That CLI is not implemented on this tag.** Transform produces the export payload; Open SBB produces the evaluation. The system under test must not report its own risk.

Roadmap issues ([#1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues)) track that inversion. They are not required to reproduce CIKM 2026.

## Docs

| You are… | Read |
|----------|------|
| Reproducing CIKM 2026 | this README + [`releases/cikm-2026/`](releases/cikm-2026/) |
| What is Semantic Boundary? | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| Protocol map | [`open-sbb/README.md`](open-sbb/README.md) |
| Use cases | [`examples/README.md`](examples/README.md) |
| BYO exports (advanced; YMMV) | [`examples/bring_your_own/README.md`](examples/bring_your_own/README.md) — productized in v0.2 |
| Mapping paper §4 → repo | [`docs/paper_to_repo.md`](docs/paper_to_repo.md) |
| Extending the protocol | [`docs/extension_points.md`](docs/extension_points.md) |
| Camera-ready change inventory | [`docs/CIKM-2026-RELEASE-NOTES.md`](docs/CIKM-2026-RELEASE-NOTES.md) |

## Frozen split checksum

Canonical JSON uses `sort_keys=True` and compact separators (`,` `:`). Regenerate with `python scripts/build_split_manifest_v0.py`.

| Artifact | Path | SHA256 |
|----------|------|--------|
| Split manifest v0 | `data/ground_truth/split_manifest_v0.json` | `b15f4cebc5570a36171eb18ddca5d65d109ad18cb334268d45f43f84e15cfac0` |

`data/ground_truth/splits.json` remains the loader source for code; `split_manifest_v0.json` is the frozen audit manifest.

### Offline rescore (optional; still no live LLM if caches are present)

Headline utility F1 uses the frozen LLM utility consumer (`qwen3:8b`; JSON key `tier1`) — not the classical Tier-0 baseline (`make eval TIER=0`).

| Goal | Command | Notes |
|------|---------|-------|
| **Verify CIKM protocol** | `make repro-cikm-2026` | Seconds; no Ollama |
| **Verify historical headlines** | `make repro-smoke` | Seconds; no Ollama |
| **Rescore** observability utility + linkage | `make eval` | Reads `data/eval_cache/`; default config is `configs/cikm_v0.1.yaml` |
| **Rescore** analytics utility | `make eval-analytics` | Then `make cohort-tier1` before figures |
| Full regen from scratch | `make pipeline` | Requires Ollama + `qwen3:8b` |

When you run `make eval` / `make eval-analytics`, assessors **read cached completions** unless an entry is missing. Do not overwrite `outputs/pilot_v2/` when replaying the paper protocol.

Paper-protocol replay (writes only under `outputs/post_acceptance_experiments/`):

```bash
# declared in configs/cikm_v0.1.yaml → paper_protocol; no Ollama if caches exist
python eval/run_purpose_specific_linkage_audit.py
python eval/run_ta5_cohort_audit.py --score-track-c-only
```

## Repository layout

```text
src/ eval/ scripts/ tests/ configs/ data/ outputs/   ← implementation
releases/cikm-2026/                                  ← cite surface (this tag)
open-sbb/                                            ← protocol map
examples/                                            ← adoption by domain
docs/                                                ← repo map, CIKM release notes
```

**CIKM cite metrics:** `outputs/pilot_v2_camera_ready/`, `outputs/post_acceptance_experiments/`  
**Historical v0.1.1 metrics:** `outputs/pilot_v2/`

## Paper-linked figures (CIKM)

| Figure | Cite path | Source |
|--------|-----------|--------|
| Fig. 2 linkage decomposition | `releases/cikm-2026/figures/linkage_decomposition.pdf` | purpose-specific observability surface |
| Fig. 3 utility matrix | `releases/cikm-2026/figures/utility_matrix_heatmap.pdf` | Track C Ta-5 |
| Fig. 4 cross-purpose regret | `releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf` | purpose-specific \(R\) at 0.45 |

## What this repo is / is not

**In scope on this tag:** reproducible lattice evaluation of the CIKM 2026 protocol; frozen reference baselines; checksum verify without Ollama.

**Out of scope:** LaTeX paper sources, Policy Studio, HIPAA/OTel certification claims, `opensbb run` / Transform CLI (v0.2), production runtime.

## License & citation

Apache-2.0 — [`LICENSE`](LICENSE). Software citation: [`CITATION.cff`](CITATION.cff).

**Paper:** Gaurav Baruah. *Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure.* CIKM 2026. DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076).

**Historical software archive:** Zenodo [10.5281/zenodo.21071088](https://doi.org/10.5281/zenodo.21071088) (`opensbb-v0.1.2`).

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`docs/adoption_path.md`](docs/adoption_path.md)
