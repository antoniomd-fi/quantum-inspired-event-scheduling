#!/usr/bin/env bash
set -Eeuo pipefail

SCENARIO="${SCENARIO:-scenarios/baseline.exs}"
STRATEGY="${STRATEGY:-round_robin}"
OUT_DIR="${OUT_DIR:-../../results/raw/baseline_round_robin}"
IMAGE_NAME="${IMAGE_NAME:-quantum-inspired-event-scheduling-sim}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_event_scheduler.sh [options]

Options:
  --scenario PATH      Scenario file inside the simulator project.
  --strategy NAME      Scheduling strategy to execute.
  --out DIR            Output directory.
  --image NAME         Docker image name.
  -h, --help           Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario) SCENARIO="${2:?Missing value for --scenario}"; shift 2 ;;
    --strategy) STRATEGY="${2:?Missing value for --strategy}"; shift 2 ;;
    --out) OUT_DIR="${2:?Missing value for --out}"; shift 2 ;;
    --image) IMAGE_NAME="${2:?Missing value for --image}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$REPO_ROOT/code/event_scheduler_sim"

docker build -t "$IMAGE_NAME" "$PROJECT_ROOT"
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace/code/event_scheduler_sim "$IMAGE_NAME" mix deps.get
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace/code/event_scheduler_sim "$IMAGE_NAME" mix sim.run --scenario "$SCENARIO" --strategy "$STRATEGY" --out "$OUT_DIR"
