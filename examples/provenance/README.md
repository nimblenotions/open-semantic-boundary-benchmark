# Provenance examples

**Status:** Synthetic illustrations only. These files are not legal templates, compliance certifications, production policies, or schema-valid instances of the CIKM provenance contract.

They exist so that provenance \(r\) is tangible: an export can suppress identifiers, release permitted semantic categories, and record which policy, schema, and transformation were used. They do not establish regulatory compliance and do not define a product interface.

The CIKM contract is [`../../data/schemas/provenance_v1.json`](../../data/schemas/provenance_v1.json). Committed pilot records use that schema under `data/transformed/` and `data/transformed_analytics/`.

## Files

Filenames retain historical labels. The rows are **illustrative contexts**, not implementations of those regimes.

| File | Illustrative context | What the record shows |
|------|----------------------|------------------------|
| [`hipaa_phi_export.json`](hipaa_phi_export.json) | health-data disclosure | identifiers suppressed; medication class exported; policy/transform/schema recorded |
| [`finra_advisor_export.json`](finra_advisor_export.json) | financial-advice supervision | client and holding literals suppressed; coarse intent exported |
| [`gdpr_minimization_export.json`](gdpr_minimization_export.json) | data-minimization scenario | exact age and city suppressed; bucketed fields exported |

## Not claimed

These examples do not establish GDPR, HIPAA, FINRA, or other regulatory compliance.
