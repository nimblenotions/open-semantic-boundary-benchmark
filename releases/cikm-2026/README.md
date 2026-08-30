# CIKM 2026 cite surface

Frozen numbers and figures for the CIKM 2026 paper
([DOI 10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076), paper **4405**).

Cite the paper for the science. Cite git tag `cikm-2026` (and the Zenodo version of this tag, when published) for this folder.

## Verify (no Ollama)

From the repository root:

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

That command checks:

1. Protocol locks (train-only TF-IDF, purpose-specific \(R\), Track C Ta-5)
2. Table 3 winners at \(R_{\max}=0.45\)
3. Token vs persona on `redact_tokenize`
4. SHA256 of the three paper figure PDFs

## Contents

| File | Role |
|------|------|
| [`CAMERA_READY_PROTOCOL.md`](CAMERA_READY_PROTOCOL.md) | Human-readable protocol statement |
| [`CAMERA_READY_PROTOCOL.json`](CAMERA_READY_PROTOCOL.json) | Machine-checked assertion |
| [`table3_operative_grid.md`](table3_operative_grid.md) | Frozen Track A vs adopted Track C |
| [`checksums.sha256`](checksums.sha256) | Figure PDF digests (repo-relative) |
| [`figures/`](figures/) | Flattened Fig. 2–4 PDFs |

Protocol-referenced originals remain under `outputs/pilot_v2_camera_ready/` and `outputs/post_acceptance_experiments/`.

`outputs/pilot_v2/` on this tag is **historical**. Do not treat it as the CIKM default.
