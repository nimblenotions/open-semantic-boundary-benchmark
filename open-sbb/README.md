# Open SBB — protocol map

Open SBB is a **benchmark protocol**, not a single dataset. This folder is a **documentation map** to the implementation at the repository root. For v0.1.1, code, data, and outputs stay in `src/`, `data/`, and `outputs/` so you can clone and reproduce without learning a new package layout.

## Protocol flow

```text
Synthetic pilot data
        ↓
Export lattice  (+ policies π materialize each condition)
        ↓
Utility assessment  +  Linkage assessment
        ↓
Operative selection
        ↓
Transformation provenance (τ, verify)
```

Policies and consumers are registered **before** scoring: the same export condition can yield different typed exports per purpose \(T_o\) vs \(T_a\).

## Module index

| Protocol module | Paper § | README | Role |
|-----------------|---------|--------|------|
| Synthetic pilot | §4.3 | [`synthetic_pilot_data/`](synthetic_pilot_data/README.md) | Corpus \(W\), split, labels |
| Export lattice | §4.1 | [`export_lattice/`](export_lattice/README.md) | Nine frozen conditions \(z,r\) |
| Policies | §4.2 | [`policies/`](policies/README.md) | Disclosure bundles π, schemas |
| Consumers | §4.2 | [`consumers/`](consumers/README.md) | Frozen assessor contracts |
| Utility assessment | §4.4 | [`utility_assessment/`](utility_assessment/README.md) | `assess_utility` → \(U(T,z)\) |
| Linkage assessment | §4.4 | [`linkage_assessment/`](linkage_assessment/README.md) | `assess_risk` → \(R(z)\) |
| Operative selection | §4.5 | [`operative_selection/`](operative_selection/README.md) | Pareto, \(R_{\max}\), bundles |
| Transformation provenance | §4.6 | [`transformation_provenance/`](transformation_provenance/README.md) | \(\tau\), `verify`, BYO \((z,r)\) |

## Paper §4 → current repo locations

| Protocol module | Paper section | Current code | Current data | Current outputs |
|-----------------|---------------|--------------|--------------|-----------------|
| Synthetic pilot | §4.3 | `src/generate/` | `data/raw/`, `data/ground_truth/` | — |
| Export lattice | §4.1 | `src/transform/`, `eval/run_*` (materialize) | `data/transformed/`, `data/transformed_analytics/`, `data/llm_transform_cache/` | (scores in metrics JSON) |
| Policies | §4.2 | `src/boundary/policy_check.py` | `data/policies/`, `data/schemas/` | — |
| Consumers | §4.2 | `src/eval/tier0_consumer.py`, `tier1_consumer.py`, `tier1_analytics_consumer.py` (legacy module names) | `data/eval_cache/`, `data/eval_cache_analytics/` | cached LLM consumer predictions |
| Utility assessment | §4.4 | `src/eval/observability_task.py`, `analytics_task.py`, `eval/run_obs_study.py`, `run_analytics_study.py` | reads lattice + caches | `outputs/pilot_v2/metrics.json`, `analytics_metrics.json` |
| Linkage assessment | §4.4 | `src/eval/adversary*.py`, `adversary_trial4.py` (linkage adversary suite) | same transforms | linkage in metrics + `outputs/pilot_v2/figures/linkage_*` |
| Operative selection | §4.5 | `src/eval/operative_selection.py`, `eval/run_operative_selection.py` | — | `outputs/pilot_v2/operative_selection/` |
| Provenance | §4.6 | `src/boundary/verify.py`, `cross.py`, `provenance_score.py` | `examples/provenance/` | `outputs/pilot_v2/boundary_bundle_v0.json` |

## Naming alias

| Name | Meaning |
|------|---------|
| **Open SBB v0.1.1** | Citeable protocol release (paper, CITATION.cff) |
| **`outputs/pilot_v2/`** | Frozen published run for v0.1.1 (historical directory name) |
| **`configs/pilot_v0.1.1.yaml`** | Primary config for this release |

## Reproduce (no Ollama)

See the [paper reproduction cheatsheet](../README.md#paper-reproduction-cheatsheet) in the root README. Short form:

```bash
make repro-smoke          # verify obs + analytics tier1 F1 + linkage R(z) — seconds
make eval                 # rescore observability from data/eval_cache/
make eval-analytics       # rescore analytics from data/eval_cache_analytics/
make figures              # paper-linked figures from committed metrics
```

Headline utility F1 is under JSON key **`tier1`** (LLM consumer `qwen3:8b`), not Tier-0.

## Further reading

| Doc | Purpose |
|-----|---------|
| Companion pre-print | submitted; id pending — full framework + pilot results |
| [`../docs/what-is-semantic-boundary.md`](../docs/what-is-semantic-boundary.md) | Framework vs benchmark — start here for concepts |
| [`../docs/adoption_path.md`](../docs/adoption_path.md) | Onboarding paths (quick repro → rescore → contributor) |
| [`../docs/paper_to_repo.md`](../docs/paper_to_repo.md) | Paper section index |
| [`../docs/extension_points.md`](../docs/extension_points.md) | How to extend the protocol |
| [`../examples/README.md`](../examples/README.md) | Domain examples + BYO |

## Not claimed

Open SBB measures utility and linkage on **released exports** under declared assessors. It does not certify HIPAA compliance, OTel conformance, or production safety.
