# Changelog

All notable changes to the Open Semantic Boundary Benchmark follow [Semantic Versioning](https://semver.org/).

## [0.1.1] — unreleased

### Added

- Adoption-first **`open-sbb/`** protocol map (8 module READMEs; no code moves)
- **`examples/`** domain index + BYO guide
- **`docs/`** — repo_map, paper_to_repo, extension_points, adoption_path
- **`make repro-smoke`** — verify frozen headline metrics without Ollama; **external repro verified** (2026-06-22)
- Standalone benchmark layout; v0.1.1 frozen published run (100 personas, 630 test events; `outputs/pilot_v2/`)
- **`data/ground_truth/split_manifest_v0.json`** — frozen split audit manifest + README SHA256
- **`data/schemas/boundary_bundle_v0.schema.json`** — JSON Schema for `boundary_bundle_v0.json`

### Changed

- Plain-language documentation sweep — retired internal labels (Tier-1, I0/I1, frozen tier) in public docs and report generators; code JSON keys and module names unchanged

## [0.1.0] — pre-release prototype

- Early lattice harness development (superseded by Open SBB v0.1.1)
