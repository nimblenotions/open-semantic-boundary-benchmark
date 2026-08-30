# What is Semantic Boundary?

This page expands the **framework** in the CIKM 2026 paper
[*Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*](https://doi.org/10.1145/3799682.3840076)
(§1–§2). It is not a second summary of the empirical findings; those stay in the paper and the [root README](../README.md).

## The disclosure problem

Consider a medication-adherence app. Patients journal how a new prescription is going; an assistant replies in plain language. Those interaction traces may go to a triage consumer for monitoring and to an analytics pipeline. To protect privacy, traces may be transformed before export using bracket placeholders, vault tokens, LLM rewrites, or combinations thereof. Those choices say *how* text looks on egress, not *which meanings* each registered consumer will receive.

A journal event may contain medication name, dose, symptoms, occupation, and timing. The assistant may reply with a generic message instead of escalating a possible safety issue. The triage consumer needs to learn that the assistant *missed a safety escalation* at *risk recognition* without receiving the journal verbatim; the analytics consumer needs medication class, symptom categories, and side-effect signal from the same event. One event; multiple consumers; no reason to assume one export suits all of them.

Raw prose preserves information but overshares. Bracket redaction hides literals yet can strip the structure observability and analytics need. Stable vault tokens hide literal identifiers but preserve longitudinal continuity; residual semantic information can also support re-identification after identifiers are removed.

This pattern is not special to adherence journals. Similar questions arise when longitudinal traces — agent session logs, conversation histories, tool-use records — cross into observability, evaluation, or analytics. Feedback loops for debugging, monitoring, and product learning need semantic signal; aggressive string suppression can remove it. The resulting question is not simply whether information should cross a boundary, but **what representation should cross for a particular downstream purpose**.

## The framework

A **semantic boundary** is the governed crossing from a trusted collection context to a registered downstream consumer. The crossing is an export contract: observation \(x\) in the trust zone becomes export \(z\) with provenance \(r\) under purpose \(T\) and disclosure policy \(\pi\), then passes `verify` before release.

\[
(x,\ \mathrm{zone}_{in}) \xrightarrow[\pi,\ T]{\mathrm{cross}} (z,\ r) \xrightarrow{\mathrm{verify}} \mathrm{consumer}_T.
\]

Three operations implement that crossing:

- **`declare`** registers the downstream consumer, purpose \(T\), and disclosure policy \(\pi\).
- **`cross`** transforms observation \(x\) into export \(z\) with provenance \(r\).
- **`verify`** checks policy compliance and provenance completeness on \((z, r)\) before release.

Purpose and policy jointly constrain the representation released as \(z\). For semantic exports, granularity \(g\) further determines which fields and specificity levels are permitted.

Semantic exports for an observability consumer may carry `failure_mode`; exports for an analytics consumer may omit it while carrying `medication_class` or `symptom_categories`. Provenance \(r\) accompanies the export as evidence of the contract’s execution, not as a general operational log; it makes the crossing auditable.

The framework specifies the `declare`–`cross`–`verify` contract. It does not prescribe a particular production transformation or egress implementation. Semantic Boundary and the benchmark below are a disclosure framework and a protocol for comparing export contracts — not a new privacy algorithm.

## The benchmark (SBB)

The **Semantic Boundary Benchmark** (SBB) layers a protocol on that framework: registered purposes and policies, an event corpus, a frozen export lattice \(\mathcal{C}\), joint assessment of task utility \(U(T, z_{c,T})\) and linkage \(R(z_{c,T})\) on the representation released for \(T\), and **operative selection** under linkage tolerance \(R_{\max}\).

Here \(z_{c,T}\) is the export produced by lattice condition \(c\) under the contract registered for purpose \(T\). A registered purpose may contain several utility tasks (for example \(T_a\)-1 through \(T_a\)-3 and \(T_a\)-5); those tasks share \(z_{c,T}\) and its linkage assessment but retain task-specific utility.

Combined \(R(z_{c,T})\) is an unweighted mean of persona re-identification, attribute inference, and longitudinal linkage. Token recovery is a span-leak diagnostic, not a fourth term in \(R\). Combined \(R\) is a reporting convenience for operative selection, not a calibrated re-identification probability.

This repository is the public artifact of the SBB **pilot**: synthetic medication-adherence journals, 100 personas, 630 held-out events, observability and analytics purposes, nine lattice conditions. Frozen tag: `cikm-2026`.

Oracle semantic conditions use simulator fields rather than learned extraction. They isolate representation choice; they are not production extraction estimates.

## What the paper does not claim

The paper does not claim universal semantic superiority, regulatory compliance, or production-ready semantic extraction. It claims measurable, purpose-specific linkage–utility frontiers that differ across registered consumers. Policy \(\pi\) in the pilot is a machine-readable disclosure policy: `verify` checks the stated policy, not GDPR or HIPAA compliance.

## Next

Frozen Table 3 and Figures 2–4: [`../releases/cikm-2026/`](../releases/cikm-2026/).  
Paper sections to paths: [`paper_to_repo.md`](paper_to_repo.md).  
Inspect or extend the artifact: [`adoption_path.md`](adoption_path.md).
