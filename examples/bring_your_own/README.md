# Bring your own exports (advanced / enthusiast path)

> **Early development — your mileage may vary.** Open SBB **v0.1.1** is a frozen **reference release** for the medication-adherence pilot. Evaluating **your own** exports is supported in principle (same `(z, r)` contract, same assessors) but **not productized**: no one-command CLI or adapter API yet. Expect manual steps, config edits, and rough edges. Track [issue #1](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues/1) (`opensbb evaluate`) and [issue #6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues/6) (adapters) for v0.2.

**Start here instead if you are new:** [`make repro-smoke`](../../README.md#quick-start) on the committed pilot, then [`examples/provenance/`](../provenance/README.md) for lightweight `(z, r)` examples.

## What v0.1.1 vs v0.2 means

| | v0.1.1 (now) | v0.2 (planned) |
|---|--------------|----------------|
| **Reproduce frozen pilot** | ✅ `make repro-smoke` | Same |
| **Export format contract** | ✅ Documented below; committed transforms are the reference | Same schemas |
| **Score your exports (productized)** | ⚠️ Manual enthusiast path only — **YMMV** | `opensbb evaluate`, adapters, domain registration |
| **Your own corpus / labels** | ❌ Not supported without forking ground truth | Domain registration (issue #2) |

## Question this answers

> How *could* I evaluate exports in Open SBB format without regenerating the pilot corpus?

This README is an **implementation map** for early enthusiasts and design partners — not the primary adoption path.

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

## Sample bundle (format reference)

[`sample_events.jsonl`](sample_events.jsonl) — eight held-out **test-split** exports copied from `data/transformed/sem_medium/events.jsonl`. Use it to inspect shape and to sanity-check your wiring:

```bash
make byo-smoke   # pytest: load sample → join pilot labels → provenance assessor
head -1 examples/bring_your_own/sample_events.jsonl | python -m json.tool
```

This does **not** score your custom exports; it only proves the BYO join path against frozen ground truth.

## Target workflow (v0.2 — not shipped)

```bash
# Planned — see GitHub issue #1
opensbb evaluate \
  --events examples/bring_your_own/events.jsonl \
  --purpose observability \
  --policy data/policies/obs_policy_v1.json \
  --condition redact_bracket
```

## Enthusiast workflow (v0.1.1 — manual, YMMV)

**Before you start:** open a [GitHub issue](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues/new/choose) if you hit blockers — we are actively shaping v0.2 from early feedback.

1. Match **condition IDs**, **policy IDs**, and **schema IDs** to the frozen pilot.
2. Align **`event_id`** (and usually **`persona_id`**) with `data/ground_truth/labels.jsonl` and `splits.json` — assessors join on these keys today.
3. Write `events.jsonl` under `data/transformed/{condition}/` (or register a parallel path in config).
4. Run assessors:

```bash
make eval CONFIG=configs/pilot_v0.1.1.yaml
make eval-analytics CONFIG=configs/pilot_v0.1.1.yaml
```

5. Compare to `outputs/pilot_v2/metrics.json` or your own baseline.

**Known gaps (v0.1.1):** scoring your own exports still requires manual placement under `data/transformed/`; comparing to published headline utility F1 requires frozen LLM consumer caches or Ollama regen; a different domain/corpus requires fork-level work until v0.2.

Quick trust check on the **frozen pilot** (not your BYO files):

```bash
make repro-smoke
```

## Checklist (enthusiast / design partner)

- [ ] Held-out split documented (or reuse `data/ground_truth/splits.json` event IDs)
- [ ] Same frozen LLM consumer prompts if comparing to published headline utility numbers
- [ ] Provenance `r` present if using provenance completeness operative gates
- [ ] Report \(U(T,z)\) and \(R(z)\) — do not claim regulatory certification
- [ ] Expect API and path changes in v0.2 — pin to tag `sbb-obs-0.1.1` for citeable comparisons

## Further reading

- [`../provenance/README.md`](../provenance/README.md) — lighter-weight `(z, r)` examples (no full lattice)
- [`../../open-sbb/policies/README.md`](../../open-sbb/policies/README.md)
- [`../../open-sbb/consumers/README.md`](../../open-sbb/consumers/README.md)
- [`../../open-sbb/export_lattice/README.md`](../../open-sbb/export_lattice/README.md)
- [`../../docs/extension_points.md`](../../docs/extension_points.md)
- v0.2 roadmap: [issues #1–#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues)

## Not claimed

BYO evaluation demonstrates benchmark **applicability in principle**; it is not regulatory attestation, not a supported product surface in v0.1.1, and results on custom exports are **not** comparable to the frozen pilot without explicit methodology notes.
