# Open Semantic Boundary Benchmark

Open SBB is a benchmark for evaluating **what semantic content should cross a boundary** from sensitive traces into downstream systems.

Most privacy tools ask: *which strings should be removed?*

Open SBB asks: *which meanings may be disclosed for a registered purpose, with what utility and residual linkage risk?*

Use it to compare export strategies for **AI observability**, **analytics**, **evaluation**, and **agent workflows** — on a counterfactual export lattice with frozen assessors.

Public home (at release): [`nimblenotions/open-semantic-boundary-benchmark`](https://github.com/nimblenotions/open-semantic-boundary-benchmark)

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
| Release acceptance checklist | [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) |

## Status: Open SBB v0.1.1

| Component | Notes |
|-----------|-------|
| Nine lattice conditions | Frozen oracle transforms in `data/transformed/` |
| Policies + schemas | `data/policies/`, `data/schemas/` |
| Pilot corpus | 100 personas · seed 42 · **630 test events** |
| Published run | **`outputs/pilot_v2/`** (= v0.1.1 frozen outputs; historical dir name) |
| Config | `configs/pilot_v0.1.1.yaml` |

## Quick start

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

make repro-smoke    # verify headline metrics; no Ollama
make test
```

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
| Observability consumer | `data/eval_cache/` | Per-model, per-lattice-arm `predictions.jsonl` (primary: `qwen3_8b/`) |
| Analytics consumer | `data/eval_cache_analytics/` | Same layout for analytics prompts |

When you run `make eval` or `make eval-analytics`, assessors **read these cached completions** and compute metrics (F1, linkage, etc.) — they do not call Ollama unless a cache entry is missing. `make repro-smoke` skips inference entirely and checks committed `outputs/pilot_v2/metrics.json` against expected headline tolerances.

To **regenerate** LLM consumer predictions (optional, heavy), you need Ollama + `qwen3:8b` and `make pipeline` or the observability/analytics study scripts; new runs can be consolidated back into `data/eval_cache*` via `scripts/consolidate_eval_cache.py`.

Details: [`open-sbb/consumers/README.md`](open-sbb/consumers/README.md) (includes **Tier-1 → `qwen3:8b` consumer** alias for code and frozen outputs).

## Repository layout

```text
src/ eval/ scripts/ tests/ configs/ data/ outputs/   ← implementation (stable v0.1.1)
open-sbb/                                              ← protocol map (paper §4)
examples/                                              ← adoption by domain
docs/                                                  ← repo map, adoption path
```

**Headline metrics:** `outputs/pilot_v2/metrics.json`, `analytics_metrics.json`  
**Narrative summary:** `outputs/pilot_v2/sensitivity_report.md` (title says “Tier-1” = paper’s primary `qwen3:8b` consumer; see [`open-sbb/consumers/README.md`](open-sbb/consumers/README.md))

## Paper-linked figures

| Figure | Path |
|--------|------|
| Linkage decomposition | `outputs/pilot_v2/figures/linkage_decomposition.*` |
| Utility matrix | `outputs/pilot_v2/figures/utility_matrix_heatmap.*` |
| Cross-purpose regret | `outputs/pilot_v2/figures/cross_purpose_regret_matrix.*` |
| Granularity stacked | `outputs/pilot_v2/additional_analyses/aa_trial4_sem_granularity_stacked.*` |

## What this repo is / is not

**In scope:** reproducible lattice evaluation, frozen pilot_v2 artifacts, BYO path (same schema IDs → same assessors).

**Out of scope:** LaTeX paper sources, Policy Studio, HIPAA/OTel certification claims, learned extractors (deferred to v0.2+), production runtime.

## License & citation

Apache-2.0 — [`LICENSE`](LICENSE). Citation: [`CITATION.cff`](CITATION.cff).

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`docs/adoption_path.md`](docs/adoption_path.md)
