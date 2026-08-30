# Contributing

Thanks for helping improve the Open Semantic Boundary Benchmark.

On this tag the scientific record is the CIKM 2026 paper plus `releases/cikm-2026/`. If you edit user-facing docs, follow [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md) — explain the paper; do not invent terminology.

## Development setup

Use a project virtual environment — do not install into system Python.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make test
make lint
```

Activate before interactive work (`python`, `pytest`, editors). `make` targets also resolve `.venv/bin/` when the venv exists, so a quick `make repro-smoke` works even if you forgot to activate.

## What to contribute

- Reproduction bugs (include OS, Python version, commands run)
- README and reproducibility fixes (setup commands, artifact paths, tolerance notes)
- New export conditions or domains — **discuss in an issue first**; this tag is a frozen CIKM artifact
- Later harness work (`opensbb run`, adapters) — see [open issues](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues)

## Pull requests

1. Branch from `cikm-2026` for artifact/docs fixes on this freeze, or from `main` for later harness work.
2. Run `make test` and `make lint`. On this tag also run `make repro-cikm-2026`.
3. Keep changes scoped; do not expand scope into commercial product features.

## Frozen release policy

Patch releases (`0.1.x`) must not change assessor definitions, split seeds, or committed transform IDs without a migration note in `CHANGELOG.md`. The CIKM numbers live under `releases/cikm-2026/`; do not overwrite `outputs/pilot_v2/`.

## Code of conduct

Be respectful and precise. Benchmark claims must match what the harness actually measures.

## Security

See [`SECURITY.md`](SECURITY.md) for how to report security-sensitive issues privately.
