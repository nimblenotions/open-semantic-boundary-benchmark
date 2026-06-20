# Policies

## What this module is

**Policy** \(\pi\) is the versioned disclosure bundle: prohibited fields, allowed semantic fields, combination guards, granularity caps, and required provenance fields.

## Paper connection

Maps to **§4.2 Registered Consumers and Policies** (policy half).

## Current implementation

Code:

- `src/boundary/policy_check.py` — policy validation helpers
- `src/boundary/cross.py` — materialize \((z,r)\) under \(\pi\)

Data:

- `data/policies/obs_policy_v1.json`
- `data/policies/analytics_policy_v1.json`
- `data/schemas/obs_schema_coarse.json`
- `data/schemas/obs_schema_medium.json`
- `data/schemas/obs_schema_fine.json`
- `data/schemas/analytics_schema_coarse.json`
- `data/schemas/analytics_schema_medium.json`
- `data/schemas/analytics_schema_fine.json`
- `data/schemas/provenance_v1.json`
- `data/schemas/obs_labels_v1.json`

Outputs:

- `outputs/pilot_v2/config_snapshot/pilot_v0.1.1.yaml`
- `outputs/pilot_v2/config_snapshot/manifest.json`

## Reproduce

```bash
make repro-smoke
python -m json.tool data/policies/obs_policy_v1.json | head -40
```

## Extend

Add policy JSON under `data/policies/` + matching schemas under `data/schemas/`. Wire purpose in config and utility tasks.

## Not claimed

Policy JSON is a **benchmark contract**, not legal advice or compliance certification.
