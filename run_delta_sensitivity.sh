#!/bin/bash
# Sensitivity analysis: delta_rho (δ_ρ) × delta_epsilon (δ_ε)  3×3 conditions × 30 seeds = 270 runs
# Baseline network: HolmeKim (m=3, A=1, pt=0.3), mu=0.8, epsilon_s=0.5, target=+1.0
# HK produces ~50% valid seeds per condition (targeting succeeds when neutral hub found);
# 30 seeds → expect ~15+ valid per condition → analysis uses up to 10 valid seeds.
#
# Output layout:  results/sa_delta/dr{X}_de{Y}/seed_{s}/
# Early-stop seeds (no valid target at step 20000) are retained but flagged in the notebook.
set -euo pipefail

SEEDS="$(seq 1 30)"
NUM_SEEDS=30
TARGET=1.0
OUTDIR="results/sa_delta"
JAVA_HEAP="2g"
LOGDIR="logs/sa_delta"

DELTA_RHOS="0.05 0.1 0.2"
DELTA_EPSILONS="0.95 0.99 0.999"

# Writer.java outputs in 1000-step batches; pick windows just before/after manipulation
# manipulation starts at step 20000; simulation ends at step 40000
PRE_BATCH="post_result_19000_19999.csv"   # steps 19000–19999 (pre-manipulation)
POST_BATCH="post_result_39000_39999.csv"  # steps 39000–39999 (post-manipulation)

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

mkdir -p "$LOGDIR"

# ================================
# 2. save original config
# ================================
cp config.yaml config.yaml.bak
trap 'echo "Restoring config.yaml..."; cp config.yaml.bak config.yaml; rm -f config.yaml.bak' EXIT

# ================================
# 3. run 90 combinations
# ================================
total_runs=$((9 * 30))
run_count=0

for dr in $DELTA_RHOS; do
    for de in $DELTA_EPSILONS; do
        label="dr${dr}_de${de}"
        mkdir -p "${OUTDIR}/${label}"

        for seed in $SEEDS; do
            run_count=$((run_count + 1))
            seed_dir="${OUTDIR}/${label}/seed_${seed}"

            echo ""
            echo "=== Run ${run_count}/${total_runs}: delta_rho=${dr}  delta_epsilon=${de}  seed=${seed} ==="

            # skip if already completed (allows resume after interruption)
            if [ -d "$seed_dir" ]; then
                echo "    -> already exists, skipping"
                continue
            fi

            cat > config.yaml << EOF
topology: HolmeKim
network_params:
  m: 3
  A: 1
  pt: 0.3
mu: 0.8
epsilon_s: 0.5
delta_rho: ${dr}
delta_epsilon: ${de}
EOF

            rm -rf "results/run_${seed}_dir_${TARGET}"

            java -Xmx${JAVA_HEAP} \
                 -XX:+ExitOnOutOfMemoryError \
                 -cp "${LIBCP}:bin" \
                 dynamics.OpinionDynamics "$seed" "$TARGET" \
                 > "${LOGDIR}/run_${label}_s${seed}.log" 2>&1

            mv "results/run_${seed}_dir_${TARGET}" "$seed_dir"
            echo "    -> saved to ${seed_dir}"
        done
    done
done

echo ""
echo "All ${total_runs} runs completed."
echo "Results in: ${OUTDIR}/"
echo ""

# ================================
# 4. summary statistics per condition
# ================================
# columns in post_result_*.csv: step,bin_0(neg),bin_1,bin_2(neutral),bin_3,bin_4(pos),sumOfPosts
# ΔV_target   = mean(bin_4 post-manip) − mean(bin_4 pre-manip)   [positive side]
# ΔV_opposite = mean(bin_0 post-manip) − mean(bin_0 pre-manip)   [negative side]
# diff = ΔV_target − ΔV_opposite;  diff < 0 → backfire
echo "=== Sensitivity analysis summary  (up to 30 seeds attempted per condition) ==="
echo ""
printf "%-22s %-8s %-13s %-12s %-10s %-10s %s\n" \
    "Condition" "δ_ρ" "δ_ε" "Mean diff" "SD" "BF rate" "BF seeds"
printf -- "%.0s-" {1..80}; echo ""

for dr in $DELTA_RHOS; do
    for de in $DELTA_EPSILONS; do
        label="dr${dr}_de${de}"

        # collect per-seed diff values (space-separated, "NA" on missing files)
        diff_values=""
        for seed in $SEEDS; do
            pre_f="${OUTDIR}/${label}/seed_${seed}/posts/${PRE_BATCH}"
            post_f="${OUTDIR}/${label}/seed_${seed}/posts/${POST_BATCH}"

            if [ -f "$pre_f" ] && [ -f "$post_f" ]; then
                d=$(awk -F',' -v pre="$pre_f" -v post="$post_f" '
                    FILENAME == pre  && FNR > 1 { pn += $2; pp += $6; n1++ }
                    FILENAME == post && FNR > 1 { qn += $2; qp += $6; n2++ }
                    END {
                        if (n1 > 0 && n2 > 0) {
                            dt = (qp/n2) - (pp/n1)
                            do_ = (qn/n2) - (pn/n1)
                            printf "%.6f", dt - do_
                        } else printf "NA"
                    }
                ' "$pre_f" "$post_f")
                diff_values="${diff_values} ${d}"
            else
                diff_values="${diff_values} NA"
            fi
        done

        # compute mean, SD (sample), backfire rate from the collected values
        stats=$(printf '%s\n' $diff_values | grep -v '^NA$' | grep -v '^$' | awk '
            { v[NR] = $1; s += $1; n++ }
            END {
                if (n == 0) { printf "NA NA 0.0 0/%d", '"$NUM_SEEDS"'; exit }
                mean = s / n
                for (i = 1; i <= n; i++) ss += (v[i] - mean)^2
                sd = (n > 1) ? sqrt(ss / (n - 1)) : 0
                bf = 0
                for (i = 1; i <= n; i++) if (v[i] < 0) bf++
                printf "%.4f %.4f %.1f %d/%d", mean, sd, 100.0 * bf / n, bf, n
            }
        ')

        read mean sd bf_pct bf_frac <<< "$stats"
        printf "%-22s %-8s %-13s %-12s %-10s %-10s %s\n" \
            "$label" "$dr" "$de" "$mean" "±${sd}" "${bf_pct}%" "$bf_frac"
    done
done

echo ""
echo "Note: diff = ΔV_target(bin_4) − ΔV_opposite(bin_0); negative = backfire confirmed."
