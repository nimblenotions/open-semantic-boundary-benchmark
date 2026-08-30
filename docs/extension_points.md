# Extension points

How to adapt this SBB artifact without silently changing the frozen CIKM experiment. **Discuss in an issue before changing assessors or splits.**

This tag (`cikm-2026`) is a frozen scientific artifact. The plug-in harness for an external disclosure method is not here yet; see [open issues](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues).

## Summary table

| Extension | Where to start | Protocol map |
|-----------|----------------|--------------|
| New export condition | `src/transform/`, `configs/cikm_v0.1.yaml`, materialize `data/transformed/` | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md) |
| New policy / schema | `data/policies/`, `data/schemas/`, `src/boundary/` | [`open-sbb/policies/`](../open-sbb/policies/README.md) |
| New purpose | policies + consumers + utility task modules | policies + consumers READMEs |
| New utility task | `src/eval/*_task.py`, eval runners | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md) |
| New adversary / linkage channel | `src/eval/adversary*.py` | [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md) |
| New operative rule | `src/eval/operative_selection.py` | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md) |
| New domain corpus | `examples/<domain>/`, generator or BYO data | [`examples/README.md`](../examples/README.md) |
| BYO exports (manual, experimental) | [`examples/bring_your_own/`](../examples/bring_your_own/README.md) | same schema IDs → same assessors; not part of the CIKM evaluation |
| Provenance / verify | `src/boundary/verify.py`, `provenance_v1.json` | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md) |

## Frozen on this tag

Do not silently change:

- The nine primary condition IDs
- Split seed 42 / 630 test events
- Frozen LLM utility consumer prompts and primary model (`qwen3:8b`)
- Metric definitions in the camera-ready / post-acceptance trees that `make repro-cikm-2026` checks

Document any change in `CHANGELOG.md`.

## Deferred (later release on `main`)

- Productized BYO — `opensbb run` / `evaluate` ([#1](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues/1)), adapter interface ([#6](https://github.com/nimblenotions/open-semantic-boundary-benchmark/issues/6))
- Learned semantic extractors
- Domain registration spec

## Contributor workflow

1. Read [`adoption_path.md`](adoption_path.md)
2. Open an issue describing the extension
3. Branch, implement, run `make test` and `make repro-cikm-2026`
4. Update the relevant `open-sbb/*/README.md` if adopters will see the change
5. Follow [`DOCUMENTATION.md`](DOCUMENTATION.md) if you touch user-facing docs
