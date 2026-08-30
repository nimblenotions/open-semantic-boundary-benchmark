# Using and extending Open-SBB

This page is for people who want to **do something** with the harness, not only read the paper.

On this frozen tag there is no `opensbb run` yet. You can verify the CIKM evidence, inspect how an export is scored, rescore with the committed caches, and try a manual bring-your-own bundle. A plug-in interface for an external disclosure method is planned for a later release on `main`.

Times below are wall-clock for someone new to the repo.

## Verify the paper (~15–30 minutes)

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

That is the supported check: Table 3 at \(R_{\max}=0.45\), tokenize vs persona, figure checksums. No Ollama.

Then read [`../releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](../releases/cikm-2026/CAMERA_READY_PROTOCOL.md) and, if you want paths from the PDF, [`paper_to_repo.md`](paper_to_repo.md).

## Look at one export (~1–2 hours)

After the verify step:

1. Read [`../open-sbb/export_lattice/README.md`](../open-sbb/export_lattice/README.md) and [`../open-sbb/utility_assessment/README.md`](../open-sbb/utility_assessment/README.md).
2. Inspect a single condition:

```bash
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

3. Open the cite-surface PDFs in [`../releases/cikm-2026/figures/`](../releases/cikm-2026/figures/). PNG siblings live under `outputs/post_acceptance_experiments/` and `outputs/pilot_v2_camera_ready/figures/`.

The idea behind the protocol is in [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md).

## Rescore the committed pilot (~2–3 hours)

For people who want to **run assessors**, not only verify frozen outputs.

```bash
make eval                 # default config is configs/cikm_v0.1.yaml
make eval-analytics
make cohort-tier1         # required after eval-analytics before figures
```

No Ollama if `data/eval_cache*` is present. Do **not** overwrite `outputs/pilot_v2/`. Regenerating from scratch is `make pipeline` (needs Ollama and `qwen3:8b`).

## Bring your own exports (experimental)

[`../examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) shows the on-disk `events.jsonl` shape. It is a manual path, **not** part of the CIKM evaluation, and it will change when the plug-in harness lands.

## Contribute

1. Read [`extension_points.md`](extension_points.md) — what is frozen vs what is fair game.
2. Run `make test` and `make lint`.
3. Follow [`CONTRIBUTING.md`](../CONTRIBUTING.md). Open an issue before changing assessors or splits.

## Pre-camera-ready snapshot

`make repro-smoke` and `outputs/pilot_v2/` audit the older published run (transductive TF-IDF, mixed Ta-5). Same bundle: [Zenodo v0.1.2](https://doi.org/10.5281/zenodo.21071088). See [`../outputs/pilot_v2/HISTORICAL.md`](../outputs/pilot_v2/HISTORICAL.md). That is **not** the CIKM default.
