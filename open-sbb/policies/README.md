# Policies

Disclosure policy \(\pi\) is the versioned contract registered with a purpose \(T\). In this artifact it records prohibited export fields, prohibited field combinations, granularity caps that select a schema family, and required provenance fields. Permitted semantic fields for a given granularity live in the corresponding schema files, not as a separate “allowed fields” list in the policy JSON.

`verify` checks the declared provenance fields (and, when raw strings are supplied, verbatim replay of source text). Field and combination prohibitions are applied by `policy_check` during `cross`.

## Implementation

- `src/boundary/policy_check.py` — prohibited fields, combination guards, granularity-cap lookup
- `src/boundary/cross.py` — emit \((z, r)\) under \(\pi\)
- `src/boundary/verify.py` — provenance completeness and optional raw-substring check

Data:

- `data/policies/obs_policy_v1.json`
- `data/policies/analytics_policy_v1.json`
- `data/schemas/obs_schema_{coarse,medium,fine}.json`
- `data/schemas/analytics_schema_{coarse,medium,fine}.json`
- `data/schemas/provenance_v1.json`

Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Verify

```bash
make repro-cikm-2026
python -m json.tool data/policies/obs_policy_v1.json | head -40
```

## Extend

Add policy JSON under `data/policies/` and matching schemas under `data/schemas/`. See [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

Policy JSON is a **benchmark contract**. Verification of that contract does not establish GDPR, HIPAA, or other regulatory compliance.
