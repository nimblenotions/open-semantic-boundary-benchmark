# Open Semantic Boundary Benchmark

Open SBB is a benchmark for evaluating **what semantic content should cross a boundary** from sensitive traces into downstream systems.

Most privacy tools ask: *which strings should be removed?*

Open SBB asks: *which meanings may be disclosed for a registered purpose, with what utility and residual linkage risk?*

Use it to compare export strategies for **AI observability**, **analytics**, **evaluation**, and **agent workflows** — on a counterfactual export lattice with frozen assessors.

Public home: [`nimblenotions/open-semantic-boundary-benchmark`](https://github.com/nimblenotions/open-semantic-boundary-benchmark)

## Start here

| You are… | Read |
|----------|------|
| **What is Semantic Boundary?** | [`docs/what-is-semantic-boundary.md`](docs/what-is-semantic-boundary.md) |
| New to the benchmark | [`open-sbb/README.md`](open-sbb/README.md) |
| Looking for use cases | [`examples/README.md`](examples/README.md) |
| Bringing your own exports | [`examples/bring_your_own/README.md`](examples/bring_your_own/README.md) |
| Reproducing the paper | Run `make repro-smoke` (below) |
| Mapping paper §4 → repo | [`docs/paper_to_repo.md`](docs/paper_to_repo.md) |
| Extending the protocol | [`docs/extension_points.md`](docs/extension_points.md) |
| v0.2 roadmap (contributions) | [GitHub issues #1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues) |
| Release acceptance checklist | [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) |

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

```bash
uv venv
uv pip install -e ".[dev]"

make repro-smoke    # verify headline metrics; no Ollama
make test
make lint
```

The `Makefile` uses `.venv/bin/python`, `pytest`, and `ruff` automatically when `.venv/` exists — you do **not** need `source .venv/bin/activate` for `make` targets. Activate the venv only if you run `python` or `pytest` directly in your shell.

Optional — rescore from cached LLM consumer predictions:

```bash
make eval CONFIG=configs/pilot_v0.1.1.yaml
make eval-analytics CONFIG=configs/pilot_v0.1.1.yaml
make figures
make operative-selection
make bootstrap-cis
```

Full regen (`make pipeline`) requires Ollama with `qwen3:8b` for the frozen LLM utility consumers.

## Offline reproduction (no Ollama)

Paper headline numbers do **not** require a live LLM at audit time. v0.1.1 ships a frozen **evaluation registry** of pre-computed utility-consumer predictions (primary: `qwen3:8b`):

| Registry | Path | Contents |
|----------|------|----------|
| Observability consumer | `data/eval_cache/` | Per-model, per-export-condition `predictions.jsonl` (primary: `qwen3_8b/`) |
| Analytics consumer | `data/eval_cache_analytics/` | Same layout for analytics prompts |

When you run `make eval` or `make eval-analytics`, assessors **read these cached completions** and compute metrics (F1, linkage, etc.) — they do not call Ollama unless a cache entry is missing. `make repro-smoke` skips inference entirely and checks committed `outputs/pilot_v2/metrics.json` against expected headline tolerances.

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

Apache-2.0 — [`LICENSE`](LICENSE). Citation: [`CITATION.cff`](CITATION.cff).

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`docs/adoption_path.md`](docs/adoption_path.md)
