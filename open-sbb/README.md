# Protocol map

Exact protocol detail for people who already know what Open-SBB is testing.

CIKM paper numbers and figures live in [`../releases/cikm-2026/`](../releases/cikm-2026/). Implementation stays at the repo root (`src/`, `data/`, `eval/`).

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

## Modules

| Module | README |
|--------|--------|
| Synthetic pilot | [`synthetic_pilot_data/`](synthetic_pilot_data/README.md) |
| Export lattice | [`export_lattice/`](export_lattice/README.md) |
| Policies | [`policies/`](policies/README.md) |
| Consumers | [`consumers/`](consumers/README.md) |
| Utility assessment | [`utility_assessment/`](utility_assessment/README.md) |
| Linkage assessment | [`linkage_assessment/`](linkage_assessment/README.md) |
| Operative selection | [`operative_selection/`](operative_selection/README.md) |
| Transformation provenance | [`transformation_provenance/`](transformation_provenance/README.md) |

Where the paper maps onto these folders: [`../docs/paper_to_repo.md`](../docs/paper_to_repo.md).  
Verify: `make repro-cikm-2026`.
