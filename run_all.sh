#!/bin/bash
# Full parameter sweep across topology × mu × epsilon_s.
# Compile once → for each condition: write config.yaml → simulate → notebooks/00_build_summary.ipynb
# Degree-aligned params (all topologies <k>≈4, set 2026-06-16): HK m=2, CNNR p=0.50, ER p=0.002, WS K=4.
set -euo pipefail

PROJ="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ"

# ── parallel / resource settings ─────────────────────────────────────────────
TARGET_SEEDS="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99"
MAX_PARALLEL=10
JAVA_HEAP="2g"
LOGDIR="$PROJ/logs"

# agent parameter sweep
MU_VALUES="0.5 0.6 0.7 0.8 0.9"
EPS_VALUES="0.1 0.3 0.5 0.7 0.9"

# HolmeKim: 4 pt × 25 = 100
# LFR/CNNR/WS/ER/DCSBM: 3 × 25 = 75 each
TOTAL_CONDITIONS=125
PROGRESS_DIR="$PROJ/progress"

# ── progress state init ───────────────────────────────────────────────────────
mkdir -p "$PROGRESS_DIR/seeds"
if [[ -f "$PROGRESS_DIR/completed.txt" ]] && [[ "$(cat "$PROGRESS_DIR/completed.txt")" -gt 0 ]]; then
    RESUME_FROM=$(cat "$PROGRESS_DIR/completed.txt")
    echo "=== Resuming from condition $((RESUME_FROM + 1))/${TOTAL_CONDITIONS} ==="
else
    RESUME_FROM=0
    date +%s > "$PROGRESS_DIR/start_time.txt"
    echo "0" > "$PROGRESS_DIR/completed.txt"
fi
echo "Starting…"  > "$PROGRESS_DIR/current.txt"
echo "$TOTAL_CONDITIONS" > "$PROGRESS_DIR/total.txt"
export PROGRESS_DIR RESUME_FROM

# ── compile once ─────────────────────────────────────────────────────────────
echo "=== Compiling Java sources ==="
LIBCP="$(find lib -name '*.jar' 2>/dev/null | tr '\n' ':')bin"
rm -rf bin && mkdir -p bin
javac -cp "$LIBCP" -d bin src/**/*.java
echo "Compilation done."
echo ""

# ── helpers ───────────────────────────────────────────────────────────────────
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

# Write config.yaml.
# Usage: write_config TOPOLOGY MU EPSILON_S [key=val ...]
write_config() {
    local topology="$1" mu="$2" epsilon_s="$3"
    shift 3
    python3 - "$topology" "$mu" "$epsilon_s" "$@" <<'PYEOF'
import sys, yaml
topology = sys.argv[1]
mu = float(sys.argv[2])
epsilon_s = float(sys.argv[3])
params = {}
for kv in sys.argv[4:]:
    k, v = kv.split('=', 1)
    try:    v = int(v)
    except:
        try: v = float(v)
        except: pass
    params[k] = v
cfg = {
    'topology': topology,
    'network_params': params,
    'mu': mu,
    'epsilon_s': epsilon_s,
}
with open('config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
PYEOF
}

# Run one full condition (simulate + save).
run_condition() {
    local cnum="$1" label="$2"
    if [[ $cnum -le $RESUME_FROM ]]; then
        echo "  [SKIP] ${cnum}/${TOTAL_CONDITIONS}  $label"
        return 0
    fi
    echo "------------------------------------------------------"
    echo "  ${cnum}/${TOTAL_CONDITIONS}  $label"
    echo "------------------------------------------------------"

    rm -f "$PROGRESS_DIR/seeds/"*.done 2>/dev/null || true
    echo "${cnum}/${TOTAL_CONDITIONS}  ${label}" > "$PROGRESS_DIR/current.txt"

    rm -rf "$PROJ/results/run_"* "$LOGDIR"/*.log 2>/dev/null || true
    mkdir -p "$LOGDIR"
    local n; n=$(echo "$TARGET_SEEDS" | wc -w)
    echo "  $((n*2)) runs (${n} seeds × 2 directions, ${MAX_PARALLEL} parallel)..."
    for seed in $TARGET_SEEDS; do
        echo "$seed"; echo "1.0"
        echo "$seed"; echo "-1.0"
    done | xargs -n 2 -P "$MAX_PARALLEL" bash -c 'run_one "$1" "$2"' _

    echo "  Simulations done. Saving results..."
    source "$PROJ/venv/bin/activate"
    jupyter nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.timeout=7200 \
        "$PROJ/notebooks/00_build_summary.ipynb"

    echo "$cnum" > "$PROGRESS_DIR/completed.txt"
    echo "  Done: $label"
    echo ""
}

CONDITION=0

# ══════════════════════════════════════════════════════════════════════════════
# HolmeKim  — pt=0.0, 0.3  (m=2, A=1 fixed)
# m=2 → undirected <k>=2m=4 (degree-aligned across all topologies; see go/no-go 2026-06-16)
# pt=0.0 is equivalent to DMS (no triangle closing)
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  HolmeKim  (pt sweep × mu × epsilon_s)              ║"
echo "╚══════════════════════════════════════════════════════╝"
for mu in $MU_VALUES; do
    for epsilon_s in $EPS_VALUES; do
        for pt in 0.0 0.3; do
            CONDITION=$((CONDITION+1))
            write_config "HolmeKim" "$mu" "$epsilon_s" "m=2" "A=1" "pt=$pt"
            run_condition "${CONDITION}" "HK pt=${pt} mu=${mu} eps=${epsilon_s}"
        done
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# CNNR  — p=0.50  (r=0.01 fixed) → undirected <k>≈4 (calibrated 2026-06-16; was p=0.3→2.9)
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  CNNR  (p sweep × mu × epsilon_s)                   ║"
echo "╚══════════════════════════════════════════════════════╝"
for mu in $MU_VALUES; do
    for epsilon_s in $EPS_VALUES; do
        CONDITION=$((CONDITION+1))
        write_config "CNNR" "$mu" "$epsilon_s" "p=0.50" "r=0.01"
        run_condition "${CONDITION}" "CNNR p=0.50 mu=${mu} eps=${epsilon_s}"
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# WS  — beta=0.01,0.1,0.5  (K=4 fixed)
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  WS  (beta sweep × mu × epsilon_s)                  ║"
echo "╚══════════════════════════════════════════════════════╝"
for mu in $MU_VALUES; do
    for epsilon_s in $EPS_VALUES; do
        CONDITION=$((CONDITION+1))
        write_config "WS" "$mu" "$epsilon_s" "K=4" "beta=0.1"
        run_condition "${CONDITION}" "WS beta=0.1 mu=${mu} eps=${epsilon_s}"
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# ER  — p=0.002  → undirected <k>=2(N-1)p≈4 (degree-aligned 2026-06-16; was p=0.003→6.0)
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ER  (p sweep × mu × epsilon_s)                     ║"
echo "╚══════════════════════════════════════════════════════╝"
for mu in $MU_VALUES; do
    for epsilon_s in $EPS_VALUES; do
        CONDITION=$((CONDITION+1))
        write_config "ER" "$mu" "$epsilon_s" "p=0.002"
        run_condition "${CONDITION}" "ER p=0.002 mu=${mu} eps=${epsilon_s}"
    done
done

echo "════════════════════════════════════════════════════════"
echo "  All ${CONDITION} conditions complete."
echo "  Results: results/summary/"
echo "════════════════════════════════════════════════════════"
