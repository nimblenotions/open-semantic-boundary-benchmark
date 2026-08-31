# Transformation provenance

Provenance \(r\) accompanies export \(z\) as evidence that the declared `declare`–`cross`–`verify` contract was executed. It is not a general operational log.

In this artifact, \(r\) records `policy_id`, `policy_version`, `schema_id`, `transform_id`, `event_id`, and `verify_outcome`, and may list `fields_suppressed`. Completeness \(\tau(z,r)\) is the fraction of exports whose required provenance fields are present.

`src/boundary/verify.py` checks that the policy’s required provenance fields are present on \(r\) and, when raw source strings are supplied, that those strings are not replayed verbatim in \(z\). Prohibited fields and combinations are checked by `src/boundary/policy_check.py` during `cross`, not inside `verify.py`.

The paper includes \(\tau \ge \tau_{\min}\) in the operative-selection constraint. In this pilot, scored conditions have complete provenance (\(\tau = 1\)), so Table 3 is determined by utility and \(R \le R_{\max}\) only.

## Implementation

- `src/boundary/cross.py` — emit \((z, r)\)
- `src/boundary/verify.py` — provenance fields and optional raw-substring check
- `src/boundary/policy_check.py` — field and combination prohibitions
- `src/eval/provenance_score.py` — completeness \(\tau\)
- `data/schemas/provenance_v1.json`

Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Verify

```bash
make repro-cikm-2026
python -m json.tool data/schemas/provenance_v1.json | head -30
```

## Extend

BYO exports that use repository tooling should attach \(r\) matching `provenance_v1.json`. See [`../../examples/bring_your_own/README.md`](../../examples/bring_your_own/README.md) (experimental; not part of the CIKM evaluation).

## Not claimed

Provenance supports auditability of the declared contract. It does not establish GDPR, HIPAA, or other regulatory compliance.
