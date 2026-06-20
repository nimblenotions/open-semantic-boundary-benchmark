#!/usr/bin/env bash
# Poll obs Tier-1 primary PIDs; run analytics tier1 when done.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"

LOG="${LOG:-outputs/pilot_v1/tier1_serial.log}"
ANALYTICS_OUT="${ANALYTICS_OUT:-outputs/pilot_v1/analytics_metrics_tier1.json}"
OBS_PIDS="${OBS_PIDS:-5558 5569}"
TARGET_CACHE=1218
POLL_INTERVAL=150  # ~2.5 min
MAX_WAIT=7200      # 2 hours

mkdir -p outputs/pilot_v1

log() { echo "$@" | tee -a "$LOG"; }

obs_alive() {
  for pid in $OBS_PIDS; do
    if ps -p "$pid" >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

cache_count() {
  find data/eval_cache/qwen3_8b -name '*.json' 2>/dev/null | wc -l | tr -d ' '
}

POLL_START=$(date +%s)
log "=== Tier-1 obs monitor started $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
log "[monitor] watching PIDs: $OBS_PIDS"

while obs_alive; do
  NOW=$(date +%s)
  ELAPSED=$((NOW - POLL_START))
  if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
    log "[monitor] TIMEOUT after 2h — obs still running"
    exit 1
  fi
  CACHE=$(cache_count)
  PCT=$((CACHE * 100 / TARGET_CACHE))
  if [ "$ELAPSED" -ge 1800 ]; then
    log "[poll] $(date -u +%Y-%m-%dT%H:%M:%SZ) obs alive, cache=${CACHE}/${TARGET_CACHE} (${PCT}%)"
  else
    log "[poll] $(date -u +%Y-%m-%dT%H:%M:%SZ) obs alive, cache=${CACHE}/${TARGET_CACHE}"
  fi
  sleep "$POLL_INTERVAL"
done

COMPLETION_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
FINAL_CACHE=$(cache_count)
log "=== OBS primary completed at ${COMPLETION_TIME}, cache=${FINAL_CACHE}/${TARGET_CACHE} ==="

# Wait briefly for merge step in run_tier1_primary.sh
for _ in $(seq 1 30); do
  if [ -f outputs/pilot_v1/metrics_tier1.json ]; then
    break
  fi
  sleep 10
done

# Verify metrics.json tier1 blocks
python - <<'PY' | tee -a "$LOG"
import json
import sys
from pathlib import Path

metrics_path = Path("outputs/pilot_v1/metrics.json")
tier1_path = Path("outputs/pilot_v1/metrics_tier1.json")

if tier1_path.exists():
    tier1_run = json.loads(tier1_path.read_text())
    conditions = tier1_run.get("conditions", {})
    ok_count = 0
    for cid, cond in conditions.items():
        t1 = cond.get("tier1", {})
        status = t1.get("status", "missing")
        f1 = t1.get("failure_mode_macro_f1")
        print(f"[verify] metrics_tier1.json {cid}: status={status} f1={f1}")
        if status == "ok":
            ok_count += 1
    print(f"[verify] tier1 ok blocks: {ok_count}/{len(conditions)}")
else:
    print("[verify] metrics_tier1.json not found yet", file=sys.stderr)

if metrics_path.exists():
    metrics = json.loads(metrics_path.read_text())
    conditions = metrics.get("conditions", {})
    ok_count = 0
    for cid, cond in conditions.items():
        t1 = cond.get("tier1", {})
        if not t1:
            print(f"[verify] metrics.json {cid}: tier1=missing")
            continue
        status = t1.get("status", "missing")
        f1 = t1.get("failure_mode_macro_f1")
        print(f"[verify] metrics.json {cid}: status={status} f1={f1}")
        if status == "ok":
            ok_count += 1
    print(f"[verify] metrics.json tier1 ok blocks: {ok_count}")
else:
    print("[verify] metrics.json not found", file=sys.stderr)
PY

# Analytics tier1 (step 2 from run_tier1_serial.sh)
log "[step 2/2] Analytics Tier-1 primary (qwen3:8b, cache resume)"
python - <<'PY' | tee -a "$LOG"
import copy
import sys
from pathlib import Path

import yaml

cfg = yaml.safe_load(Path("configs/pilot_v0.1.1.yaml").read_text())
cfg = copy.deepcopy(cfg)
cfg["eval"]["tier1"]["sensitivity_models"] = []
tmp = Path("outputs/pilot_v1/pilot_v0.1.1_tier1_analytics.yaml")
tmp.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))
print(f"[setup] wrote {tmp} (sensitivity_models=[])", file=sys.stderr)
PY

START=$(date +%s)
python eval/run_analytics_study.py \
  --tier 1 \
  --config outputs/pilot_v1/pilot_v0.1.1_tier1_analytics.yaml \
  --output "$ANALYTICS_OUT" 2>&1 | tee -a "$LOG"
END=$(date +%s)
log "=== Analytics Tier-1 finished in $((END - START))s ==="

# Sample F1 from obs + analytics
python - <<'PY' | tee -a "$LOG"
import json
from pathlib import Path

print("=== Sample tier1 F1 (obs) ===")
for path in [Path("outputs/pilot_v1/metrics_tier1.json"), Path("outputs/pilot_v1/metrics.json")]:
    if not path.exists():
        continue
    data = json.loads(path.read_text())
    for cid in ["raw", "redact_tokenize", "sem_fine"]:
        t1 = data.get("conditions", {}).get(cid, {}).get("tier1", {})
        if t1:
            print(f"  {path.name} {cid}: f1={t1.get('failure_mode_macro_f1')} status={t1.get('status')}")

print("=== Sample tier1 F1 (analytics) ===")
apath = Path("outputs/pilot_v1/analytics_metrics_tier1.json")
if apath.exists():
    adata = json.loads(apath.read_text())
    for cid in ["raw", "redact_tokenize", "sem_fine"]:
        t1 = adata.get("conditions", {}).get(cid, {}).get("tier1", {})
        if t1:
            print(f"  analytics {cid}: f1={t1.get('failure_mode_macro_f1')} status={t1.get('status')}")
PY

log "=== Tier-1 monitor complete $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
