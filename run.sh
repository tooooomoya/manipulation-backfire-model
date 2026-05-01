#!/bin/bash
set -euo pipefail

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

rm -rf bin
mkdir -p bin

if [ -n "$(find lib -name '*.jar' 2>/dev/null)" ]; then
    javac -cp "$LIBCP" -d bin src/**/*.java
else
    javac -d bin src/**/*.java
fi

echo "Compilation finished."

# ================================
# 2. parallel execution settings
# ================================
#TARGET_SEEDS="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99"
TARGET_SEEDS="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19"

MAX_PARALLEL=10  
JAVA_HEAP="2g"
LOGDIR="logs"

mkdir -p "$LOGDIR"

SEED_COUNT=$(echo $TARGET_SEEDS | wc -w)
TOTAL_RUNS=$((SEED_COUNT * 2))

echo "Starting simulations for specific seeds: [ $TARGET_SEEDS ]"
echo "Total runs: $TOTAL_RUNS (x2 targets per seed)..."

# ================================
# 3. run function
# ================================
run_one() {
    local seed=$1
    local target=$2
    
    local label="pos"
    if [ "$target" = "-1.0" ]; then
        label="neg"
    fi
    local logfile="${LOGDIR}/run_${seed}_${label}.log"

    echo "[START] seed=$seed target=$target $(date)" > "$logfile"

    java -Xmx${JAVA_HEAP} \
         -XX:+ExitOnOutOfMemoryError \
         -cp "${LIBCP}:bin" \
         dynamics.OpinionDynamics "$seed" "$target" \
         >> "$logfile" 2>&1

    echo "[END]   seed=$seed target=$target $(date)" >> "$logfile"
}

export -f run_one
export LIBCP JAVA_HEAP LOGDIR

# ================================
# 4. execute in parallel
# ================================

for seed in $TARGET_SEEDS; do
    # pattarn 1: Target 1.0
    echo "$seed"
    echo "1.0"
    
    # pattarn 2: Target -1.0
    echo "$seed"
    echo "-1.0"
done | xargs -n 2 -P "$MAX_PARALLEL" bash -c 'run_one "$1" "$2"' _

echo "All simulations completed!"