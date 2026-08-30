# Inspecting and extending this artifact

This page is for researchers who have the paper (or the README) and want to **work with the frozen SBB pilot** — not for a vendor plug-in workflow. There is no `opensbb run` on this tag. A later release on `main` is intended to make external transformations first-class; this branch is the scientific artifact.

Times are wall-clock for someone new to the repository.

## Reproduce the reported check (~15–30 minutes)

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

That is the supported reproduction path: Table 3 at \(R_{\max}=0.45\), token recovery versus persona linkage on the tokenize condition, and figure checksums. No Ollama.

Then read [`../releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](../releases/cikm-2026/CAMERA_READY_PROTOCOL.md). Paths from the PDF: [`paper_to_repo.md`](paper_to_repo.md). Framework: [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md).

## Inspect one export (~1–2 hours)

1. Read [`../open-sbb/export_lattice/README.md`](../open-sbb/export_lattice/README.md) (lattice \(\mathcal{C}\)) and [`../open-sbb/utility_assessment/README.md`](../open-sbb/utility_assessment/README.md).
2. Look at a single purpose-conditioned export:

```bash
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

(`redact_bracket` is `red_bracket` in the paper.)

3. Open Figures 2–4 under [`../releases/cikm-2026/figures/`](../releases/cikm-2026/figures/).

## Rescore with committed caches (~2–3 hours)

To rerun registered assessors rather than only verify frozen files:

```bash
make eval                 # default config is configs/cikm_v0.1.yaml
make eval-analytics
make cohort-tier1         # after eval-analytics, before regenerating figures
```

No Ollama if `data/eval_cache*` is present. Do not overwrite `outputs/pilot_v2/`. Regenerating lattice text from scratch is `make pipeline` (needs Ollama and `qwen3:8b`).

## Extend

[`extension_points.md`](extension_points.md) lists what is frozen (splits, assessor definitions, condition IDs) and where a new lattice condition, purpose, or adversary would land. Open an issue before changing those.

[`../examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) documents an experimental on-disk `events.jsonl` shape. It is **not** part of the CIKM evaluation.

Then `make test`, `make lint`, and [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Pre-camera-ready snapshot

`make repro-smoke` and `outputs/pilot_v2/` audit an earlier published run. Same bundle: [Zenodo v0.1.2](https://doi.org/10.5281/zenodo.21071088). See [`../outputs/pilot_v2/HISTORICAL.md`](../outputs/pilot_v2/HISTORICAL.md). That snapshot is not the CIKM default.
