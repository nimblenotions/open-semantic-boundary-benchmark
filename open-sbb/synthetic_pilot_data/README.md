# Synthetic pilot data

## What this module is

Counterfactual control corpus: 100 personas, split seed 42, **630 test events** on the medication-adherence simulator.

## Paper connection

Maps to **§4.3 Synthetic Pilot Construction**.

## Current implementation

Code:

- `src/generate/generate_corpus.py`
- `src/generate/corpus.py`, `persona.py`, `observation.py`, `ground_truth.py`
- `src/generate/validate.py`
- `src/generate/provenance_targets.py`
- `scripts/generate_provenance_targets.py`

Data:

- `data/raw/events.jsonl`
- `data/ground_truth/splits.json`
- `data/ground_truth/persona_table.jsonl`
- `data/ground_truth/labels.jsonl`
- `data/ground_truth/provenance_targets.jsonl`
- `data/ground_truth/exemplars.json`

Outputs:

- `make validate` — JSON report on **stdout** (tier, event/persona counts, failure-mode floors, `ok` / `failures`); not written to disk by default
- `data/ground_truth/splits.json` — frozen persona split (`seed: 42`, train/val/test assignments; 20 test personas → 630 test events)
- Published run snapshot: `outputs/pilot_v2/config_snapshot/pilot_v0.1.1.yaml` (corpus scale + split settings used for v0.1.1)

## Reproduce

```bash
make repro-smoke
make generate CONFIG=configs/pilot_v0.1.1.yaml
make validate CONFIG=configs/pilot_v0.1.1.yaml
python -c "import json; s=json.load(open('data/ground_truth/splits.json')); print(len(s.get('test',[])), 'test personas')"
```

## Extend

New domain → see [`../../examples/`](../../examples/). v0.1.1 numbers use this pilot only.

## Not claimed

Synthetic personas are not real patients.
