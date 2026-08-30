# How to write Open-SBB documentation

This page is for people who edit the docs (including coding agents). Readers of the benchmark should not need it.

## Who you are writing for

A technically sophisticated stranger. They may have read the CIKM paper, or they may have only the repo URL. They do not know `pilot_v2`, Track C, or why two Zenodo versions exist.

Every page should answer some version of:

> What is this? Why should I care? What can I do with it? Show me one thing. How do I try it? Where do I go next?

The documentation should teach someone into using Open-SBB. It should not primarily describe the repository.

Adoption-friendly does not mean more documentation. It means fewer conceptual jumps.

## Three jobs, in this order

1. **Comprehension.** Understand the Semantic Boundary problem and this experiment without reading code.
2. **Reproduction.** Inspect or verify the CIKM evidence without learning repository history.
3. **Adoption.** See how to evaluate a disclosure method (today: inspect and extend; later: `opensbb run`).

Do not put camera-ready repair history, internal branch names, or deprecated outputs on those three paths.

## One scientific record

| Need | Authority |
|------|-----------|
| The science | CIKM 2026 paper, DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076) |
| Exact code and numbers | Git tag / branch `cikm-2026`, plus the Zenodo version of that tag when published |
| Ongoing development | `main`, after this freeze |
| Pre-camera-ready software | Zenodo [v0.1.2](https://doi.org/10.5281/zenodo.21071088) — historical, not the paper default |

There is no forthcoming technical report. A later long paper, if any, would be new research (more domains, BYO transforms, stronger adversaries), not a longer copy of this study.

Do not report an unofficial aggregate “Open-SBB score.” Cite the result card (Table 3, figures, protocol assertion).

## One job per page

| Page | Job |
|------|-----|
| [`README.md`](../README.md) | What is this, what did we find, how do I try it? |
| [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md) | Teach me the idea. |
| [`paper_to_repo.md`](paper_to_repo.md) | I read the paper; show me where everything is. |
| [`adoption_path.md`](adoption_path.md) | I want to use or extend Open-SBB. |
| [`open-sbb/`](../open-sbb/README.md) | I need exact protocol details. |
| [`releases/cikm-2026/`](../releases/cikm-2026/README.md) | I need the frozen scientific record. |

Protocol module READMEs under `open-sbb/*/` may list `outputs/pilot_v2/` paths (that tree is still on disk). They must say, near the top, that **CIKM numbers live under `releases/cikm-2026/`**, and that `pilot_v2` is the pre-repair snapshot.

[`CIKM-2026-RELEASE-NOTES.md`](CIKM-2026-RELEASE-NOTES.md) is maintainer archaeology. Do not link it from the README.

## Voice

Straightforward, explanatory, occasionally conversational. No marketing superlatives. No “enterprise-grade,” “audit-grade,” or “revolutionary.” No claims beyond this CIKM artifact.

Start from the problem. Name the reader’s goal. Explain a term before using a repo identifier (`redact_tokenize`, `tier1`, `Track C`).

When v0.2 exists, design toward this journey — do not pretend it exists on this tag:

```text
I have a disclosure method.
        ↓
What does Open-SBB test?
        ↓
opensbb run ...
        ↓
Here is my result.
        ↓
What does this result mean?
```

On `cikm-2026`, the honest adoption story is: reproduce the paper, inspect the protocol, try the experimental BYO path, wait for the plug-in harness on `main`.
