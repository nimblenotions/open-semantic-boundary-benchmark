# Linkage assessment

## What this module is

**Linkage assessment** — `assess_risk` → \(R(z)\) under closed-world adversaries. Combined index:

\[
R(z) = \tfrac{1}{3}(\text{persona\_top1} + \text{attribute\_macro\_F1} + \text{longitudinal\_AUC})
\]

Token recovery is separate (text arms) and **excluded** from \(R(z)\).

## Paper connection

Maps to **§4.4 Utility and Linkage Assessment** (linkage half): persona top-1, attribute macro-F1, longitudinal linkage AUC.

## Current implementation

Code:

- `src/eval/adversary_trial4.py` — Trial4 adversary suite (primary)
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
make eval-linkage CONFIG=configs/pilot_v0.1.1.yaml
make figures CONFIG=configs/pilot_v0.1.1.yaml
```

Persona top-1 on `redact_tokenize` (≈ 0.87 linkage stress test):

```bash
python -c "import json; m=json.load(open('outputs/pilot_v2/metrics.json')); print(m['conditions']['redact_tokenize']['trial4_adversary']['persona_top1'])"
```

## Extend

New adversary → `src/eval/adversary_trial4.py` or sibling module + protocol note.

## Not claimed

\(R(z)\) is a diagnostic benchmark index, not a calibrated re-identification probability or regulatory threshold.
