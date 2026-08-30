# Documentation constitution (CIKM 2026)

This page is for people who edit the docs, including coding agents. Readers of the artifact should not need it.

**The CIKM 2026 paper is the canonical scientific narrative.** Documentation should explain, operationalize, or reproduce that narrative. It should not independently re-summarize the science using new terminology or compressed claims.

Source of truth: Gaurav Baruah, *Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*, CIKM 2026, DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076). Camera-ready source: research repo `paper/cikm-2026-short-paper-v3/main.tex`.

Do not invent a parallel “forthcoming technical report.” A later long paper would be new research, not a longer copy of this study.

## Voice

Write like the paper: explanatory sentences, concepts before notation, qualifications where needed, enough connective tissue that one sentence motivates the next.

This branch is an approachable **scientific artifact**, not a productized benchmark ecosystem. Adoption here means: a researcher can understand the framework, inspect the experiment, reproduce it, and see how they could extend it. It does not mean `pip install` → vendor plug-in → leaderboard. That is later work on `main`.

No marketing superlatives. No claims the paper does not make. Do not “improve the prose” by inventing punchier paraphrases of the findings.

## Vocabulary (use these; do not substitute)

| Concept | Canonical wording (from the paper) |
| --- | --- |
| Overall problem | What **representation** should cross a system boundary for a particular **downstream purpose**; which **meanings** each **registered consumer** will receive |
| Source | Observation \(x\) in a trusted collection context; **sensitive inputs**; **interaction traces**; **operational traces** (conversations, tool use, logs, reports); **longitudinal behavioural traces** |
| Destination | **Registered downstream consumer**; **purpose** \(T\) |
| What crosses | **Export** \(z\); **policy-governed export**; **representation**; purpose-conditioned export \(z_{c,T}\) |
| \(T\) | **Purpose**. A purpose may contain multiple **utility tasks** (e.g. \(T_o\)-1, \(T_a\)-1) |
| \(z\) | **Export** |
| \(c\) | **Lattice condition** (a transformation in the frozen set \(\mathcal{C}\)) |
| \(\pi\) | **Disclosure policy** |
| \(R_{\max}\) | **Linkage tolerance**; maximum acceptable assessed linkage |
| Semantic Boundary | The **framework** (C1) |
| SBB | **Semantic Boundary Benchmark** (C2). This repository is the public artifact of the reported SBB pilot. The GitHub project name is Open Semantic Boundary Benchmark; do not treat “Open-SBB” as a different scientific object |
| Utility \(U(T,z_{c,T})\) | Task utility of the representation released for purpose \(T\) |
| Linkage \(R(z_{c,T})\) | Residual linkage on that same export. Combined \(R\) is an unweighted mean of persona, attribute, and longitudinal channels — a **reporting convenience**, not a calibrated re-identification probability |
| Provenance \(r\) | Evidence of the contract’s execution, not a general operational log |
| Operative selection | Risk-constrained choice among lattice conditions under \(R_{\max}\) (C3) |

**Do not use in reader-facing prose** (development jargon): downstream *team*; unofficial “Open-SBB score”; “bite”; “dumb redactor”; “hero question”; “Track C” (keep that identifier in protocol/release files where it names a scoring path); forthcoming technical report; EasyChair/Sheridan paper id **4405** (leave it in maintainer archaeology such as [`CIKM-2026-RELEASE-NOTES.md`](CIKM-2026-RELEASE-NOTES.md) and research Sheridan filenames).

Prefer **purpose / consumer / task** over organizational “team.” Prefer **lattice condition** or **transformation** over vague “method.” Prefer the paper’s **forcing one condition across consumers** over a newly coined “global export.”

Paper lattice IDs (`red_bracket`, …) and repo IDs (`redact_bracket`, …) differ. When both appear, map them; do not silently mix them.

## Canonical claims (elaborate; do not replace)

From the paper’s introduction and results:

1. **Span metrics mislead.** Near-zero token recovery can coexist with high persona linkage on longitudinal traces.
2. **Purpose-specific utility prevents a global ranking.** No single lattice condition maximizes every registered task. Different tasks favour different conditions; bracket redaction can win observability triage and perform poorly on pharmacologic analytics over the same events.
3. **Operative selection is actionable.** Risk-constrained winners diverge across registered tasks. Forcing one lattice condition across consumers incurs measurable utility regret.

Also: Semantic Boundary and SBB are a disclosure framework and a benchmark for comparing export contracts — **not a new privacy algorithm**.

**Do not claim** (paper §1, §6): universal semantic superiority; regulatory compliance (GDPR/HIPAA); production-ready semantic extraction; calibrated re-identification probabilities; empirical generalization across domains.

## Page jobs

| Page | Job |
|------|-----|
| [`README.md`](../README.md) | Prose introduction to the artifact; paper assets; one-command reproduce; where to go next |
| [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md) | Readable expansion of the framework (paper §1–§2), not another findings summary |
| [`paper_to_repo.md`](paper_to_repo.md) | Navigation from paper sections/tables to paths |
| [`adoption_path.md`](adoption_path.md) | Researcher journeys: inspect, reproduce, extend |
| [`open-sbb/`](../open-sbb/README.md) | Protocol detail (may be dry) |
| [`releases/cikm-2026/`](../releases/cikm-2026/README.md) | Frozen numbers and figures |

Do not triplicate the findings (no “what we evaluate” + “headline findings” + “paper in 60 seconds”).

[`CIKM-2026-RELEASE-NOTES.md`](CIKM-2026-RELEASE-NOTES.md) is maintainer archaeology. Do not link it from the README.

## Mechanical edits only after this sheet

Do not autonomously rewrite user-facing prose for “friendliness.” After this constitution and the three human-facing pages are set, other files inherit vocabulary and lose contradictions.
