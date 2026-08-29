# Repository map

Quick navigation for newcomers. Implementation stays at the repo root.

## I want to…

| Goal | Start here |
|------|------------|
| Understand the protocol | [`open-sbb/README.md`](../open-sbb/README.md) |
| Inspect Table 3 / Figs. 2–4 | [`../releases/cikm-2026/`](../releases/cikm-2026/) |
| Reproduce CIKM 2026 (fast) | `make repro-cikm-2026` |
| Historical v0.1.1 headlines | `make repro-smoke` |
| Reproduce full eval | `make eval`, `make eval-analytics` |
| See domain use cases | [`examples/README.md`](../examples/README.md) |
| Evaluate my own exports (advanced) | [`examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) — **YMMV** until v0.2 |
| Map paper → repo | [`paper_to_repo.md`](paper_to_repo.md) |
| Extend the benchmark | [`extension_points.md`](extension_points.md) |
| Onboarding paths | [`adoption_path.md`](adoption_path.md) |

## Directory guide

| Path | Contents |
|------|----------|
| `open-sbb/` | Protocol map (README per paper §4 module) — **docs only** |
| `src/` | Python packages: generate, transform, boundary, eval |
| `eval/` | Study CLI entrypoints |
| `scripts/` | Pipeline, cache, repro verify |
| `tests/` | Regression tests |
| `configs/cikm_v0.1.yaml` | CIKM 2026 paper protocol (default) |
| `configs/pilot_v0.1.1.yaml` | Historical v0.1.1 config |
| `data/` | Frozen pilot data, transforms, eval caches |
| `releases/cikm-2026/` | Cite surface: Table 3, Figs. 2–4, protocol |
| `outputs/pilot_v2_camera_ready/`, `outputs/post_acceptance_experiments/` | Canonical CIKM metrics |
| `outputs/pilot_v2/` | Historical v0.1.1 snapshot — not the CIKM default |
| `examples/` | Adoption examples by domain |

## By protocol concern

| Concern | Code | Data | Outputs |
|---------|------|------|---------|
| Lattice transforms | `src/transform/` | `data/transformed/` | metrics JSON |
| Policies / schemas | `src/boundary/` | `data/policies/`, `data/schemas/` | config snapshot |
| Consumers (LLM + classical baselines) | `src/eval/tier*_consumer.py` | `data/eval_cache*` | metrics JSON |
| Synthetic corpus | `src/generate/` | `data/raw/`, `data/ground_truth/` | — |
| Utility | `eval/run_*_study.py` | caches + transforms | `metrics.json`, figures |
| Linkage | `src/eval/adversary*.py` | transforms | linkage in metrics, figures |
| Operative rules | `src/eval/operative_selection.py` | — | `operative_selection/` |
| Provenance | `src/boundary/verify.py` | `examples/provenance/` | `boundary_bundle_v0.json` |

## Naming

- **`releases/cikm-2026/`** = paper cite surface (Table 3, Figs. 2–4).
- **`outputs/pilot_v2_camera_ready/`** + **`outputs/post_acceptance_experiments/`** = canonical CIKM metric trees.
- **`outputs/pilot_v2/`** = historical **Open SBB v0.1.1** snapshot (transductive TF-IDF, mixed Ta-5).
- **`configs/cikm_v0.1.yaml`** = default config on this tag; **`configs/pilot_v0.1.1.yaml`** = historical.

## Makefile targets (common)

```bash
make install
make test
make repro-cikm-2026   # CIKM 2026 protocol + figure checksums
make repro-smoke       # historical v0.1.1 headlines
make eval
make eval-analytics
make pipeline          # full regen; requires Ollama for LLM utility consumers
```
