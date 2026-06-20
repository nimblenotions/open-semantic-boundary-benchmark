#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"
CONFIG="${CONFIG:-configs/pilot_v0.1.1.yaml}"

echo "== generate =="
python -m generate.generate_corpus --config "$CONFIG"
echo "== transform =="
python -m transform.run_transforms --config "$CONFIG"
echo "== eval =="
python eval/run_obs_study.py --config "$CONFIG" --tier all
echo "== figures =="
python eval/run_figures.py --config "$CONFIG"
echo "pipeline done"
