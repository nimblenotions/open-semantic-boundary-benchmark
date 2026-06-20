# Provenance examples — audit evidence (illustrative)

**Status:** Synthetic illustrations only. **Not** legal templates, compliance certifications, or production policies.

These examples show how transformation provenance `r` supports **governance and audit** alongside export `z`. Provenance does **not** make an organization HIPAA-, FINRA-, GDPR-, or SOC2-compliant; it provides **evidence** that stated controls were applied consistently.

Schema: [`data/schemas/provenance_v1.json`](../data/schemas/provenance_v1.json)

## Files

| File | Sector | Scenario |
|------|--------|----------|
| [`hipaa_phi_export.json`](hipaa_phi_export.json) | HIPAA | PHI removed/generalized before LLM egress |
| [`finra_advisor_export.json`](finra_advisor_export.json) | FINRA | Client note abstracted for AI supervision |
| [`gdpr_minimization_export.json`](gdpr_minimization_export.json) | GDPR | Age bucketed under minimization rule |
| [`middleware_audit_record.json`](middleware_audit_record.json) | Product | Per-request audit trail (middleware shape) |

## Evaluation stack

```text
Typical benchmark:     input x  →  output z     (utility U, leakage R)

Open SBB:              input x  →[π cross]  (z, r)   (U, R, governance τ)
```

## Safe claim

> Semantic Boundary provenance provides **auditable evidence** of policy-constrained semantic transformations and may **assist** organizations in demonstrating practices related to auditability, accountability, and data minimization—not regulatory compliance by itself.
