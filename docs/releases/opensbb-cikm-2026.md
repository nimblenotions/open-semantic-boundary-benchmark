# Open-SBB v0.1.3 / `cikm-2026` — Zenodo deposit

**Status:** GitHub tag/branch `cikm-2026` is the living artifact. The **version DOI** is minted when this tree is deposited as a new version of the existing Zenodo record. Do not invent a DOI in `CITATION.cff` until Zenodo assigns one.

This is **not** v0.2. v0.2 is the later plug-in harness.

## Why a new version

[Zenodo v0.1.2](https://doi.org/10.5281/zenodo.21071088) is the pre-camera-ready snapshot. It predates train-only TF-IDF, purpose-specific linkage, Track C Ta-5, final Table 3, final figures, and `releases/cikm-2026/`.

Zenodo’s own guidance is to create a **new version** when published files change. Each version keeps a persistent identifier; versions stay linked.

Do **not** assign the ACM article DOI to the software record. Link the paper as related work.

## Citation hierarchy

```text
ACM DOI  10.1145/3799682.3840076
        describes the science
        ▼
CIKM 2026 short paper

Zenodo version DOI  (this deposit)
        archives the exact artifact
        ▼
Open-SBB v0.1.3 / cikm-2026

Git tag  cikm-2026
        browsable source
```

After the deposit, add the new version DOI to [`CITATION.cff`](../../CITATION.cff) `identifiers` (keep 10.5281/zenodo.21071088 labeled historical).

## What to upload

From a clean checkout of **branch** `cikm-2026` at the docs freeze you intend to cite (currently ahead of the annotated tag by documentation-only commits):

- Source, `data/`, camera-ready and post-acceptance outputs already in git
- Cite surface `releases/cikm-2026/`
- `CITATION.cff` (Zenodo reads this for software metadata)

Exclude: `.venv`, `__pycache__`, uncommitted Sheridan copies, research-repo strategy docs (they are not in this repository).

## Zenodo form (checklist)

1. New version of the existing Open SBB concept DOI (do not start a disconnected record).
2. Title: **Open Semantic Boundary Benchmark**
3. Version: **0.1.3** (resource type: software)
4. Related identifier: `10.1145/3799682.3840076` — relation **is documented by** / supplement to the CIKM paper (not “is identical to”)
5. Related identifier: `10.5281/zenodo.21071088` — previous version
6. Description: paste [`scripts/zenodo_opensbb_cikm-2026_description.html`](../../scripts/zenodo_opensbb_cikm-2026_description.html)
7. License: Apache-2.0
8. Publish; copy the **version DOI** into `CITATION.cff` and the README “What to cite” table

## After publish

- Commit the DOI into `CITATION.cff` on branch `cikm-2026` (docs-only; do not rewrite science files).
- Optionally move or add a git tag `opensbb-v0.1.3` pointing at that commit. Keep annotated tag `cikm-2026` as the science freeze unless you deliberately retag.
- Leave v0.1.2 immutable.
