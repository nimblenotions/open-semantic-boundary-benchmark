#!/usr/bin/env bash
# Tier-1 primary (qwen3:8b) eval with cache resume; sensitivity deferred.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"

CONFIG="${CONFIG:-configs/pilot_v0.1.1.yaml}"
LOG="${LOG:-outputs/pilot_v1/tier1_run.log}"
TIER1_OUT="${TIER1_OUT:-outputs/pilot_v1/metrics_tier1.json}"
METRICS="${METRICS:-outputs/pilot_v1/metrics.json}"

mkdir -p outputs/pilot_v1

echo "=== Tier-1 primary run started $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee -a "$LOG"

python - <<'PY' | tee -a "$LOG"
import copy
import json
import sys
from pathlib import Path

import yaml

root = Path(".")
cfg_path = Path("configs/pilot_v0.1.1.yaml")
cfg = yaml.safe_load(cfg_path.read_text())
cfg = copy.deepcopy(cfg)
cfg["eval"]["tier1"]["sensitivity_models"] = []
tmp = root / "outputs/pilot_v1/pilot_v0.1.1_tier1_primary.yaml"
tmp.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))
print(f"[setup] wrote {tmp} (sensitivity_models=[])", file=sys.stderr)
PY

START=$(date +%s)
python eval/run_obs_study.py \
  --tier 1 \
  --config outputs/pilot_v1/pilot_v0.1.1_tier1_primary.yaml \
  --output "$TIER1_OUT" 2>&1 | tee -a "$LOG"
END=$(date +%s)
RUNTIME=$((END - START))
echo "=== Tier-1 eval finished in ${RUNTIME}s ===" | tee -a "$LOG"

python - <<PY | tee -a "$LOG"
import json
from pathlib import Path

metrics_path = Path("$METRICS")
tier1_path = Path("$TIER1_OUT")
metrics = json.loads(metrics_path.read_text())
tier1_run = json.loads(tier1_path.read_text())

for cid, cond in tier1_run.get("conditions", {}).items():
    if "tier1" in cond:
        metrics.setdefault("conditions", {}).setdefault(cid, {})["tier1"] = cond["tier1"]

metrics["tier"] = "all"
notes = metrics.setdefault("notes", {})
notes["tier1_consumer"] = "active"
notes["tier1_sensitivity"] = "deferred — run llama3.1:8b + gemma4:latest separately"
metrics["generated_at_utc"] = tier1_run.get("generated_at_utc", metrics.get("generated_at_utc"))

metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")
print(f"Merged tier1 into {metrics_path}", flush=True)
PY

echo "=== Merge complete; generating figures ===" | tee -a "$LOG"
python eval/run_figures.py --config "$CONFIG" --metrics "$METRICS" 2>&1 | tee -a "$LOG"

echo "=== Total wall time: ${RUNTIME}s ===" | tee -a "$LOG"
