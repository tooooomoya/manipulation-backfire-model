#!/bin/bash
set -euo pipefail

# Calibration run: reads config.yaml as-is, 30 seeds, dir_1.0 only.
# Results go to results/run_{seed}_dir_1.0/ — validation.ipynb picks them up directly.
# Edit config.yaml before running to set the condition.

cleanup() {
    echo "Interrupted. Cleaning up..."
    pkill -f OpinionDynamics || true
    exit 1
}
trap cleanup SIGINT SIGTERM

# ================================
# 1. compile
# ================================
echo "Compiling Java sources..."

LIBCP="$(find lib -name '*.jar' 2>/dev/null | tr '\n' ':')bin"
rm -rf bin && mkdir -p bin

if [ -n "$(find lib -name '*.jar' 2>/dev/null)" ]; then
    javac -cp "$LIBCP" -d bin src/**/*.java
else
    javac -d bin src/**/*.java
fi
echo "Compilation finished."

# ================================
# 2. settings
# ================================
TARGET_SEEDS="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29"
MAX_PARALLEL=10
JAVA_HEAP="2g"
LOGDIR="logs"

mkdir -p "$LOGDIR"
rm -f "$LOGDIR"/*.log
rm -rf results/run_*

echo "Config:"
sed 's/^/  /' config.yaml
echo ""

SEED_COUNT=$(echo $TARGET_SEEDS | wc -w)
echo "Starting $SEED_COUNT seeds (dir_1.0 only)..."

# ================================
# 3. run function
# ================================
run_one() {
    local seed=$1
    local logfile="${LOGDIR}/run_${seed}_pos.log"

    echo "[START] seed=$seed target=1.0 $(date)" > "$logfile"

    java -Xmx${JAVA_HEAP} \
         -XX:+ExitOnOutOfMemoryError \
         -cp "${LIBCP}:bin" \
         dynamics.OpinionDynamics "$seed" "1.0" \
         >> "$logfile" 2>&1

    echo "[END]   seed=$seed target=1.0 $(date)" >> "$logfile"
}
export -f run_one
export LIBCP JAVA_HEAP LOGDIR

# ================================
# 4. execute in parallel
# ================================
echo $TARGET_SEEDS | tr ' ' '\n' | \
    xargs -P "$MAX_PARALLEL" -I{} bash -c 'run_one "$@"' _ {}

echo "All simulations completed."
