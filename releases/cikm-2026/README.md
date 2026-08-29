# CIKM 2026 cite surface

This folder is the **cite surface** for tag `cikm-2026`: the submitted CIKM 2026 protocol (paper **4405**, DOI [10.1145/3799682.3840076](https://doi.org/10.1145/3799682.3840076)).

## Verify (no Ollama)

From the repository root:

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
make repro-cikm-2026
```

That command checks:

1. `paper_protocol` locks (train-only TF-IDF, purpose-specific \(R\), Track C Ta-5)
2. Table 3 winners at \(R_{\max}=0.45\)
3. `red_tokenize` token vs persona bite
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

`outputs/pilot_v2/` on this tag is **historical** (transductive TF-IDF, mixed Ta-5). Do not treat it as the CIKM default.

Camera-ready repair inventory (not required for reading the paper): [`../../docs/CIKM-2026-RELEASE-NOTES.md`](../../docs/CIKM-2026-RELEASE-NOTES.md).

## Cite

Evaluated on Open SBB tag `cikm-2026`; see the result artifacts in this folder. Do not report an unofficial aggregate “Open-SBB score.”
