# Paper to repository map

This page maps the main concepts, protocol components, figures, and tables in the CIKM 2026 paper to their corresponding locations in the repository.

Paper:

Gaurav Baruah, *Semantic Boundary: A Framework and Benchmark for Policy-Constrained Semantic Disclosure*, CIKM 2026.
https://doi.org/10.1145/3799682.3840076

The frozen supporting artifact for the published study is under [`releases/cikm-2026/`](../releases/cikm-2026/).

## Framework and protocol

| Paper concept                                    | Repository documentation                                                                                         | Main implementation or data                                                                                                          |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Semantic Boundary framework                      | [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md)                                                   | Framework description and supporting boundary components under `src/boundary/`                                                       |
| Disclosure policies and registered consumers     | [`open-sbb/policies/`](../open-sbb/policies/README.md), [`open-sbb/consumers/`](../open-sbb/consumers/README.md) | `data/policies/`, `data/schemas/`, `configs/cikm_v0.1.yaml`                                                                          |
| Frozen transformation lattice \(\mathcal{C}\)    | [`open-sbb/export_lattice/`](../open-sbb/export_lattice/README.md)                                               | `src/transform/`, `data/transformed/`, `data/transformed_analytics/`                                                                 |
| Synthetic medication-adherence corpus            | [`open-sbb/synthetic_pilot_data/`](../open-sbb/synthetic_pilot_data/README.md)                                   | `data/raw/`, `data/ground_truth/`                                                                                                    |
| Utility assessment \(U\)                         | [`open-sbb/utility_assessment/`](../open-sbb/utility_assessment/README.md)                                       | `src/eval/observability_task.py`, `src/eval/analytics_task.py`, `src/eval/tier1_consumer.py`, `src/eval/tier1_analytics_consumer.py` |
| Linkage assessment \(R\)                         | [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md)                                       | `src/eval/adversary.py`, `src/eval/adversary_trial4.py`                                                                              |
| Token-recovery diagnostic                        | [`open-sbb/linkage_assessment/`](../open-sbb/linkage_assessment/README.md)                                       | `src/eval/retention.py`                                                                                                              |
| Operative selection under \(R_{\max}\)           | [`open-sbb/operative_selection/`](../open-sbb/operative_selection/README.md)                                     | `src/eval/operative_selection.py`                                                                                                    |
| Transformation provenance \(r\) and verification | [`open-sbb/transformation_provenance/`](../open-sbb/transformation_provenance/README.md)                         | `src/boundary/cross.py`, `src/boundary/verify.py`, `data/schemas/provenance_v1.json`                                                 |

## Transformation-condition identifiers

Some transformation identifiers differ slightly between the paper and the implementation.

| Paper identifier     | Repository identifier   |
| -------------------- | ----------------------- |
| `raw`                | `raw`                   |
| `red_bracket`        | `redact_bracket`        |
| `red_tokenize`       | `redact_tokenize`       |
| `red_surrogate`      | `redact_surrogate`      |
| `red_llm_substitute` | `redact_llm_substitute` |
| `red_llm_rephrase`   | `redact_llm_rephrase`   |
| `sem_coarse`         | `sem_coarse`            |
| `sem_medium`         | `sem_medium`            |
| `sem_fine`           | `sem_fine`              |

The scientific meaning of these conditions is defined by the paper and the frozen CIKM configuration; the repository names are implementation identifiers.

## Reported results and frozen protocol

The frozen release contains the protocol statement and figure assets corresponding to the reported CIKM 2026 experiment.

| Paper or artifact                  | Frozen repository file                                                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Human-readable frozen protocol     | [`releases/cikm-2026/experimental_protocol.md`](../releases/cikm-2026/experimental_protocol.md)                               |
| Machine-readable frozen protocol   | [`releases/cikm-2026/experimental_protocol.json`](../releases/cikm-2026/experimental_protocol.json)                           |
| Table 3 — risk-constrained winners | [`releases/cikm-2026/experimental_protocol.md`](../releases/cikm-2026/experimental_protocol.md)                               |
| Figure 2 — linkage decomposition   | [`releases/cikm-2026/figures/linkage_decomposition.pdf`](../releases/cikm-2026/figures/linkage_decomposition.pdf)             |
| Figure 3 — utility matrix          | [`releases/cikm-2026/figures/utility_matrix_heatmap.pdf`](../releases/cikm-2026/figures/utility_matrix_heatmap.pdf)           |
| Figure 4 — cross-task regret       | [`releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf`](../releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf) |

The paper remains the authoritative source for the complete presentation and interpretation of the reported results.

Committed evaluation directories under [`outputs/`](../outputs/README.md) hold the underlying result snapshot, supporting protocol audits, and a historical development snapshot. They are not independently canonical.

## Verify the frozen artifact

The supported verification path for the CIKM 2026 artifact is:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

This verifies the committed CIKM artifacts without regenerating the LLM transformation outputs.

For a walkthrough of inspecting and reproducing the artifact, see [`adoption_path.md`](adoption_path.md). To add a new transformation, purpose, assessor, or domain without silently changing the frozen experiment, see [`extension_points.md`](extension_points.md).
