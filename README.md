# Open Semantic Boundary Benchmark

Open SBB is a benchmark for evaluating **what semantic content should cross a boundary** from sensitive traces into downstream systems.

Most privacy tools ask: *which strings should be removed?*

Open SBB asks: *which meanings may be disclosed for a registered purpose, with what utility and residual linkage risk?*

Use it to compare export strategies for **AI observability**, **analytics**, **evaluation**, and **agent workflows** — on a counterfactual export lattice with frozen assessors.

One sensitive event can yield **different semantic exports** per downstream purpose; each is scored for utility, linkage, and provenance. [Conceptual overview →](docs/what-is-semantic-boundary.md#multi-purpose-exports)

Public home: [`nimblenotions/open-semantic-boundary-benchmark`](https://github.com/nimblenotions/open-semantic-boundary-benchmark)

**Companion arXiv preprint:** submitted; ID pending.

> **Early development.** v0.1.1 is a citeable **frozen reference release** for the medication-adherence pilot. Reproduction (`make repro-smoke`) is the supported first path. Bring-your-own exports, adapters, and one-command evaluation are **enthusiast / v0.2** — see [`examples/bring_your_own/README.md`](examples/bring_your_own/README.md). **Your mileage may vary** outside the committed pilot.

## Start here

| You are… | Read |
|----------|------|
| **What is Semantic Boundary?** | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| New to the benchmark | [`open-sbb/README.md`](open-sbb/README.md) |
| Looking for use cases | [`examples/README.md`](examples/README.md) |
| Reproducing the paper | [`Paper reproduction cheatsheet`](#paper-reproduction-cheatsheet) below |
| BYO exports (advanced; YMMV) | [`examples/bring_your_own/README.md`](examples/bring_your_own/README.md) — productized in v0.2 |
| Mapping paper §4 → repo | [`docs/paper_to_repo.md`](docs/paper_to_repo.md) |
| Extending the protocol | [`docs/extension_points.md`](docs/extension_points.md) |
| v0.2 roadmap (contributions) | [GitHub issues #1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues) |

## Status: Open SBB v0.1.1

| Component | Notes |
|-----------|-------|
| Nine lattice conditions | Frozen oracle transforms in `data/transformed/` |
| Policies + schemas | `data/policies/`, `data/schemas/` |
| Pilot corpus | 100 personas · seed 42 · **630 test events** |
| Published run | **`outputs/pilot_v2/`** (= v0.1.1 frozen outputs; historical dir name) |
| Config | `configs/pilot_v0.1.1.yaml` |

### Frozen release checksums

Canonical JSON uses `sort_keys=True` and compact separators (`,` `:`). Regenerate with `python scripts/build_split_manifest_v0.py`.

| Artifact | Path | SHA256 |
|----------|------|--------|
| Split manifest v0 | `data/ground_truth/split_manifest_v0.json` | `b15f4cebc5570a36171eb18ddca5d65d109ad18cb334268d45f43f84e15cfac0` |

`data/ground_truth/splits.json` remains the loader source for code; `split_manifest_v0.json` is the frozen audit manifest (persona counts, test-event count, checksum).

## Quick start

Use a **project virtual environment** (`.venv/`) — do not install into system Python.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

make repro-smoke    # verify headline metrics; no Ollama
make test
make lint
```

**Why activate?** Standard Python practice: your shell then uses the venv’s `python`, `pytest`, and installed packages. That matters when you run scripts or tests outside `make`.

**Without activation:** `make` targets still work if `.venv/` exists — the `Makefile` calls `.venv/bin/python`, `.venv/bin/pytest`, and `.venv/bin/ruff` directly. CI uses global `pip install` (no `.venv`); locally, create `.venv` first as above.

### Paper reproduction cheatsheet

Headline utility F1 in the paper comes from the **frozen LLM utility consumer** (`qwen3:8b`; JSON key `tier1` in metrics) — not the classical Tier-0 baseline (`make eval TIER=0`).

| Goal | Command | Output / notes |
|------|---------|----------------|
| **Verify** published numbers (start here) | `make repro-smoke` | Checks committed obs + analytics **tier1** F1 and linkage **R(z)** vs paper table (±0.02); **seconds**; no Ollama |
| **Rescore** observability utility + linkage | `make eval` | Recomputes from `data/eval_cache/` → `outputs/pilot_v2/metrics.json`; typically **a few minutes** |
| **Rescore** analytics utility | `make eval-analytics` | Recomputes from `data/eval_cache_analytics/` → `analytics_metrics.json` |
| Regenerate figures / CIs (optional) | `make figures`, `make bootstrap-cis`, … | Uses metrics JSON; see Makefile |

Use **`make repro-smoke` alone** to audit the frozen release. Use **`make eval` + `make eval-analytics`** when you want to recompute headlines from cached LLM predictions (both commands needed for the full paper table).

Full regen (`make pipeline`) requires Ollama with `qwen3:8b` for the frozen LLM utility consumers.

## Offline reproduction (no Ollama)

Paper headline numbers do **not** require a live LLM at audit time. v0.1.1 ships a frozen **evaluation registry** of pre-computed utility-consumer predictions (primary: `qwen3:8b`):

| Registry | Path | Contents |
|----------|------|----------|
| Observability consumer | `data/eval_cache/` | Per-model, per-export-condition `predictions.jsonl` (primary: `qwen3_8b/`) |
| Analytics consumer | `data/eval_cache_analytics/` | Same layout for analytics prompts |

When you run `make eval` or `make eval-analytics`, assessors **read these cached completions** and compute metrics (F1, linkage, etc.) — they do not call Ollama unless a cache entry is missing. `make repro-smoke` skips rescoring entirely and checks committed `outputs/pilot_v2/metrics.json` and `analytics_metrics.json` against expected headline tolerances.

To **regenerate** LLM consumer predictions (optional, heavy), you need Ollama + `qwen3:8b` and `make pipeline` or the observability/analytics study scripts; new runs can be consolidated back into `data/eval_cache*` via `scripts/consolidate_eval_cache.py`.

Details: [`open-sbb/consumers/README.md`](open-sbb/consumers/README.md) — primary LLM utility consumer is **`qwen3:8b`** (legacy JSON key `tier1` in metrics).

## Repository layout

```text
src/ eval/ scripts/ tests/ configs/ data/ outputs/   ← implementation (stable v0.1.1)
open-sbb/                                              ← protocol map (paper §4)
examples/                                              ← adoption by domain
docs/                                                  ← repo map, adoption path
```

**Headline metrics:** `outputs/pilot_v2/metrics.json`, `analytics_metrics.json`  
**Narrative summary:** `outputs/pilot_v2/sensitivity_report.md` — consumer sensitivity across open-weight models (primary: `qwen3:8b`)

## Paper-linked figures

| Figure | Path |
|--------|------|
| Linkage decomposition | `outputs/pilot_v2/figures/linkage_decomposition.*` |
| Utility matrix | `outputs/pilot_v2/figures/utility_matrix_heatmap.*` |
| Cross-purpose regret | `outputs/pilot_v2/figures/cross_purpose_regret_matrix.*` |
| Semantic granularity (linkage adversary suite) | `outputs/pilot_v2/additional_analyses/aa_trial4_sem_granularity_stacked.*` |

## What this repo is / is not

**In scope:** reproducible lattice evaluation, frozen v0.1.1 published run (`outputs/pilot_v2/`), BYO path (same schema IDs → same assessors).

**Out of scope:** LaTeX paper sources, Policy Studio, HIPAA/OTel certification claims, learned extractors (deferred to v0.2+), production runtime.

## License & citation

Apache-2.0 — [`LICENSE`](LICENSE). Citation: [`CITATION.cff`](CITATION.cff). Companion arXiv preprint: submitted; ID pending.

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`docs/adoption_path.md`](docs/adoption_path.md)
