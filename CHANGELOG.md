# Changelog

All notable changes to the Open Semantic Boundary Benchmark follow [Semantic Versioning](https://semver.org/).

## [0.1.3] / cikm-2026 — 2026-08-30

Software identity for the **CIKM 2026** artifact (branch `cikm-2026`, software **v0.1.3**). Same frozen experiment as the 2026-08-28 export; documentation and citation metadata now treat the CIKM paper as the canonical scientific record.

### Added

- Cite surface [`releases/cikm-2026/`](releases/cikm-2026/) — protocol assertion, focal Table 3 result, Fig. 2–4 PDFs, checksums
- `make repro-cikm-2026` — verify protocol + figure checksums **without Ollama**
- Camera-ready and post-acceptance metric trees used by the submitted paper

### Changed

- Default config is `configs/cikm_v0.1.yaml` on this branch
- README and user-facing docs explain the paper; they do not maintain a parallel “forthcoming technical report”
- Contributor documentation style lives in [`CONTRIBUTING.md`](CONTRIBUTING.md); agent documentation rules live in [`AGENTS.md`](AGENTS.md)
- `outputs/pilot_v2/` labeled **historical** (pre-camera-ready)
- `CITATION.cff` title and version (`0.1.3`); preferred citation is the ACM paper

This is not a Core / v0.2 harness inversion. `opensbb run` is not implemented on this branch. Cite branch `cikm-2026` (software v0.1.3) and the ACM paper. Do not treat v0.1.2 as the CIKM artifact.

## [0.1.2] — 2026-06-30

Git tag `opensbb-v0.1.2`. No change to frozen pilot artifacts vs v0.1.1. **This version is not the CIKM 2026 default.**

### Changed

- Citation and docs pointed at a then-planned longer write-up (since retired as an active deliverable)

## [0.1.1] — 2026-06-26

### Added

- **`open-sbb/`** protocol map (8 module READMEs; implementation at repo root)
- **`examples/`** domain index + BYO guide
- **`docs/`** — paper_to_repo, extension_points, adoption_path
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
