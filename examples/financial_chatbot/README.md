# Financial chatbot (conceptual)

## Use case

Regulated financial chatbots must abstract **client identifiers** and **account detail** before LLM supervision or analytics — while preserving enough semantics for compliance review tasks.

## Related artifact in repo

Illustrative provenance (synthetic, not legal advice):

- [`../provenance/finra_advisor_export.json`](../provenance/finra_advisor_export.json)
- [`../provenance/README.md`](../provenance/README.md)

## Open SBB angle

Score competing export strategies (tokenize vs surrogate vs semantic JSON) on:

- Utility: can a supervisor consumer still classify risk stage?
- Linkage: persona re-identification under tokenization stress tests
- Provenance: auditable transform lineage via `verify`

## Shipped pilot analogue

`surrogate` and `redact_tokenize` arms in the medication pilot mirror **replacement** vs **token** strategies:

```bash
make repro-smoke
python -c "import json; m=json.load(open('outputs/pilot_v2/metrics.json')); c=m['conditions']; print('tokenize R', c['redact_tokenize']['trial4_adversary']['combined_linkage_score'])"
```

## Not claimed

Not FINRA-compliant tooling. JSON examples assist **governance storytelling**, not regulatory certification.
