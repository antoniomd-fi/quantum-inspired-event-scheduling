# Script Entry Points

This folder contains reproducible entry points for the simulator, analysis
pipeline, and QAOA validation.

Both shells are supported:

- `*.ps1` for Windows PowerShell.
- `*.sh` for Bash on Linux, macOS, WSL, or Git Bash.

The Bash scripts mirror the PowerShell defaults. Run them from the repository
root with `bash`:

```bash
bash scripts/run_targeted_stress_matrix.sh
bash scripts/run_targeted_stress_analysis.sh
bash scripts/run_qaoa_validation_analysis.sh
```

On Unix-like systems you can optionally mark them as executable:

```bash
chmod +x scripts/*.sh
./scripts/run_targeted_stress_matrix.sh
```

Most scripts accept long options. For example:

```bash
bash scripts/run_targeted_stress_matrix.sh \
  --profiles burst_critical,flooding_critical \
  --loads high,overload \
  --seeds 1..30
```

Environment variables with matching uppercase names can also override defaults,
for example:

```bash
IMAGE_NAME=quantum-inspired-event-scheduling-sim \
  bash scripts/run_extended_event_driven_matrix.sh
```
