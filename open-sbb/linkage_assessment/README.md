# Linkage assessment

Residual linkage \(R(z_{c,T})\) is scored on the purpose-conditioned export under declared closed-world adversaries. Combined \(R\) is the unweighted mean of three channels:

\[
R(z_{c,T}) = \tfrac{1}{3}(\text{persona top-1} + \text{attribute macro-F1} + \text{longitudinal AUC}).
\]

**Token recovery is separate.** It measures the fraction of sensitive surface forms from raw \(x\) that reappear in text-like \(z_{c,T}\). It is not a fourth term in \(R\). Low token recovery does not, by itself, imply low residual linkage.

The published protocol uses TF-IDF with `char_wb` character n-grams \(1\)–\(3\) and 5,000 features, **fit on training export strings only** and applied unchanged to held-out exports. Linkage is **purpose-specific**: \(R(z_{c,T_o})\) and \(R(z_{c,T_a})\) can differ, especially for semantic conditions.

Persona re-identification matches each held-out event to mean profiles of the 20 test personas, excluding the query event from its own profile. Attribute inference uses logistic regression trained on train-split event vectors. Longitudinal linkage is same-versus-different-persona AUC from cosine similarities over the 30-day traces.

Combined \(R\) is a reporting convenience for operative selection, not a calibrated re-identification probability.

## Implementation

- `src/eval/adversary_trial4.py` — persona, attribute, and longitudinal channels
- `src/eval/adversary.py` — helpers including token recovery
- `src/eval/retention.py` — token-recovery diagnostic
- `src/eval/embeddings.py` — TF-IDF encoding
- `configs/cikm_v0.1.yaml` → `paper_protocol.linkage` (`fit: train_only`, `risk_surface: purpose_specific`)

Published decomposition: Figure 2 under [`../../releases/cikm-2026/`](../../releases/cikm-2026/). Focal `red_tokenize` contrast (token recovery vs persona top-1): [`../../releases/cikm-2026/experimental_protocol.md`](../../releases/cikm-2026/experimental_protocol.md). Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Verify

```bash
make repro-cikm-2026
```

That command checks the locked linkage protocol and the reported `red_tokenize` recovery-versus-persona contrast. It does not re-fit the adversary from scratch.

## Extend

New adversary: [`../../docs/extension_points.md`](../../docs/extension_points.md).

## Not claimed

\(R(z_{c,T})\) is a diagnostic benchmark index, not a calibrated re-identification probability or a regulatory threshold.
