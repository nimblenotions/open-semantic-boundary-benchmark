# Bring your own exports

**Most important example for adoption.** Evaluate **your** semantic exports with Open SBB frozen assessors.

## Question this answers

> How do I evaluate my own exports without regenerating the pilot corpus?

## Enterprise field map (paper Figure 1 → repo)

| Paper / product concept | Repo field (in `z`) | Typical consumer |
|-------------------------|---------------------|------------------|
| Triage routing label | `failure_mode` | Observability vendor (\(T_o\)) |
| Pipeline stage | `error_stage` | Observability vendor (\(T_o\)) |
| Drug class (not brand) | `medication_class` | Analytics warehouse (\(T_a\)) |
| Symptom abstraction | `symptom_categories` (list) | Analytics / epidemiology (\(T_a\)) |
| Policy allow/deny | `policy_action` | Governance audit |
| Input event type | `input_semantic_type` | Workflow routing |

Paper Figure 1 (`fig:anchor-example`) semantic export (conceptual):

```json
{
  "medication_class": "SSRI",
  "symptom_categories": ["vestibular", "GI"],
  "failure_mode": "missed_safety_escalation",
  "error_stage": "risk_recognition"
}
```

Those keys live inside **`z`** in the repo's `events.jsonl` format (see below).

## Actual on-disk shape (v0.1.1)

Each line in `data/transformed/{condition}/events.jsonl` is one scored export. Minimal fields:

```json
{
  "event_id": "evt_000001",
  "persona_id": "persona_001",
  "condition_id": "sem_medium",
  "schema_id": "obs_schema_medium",
  "z": {
    "medication_class": "SSRI",
    "symptom_categories": ["vestibular", "GI"],
    "failure_mode": "missed_safety_escalation",
    "error_stage": "risk_recognition",
    "input_semantic_type": "safety_escalation",
    "policy_action": "allow"
  },
  "r": {
    "policy_id": "obs_policy_v1",
    "policy_version": "1.0.0",
    "schema_id": "obs_schema_medium",
    "transform_id": "sem_medium",
    "event_id": "evt_000001",
    "fields_suppressed": ["raw_journal", "raw_completion"],
    "verify_outcome": "pass"
  },
  "verify_outcome": "pass"
}
```

**Condition IDs** in this repo use `redact_bracket` (paper shorthand: `red_bracket`). Match frozen IDs in `configs/pilot_v0.1.1.yaml` → `lattice.conditions`.

Verify against a real committed line:

```bash
head -1 data/transformed/sem_medium/events.jsonl | python -m json.tool
```

Schema contracts: `data/schemas/obs_schema_medium.json`, `data/schemas/provenance_v1.json`.

## Target workflow (v0.2 CLI)

```bash
# Planned — not fully implemented in v0.1.1
opensbb evaluate \
  --events examples/bring_your_own/events.jsonl \
  --purpose observability \
  --policy data/policies/obs_policy_v1.json \
  --condition redact_bracket
```

## Current workflow (v0.1.1)

1. Match **condition IDs**, **policy IDs**, and **schema IDs** to the frozen pilot.
2. Write `events.jsonl` under `data/transformed/{condition}/` (or register a parallel path in config).
3. Run assessors:

```bash
make eval CONFIG=configs/pilot_v0.1.1.yaml
make eval-analytics CONFIG=configs/pilot_v0.1.1.yaml
```

4. Compare to `outputs/pilot_v2/metrics.json` or your baseline.

Quick trust check (no Ollama):

```bash
make repro-smoke
```

## Checklist

- [ ] Held-out split documented (or reuse `data/ground_truth/splits.json` event IDs)
- [ ] Same frozen LLM consumer prompts if comparing to published headline utility numbers
- [ ] Provenance `r` present if using \(\tau\) operative gates
- [ ] Report \(U(T,z)\) and \(R(z)\) — do not claim regulatory certification

## Further reading

- [`../../open-sbb/policies/README.md`](../../open-sbb/policies/README.md)
- [`../../open-sbb/consumers/README.md`](../../open-sbb/consumers/README.md)
- [`../../open-sbb/export_lattice/README.md`](../../open-sbb/export_lattice/README.md)
- [`../../docs/extension_points.md`](../../docs/extension_points.md)

## Not claimed

BYO evaluation demonstrates benchmark applicability; it is not regulatory attestation.
