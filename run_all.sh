#!/bin/bash
# Full parameter sweep across all topology conditions.
# Compile once → for each condition: write config.yaml → simulate → save-results.ipynb
set -euo pipefail

PROJ="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ"

# ── parallel / resource settings ─────────────────────────────────────────────
TARGET_SEEDS="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99"
MAX_PARALLEL=10
JAVA_HEAP="2g"
LOGDIR="$PROJ/logs"
TOTAL_CONDITIONS=76
PROGRESS_DIR="$PROJ/progress"

# ── progress state init ───────────────────────────────────────────────────────
rm -rf "$PROGRESS_DIR"
mkdir -p "$PROGRESS_DIR/seeds"
date +%s > "$PROGRESS_DIR/start_time.txt"
echo "0"          > "$PROGRESS_DIR/completed.txt"
echo "Starting…"  > "$PROGRESS_DIR/current.txt"
echo "$TOTAL_CONDITIONS" > "$PROGRESS_DIR/total.txt"
export PROGRESS_DIR

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

# Write config.yaml from key=value pairs.
# Usage: write_config TOPOLOGY [key=val ...]
write_config() {
    local topology="$1"; shift
    python3 - "$topology" "$@" <<'PYEOF'
import sys, yaml
topology = sys.argv[1]
params = {}
for kv in sys.argv[2:]:
    k, v = kv.split('=', 1)
    try:    v = int(v)
    except:
        try: v = float(v)
        except: pass
    params[k] = v
cfg = {
    'topology': topology,
    'network_params': params,
    'N': 1000, 'mu': 0.5, 'epsilon_s': 0.5,
    'delta_p': 0.1, 'delta_bc': 0.01, 'opinion_std': 0.6,
    'start_seed': 0, 'end_seed': 99, 'num_seed': 50, 'target_opinion': 1.0,
}
with open('config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
PYEOF
}

# Run one full condition (simulate + save).
# Usage: run_condition CONDITION_NUM LABEL
run_condition() {
    local cnum="$1" label="$2"
    echo "------------------------------------------------------"
    echo "  ${cnum}/${TOTAL_CONDITIONS}  $label"
    echo "------------------------------------------------------"

    # progress state: clear per-condition seed markers, write current label
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
        --ExecutePreprocessor.timeout=3600 \
        "$PROJ/save-results.ipynb"

    echo "$cnum" > "$PROGRESS_DIR/completed.txt"
    echo "  Done: $label"
    echo ""
}

CONDITION=0

# ══════════════════════════════════════════════════════════════════════════════
# HolmeKim  — vary m (degree) × pt (clustering)
# baseline: m=3, A=1, pt=0.3
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  HolmeKim  (m × pt grid)                            ║"
echo "╚══════════════════════════════════════════════════════╝"
for m in 2 3 4; do
    for pt in 0.1 0.3 0.5; do
        CONDITION=$((CONDITION+1))
        write_config "HolmeKim" "m=$m" "A=1" "pt=$pt"
        run_condition "${CONDITION}" "HolmeKim m=${m} A=1 pt=${pt}"
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# LFR  — vary avg_degree × mu (community mixing)
# baseline: avg_degree=3, mu=0.1
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  LFR  (avg_degree × mu grid)                        ║"
echo "╚══════════════════════════════════════════════════════╝"
for avg_degree in 3 5; do
    for mu in 0.1 0.2 0.3 0.4 0.5; do
        CONDITION=$((CONDITION+1))
        write_config "LFR" \
            "avg_degree=$avg_degree" "max_degree=50" \
            "mu=$mu" "gamma=2.5" "beta=1.5" "min_comm=50" "max_comm=250"
        run_condition "${CONDITION}" "LFR avg_degree=${avg_degree} mu=${mu}"
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# DMS  — vary m × A
# baseline: m=3, A=2
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  DMS  (m × A grid)                                  ║"
echo "╚══════════════════════════════════════════════════════╝"
for m in 2 3 4; do
    for A in 1 2 3; do
        CONDITION=$((CONDITION+1))
        write_config "DMS" "m=$m" "A=$A"
        run_condition "${CONDITION}" "DMS m=${m} A=${A}"
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# BA  — vary m (scale-free degree)
# baseline: m=3
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  BA  (m sweep)                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
for m in 1 2 3 4 5 6 7 8 9 10; do
    CONDITION=$((CONDITION+1))
    write_config "BA" "m=$m"
    run_condition "${CONDITION}" "BA m=${m}"
done

# ══════════════════════════════════════════════════════════════════════════════
# CNNR  — vary p × r
# baseline: p=0.3, r=0.01
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  CNNR  (p × r grid)                                 ║"
echo "╚══════════════════════════════════════════════════════╝"
for p in 0.1 0.3 0.5; do
    for r in 0.001 0.01 0.1; do
        CONDITION=$((CONDITION+1))
        write_config "CNNR" "p=$p" "r=$r"
        run_condition "${CONDITION}" "CNNR p=${p} r=${r}"
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# WS  — vary K × beta (rewiring)
# baseline: K=4, beta=0.1
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  WS  (K × beta grid)                                ║"
echo "╚══════════════════════════════════════════════════════╝"
for K in 2 4; do
    for beta in 0.01 0.05 0.1 0.3 0.5; do
        CONDITION=$((CONDITION+1))
        write_config "WS" "K=$K" "beta=$beta"
        run_condition "${CONDITION}" "WS K=${K} beta=${beta}"
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# ER  — vary p (≈ avg degree = p × 999)
# baseline: p=0.003  (avg_degree ≈ 3)
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ER  (p / avg_degree sweep)                         ║"
echo "╚══════════════════════════════════════════════════════╝"
for p in 0.002 0.003 0.004 0.005 0.006 0.007 0.008 0.009 0.010 0.015; do
    CONDITION=$((CONDITION+1))
    write_config "ER" "p=$p"
    run_condition "${CONDITION}" "ER p=${p}"
done

# ══════════════════════════════════════════════════════════════════════════════
# DCSBM  — vary num_communities × p_in  (p_out = p_in / 4, avg_degree fixed)
# baseline: K=6, p_in=0.03, p_out=0.008
# ══════════════════════════════════════════════════════════════════════════════
echo "╔══════════════════════════════════════════════════════╗"
echo "║  DCSBM  (num_communities × p_in grid)               ║"
echo "╚══════════════════════════════════════════════════════╝"
# p_out = p_in / 4  (keeps community-separation ratio constant)
declare -A POUT=( ["0.02"]="0.005" ["0.03"]="0.008" ["0.05"]="0.012" )
for K in 4 6 8; do
    for p_in in 0.02 0.03 0.05; do
        p_out="${POUT[$p_in]}"
        CONDITION=$((CONDITION+1))
        write_config "DCSBM" \
            "num_communities=$K" "p_in=$p_in" "p_out=$p_out" \
            "gamma=2.3" "avg_degree=5"
        run_condition "${CONDITION}" "DCSBM K=${K} p_in=${p_in} p_out=${p_out}"
    done
done

echo "════════════════════════════════════════════════════════"
echo "  All ${CONDITION} conditions complete."
echo "  Results: results/summary/"
echo "════════════════════════════════════════════════════════"
