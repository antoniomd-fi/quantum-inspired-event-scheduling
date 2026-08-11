#!/usr/bin/env bash
set -Eeuo pipefail

INSTANCES_DIR="${INSTANCES_DIR:-results/raw/v1_qaoa_validation_instances}"
OUT_DIR="${OUT_DIR:-results/raw/v1_qaoa_validation}"
ELIXIR_IMAGE_NAME="${ELIXIR_IMAGE_NAME:-quantum-inspired-event-scheduling-sim}"
QAOA_IMAGE_NAME="${QAOA_IMAGE_NAME:-qaoa-validation}"
BATCH_SIZE="${BATCH_SIZE:-3}"
BATCHES="${BATCHES:-1}"
REPS="${REPS:-1}"
SEEDS="${SEEDS:-7}"
SHOTS="${SHOTS:-512}"
MAXITER="${MAXITER:-25}"
MAX_VARIABLES="${MAX_VARIABLES:-9}"

usage() {
  cat <<'EOF'
Usage: bash scripts/run_qaoa_validation.sh [options]

Options:
  --instances DIR          Host-relative QUBO instance directory.
  --out DIR                Host-relative validation output directory.
  --elixir-image NAME      Elixir simulator Docker image name.
  --qaoa-image NAME        QAOA Docker image name.
  --batch-size N           Events per exported QUBO batch.
  --batches N              Number of batches per scenario.
  --reps LIST              QAOA depths.
  --seeds LIST             QAOA seeds.
  --shots N                Sampler shots.
  --maxiter N              Optimizer iteration limit.
  --max-variables N        Maximum accepted QUBO variables.
  -h, --help               Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --instances) INSTANCES_DIR="${2:?Missing value for --instances}"; shift 2 ;;
    --out) OUT_DIR="${2:?Missing value for --out}"; shift 2 ;;
    --elixir-image) ELIXIR_IMAGE_NAME="${2:?Missing value for --elixir-image}"; shift 2 ;;
    --qaoa-image) QAOA_IMAGE_NAME="${2:?Missing value for --qaoa-image}"; shift 2 ;;
    --batch-size) BATCH_SIZE="${2:?Missing value for --batch-size}"; shift 2 ;;
    --batches) BATCHES="${2:?Missing value for --batches}"; shift 2 ;;
    --reps) REPS="${2:?Missing value for --reps}"; shift 2 ;;
    --seeds) SEEDS="${2:?Missing value for --seeds}"; shift 2 ;;
    --shots) SHOTS="${2:?Missing value for --shots}"; shift 2 ;;
    --maxiter) MAXITER="${2:?Missing value for --maxiter}"; shift 2 ;;
    --max-variables) MAX_VARIABLES="${2:?Missing value for --max-variables}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

to_container_path() {
  local value="${1//\\//}"

  if [[ "$value" == /workspace/* ]]; then
    printf '%s\n' "$value"
    return
  fi

  value="${value#./}"
  value="${value#/}"
  printf '/workspace/%s\n' "$value"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$REPO_ROOT/code/event_scheduler_sim"
QAOA_DOCKERFILE="$REPO_ROOT/analysis/qaoa_validation/Dockerfile"

SCENARIOS="scenarios/baseline.exs,scenarios/steady_load.exs,scenarios/burst_load.exs,scenarios/critical_priority.exs,scenarios/heterogeneous_workers.exs"
CONTAINER_INSTANCES_DIR="$(to_container_path "$INSTANCES_DIR")"
CONTAINER_OUT_DIR="$(to_container_path "$OUT_DIR")"

docker build -t "$ELIXIR_IMAGE_NAME" "$PROJECT_ROOT"
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace/code/event_scheduler_sim "$ELIXIR_IMAGE_NAME" mix deps.get
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace/code/event_scheduler_sim "$ELIXIR_IMAGE_NAME" mix sim.qubo.export --scenarios "$SCENARIOS" --profile sequencing --batch-size "$BATCH_SIZE" --batches "$BATCHES" --out "$CONTAINER_INSTANCES_DIR"

docker build -t "$QAOA_IMAGE_NAME" -f "$QAOA_DOCKERFILE" "$REPO_ROOT"
docker run --rm -v "$REPO_ROOT:/workspace" -w /workspace "$QAOA_IMAGE_NAME" python analysis/qaoa_validation/qaoa_validate_qubo.py --instances "$CONTAINER_INSTANCES_DIR" --out "$CONTAINER_OUT_DIR" --reps "$REPS" --seeds "$SEEDS" --shots "$SHOTS" --maxiter "$MAXITER" --max-variables "$MAX_VARIABLES"
