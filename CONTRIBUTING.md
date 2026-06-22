# Contributing

Thanks for helping improve the Open Semantic Boundary Benchmark.

## Development setup

```bash
uv venv
uv pip install -e ".[dev]"
make test
make lint
```

`make` targets use `.venv/bin/` when the venv exists; activation is optional unless you invoke `python`/`pytest` directly.

## What to contribute

- Reproduction bugs (include OS, Python version, commands run)
- README and reproducibility fixes (setup commands, artifact paths, tolerance notes)
- New export conditions or domains — **discuss in an issue first**; v0.1.1 is a frozen reference instrument
- v0.2 roadmap items — see [open issues](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues) (`help wanted`, `v0.2`, `research`)

## Pull requests

1. Branch from `main` (or the active release branch).
2. Run `make test` and `make lint`.
3. Keep changes scoped; do not expand scope into commercial product features.

## Frozen release policy

Patch releases (`0.1.x`) must not change assessor definitions, split seeds, or committed transform IDs without a migration note in `CHANGELOG.md`.

## Code of conduct

Be respectful and precise. Benchmark claims must match what the harness actually measures.
