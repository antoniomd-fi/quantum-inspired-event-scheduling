#!/usr/bin/env bash
set -Eeuo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_qubo_results_analysis.sh [options]

Options:
  --python COMMAND     Python executable to use.
  -h, --help           Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python) PYTHON_BIN="${2:?Missing value for --python}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if [[ "$PYTHON_BIN" == "python3" ]] && command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python executable not found: $PYTHON_BIN" >&2
    exit 1
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
"$PYTHON_BIN" analysis/qubo_results_analysis.py
