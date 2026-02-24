#!/bin/bash
set -euo pipefail

cleanup() {
    echo "Interrupted. Cleaning up..."
    pkill -f OpinionDynamics || true
    exit 1
}
trap cleanup SIGINT SIGTERM

# ================================
# 1. コンパイル
# ================================
echo "Compiling Java sources..."

# findで見つからなかった場合のエラー回避
LIBCP="$(find lib -name '*.jar' 2>/dev/null | tr '\n' ':')bin"

rm -rf bin
mkdir -p bin

# 依存ライブラリがない場合も考慮してコンパイル
if [ -n "$(find lib -name '*.jar' 2>/dev/null)" ]; then
    javac -cp "$LIBCP" -d bin src/**/*.java
else
    javac -d bin src/**/*.java
fi

echo "Compilation finished."

# ================================
# 2. 並列実行設定
# ================================
# 以下に実行したいSeedをスペース区切りで指定してください
# TARGET_SEEDS="4 6 7 8 11 12 13 29 31 33 34 41 44 46 51"
TARGET_SEEDS="7 8 11 12 13 29 31 41 44 46 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72"

MAX_PARALLEL=10       # ★ 最大並列数
JAVA_HEAP="2g"
LOGDIR="logs"

mkdir -p "$LOGDIR"

# 実行数カウント（表示用）
SEED_COUNT=$(echo $TARGET_SEEDS | wc -w)
TOTAL_RUNS=$((SEED_COUNT * 2))

echo "Starting simulations for specific seeds: [ $TARGET_SEEDS ]"
echo "Total runs: $TOTAL_RUNS (x2 targets per seed)..."

# ================================
# 3. 並列実行関数
# ================================
run_one() {
    local seed=$1
    local target=$2
    
    # ログファイル名設定
    local label="pos"
    if [ "$target" = "-1.0" ]; then
        label="neg"
    fi
    local logfile="${LOGDIR}/run_${seed}_${label}.log"

    echo "[START] seed=$seed target=$target $(date)" > "$logfile"

    # Java実行
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
# 4. タスク生成と実行（変更箇所）
# ================================
# 配列またはリストからSeedを取り出し、ターゲット(1.0, -1.0)とセットで出力してxargsに渡す

for seed in $TARGET_SEEDS; do
    # パターン1: Target 1.0
    echo "$seed"
    echo "1.0"
    
    # パターン2: Target -1.0
    echo "$seed"
    echo "-1.0"
done | xargs -n 2 -P "$MAX_PARALLEL" bash -c 'run_one "$1" "$2"' _

echo "All simulations completed!"