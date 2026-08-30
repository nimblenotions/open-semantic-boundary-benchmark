# Contributing

Thanks for helping improve the Open Semantic Boundary Benchmark.

For the `cikm-2026` release, the CIKM 2026 paper and the supporting materials under [`releases/cikm-2026/`](releases/cikm-2026/) define the frozen scientific artifact.

When editing documentation, preserve the terminology and scientific claims of the CIKM 2026 paper. Introduce concepts before notation, avoid unsupported generalizations or compliance claims, and do not introduce new scientific terminology for concepts already named in the paper. The paper and [`releases/cikm-2026/`](releases/cikm-2026/) are the authoritative references for the published artifact.

## Development setup

Use a project virtual environment rather than installing dependencies into the system Python environment.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make test
make lint
```

Activate the environment before interactive work with `python`, `pytest`, or an editor. When a `.venv` is present, repository `make` targets can also resolve the corresponding executables directly.

## What to contribute

Contributions to the frozen CIKM artifact are especially useful when they improve reproducibility, correctness, or clarity. Examples include:

* reproduction bugs, with the operating system, Python version, and commands needed to reproduce the problem;
* README and documentation fixes, including setup instructions, artifact paths, and terminology corrections; and
* fixes to tests, verification scripts, or packaging that preserve the reported experimental protocol.

Changes that introduce new transformation conditions, benchmark domains, purposes, assessors, or other scientific extensions should be discussed in an issue first because they may change the scope of the frozen artifact.

Development beyond the CIKM 2026 artifact should normally target `main`.

## Pull requests

1. Branch from `cikm-2026` for fixes to the frozen artifact or its documentation, or from `main` for subsequent benchmark development.

2. Run:

   ```bash
   make test
   make lint
   ```

   For changes affecting the CIKM artifact, also run:

   ```bash
   make repro-cikm-2026
   ```

3. Keep each pull request focused on the change being proposed.

## Frozen release policy

Patch releases in the `0.1.x` series must preserve the scientific protocol associated with the CIKM 2026 artifact. In particular, changes to assessor definitions, data-split seeds, or committed transformation-condition identifiers require explicit documentation and should not silently alter reported results.

The frozen reported artifacts under [`releases/cikm-2026/`](releases/cikm-2026/) and historical evaluation outputs retained for provenance should not be overwritten as part of unrelated changes.

## Code of conduct

Be respectful, constructive, and precise. Claims about the benchmark should reflect what the implementation and reported evaluations actually measure.

## Security

See [`SECURITY.md`](SECURITY.md) for instructions on reporting security-sensitive issues privately.
