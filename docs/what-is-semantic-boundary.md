# What is Semantic Boundary?

Teams ship sensitive traces to observability vendors, analytics warehouses, eval harnesses, and agents. The usual question is:

> Which strings should we remove, tokenize, or rewrite?

That question is necessary but incomplete. Downstream systems often need **structured meaning** — a failure mode, a medication class, a symptom category — not raw text, and not the same meaning for every consumer.

**Semantic Boundary** asks a different question:

> For this registered purpose, under this policy, at this granularity — which meanings may cross, with what task utility and what residual linkage risk?

**Open SBB** (this repository) is the evaluation instrument for that idea. It does not ship production egress. It measures whether candidate exports preserve utility while limiting linkage.

The peer-reviewed account of this study is
[*Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*](https://doi.org/10.1145/3799682.3840076)
(CIKM 2026). Cite that paper for the science.

---

## The framework

A **semantic boundary** is a governed crossing from a trusted collection zone to a registered downstream consumer.

One sensitive event can support **different legitimate exports** for different purposes — not one sanitizer for every team:

```text
Raw event (x)
      │
      ▼
Semantic Boundary  (policy, purpose, granularity)
      │
      ├──► Observability export  ──► utility, linkage, provenance
      ├──► Analytics export      ──► utility, linkage, provenance
      ├──► Evaluation export     ──► …  (not in this pilot)
      └──► Agent export          ──► …  (not in this pilot)
```

- **Utility** \(U(T,z)\) — can the consumer do its job on export \(z\)?
- **Linkage** \(R(z)\) — how much re-identification risk remains in \(z\)?
- **Provenance** — how \(z\) was produced (policy version, transforms, verify outcome)

The CIKM pilot benchmarks **observability** and **analytics** on a frozen medication-adherence corpus. Evaluation and agent slices in the sketch above are examples of where the framework can go; they are not part of this artifact.

### What each crossing produces

Given a trusted observation \(x\), purpose \(T\), policy \(\pi\), and schema granularity \(g\), a crossing emits an export \(z\) (the fields the consumer receives) and a provenance record of how it was made. Then:

```text
(x, trusted zone)  ──cross──►  export z  ──verify──►  consumer
                                  │
                                  ├── assess_utility(T, z)  →  U(T, z)
                                  └── assess_risk(z)        →  R(z)
```

| Operation | What it does |
|-----------|----------------|
| **declare** | Register consumer, purpose, policy, granularity |
| **cross** | Transform the observation into an export under policy |
| **verify** | Check policy compliance and provenance before release |
| **assess_utility** | Score task performance on held-out exports |
| **assess_risk** | Score linkage under declared adversaries |

### vs string redaction

| String-centric egress | Semantic Boundary |
|----------------------|-------------------|
| Remove or tokenize literals | Release **typed fields** under purpose and policy |
| One sanitizer for all teams | **Different valid exports** per purpose on the same incident |
| Hard to compare strategies | Benchmark **utility vs linkage** on the same events |
| Audit = “we redacted” | Audit = provenance plus a verify gate |

Semantic abstraction is **not** safe by construction. Coarse JSON can fail triage; fine JSON can re-link personas. The point is to make the trade-off **measurable**, not to claim privacy by default.

---

## One incident, two legitimate exports

The pilot uses synthetic medication-adherence journals. One incident can support conflicting contracts:

**Observability** needs triage labels without verbatim journal text:

```json
{
  "failure_mode": "missed_safety_escalation",
  "error_stage": "risk_recognition",
  "symptom_categories": ["vestibular", "GI"]
}
```

**Analytics** needs epidemiology fields without observability routing labels:

```json
{
  "medication_class": "SSRI",
  "symptom_categories": ["vestibular", "GI"]
}
```

Bracket redaction, tokenization, and semantic JSON are comparable **methods** on the same events, not interchangeable “privacy levels.”

---

## What Open SBB is

Open SBB holds incidents fixed and varies the export method (raw, bracket, tokenize, semantic coarse/medium/fine, and so on). Each method gets the same utility and linkage assessors.

This artifact: synthetic medication-adherence corpus · 100 personas · 630 test events · nine methods · observability and analytics. Frozen tag: `cikm-2026`.

| | Semantic Boundary | Open SBB |
|---|-------------------|----------|
| Role | Framework: declare, cross, verify, assess | Benchmark: score export methods on a frozen set of events |
| Delivers | The idea and the assessor contracts | Code, frozen data, reproducible metrics |
| In the paper | §2 | §3–§5 |

---

## What we do not claim

- HIPAA, FINRA, GDPR, or SOC 2 certification
- Production-safe egress without an organizational linkage ceiling and governance
- That learned extractors are state of the art (oracle semantic arms here are **upper bounds**)
- That one export serves every downstream consumer optimally

---

## Next

Paper tables and figures: [`../releases/cikm-2026/`](../releases/cikm-2026/).  
Where the paper maps onto this repo: [`paper_to_repo.md`](paper_to_repo.md).  
If you want to run or extend the harness: [`adoption_path.md`](adoption_path.md).
