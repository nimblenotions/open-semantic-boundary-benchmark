# Protocol map

Protocol modules for the Semantic Boundary Benchmark (SBB) as instantiated in this CIKM 2026 artifact. Frozen numbers and figures: [`../releases/cikm-2026/`](../releases/cikm-2026/). Implementation is at the repository root (`src/`, `data/`, `eval/`).

```text
Synthetic pilot corpus
        ↓
Export lattice  (policy π materializes each condition c)
        ↓
Utility U(T, z_{c,T})  +  linkage R(z_{c,T})
        ↓
Operative selection under R_max
        ↓
Provenance r and verify
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

Paper → paths: [`../docs/paper_to_repo.md`](../docs/paper_to_repo.md).  
Verify: `make repro-cikm-2026`.
