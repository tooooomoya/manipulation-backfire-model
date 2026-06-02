#!/bin/bash
# Recomputes connectivity_5000step.csv for all conditions where it is missing.
#
# Strategy:
#   For each missing condition —
#     1. Restore its config.yaml from results/summary/.../config.yaml
#     2. Re-run the Java simulation for only the previously selected seeds
#        (read from selected_seeds.json — ~50 seeds instead of all 100)
#     3. Run compute_connectivity.py to write the missing CSV
#     4. Clean up raw results before the next condition
#
# Run from the project root:  bash rerun_connectivity.sh
set -euo pipefail

PROJ="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ"

MAX_PARALLEL=10
JAVA_HEAP="2g"
LOGDIR="$PROJ/logs"
SUMMARY_ROOT="$PROJ/results/summary"
PROGRESS_DIR="$PROJ/progress"

# ── Compile once ─────────────────────────────────────────────────────────────
echo "=== Compiling Java sources ==="
LIBCP="$(find lib -name '*.jar' 2>/dev/null | tr '\n' ':')bin"
rm -rf bin && mkdir -p bin
javac -cp "$LIBCP" -d bin src/**/*.java
echo "Done."
echo ""

run_one() {
    local seed=$1 target=$2
    local label; label=$([ "$target" = "-1.0" ] && echo "neg" || echo "pos")
    local logfile="${LOGDIR}/run_${seed}_${label}.log"
    echo "[START] seed=$seed target=$target $(date)" > "$logfile"
    java -Xmx${JAVA_HEAP} -XX:+ExitOnOutOfMemoryError \
         -cp "${LIBCP}:bin" dynamics.OpinionDynamics "$seed" "$target" \
         >> "$logfile" 2>&1
    echo "[END]   seed=$seed target=$target $(date)" >> "$logfile"
    touch "${PROGRESS_DIR}/seeds/${seed}_${label}.done"
}
export -f run_one
export LIBCP JAVA_HEAP LOGDIR PROGRESS_DIR

# ── Find conditions missing connectivity ──────────────────────────────────────
mapfile -t MISSING < <(python3 - <<'PYEOF'
import os, glob
root = './results/summary'
for cfg in sorted(glob.glob(os.path.join(root, '*', '*', '*', 'config.yaml'))):
    d    = os.path.dirname(cfg)
    topo = os.path.relpath(d, root).split(os.sep)[0]
    if topo == 'Unknown':
        continue
    if 'connectivity_5000step.csv' not in os.listdir(d):
        print(d)
PYEOF
)

N=${#MISSING[@]}
if [[ $N -eq 0 ]]; then
    echo "No conditions missing connectivity. Nothing to do."
    exit 0
fi
echo "=== $N conditions to process ==="
echo ""

# ── Init progress state (compatible with progress.sh) ────────────────────────
mkdir -p "$PROGRESS_DIR/seeds"
rm -f "$PROGRESS_DIR/seeds/"*.done 2>/dev/null || true
date +%s        > "$PROGRESS_DIR/start_time.txt"
echo "$N"       > "$PROGRESS_DIR/total.txt"
echo "0"        > "$PROGRESS_DIR/completed.txt"
echo "Starting…" > "$PROGRESS_DIR/current.txt"

source "$PROJ/venv/bin/activate"

for i in "${!MISSING[@]}"; do
    dest_dir="${MISSING[$i]}"
    IDX=$((i+1))
    rel=$(python3 -c "import os; print(os.path.relpath('$dest_dir', '$SUMMARY_ROOT'))")
    echo "─── [$IDX/$N]  $rel ───"
    echo "[$IDX/$N]  $rel" > "$PROGRESS_DIR/current.txt"

    # Restore config.yaml for this condition
    cp "$dest_dir/config.yaml" ./config.yaml

    # Read previously selected seeds (avoids re-running all 100)
    mapfile -t SEL_SEEDS < <(python3 -c "
import json
with open('$dest_dir/selected_seeds.json') as f:
    d = json.load(f)
for s in d['selected']:
    print(s)
")
    echo "  Simulating ${#SEL_SEEDS[@]} seeds × 2 directions (parallel=$MAX_PARALLEL)..."

    rm -rf "$PROJ/results/run_"* "$LOGDIR"/*.log 2>/dev/null || true
    rm -f "$PROGRESS_DIR/seeds/"*.done 2>/dev/null || true
    mkdir -p "$LOGDIR"

    for seed in "${SEL_SEEDS[@]}"; do
        printf '%s\n1.0\n%s\n-1.0\n' "$seed" "$seed"
    done | xargs -n 2 -P "$MAX_PARALLEL" bash -c 'run_one "$1" "$2"' _

    echo "  Simulations done. Computing connectivity..."
    python3 compute_connectivity.py "$dest_dir"

    echo "$IDX" > "$PROGRESS_DIR/completed.txt"

    # Clean up raw results to free disk
    rm -rf "$PROJ/results/run_"*
    echo ""
done

echo "════════════════════════════════════════════════"
echo "  All $N conditions processed."
echo "════════════════════════════════════════════════"
