# Adoption path

Structured onboarding for paper readers, reproducers, and contributors.

Time labels are **realistic wall-clock estimates** for someone new to the repo.

## Paper reader — ~5 minutes

**Goal:** understand what the CIKM 2026 artifact contains.

1. Read the [root README](../README.md) (especially *Paper in 60 seconds*).
2. Open [`../releases/cikm-2026/table3_operative_grid.md`](../releases/cikm-2026/table3_operative_grid.md).
3. Open Figs. 2–4 under [`../releases/cikm-2026/figures/`](../releases/cikm-2026/figures/).
4. Optionally run `make repro-cikm-2026` (after the install steps below).

## Reproducer — ~15–30 minutes

**Goal:** verify the submitted CIKM protocol without Ollama.

1. Clone and create a venv (`uv venv`, `uv pip install -e ".[dev]"`) — **~5–10 min**.
2. Run `make repro-cikm-2026` — **seconds**. Checks Table 3 @ 0.45, `red_tokenize` token vs persona, and figure checksums.
3. Read [`../releases/cikm-2026/CAMERA_READY_PROTOCOL.md`](../releases/cikm-2026/CAMERA_READY_PROTOCOL.md).
4. Follow [`paper_to_repo.md`](paper_to_repo.md) if you want §-to-path mapping.

Optional: skim [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md) and [`../open-sbb/README.md`](../open-sbb/README.md).

## Understand the protocol (~1–2 hours)

1. Complete the reproducer path.
2. Read [`../open-sbb/export_lattice/README.md`](../open-sbb/export_lattice/README.md) and [`../open-sbb/utility_assessment/README.md`](../open-sbb/utility_assessment/README.md).
3. Inspect one export condition:

```bash
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

4. Browse the cite-surface PDFs, or the PNG siblings under `outputs/post_acceptance_experiments/` / `outputs/pilot_v2_camera_ready/figures/`.

## Rescore the committed pilot (~2–3 hours total)

For people who want to **run assessors**, not just verify frozen outputs.

```bash
make eval                 # default config is configs/cikm_v0.1.yaml
make eval-analytics
make cohort-tier1         # required after eval-analytics before figures
```

No Ollama if `data/eval_cache*` is present. Do **not** overwrite `outputs/pilot_v2/`. Full regen from scratch is `make pipeline` (needs Ollama + `qwen3:8b`).

**Optional / advanced:** [`../examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) — **YMMV**; not part of the CIKM evaluation.

## Contributor path (~half day first time)

1. Read [`extension_points.md`](extension_points.md) and [`paper_to_repo.md`](paper_to_repo.md).
2. Run `make test` and `make lint`.
3. Follow [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Reviewer path (paper ↔ repo) (~30–60 min)

1. [`paper_to_repo.md`](paper_to_repo.md).
2. `make repro-cikm-2026` + spot-check protocol folders under `open-sbb/`.

## Historical v0.1.1 / Zenodo

`make repro-smoke` and `outputs/pilot_v2/` audit the **pre-repair** published snapshot (transductive TF-IDF, mixed Ta-5). Same bundle: [Zenodo 10.5281/zenodo.21071088](https://doi.org/10.5281/zenodo.21071088). See [`../outputs/pilot_v2/HISTORICAL.md`](../outputs/pilot_v2/HISTORICAL.md). **Not** the CIKM default.

```bash
python -c "import json; print(json.load(open('outputs/pilot_v2/metrics.json'))['conditions']['raw']['tier1']['failure_mode_macro_f1'])"
```

## Strategic framing

| Layer | Role |
|-------|------|
| **Semantic Boundary** | Framework |
| **Open-SBB** | Benchmark / evaluation instrument |
| **CIKM 2026 artifact** | This frozen experiment ([DOI](https://doi.org/10.1145/3799682.3840076)) |
