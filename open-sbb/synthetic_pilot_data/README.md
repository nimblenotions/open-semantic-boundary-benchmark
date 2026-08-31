# Synthetic pilot data

The CIKM 2026 pilot uses a synthetic medication-adherence corpus generated from a templated simulator. Utility labels, quasi-identifiers, and linkage targets sit on the same events so that only the lattice condition varies.

The frozen corpus has **100 personas** and 3,894 observations over 30 days. A whole-persona split (70 train / 10 validation / 20 test, seed 42) keeps train and test disjoint and yields **630** held-out events from 20 test personas.

## Implementation

Generator:

- `src/generate/generate_corpus.py`
- `src/generate/corpus.py`, `persona.py`, `observation.py`, `ground_truth.py`
- `src/generate/validate.py`

Frozen data:

- `data/raw/events.jsonl`
- `data/ground_truth/splits.json`
- `data/ground_truth/split_manifest_v0.json` — audit manifest (persona counts, 630 test events; canonical JSON SHA-256 in [`../../releases/cikm-2026/experimental_protocol.md`](../../releases/cikm-2026/experimental_protocol.md))
- `data/ground_truth/persona_table.jsonl`
- `data/ground_truth/labels.jsonl`
- `data/ground_truth/provenance_targets.jsonl`

Protocol: [`../../configs/cikm_v0.1.yaml`](../../configs/cikm_v0.1.yaml). Paper map: [`../../docs/paper_to_repo.md`](../../docs/paper_to_repo.md).

## Verify the frozen corpus

```bash
make repro-cikm-2026
python -c "import json; m=json.load(open('data/ground_truth/split_manifest_v0.json')); print(m['persona_counts'], m['test_event_count'])"
```

This checks the committed split and protocol. It does not regenerate the corpus.

## Development: regenerate

`make generate` rebuilds simulator output. That is development work, not reproduction of the published artifact. See [`../../docs/extension_points.md`](../../docs/extension_points.md) and [`../../examples/`](../../examples/).

## Not claimed

Synthetic personas are not real patients. Utility labels are simulator ground truth, not human annotations.
