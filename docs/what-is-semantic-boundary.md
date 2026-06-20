# What is Semantic Boundary?

This page explains the **Semantic Boundary** idea and how it relates to **Open SBB** (this repository). The paper gives the full treatment; this is the adoption-oriented overview.

---

## The problem

Teams ship sensitive traces to many downstream systems: observability vendors, analytics warehouses, eval harnesses, agent planners. The usual privacy playbook asks:

> *Which strings should we remove, tokenize, or rewrite?*

That question is necessary but incomplete. Downstream systems often need **structured meaning** (failure mode, medication class, symptom category) — not raw text, and not the same meaning for every consumer.

**Semantic Boundary** reframes egress as an **export contract**:

> *For this registered purpose, under this policy, at this granularity — which fields may cross, with what task utility and what residual linkage risk?*

---

## Semantic Boundary (the framework)

A **semantic boundary** is a governed crossing from a trusted collection zone to a registered downstream consumer.

Given a trusted observation \(x\), purpose \(T\), policy \(\pi\), and schema granularity \(g\), the boundary emits:

- **Export \(z\)** — typed semantic fields released to the consumer  
- **Provenance \(r\)** — audit record of policy version, transforms, suppressed fields, verify outcome  

```text
(x, trusted zone)  ──cross(π, T, g)──►  (z, r)  ──verify──►  consumer_T
                                              │
                                              ├── assess_utility(T, z)  →  U(T, z)
                                              └── assess_risk(z)          →  R(z)
```

### Core operations

| Operation | What it does |
|-----------|----------------|
| **declare** | Register consumer, purpose \(T\), policy \(\pi\), granularity \(g\) |
| **cross** | Transform observation \(x\) into export \((z, r)\) under \(\pi\) |
| **verify** | Check policy compliance and provenance completeness before release |
| **assess_utility** | Score task performance \(U(T, z)\) on held-out exports |
| **assess_risk** | Score linkage / leakage \(R(z)\) under declared adversaries |

### Key symbols (plain English)

| Symbol | Meaning |
|--------|---------|
| \(x\) | Raw trusted observation (journal, ticket, trace, tool log) |
| \(T\) | Registered purpose (observability triage, analytics, eval, agent trace) |
| \(\pi\) | Disclosure policy — allowed/prohibited fields, guards, provenance requirements |
| \(g\) | Granularity (coarse / medium / fine semantic schema) |
| \(z\) | Typed export the consumer receives |
| \(r\) | Provenance — *how* \(z\) was produced |
| \(U(T,z)\) | Utility for purpose \(T\) |
| \(R(z)\) | Linkage risk on export \(z\) |
| \(R_{\max}\) | Organizational linkage tolerance for operative selection |

### vs string redaction

| String-centric egress | Semantic Boundary |
|----------------------|-------------------|
| Remove/tokenize literals | Release **typed fields** under purpose + policy |
| One sanitizer for all teams | **Different valid exports** per purpose on the same incident |
| Hard to compare strategies | Benchmark **utility vs linkage** on the same events |
| Audit = “we redacted” | Audit = **provenance \(r\)** + verify gate |

**Important:** Semantic abstraction is **not** safe by construction. Coarse JSON can fail triage; fine JSON can re-link personas. The point is to make trade-offs **measurable**, not to claim privacy by default.

---

## Anchor example (medication-adherence pilot)

One journal incident can support **conflicting** legitimate exports:

**Observability consumer** needs triage labels without verbatim journal text:

```json
{
  "failure_mode": "missed_safety_escalation",
  "error_stage": "risk_recognition",
  "symptom_categories": ["vestibular", "GI"]
}
```

**Analytics consumer** needs epidemiology fields without observability routing labels:

```json
{
  "medication_class": "SSRI",
  "symptom_categories": ["vestibular", "GI"]
}
```

Same underlying event — different **purpose-bound contracts**. Bracket redaction, tokenization, and semantic JSON are comparable **lattice arms**, not interchangeable “privacy levels.”

See [`../examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) for the on-disk `events.jsonl` shape.

---

## Open SBB (this repository)

**Open Semantic Boundary Benchmark (Open SBB)** is the **open evaluation instrument** for the framework — not the production egress product.

| | Semantic Boundary (framework) | Open SBB (this repo) |
|---|------------------------------|----------------------|
| Role | Protocol: declare, cross, verify, assess | **Benchmark**: score export arms on a frozen lattice |
| Delivers | Concept + assessor contracts | Code, frozen pilot data, reproducible metrics |
| Paper | §3 framework | §4 benchmark + §5–§6 results |

Open SBB holds incidents fixed and varies **transform condition** \(c \in \mathcal{C}\) (raw, bracket, tokenize, semantic coarse/medium/fine, …). Each arm gets the same \(U(T,z)\) and \(R(z)\) assessors — the counterfactual fairness constraint.

**v0.1.1 pilot:** synthetic medication-adherence corpus · 100 personas · 630 test events · nine lattice conditions · dual purposes (observability + analytics).

---

## How the pieces connect

```text
Semantic Boundary (idea)
        │
        ├── Production crossing (future product) — declare / cross / verify at runtime
        │
        └── Open SBB (this repo) — assess_utility + assess_risk on frozen exports
                    │
                    ├── open-sbb/     ← paper §4 protocol map
                    ├── examples/     ← domains + bring-your-own
                    └── src/ data/    ← harness (stable layout)
```

---

## Where to go next

| Goal | Doc |
|------|-----|
| Benchmark protocol (paper §4) | [`../open-sbb/README.md`](../open-sbb/README.md) |
| Run repro smoke test | Root [`README.md`](../README.md) → `make repro-smoke` |
| Evaluate your exports | [`../examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) |
| Find code for linkage / operative selection | [`../open-sbb/linkage_assessment/README.md`](../open-sbb/linkage_assessment/README.md), [`../open-sbb/operative_selection/README.md`](../open-sbb/operative_selection/README.md) |
| Onboarding paths | [`adoption_path.md`](adoption_path.md) |

---

## What we do not claim

- HIPAA, FINRA, GDPR, or SOC2 **certification**
- Production-safe egress without organizational \(R_{\max}\) and governance
- Learned extractors as SOTA (oracle semantic arms are **upper bounds** for v0.1.1)
- That one export serves all downstream consumers optimally

Open SBB helps you **compare** purpose-bound export strategies with reproducible \(U\) and \(R\) — the first step toward governed semantic disclosure, not the last step toward compliance.
