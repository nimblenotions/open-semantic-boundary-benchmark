# Customer support (conceptual)

## Use case

Support platforms export **ticket text**, **intent labels**, and **routing outcomes** to separate observability (failure triage) and analytics (topic/adherence cohorts) teams — often with conflicting disclosure needs.

Open SBB compares lattice arms on **the same incidents** so you can see when a sanitizer that helps triage destroys analytics utility (cross-purpose regret).

## Map to protocol

| Need | Open SBB module |
|------|-----------------|
| Compare redaction vs semantic JSON | [`open-sbb/export_lattice/`](../../open-sbb/export_lattice/README.md) |
| Separate obs vs analytics policies | [`open-sbb/policies/`](../../open-sbb/policies/README.md) |
| Pick arm under \(R_{\max}\) | [`open-sbb/operative_selection/`](../../open-sbb/operative_selection/README.md) |

## Try on shipped pilot first

The medication pilot demonstrates the **same structural conflict** (bracket helps obs, hurts analytics med-class):

```bash
make repro-smoke
# redact_bracket: observability utility ↑, analytics utility ↓ vs raw
```

## BYO

When you have ticket exports, follow [`bring_your_own/README.md`](../bring_your_own/README.md).

## Not claimed

No customer-support corpus ships in v0.1.1. This example frames **applicability**, not benchmark numbers.
