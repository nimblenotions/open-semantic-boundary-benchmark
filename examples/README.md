# Examples

Open SBB evaluates **semantic disclosure strategies**: what meanings may cross a boundary for a registered purpose, with what utility and residual linkage risk.

Use Open SBB when you have **sensitive traces** that downstream systems need to learn from, but you do not want to export raw observations.

## Example domains

| Folder | Scenario | Status |
|--------|----------|--------|
| [`medication_adherence/`](medication_adherence/README.md) | **Shipped pilot** — synthetic health journaling (paper v0.1.1) | Frozen v0.1.1 run in `data/`, `outputs/pilot_v2/` (historical dir name) |
| [`bring_your_own/`](bring_your_own/README.md) | **BYO exports** — evaluate your export condition on your events | Target workflow; see current commands |
| [`agent_observability/`](agent_observability/README.md) | AI agent traces, tool calls, routing failures | Conceptual v0.1.1; SBB-Agent slice v0.2 |
| [`customer_support/`](customer_support/README.md) | Ticket + chat exports for triage vs analytics | Conceptual |
| [`financial_chatbot/`](financial_chatbot/README.md) | FINRA-style supervision abstracts | Conceptual; see provenance JSON |
| [`provenance/`](provenance/README.md) | Illustrative audit-evidence \((z,r)\) records | Synthetic JSON only |

## Core question Open SBB answers

> Most privacy tools ask: *which strings should be removed?*  
> Open SBB asks: *which meanings may be disclosed for purpose \(T\), with what \(U(T,z)\) and \(R(z)\)?*

## Quick start

```bash
make repro-smoke
```

Then open the README for your domain above.

## Not claimed

Examples are **benchmark illustrations**, not legal templates or production policies.
