# Bring your own exports

> **Experimental.** This folder is not part of the CIKM 2026 evaluation and does not provide a general external-evaluation interface.

You can represent an external transform using the same export \(z\) and provenance \(r\) structure as the frozen pilot. [`sample_events.jsonl`](sample_events.jsonl) is a tiny copy of committed observability `sem_medium` records so you can inspect that shape.

The current scoring code remains coupled to the frozen pilot's purposes, labels, split, assessors, and linkage protocol. Matching this shape does not make a result comparable to the published benchmark. Evaluating a new domain or purpose requires explicit protocol extension; see [`../../docs/extension_points.md`](../../docs/extension_points.md).

```json
{
  "event_id": "evt_000040",
  "persona_id": "persona_004",
  "condition_id": "sem_medium",
  "schema_id": "obs_schema_medium",
  "z": {
    "medication_class": "NDRI",
    "failure_mode": "assistant_ok"
  },
  "r": {
    "policy_id": "obs_policy_v1",
    "policy_version": "1.0.0",
    "schema_id": "obs_schema_medium",
    "transform_id": "sem_medium",
    "event_id": "evt_000040",
    "verify_outcome": "pass"
  }
}
```

```bash
head -1 examples/bring_your_own/sample_events.jsonl | python -m json.tool
make repro-cikm-2026
```

`make byo-smoke` checks that the sample records join the frozen pilot labels. That is a format check, not a supported evaluation API.

## Not claimed

This folder does not provide a production API, hosted evaluation service, or cross-domain leaderboard.
