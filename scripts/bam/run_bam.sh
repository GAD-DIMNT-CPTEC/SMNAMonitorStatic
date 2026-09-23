#!/usr/bin/env bash
# Configure paths through environment variables or bam.env beside this script.
set -euo pipefail
umask 022
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${BAM_CONFIG:-$SCRIPT_DIR/bam.env}" ]]; then
  source "${BAM_CONFIG:-$SCRIPT_DIR/bam.env}"
fi
: "${BAM_PYTHON:=python3}"
: "${BAM_OUTPUT:=$SCRIPT_DIR/../../static/bam}"
: "${BAM_CACHE:=$SCRIPT_DIR/../../work/bam-cache}"
: "${BAM_LIMIT:=0}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$BAM_CACHE/matplotlib}"
mkdir -p "$MPLCONFIGDIR"
args=(--output "$BAM_OUTPUT" --cache "$BAM_CACHE" --limit "$BAM_LIMIT")
[[ -z "${BAM_FINPE_SOURCE:-}" ]] || args+=(--smna-finpe "$BAM_FINPE_SOURCE")
[[ -z "${BAM_FNCEP_SOURCE:-}" ]] || args+=(--smna-fncep "$BAM_FNCEP_SOURCE")
exec "$BAM_PYTHON" "$SCRIPT_DIR/operational.py" "${args[@]}" "$@"
