#!/bin/bash
# Manipulation ablation (JCSO R1, reviewer 3 item 3): separate the target's opinion shift
# from the posting-probability (rho) treatment.
#
# Conditions (tag : manip_shift / manip_rho_mode / manip_rho_value):
#   A      : no shift, rho free          -- null control (target behaves as an ordinary agent)
#   B      : no shift, rho fixed 0.5     -- rho boost alone
#   C      : shift,    rho free          -- shift alone, endogenous rho
#   Cprime : shift,    rho frozen        -- shift alone, rho held at the target's own onset value
#   D      : shift,    rho fixed 0.5     -- submitted model
#   E10..E40 : shift,  rho fixed 0.1..0.4 -- dose-response of rho
#
# Baseline (everything except the treatment) is fixed below; edit BASE_* to change it.
# All conditions share the same seeds, so pre-onset trajectories coincide and comparisons
# can be paired by (seed, direction).
#
# Usage: ./run_ablation.sh [TAG ...]   (default: all conditions, in the order below)
set -euo pipefail

PROJ="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ"

# ── baseline (HK, degree-aligned <k>=4; mu / epsilon_s as in the paper's baseline) ─────
BASE_M=2; BASE_A=1; BASE_PT=0.3
BASE_MU=0.7; BASE_EPS=0.5

TARGET_SEEDS="$(seq 0 79 | tr '\n' ' ')"
MAX_PARALLEL=18
JAVA_HEAP="2g"
OUTROOT="results/ablation"

# tag shift rho_mode rho_value
CONDITIONS=(
  "A      false free   0.5"
  "B      false fixed  0.5"
  "C      true  free   0.5"
  "Cprime true  freeze 0.5"
  "D      true  fixed  0.5"
  "E10    true  fixed  0.1"
  "E20    true  fixed  0.2"
  "E30    true  fixed  0.3"
  "E40    true  fixed  0.4"
)
# (rho_value is ignored unless mode == fixed)

SELECT=("$@")

echo "=== Compiling ==="
LIBCP="$(find lib -name '*.jar' 2>/dev/null | tr '\n' ':')bin"
rm -rf bin && mkdir -p bin
javac -cp "$LIBCP" -d bin src/**/*.java

run_one() {
    local seed=$1 dir=$2 tag=$3
    java -Xmx${JAVA_HEAP} -XX:+ExitOnOutOfMemoryError -cp "${LIBCP}:bin" \
         dynamics.OpinionDynamics "$seed" "$dir" "ablation/${tag}" \
         > "logs/ablation_${tag}_${seed}_${dir}.log" 2>&1
}
export -f run_one
export LIBCP JAVA_HEAP

mkdir -p logs
for cond in "${CONDITIONS[@]}"; do
    read -r tag shift mode val <<< "$cond"
    if [[ ${#SELECT[@]} -gt 0 ]] && [[ ! " ${SELECT[*]} " =~ " ${tag} " ]]; then continue; fi
    if [[ -d "$OUTROOT/$tag" ]]; then
        echo "[SKIP] $tag: $OUTROOT/$tag already exists (delete it to rerun)"; continue
    fi

    echo "------------------------------------------------------"
    echo "  condition $tag : shift=$shift rho_mode=$mode rho_value=$val"
    echo "------------------------------------------------------"
    # config.yaml is read by every JVM at start-up, so conditions run sequentially.
    cat > config.yaml <<EOF
topology: HolmeKim
network_params:
  m: $BASE_M
  A: $BASE_A
  pt: $BASE_PT
mu: $BASE_MU
epsilon_s: $BASE_EPS
manip_shift: $shift
manip_rho_mode: $mode
manip_rho_value: $val
EOF
    mkdir -p "$OUTROOT/$tag"
    cp config.yaml "$OUTROOT/$tag/config.yaml"   # provenance

    for seed in $TARGET_SEEDS; do echo "$seed 1.0 $tag"; echo "$seed -1.0 $tag"; done \
        | xargs -n 3 -P "$MAX_PARALLEL" bash -c 'run_one "$1" "$2" "$3"' _
    echo "  done: $tag"
done
echo "=== ablation finished ==="
