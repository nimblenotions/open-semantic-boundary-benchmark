# Extension points

This page describes where to extend the Semantic Boundary Benchmark while preserving the frozen CIKM 2026 artifact.

The `cikm-2026` release defines a fixed experimental protocol. You can add new transformation conditions, purposes, utility tasks, linkage assessments, policies, or domains, but such changes should be treated as extensions rather than as modifications to the reported CIKM experiment.

Changes to frozen assessors, data splits, or reported protocol definitions should be discussed in an issue before implementation.

## Where to extend the benchmark

| Extension                         | Where to start                                                                                                                   | Related documentation                                                                                               |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| New transformation condition      | `src/transform/`, `configs/cikm_v0.1.yaml`, and materialized exports under `data/transformed/` and `data/transformed_analytics/` | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md)                                                  |
| New policy or schema              | `data/policies/`, `data/schemas/`, `src/boundary/`                                                                               | [`open-sbb/policies/`](../open-sbb/policies/README.md)                                                              |
| New purpose                       | Purpose wiring in `configs/cikm_v0.1.yaml`, corresponding policies, consumers, and utility tasks                                 | [`open-sbb/policies/`](../open-sbb/policies/README.md) and [`open-sbb/consumers/`](../open-sbb/consumers/README.md) |
| New utility task                  | `src/eval/*_task.py` together with the relevant evaluation runner or assessor implementation                                     | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md)                                          |
| New linkage assessment            | `src/eval/adversary*.py` and the corresponding evaluation runner                                                                 | [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md)                                          |
| New operative-selection rule      | `src/eval/operative_selection.py`                                                                                                | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md)                                        |
| New domain corpus                 | `examples/<domain>/` together with a generator or compatible input data                                                          | [`examples/README.md`](../examples/README.md)                                                                       |
| External exported representations | [`examples/bring_your_own/`](../examples/bring_your_own/README.md)                                                               | Experimental interface; not part of the CIKM 2026 evaluation                                                        |
| Provenance or verification        | `src/boundary/verify.py`, `data/schemas/provenance_v1.json`                                                                      | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md)                            |

## What is frozen for CIKM 2026

The following elements define part of the reported experimental protocol and should not be changed silently:

* the nine primary transformation-condition identifiers;
* the frozen train/test split, including split seed 42 and the 630 held-out test events;
* the primary utility-assessment model, `qwen3:8b`;
* the observability utility-assessment prompt logic in `src/eval/tier1_consumer.py` (`PROMPT_VERSION = "triage_v1"`) and the analytics utility-assessment prompt logic in `src/eval/tier1_analytics_consumer.py` (`PROMPT_VERSION = "analytics_triage_v1"`), together with the vocabularies drawn from `data/schemas/obs_labels_v1.json` and `data/ground_truth/labels.jsonl`;
* the linkage, utility, cohort, and operative-selection definitions used by the frozen CIKM 2026 protocol; and
* the committed artifacts verified by `make repro-cikm-2026`.

The LLM used for the transformation conditions is also `qwen3:8b`, but that is a separate protocol choice from the utility-assessment model.

If an extension changes one of these elements, document the change explicitly and treat the resulting evaluation as a new benchmark variant rather than as reproduction of the published experiment.

## Extending with external exports

The experimental bring-your-own example under [`examples/bring_your_own/`](../examples/bring_your_own/README.md) shows how an externally produced `events.jsonl` representation can be shaped for inspection by repository tooling.

This interface is experimental and is not part of the CIKM 2026 evaluation protocol. Compatibility with the same schema does not, by itself, imply that an external transformation reproduces the reported experiment; the applicable purpose, assessors, linkage evaluations, and protocol settings must also be held fixed.

## Contributor workflow

1. Read [`adoption_path.md`](adoption_path.md) to understand the frozen artifact and supported verification path.
2. Open an issue describing the proposed extension when it changes scientific scope or frozen protocol components.
3. Implement the extension on a separate branch.
4. Run:

```bash
make test
make lint
```

For changes that are expected to preserve the CIKM artifact, also run:

```bash
make repro-cikm-2026
```

5. Update the relevant `open-sbb/*/README.md` and other documentation when the extension changes a public interface or protocol description.
6. Follow [`CONTRIBUTING.md`](../CONTRIBUTING.md) for repository contribution requirements.
