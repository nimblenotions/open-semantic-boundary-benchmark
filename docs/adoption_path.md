# Working with the CIKM 2026 artifact

This guide is for researchers who want to inspect, verify, or extend the frozen Semantic Boundary Benchmark (SBB) artifact corresponding to the CIKM 2026 paper.

The `cikm-2026` release preserves the experimental setup reported in the paper. It supports verification of the published artifact, inspection of the exported representations and assessment components, and controlled extensions to the benchmark. A general interface for evaluating arbitrary external disclosure strategies is outside the scope of this frozen release.

## Verify the reported artifact

From the repository root:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

This is the supported verification path for the CIKM 2026 artifact. It checks:

1. the frozen experimental protocol;
2. the focal Table 3 result at \(R_{\max}=0.45\);
3. the reported contrast between token recovery and persona linkage for the `red_tokenize` condition; and
4. the checksums of Figures 2–4.

The verification command uses committed evaluation artifacts and does not regenerate the LLM-based transformation outputs.

For the frozen protocol, see [`../releases/cikm-2026/experimental_protocol.md`](../releases/cikm-2026/experimental_protocol.md). For a map from the paper to the repository implementation, see [`paper_to_repo.md`](paper_to_repo.md). For the conceptual framework, see [`what-is-semantic-boundary.md`](what-is-semantic-boundary.md).

## Inspect an exported representation

The benchmark evaluates a fixed export lattice \(\mathcal{C}\): a set of alternative transformation conditions applied to the same source events.

Start with the export-lattice documentation:

* [`../open-sbb/export_lattice/README.md`](../open-sbb/export_lattice/README.md)

You can then inspect an individual exported event, for example:

```bash
head -1 data/transformed/redact_bracket/events.jsonl | python -m json.tool
```

The repository condition identifier `redact_bracket` corresponds to `red_bracket` in the paper.

To understand how exported representations are evaluated, continue with:

* [`../open-sbb/utility_assessment/README.md`](../open-sbb/utility_assessment/README.md)
* [`../open-sbb/linkage_assessment/README.md`](../open-sbb/linkage_assessment/README.md)

## Reproducing versus regenerating

The supported CIKM 2026 reproduction path is `make repro-cikm-2026`.

Other evaluation and pipeline targets in this repository include machinery retained from earlier stages of the benchmark and should not be assumed to reproduce the published CIKM protocol. In particular, the historical `outputs/pilot_v2/` pipeline uses earlier evaluation choices that differ from the frozen paper protocol.

The purpose-specific linkage and cohort-task evaluations used for the CIKM paper are preserved under `outputs/post_acceptance_experiments/` and are checked by the reproduction workflow.

Full regeneration of the benchmark, including corpus generation and LLM-based transformations, is a broader development workflow rather than the supported paper-verification path. It requires the corresponding local model dependencies and may traverse historical pipeline components retained in this release for provenance.

## Extend the benchmark

[`extension_points.md`](extension_points.md) documents the components frozen for the CIKM 2026 artifact—including data splits, assessor definitions, and transformation-condition identifiers—and describes where new transformation conditions, purposes, or linkage assessments can be added.

The experimental example in [`../examples/bring_your_own/README.md`](../examples/bring_your_own/README.md) shows the on-disk \(z,r\) shape and a tiny sample. An external transform can use that structure, but scoring remains coupled to the frozen pilot; this is not a general evaluation interface.

Before contributing changes, run:

```bash
make test
make lint
```

and review [`CONTRIBUTING.md`](../CONTRIBUTING.md).
