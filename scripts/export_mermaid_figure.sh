#!/usr/bin/env bash
# Export a .mmd file to PNG, SVG, and PDF.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/export_mermaid_figure.py" "$@"
