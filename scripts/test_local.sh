#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKETCH_DIR="${ROOT_DIR}/sketch"

if [[ $# -gt 0 ]]; then
  SKETCH_FILE="$1"
else
  SKETCH_FILE="$(find "${SKETCH_DIR}" -maxdepth 1 -type f -name '*.sketch' | sort | head -n 1)"
fi

if [[ -n "${SKETCH_FILE:-}" && -f "${SKETCH_FILE}" ]]; then
  export SKETCH_LAYOUT_ZONING_FIXTURE="${SKETCH_FILE}"
  echo "Using sketch fixture: ${SKETCH_LAYOUT_ZONING_FIXTURE}"
else
  echo "No sketch fixture found under ${SKETCH_DIR}. 仅运行无需 Sketch 样例的测试。"
  unset SKETCH_LAYOUT_ZONING_FIXTURE 2>/dev/null || true
fi

python3 -m unittest discover -s "${ROOT_DIR}/tests" -v
