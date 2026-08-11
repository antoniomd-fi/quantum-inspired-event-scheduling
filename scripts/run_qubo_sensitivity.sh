#!/usr/bin/env bash
set -Eeuo pipefail

OUT_DIR="${OUT_DIR:-../../results/raw/v1_qubo_sensitivity}"
IMAGE_NAME="${IMAGE_NAME:-quantum-inspired-event-scheduling-sim}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_qubo_sensitivity.sh [options]

Options:
  --out DIR            Output directory.
  --image NAME         Docker image name.
  -h, --help           Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_DIR="${2:?Missing value for --out}"; shift 2 ;;
    --image) IMAGE_NAME="${2:?Missing value for --image}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$REPO_ROOT/code/event_scheduler_sim"

SCENARIOS="scenarios/baseline.exs,scenarios/steady_load.exs,scenarios/burst_load.exs,scenarios/critical_priority.exs,scenarios/heterogeneous_workers.exs"
STRATEGIES="qubo_batch_exact,qubo_batch_exact_deadline_focused,qubo_batch_exact_critical_focused,qubo_batch_exact_low_balance,priority_aware,shortest_queue"

docker build -t "$IMAGE_NAME" "$PROJECT_ROOT"
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace/code/event_scheduler_sim "$IMAGE_NAME" mix deps.get
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace/code/event_scheduler_sim "$IMAGE_NAME" mix sim.batch --scenarios "$SCENARIOS" --strategies "$STRATEGIES" --out "$OUT_DIR"
