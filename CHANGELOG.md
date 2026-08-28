# Changelog

All notable changes to the Open Semantic Boundary Benchmark follow [Semantic Versioning](https://semver.org/).

## [cikm-2026] — 2026-08-28

CIKM 2026 paper **4405** reproducibility package (Full paper package, not Open-SBB Core).

### Added

- `configs/cikm_v0.1.yaml` with locked `paper_protocol` (train-only TF-IDF, purpose-specific \(R\), Track C Ta-5)
- Cite surface [`releases/cikm-2026/`](releases/cikm-2026/) — protocol assertion, Table 3 grid, Fig. 2–4 PDFs, checksums
- `make repro-cikm-2026` — verify protocol + figure checksums **without Ollama**
- Camera-ready and post-acceptance metric trees used by the submitted paper

### Changed

- Default config is `configs/cikm_v0.1.yaml` on this tag
- README is self-contained for CIKM 2026 repro; `outputs/pilot_v2/` labeled **historical**

This is not a Core / v0.2 harness inversion. `opensbb run` is not implemented on this tag.

## [0.1.2] — 2026-06-30

### Added

- Zenodo archive: [10.5281/zenodo.21071088](https://doi.org/10.5281/zenodo.21071088) (`opensbb-v0.1.2`)

### Changed

- Companion-paper status wording (*technical report forthcoming*)
- `CITATION.cff` and docs updated with Zenodo DOI

No change to frozen pilot artifacts vs v0.1.1.

## [0.1.1] — 2026-06-26

### Added

- **`open-sbb/`** protocol map (8 module READMEs; implementation at repo root)
- **`examples/`** domain index + BYO guide
- **`docs/`** — repo_map, paper_to_repo, extension_points, adoption_path
- **`make repro-smoke`** — verify frozen headline metrics without Ollama; **external repro verified** (2026-06-22)
- Standalone benchmark layout; v0.1.1 frozen published run (100 personas, 630 test events; `outputs/pilot_v2/`)
- **`data/ground_truth/split_manifest_v0.json`** — frozen split audit manifest + README SHA256
- **`data/schemas/boundary_bundle_v0.schema.json`** — JSON Schema for `boundary_bundle_v0.json`
- **Roadmap issues** ([#1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues)) — CLI stub, domain registration, scenario pack proposal, results manifest, BYO adapters, provenance completeness research
- **GitHub issue templates** — bug/reproduction, benchmark proposal, question

### Changed

- Plain-language documentation sweep — retired internal labels (Tier-1, I0/I1, frozen tier) in public docs and report generators; code JSON keys and module names unchanged
- Ruff lint clean (`make lint`) — unused imports, ambiguous loop names, dead assignments

## [0.1.0] — pre-release prototype

- Early lattice harness development (superseded by Open SBB v0.1.1)
