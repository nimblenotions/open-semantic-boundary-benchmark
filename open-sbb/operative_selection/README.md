# Operative selection

Under a declared linkage tolerance \(R_{\max}\), a lattice condition is **feasible** when \(R(z_{c,T}) \le R_{\max}\). The **risk-constrained winner** for a registered task is the feasible condition with the highest task utility. That is the rule behind paper Table 3.

Purpose \(T\) determines the export and its linkage; utility is task-specific. A condition that wins one task under a given \(R_{\max}\) may lose another even under the same purpose.

The paper also defines Pareto deprioritization (dominated conditions) and bundle feasibility (whether one condition can serve several purposes). In this pilot, provenance completeness is \(\tau = 1\) for the scored conditions, so Table 3 varies only utility and linkage; no numerical utility floors are declared.

**Cross-task regret** (paper Figure 4) measures utility lost on task \(j\) when the winner for task \(i\) is reused. Repository filenames keep the older `cross_purpose_regret_*` stem.

## Implementation

- `src/eval/operative_selection.py`
- `src/eval/advisor_figures.py` — `cross_purpose_regret_matrix` helpers (Figure 4)
- `src/eval/dual_purpose.py`

Published results: Table 3 (focal \(R_{\max}=0.45\)) and Figure 4 under [`../../releases/cikm-2026/`](../../releases/cikm-2026/). Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Verify

```bash
make repro-cikm-2026
```

That command checks the focal Table 3 row. The paper remains authoritative for the full table across linkage tolerances.

## Extend

New selection rule: [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

Operative selection compares lattice conditions under a declared \(R_{\max}\) in this protocol. It is not a prescription of a production sanitizer or a regulatory decision procedure.
