# Repository map

Quick navigation for newcomers. Implementation stays at the repo root for v0.1.1.

## I want to…

| Goal | Start here |
|------|------------|
| Understand the protocol | [`open-sbb/README.md`](../open-sbb/README.md) |
| Reproduce paper numbers (fast) | `make repro-smoke` |
| Reproduce full eval | `make eval`, `make eval-analytics` |
| Regenerate figures | `make figures`, `make operative-selection` |
| See domain use cases | [`examples/README.md`](../examples/README.md) |
| Evaluate my own exports (advanced) | [`examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) — enthusiast path; **YMMV** until v0.2 |
| Map paper → repo | [`paper_to_repo.md`](paper_to_repo.md) |
| Extend the benchmark | [`extension_points.md`](extension_points.md) |
| Onboarding paths | [`adoption_path.md`](adoption_path.md) |

## Directory guide

| Path | Contents |
|------|----------|
| `open-sbb/` | Protocol map (README per paper §4 module) — **docs only** |
| `src/` | Python packages: generate, transform, boundary, eval |
| `eval/` | Study CLI entrypoints |
| `scripts/` | Pipeline, cache, repro smoke |
| `tests/` | Regression tests |
| `configs/pilot_v0.1.1.yaml` | Primary frozen config |
| `data/` | Frozen pilot data, transforms, eval caches |
| `outputs/pilot_v2/` | **Open SBB v0.1.1** published metrics + figures |
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

- **`outputs/pilot_v2/`** = frozen **Open SBB v0.1.1** published run (directory name is historical).
- **`configs/pilot_v0.1.1.yaml`** = config for that release.

## Makefile targets (common)

```bash
make install
make test
make repro-smoke
make eval
make eval-analytics
make figures
make operative-selection
make bootstrap-cis
make pipeline    # full regen; requires Ollama for LLM utility consumers
```
