# Transformation provenance

## What this module is

**Provenance** \(r\) records policy version, transform identity, and field lineage. **Completeness** \(\tau(z,r)\) gates operative feasibility. `verify` checks completeness and raw-substring replay.

## Paper connection

Maps to **§4.6 Transformation Provenance**.

## Current implementation

Code:

- `src/boundary/verify.py` — `verify` gate
- `src/boundary/cross.py` — crossing with provenance emission
- `src/eval/provenance_score.py` — completeness scoring
- `src/generate/provenance_targets.py` — target generation for pilot

Data:

- `data/schemas/provenance_v1.json`
- `data/schemas/boundary_bundle_v0.schema.json`
- `examples/provenance/hipaa_phi_export.json`
- `examples/provenance/finra_advisor_export.json`
- `examples/provenance/gdpr_minimization_export.json`
- `examples/provenance/middleware_audit_record.json`

Outputs:

- `outputs/pilot_v2/boundary_bundle_v0.json`
- `outputs/pilot_v2/metrics.json` → `conditions[*].provenance.completeness`
- `outputs/pilot_v2/operative_selection/provenance_gate_ablation.json`
- `outputs/pilot_v2/operative_selection/provenance_gate_ablation.png`

## Reproduce

```bash
make repro-smoke
python -c "import json; print(json.load(open('outputs/pilot_v2/metrics.json'))['conditions']['raw']['provenance'])"
ls examples/provenance/
```

## Extend

BYO exports must attach `r` matching `provenance_v1.json`. See [`../../examples/bring_your_own/README.md`](../../examples/bring_your_own/README.md).

## Not claimed

Provenance assists auditability; it does not imply HIPAA, FINRA, GDPR, or SOC2 compliance.
