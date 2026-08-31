# Export lattice

The **export lattice** \(\mathcal{C}\) is a finite, frozen set of transformation conditions. Each condition produces a purpose-conditioned export \(z_{c,T}\) (with provenance \(r\)) from the same trusted observation \(x\).

This artifact instantiates **nine** primary conditions. Paper Table 2 uses a `red_` prefix where this repository uses `redact_`:

| Paper identifier | Repository identifier | Export rule |
|------------------|-----------------------|-------------|
| `raw` | `raw` | Raw journal and assistant text |
| `red_bracket` | `redact_bracket` | Bracket placeholders (`[MEDICATION]`-style) |
| `red_tokenize` | `redact_tokenize` | Persona-scoped stable pseudonyms |
| `red_surrogate` | `redact_surrogate` | i2b2-style surrogate replacements |
| `red_llm_substitute` | `redact_llm_substitute` | LLM entity substitution |
| `red_llm_rephrase` | `redact_llm_rephrase` | LLM passage rewrite |
| `sem_coarse` | `sem_coarse` | Coarse semantic export (boolean slots) |
| `sem_medium` | `sem_medium` | Medium semantic export (typed task fields) |
| `sem_fine` | `sem_fine` | Fine semantic export (richer typed attributes) |

Semantic conditions use simulator fields rather than learned extraction. They isolate representation choice; they are not production extraction estimates.

## Implementation

- `src/transform/run_transforms.py` — observability-purpose lattice
- `src/transform/run_analytics_transforms.py` — analytics-purpose lattice
- `src/transform/redact.py`, `tokenize.py`, `surrogate.py`, `semantic_map.py`, `llm_sanitize.py`
- `src/transform/lattice.py` — condition registry
- `configs/cikm_v0.1.yaml` — frozen condition identifiers

Committed exports:

- `data/transformed/` — observability-purpose \(z_{c,T_o}\)
- `data/transformed_analytics/` — analytics-purpose \(z_{c,T_a}\)
- `data/llm_transform_cache/` — cached LLM substitute and rephrase outputs

Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Verify

```bash
make repro-cikm-2026
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

`make repro-cikm-2026` does **not** regenerate LLM transformations. Inspecting a committed export is the supported way to look at a lattice condition.

## Development: rematerialize

`make transform` rebuilds exports from the frozen corpus. Regenerating the LLM arms requires the transform model declared in the config and is not part of CIKM verification. Adding a condition: [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

Lattice conditions are benchmark comparators, not vendor reproductions. Semantic conditions are representation upper bounds, not learned-extractor performance.
