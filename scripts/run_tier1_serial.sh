#!/usr/bin/env bash
# Observability Tier-1 primary (qwen, 7 conditions), then analytics Tier-1 (qwen).
# One Ollama consumer at a time — see docs/cikm-protocol.md §4.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"

CONFIG="${CONFIG:-configs/pilot_v0.1.1.yaml}"
LOG="${LOG:-outputs/pilot_v1/tier1_serial.log}"
ANALYTICS_OUT="${ANALYTICS_OUT:-outputs/pilot_v1/analytics_metrics_tier1.json}"

mkdir -p outputs/pilot_v1

log() { echo "$@" | tee -a "$LOG"; }

log "=== Tier-1 serial run started $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
log "[step 1/2] Observability Tier-1 primary (qwen3:8b, 7 conditions, cache resume)"
LOG="$LOG" bash scripts/run_tier1_primary.sh 2>&1 | tee -a "$LOG"

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
log "=== Tier-1 serial run complete $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
