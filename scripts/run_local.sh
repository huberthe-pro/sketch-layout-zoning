#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKETCH_DIR="${ROOT_DIR}/sketch"

if [[ $# -gt 0 ]]; then
  SKETCH_FILE="$1"
else
  SKETCH_FILE="$(find "${SKETCH_DIR}" -maxdepth 1 -type f -name '*.sketch' | sort | head -n 1)"
fi

if [[ -z "${SKETCH_FILE:-}" ]]; then
  echo "ERROR: 没有找到 .sketch 文件。请把文件放到 ${SKETCH_DIR}，或者把文件路径作为第一个参数传入。" >&2
  exit 2
fi

if [[ ! -f "${SKETCH_FILE}" ]]; then
  echo "ERROR: Sketch 文件不存在: ${SKETCH_FILE}" >&2
  exit 2
fi

OUTPUT_DIR="${ROOT_DIR}/output"
mkdir -p "${OUTPUT_DIR}"

echo "Using sketch file: ${SKETCH_FILE}"
"${ROOT_DIR}/sketch-layout-zoning" report "${SKETCH_FILE}" \
  --zones-output "${OUTPUT_DIR}/sketch-zones.json" \
  --json-output "${OUTPUT_DIR}/sketch-stats.json" \
  --csv-output "${OUTPUT_DIR}/sketch-stats.csv"

echo
echo "输出文件："
echo "  ${OUTPUT_DIR}/sketch-zones.json"
echo "  ${OUTPUT_DIR}/sketch-stats.json"
echo "  ${OUTPUT_DIR}/sketch-stats.csv"
