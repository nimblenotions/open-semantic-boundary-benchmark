# Extension points

How to adapt Open SBB without breaking the frozen v0.1.1 release. **Discuss in an issue before changing frozen assessors or splits.**

## Summary table

| Extension | Where to start | Protocol map |
|-----------|----------------|--------------|
| New export condition | `src/transform/`, `configs/pilot_v0.1.1.yaml`, materialize `data/transformed/` | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md) |
| New policy / schema | `data/policies/`, `data/schemas/`, `src/boundary/` | [`open-sbb/policies/`](../open-sbb/policies/README.md) |
| New purpose \(T\) | policies + consumers + utility task modules | policies + consumers READMEs |
| New utility task | `src/eval/*_task.py`, eval runners | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md) |
| New adversary / linkage channel | `src/eval/adversary*.py` | [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md) |
| New operative rule | `src/eval/operative_selection.py` | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md) |
| New domain corpus | `examples/<domain>/`, generator or BYO data | [`examples/README.md`](../examples/README.md) |
| BYO exports (no regen) | [`examples/bring_your_own/`](../examples/bring_your_own/README.md) | same schema IDs → same assessors |
| Provenance / verify | `src/boundary/verify.py`, `provenance_v1.json` | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md) |

## Frozen release policy (v0.1.1)

Patch releases **must not** silently change:

- Nine primary condition IDs
- Split seed 42 / 630 test events
- Frozen LLM utility consumer prompts and primary model (`qwen3:8b`)
- Metric definitions in committed `metrics.json`

Document any change in `CHANGELOG.md` and bump semver appropriately.

## Explicitly deferred (v0.2+)

- Learned semantic extractors (`sem_medium_learned`)
- `opensbb evaluate` CLI (stub documented in BYO example)
- Domain registration spec
- Code relocation under `open-sbb/*/src/` (see [`open-sbb/LAYOUT-PLAN.md`](../open-sbb/LAYOUT-PLAN.md))

## Contributor workflow

1. Read [`adoption_path.md`](adoption_path.md)
2. Open an issue describing extension + semver impact
3. Branch, implement, run `make test` + `make repro-smoke`
4. Update relevant `open-sbb/*/README.md` if behavior visible to adopters
