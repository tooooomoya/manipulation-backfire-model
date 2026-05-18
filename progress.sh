#!/bin/bash
# Show run_all.sh progress. Use standalone or with watch:
#   watch -n 2 ./progress.sh

PROJ="$(cd "$(dirname "$0")" && pwd)"
PROGRESS_DIR="$PROJ/progress"

# ── helpers ───────────────────────────────────────────────────────────────────
bar() {
    local done=$1 total=$2 width=${3:-30}
    local filled=$(( done * width / total ))
    local empty=$(( width - filled ))
    printf '['
    printf '%0.s█' $(seq 1 $filled 2>/dev/null) 2>/dev/null
    printf '%0.s░' $(seq 1 $empty  2>/dev/null) 2>/dev/null
    printf '] %d/%d (%.0f%%)' "$done" "$total" "$(echo "scale=1; $done*100/$total" | bc)"
}

fmt_time() {
    local s=$1
    if   (( s < 60   )); then printf '%ds'          "$s"
    elif (( s < 3600  )); then printf '%dm %02ds'    $(( s/60 ))    $(( s%60 ))
    else                       printf '%dh %02dm'    $(( s/3600 ))  $(( s%60/60 ))
    fi
}

# ── guard: not started ────────────────────────────────────────────────────────
if [ ! -f "$PROGRESS_DIR/start_time.txt" ]; then
    echo "run_all.sh has not been started yet (no progress/ directory)."
    exit 0
fi

# ── read state ────────────────────────────────────────────────────────────────
START=$(cat "$PROGRESS_DIR/start_time.txt")
TOTAL=$(cat "$PROGRESS_DIR/total.txt"      2>/dev/null || echo 76)
COMPLETED=$(cat "$PROGRESS_DIR/completed.txt" 2>/dev/null || echo 0)
CURRENT=$(cat "$PROGRESS_DIR/current.txt"  2>/dev/null || echo "—")
SEEDS_DONE=$(ls "$PROGRESS_DIR/seeds/"*.done 2>/dev/null | wc -l)
SEEDS_TOTAL=200   # 100 seeds × 2 directions

NOW=$(date +%s)
ELAPSED=$(( NOW - START ))

# ETA based on completed conditions
if (( COMPLETED > 0 )); then
    PER_COND=$(( ELAPSED / COMPLETED ))
    REMAINING=$(( (TOTAL - COMPLETED) * PER_COND ))
else
    REMAINING=0
fi

# ── display ───────────────────────────────────────────────────────────────────
echo "┌─────────────────────────────────────────────────┐"
echo "│           run_all.sh  progress                  │"
echo "├─────────────────────────────────────────────────┤"
printf "│ Overall  : %s\n" "$(bar "$COMPLETED" "$TOTAL" 28)"
printf "│ Seeds    : %s\n" "$(bar "$SEEDS_DONE" "$SEEDS_TOTAL" 28)"
echo   "│                                                 │"
printf "│ Current  : %-33s │\n" "$CURRENT"
echo   "│                                                 │"
printf "│ Elapsed  : %-10s" "$(fmt_time $ELAPSED)"
if (( COMPLETED > 0 && COMPLETED < TOTAL )); then
    printf "  ETA: ~%-18s" "$(fmt_time $REMAINING)"
else
    printf "                           "
fi
echo "│"
echo "└─────────────────────────────────────────────────┘"

# ── recent completed log entries ─────────────────────────────────────────────
if ls "$PROJ/logs/"*.log &>/dev/null; then
    DONE_LOGS=$(grep -l '\[END\]' "$PROJ/logs/"*.log 2>/dev/null | wc -l)
    FAIL_LOGS=$(grep -rl 'Exception\|OutOfMemory\|Error' "$PROJ/logs/"*.log 2>/dev/null | wc -l)
    echo ""
    printf "  Log summary — completed: %d  errors: %d\n" "$DONE_LOGS" "$FAIL_LOGS"
    if (( FAIL_LOGS > 0 )); then
        echo "  Failed runs:"
        grep -l 'Exception\|OutOfMemory\|Error' "$PROJ/logs/"*.log 2>/dev/null \
            | sed 's|.*/||' | sed 's/\.log$//' | while read -r f; do
                echo "    $f"
            done
    fi
fi
