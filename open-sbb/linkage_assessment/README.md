# Linkage assessment

> **CIKM numbers:** [`releases/cikm-2026/`](../../releases/cikm-2026/). Paths under `outputs/pilot_v2/` below are the pre-repair snapshot. Do not quote them as paper results.

## What this module is

**Linkage assessment** — `assess_risk` → \(R(z)\) under closed-world adversaries. Combined index:

\[
R(z) = \tfrac{1}{3}(\text{persona\_top1} + \text{attribute\_macro\_F1} + \text{longitudinal\_AUC})
\]

Token recovery is separate (text arms) and **excluded** from \(R(z)\).

## Paper connection

Residual linkage \(R(z)\) in the CIKM paper (§3–§5). Paths: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Current implementation

Code:

- `src/eval/adversary_trial4.py` — primary linkage adversary suite (persona, attribute, longitudinal channels)
- `src/eval/adversary.py` — adversary helpers
- `src/eval/embeddings.py` — vector encoding (TF-IDF char_wb, sentence-transformers path)
- `src/eval/retention.py` — token recovery diagnostics
- `eval/run_obs_study.py` — merges linkage into metrics (tier `linkage` or full run)

Data:

- `data/transformed/raw/events.jsonl` … `data/transformed/sem_fine/events.jsonl` (export inputs)

Outputs:

- `outputs/pilot_v2/metrics.json` → `conditions[*].trial4_adversary.persona_top1`
- `outputs/pilot_v2/metrics.json` → `conditions[*].trial4_adversary.attribute_combined_macro_f1`
- `outputs/pilot_v2/metrics.json` → `conditions[*].trial4_adversary.longitudinal_linkage_auc`
- `outputs/pilot_v2/metrics.json` → `conditions[*].trial4_adversary.combined_linkage_score`
- `outputs/pilot_v2/metrics.json` → `conditions[*].trial4_adversary.token_recovery_rate`
- `outputs/pilot_v2/figures/linkage_decomposition.png`
- `outputs/pilot_v2/figures/linkage_channels_dual.png`
- `outputs/pilot_v2/figures/tables/linkage_decomposition.csv`

## Reproduce

```bash
make repro-smoke
make eval-linkage CONFIG=configs/cikm_v0.1.yaml
make figures CONFIG=configs/cikm_v0.1.yaml
```

Persona top-1 on `redact_tokenize` (≈ 0.87 linkage stress test):

```bash
python -c "import json; m=json.load(open('outputs/pilot_v2/metrics.json')); print(m['conditions']['redact_tokenize']['trial4_adversary']['persona_top1'])"
```

## Extend

New adversary → `src/eval/adversary_trial4.py` or sibling module + protocol note.

## Not claimed

\(R(z)\) is a diagnostic benchmark index, not a calibrated re-identification probability or regulatory threshold.
