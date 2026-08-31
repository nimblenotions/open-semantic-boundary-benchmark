#!/usr/bin/env bash
# Development pipeline. Regenerates corpus, transforms, historical eval, and
# figures. Not the CIKM 2026 reproduction path; use `make repro-cikm-2026`
# to verify the published artifact.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src:${PYTHONPATH:-}"
CONFIG="${CONFIG:-configs/cikm_v0.1.yaml}"

echo "Development pipeline. Not the CIKM 2026 reproduction path; use \`make repro-cikm-2026\` to verify the published artifact."

if [[ "${FORCE:-}" != "1" ]]; then
  echo "Refusing to run: this path writes into committed data/ and outputs/pilot_v2/." >&2
  echo "Re-run with FORCE=1 if you intend to regenerate development artifacts." >&2
  exit 2
fi

echo "== generate =="
python -m generate.generate_corpus --config "$CONFIG"
echo "== transform =="
python -m transform.run_transforms --config "$CONFIG"
echo "== eval =="
python eval/run_obs_study.py --config "$CONFIG" --tier all
echo "== figures =="
python eval/run_figures.py --config "$CONFIG"
echo "pipeline done"
