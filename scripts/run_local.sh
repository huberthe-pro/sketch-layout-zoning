#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKETCH_DIR="${ROOT_DIR}/sketch"

slugify() {
  local input="$1"
  local output
  output="$(printf '%s' "${input}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//')"
  if [[ -z "${output}" ]]; then
    output="report"
  fi
  printf '%s' "${output}"
}

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

REPORT_NAME="$(basename "${SKETCH_FILE}")"
REPORT_STEM="${REPORT_NAME%.*}"
REPORT_DIR="$(cd "$(dirname "${SKETCH_FILE}")" && pwd)/${REPORT_STEM}.report"
mkdir -p "${REPORT_DIR}"

echo "Using sketch file: ${SKETCH_FILE}"
"${ROOT_DIR}/sketch-layout-zoning" report "${SKETCH_FILE}" \
  --zones-output "${REPORT_DIR}/sketch-zones.json" \
  --json-output "${REPORT_DIR}/sketch-stats.json" \
  --csv-output "${REPORT_DIR}/sketch-stats.csv" \
  --markdown-output "${REPORT_DIR}/sketch-report.md" \
  --annotated-preview-output "${REPORT_DIR}/sketch-preview-annotated.png"

echo
echo "输出目录："
echo "  ${REPORT_DIR}"
echo
echo "输出文件："
echo "  ${REPORT_DIR}/sketch-zones.json"
echo "  ${REPORT_DIR}/sketch-stats.json"
echo "  ${REPORT_DIR}/sketch-stats.csv"
echo "  ${REPORT_DIR}/sketch-report.md"
echo "  ${REPORT_DIR}/sketch-preview-annotated.png"
