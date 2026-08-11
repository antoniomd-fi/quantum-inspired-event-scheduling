#!/usr/bin/env bash
set -Eeuo pipefail

PROFILES="${PROFILES:-burst,saturation,critical_heavy,heterogeneous}"
LOADS="${LOADS:-medium,high,overload}"
SEEDS="${SEEDS:-1..10}"
STRATEGIES="${STRATEGIES:-qubo_batch_exact,qubo_batch_exact_sequencing,priority_aware,shortest_queue,min_cost_greedy}"
OUT_DIR="${OUT_DIR:-/workspace/results/raw/v2_extended_event_driven_matrix}"
IMAGE_NAME="${IMAGE_NAME:-quantum-inspired-event-scheduling-sim}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_extended_event_driven_matrix.sh [options]

Options:
  --profiles LIST      Comma-separated profile list.
  --loads LIST         Comma-separated load-level list.
  --seeds RANGE        Seed range or list.
  --strategies LIST    Comma-separated strategy list.
  --out DIR            Output directory.
  --image NAME         Docker image name.
  -h, --help           Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profiles) PROFILES="${2:?Missing value for --profiles}"; shift 2 ;;
    --loads) LOADS="${2:?Missing value for --loads}"; shift 2 ;;
    --seeds) SEEDS="${2:?Missing value for --seeds}"; shift 2 ;;
    --strategies) STRATEGIES="${2:?Missing value for --strategies}"; shift 2 ;;
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
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace/code/event_scheduler_sim "$IMAGE_NAME" mix sim.experiment --profiles "$PROFILES" --loads "$LOADS" --seeds "$SEEDS" --strategies "$STRATEGIES" --out "$OUT_DIR"
