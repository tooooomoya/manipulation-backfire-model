#!/usr/bin/env python3
"""
Time-series of the backfire metric b(t) for Sec 4.3 ("Appearance of the
Backfire Effect"), baseline = HK(p_t=0.3), mu=0.8, epsilon_s=0.5
(exp_id 63f67d05).

Rationale
---------
Sec 4.3 currently plots absolute post counts / per-bin shares, where the
manipulation-induced change is small and hard to read. Sec 4.4 instead
quantifies backfire with the log-response-ratio b:

    b = log( v_opp^post / v_opp^pre ) - log( v_tgt^post / v_tgt^pre )

    opposite group v_opp = far_opposite + near_opposite
    target   group v_tgt = near_target  + far_target
    pre  window = [19000, 20000]  (manipulation onset at 20000)
    post window = [39000, 40000]

This script turns that scalar into a time series b(t) by replacing the fixed
POST window with the (smoothed) instantaneous post volume at step t, while
keeping the SAME fixed PRE baseline [19000,20000]:

    b(t) = log( v_opp(t) / v_opp^pre ) - log( v_tgt(t) / v_tgt^pre )

By construction b(t) ~ 0 before manipulation and rises above 0 if the
opposing camp out-grows the manipulated (target) camp afterwards = backfire.

The metric is computed PER TRIAL (seed x manipulation direction), then
averaged across trials with a standard-error band -- consistent with how b is
aggregated in Sec 4.4. The PRE_MIN_THRESHOLD drop from Sec 4.4 is mirrored so
trials with a near-empty pre-baseline group (log blow-up) are excluded.

Four panels (per user request):
  A1  first 30 seeds            , one direction  (target_sign = +1 only)
  A2  first 30 seeds            , both directions (+/-1 pooled)
  B1  top-25% in-degree targets , one direction
  B2  top-25% in-degree targets , both directions

"Top-25% in-degree" = trials whose manipulation-target in-degree at the
manipulation onset (step 20000) is >= the 75th percentile across all trials in
this condition -- identical to the large-hub filter in sensitivity-analysis.ipynb.
"""

import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EXP_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "results", "summary", "HolmeKim", "A_1_m_3_pt_0.3", "63f67d05",
)
POST_CSV = os.path.join(EXP_DIR, "post_count_100step.csv")
HUB_CSV = os.path.join(EXP_DIR, "target_hub_metrics_5000step.csv")
SEEDS_JSON = os.path.join(EXP_DIR, "selected_seeds.json")
OUT_PNG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "results", "summary", "backfire_bt_timeseries.png",
)
OUT_PNG_3G = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "results", "summary", "backfire_3group_logresp_timeseries.png",
)

MANIP_STEP = 20000           # manipulation onset
PRE_RANGE = (19000, 20000)   # fixed PRE baseline window (== Sec 4.4)
PRE_MIN_THRESHOLD = 1.0      # drop trials with pre-baseline group volume below this
N_FIRST_SEEDS = 30           # "first 30 seeds" set
HUB_PERCENTILE = 0.75        # top-25% in-degree threshold

# Visualization-only smoothing of the per-trial volume series before taking
# logs. Centered rolling mean over SMOOTH_BINS 100-step bins (does not affect
# the PRE baseline, which is a window mean). Set to 1 to disable.
SMOOTH_BINS = 10             # 10 bins = 1000 steps

OPP_COLS = ["far_opposite", "near_opposite"]
TGT_COLS = ["near_target", "far_target"]

# Three-group decomposition for the Sec 4.3-style figure (keeps the original
# 3-line time-series form: here oriented as target / neutral / opposite).
GROUPS_3 = {
    "target":   (TGT_COLS,        "#d62728"),  # manipulated side
    "neutral":  (["neutral"],     "#7f7f7f"),
    "opposite": (OPP_COLS,        "#1f77b4"),  # opposing side
}


# ---------------------------------------------------------------------------
# Per-trial b(t)
# ---------------------------------------------------------------------------
def trial_bt(grp: pd.DataFrame):
    """Return (steps, b_t) for one (seed, target_sign) trial, or None if dropped.

    grp: rows of post_count_100step.csv for a single trial, columns include
    step + the five oriented post-count bins.
    """
    grp = grp.sort_values("step")
    steps = grp["step"].to_numpy()

    opp = (grp[OPP_COLS].sum(axis=1)).to_numpy(dtype=float)
    tgt = (grp[TGT_COLS].sum(axis=1)).to_numpy(dtype=float)

    pre_mask = (steps >= PRE_RANGE[0]) & (steps <= PRE_RANGE[1])
    if pre_mask.sum() == 0:
        return None
    pre_opp = opp[pre_mask].mean()
    pre_tgt = tgt[pre_mask].mean()

    # Mirror Sec 4.4: drop trials whose pre-baseline group is near-empty
    # (log response ratio is unstable / dominated by a tiny denominator).
    if pre_opp < PRE_MIN_THRESHOLD or pre_tgt < PRE_MIN_THRESHOLD:
        return None

    # Smooth the instantaneous volumes for readability (centered rolling mean).
    if SMOOTH_BINS > 1:
        opp = pd.Series(opp).rolling(SMOOTH_BINS, center=True, min_periods=1).mean().to_numpy()
        tgt = pd.Series(tgt).rolling(SMOOTH_BINS, center=True, min_periods=1).mean().to_numpy()

    # Guard against log(0) where a smoothed instantaneous volume hits zero.
    eps = 1e-9
    b_t = np.log((opp + eps) / pre_opp) - np.log((tgt + eps) / pre_tgt)
    return steps, b_t


def aggregate_bt(df_post: pd.DataFrame):
    """Average per-trial b(t) across all trials in df_post.

    Returns (steps, mean_bt, se_bt, n_trials) on a common step grid.
    """
    series = {}  # step-grid (tuple) -> list of b_t arrays
    n = 0
    ref_steps = None
    stacked = []
    for _, grp in df_post.groupby(["seed", "target_sign"]):
        res = trial_bt(grp)
        if res is None:
            continue
        steps, b_t = res
        if ref_steps is None:
            ref_steps = steps
        # All trials share the same 100-step grid; align defensively by length.
        if len(b_t) != len(ref_steps):
            # reindex onto ref_steps
            b_t = np.interp(ref_steps, steps, b_t)
        stacked.append(b_t)
        n += 1

    if n == 0:
        return None
    arr = np.vstack(stacked)
    mean_bt = arr.mean(axis=0)
    se_bt = arr.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.zeros_like(mean_bt)
    return ref_steps, mean_bt, se_bt, n


# ---------------------------------------------------------------------------
# Per-trial log-response of a single group g:  log( v_g(t) / v_g^pre )
# (Sec 4.3-style 3-group figure. opposite_logresp - target_logresp == b(t).)
# ---------------------------------------------------------------------------
def trial_group_logresp(grp: pd.DataFrame):
    """Return (steps, {group: logresp_t}) for one trial, or None if dropped.

    Each group is normalized to its OWN fixed PRE-baseline mean, so all lines
    start near 0 at the manipulation onset and the post-onset movement is the
    whole signal. Drop rule mirrors trial_bt (target/opposite near-empty pre).
    """
    grp = grp.sort_values("step")
    steps = grp["step"].to_numpy()
    pre_mask = (steps >= PRE_RANGE[0]) & (steps <= PRE_RANGE[1])
    if pre_mask.sum() == 0:
        return None

    raw = {g: grp[cols].sum(axis=1).to_numpy(dtype=float) for g, (cols, _) in GROUPS_3.items()}
    pre = {g: v[pre_mask].mean() for g, v in raw.items()}

    # Same exclusion as Sec 4.4: unstable log when target/opposite pre is ~empty.
    if pre["target"] < PRE_MIN_THRESHOLD or pre["opposite"] < PRE_MIN_THRESHOLD:
        return None

    eps = 1e-9
    out = {}
    for g, v in raw.items():
        if SMOOTH_BINS > 1:
            v = pd.Series(v).rolling(SMOOTH_BINS, center=True, min_periods=1).mean().to_numpy()
        out[g] = np.log((v + eps) / pre[g])
    return steps, out


def aggregate_group_logresp(df_post: pd.DataFrame):
    """Average per-trial log-response across trials, per group.

    Returns (steps, {group: (mean, se)}, n_trials).
    """
    ref_steps = None
    stacks = {g: [] for g in GROUPS_3}
    n = 0
    for _, grp in df_post.groupby(["seed", "target_sign"]):
        res = trial_group_logresp(grp)
        if res is None:
            continue
        steps, out = res
        if ref_steps is None:
            ref_steps = steps
        for g, series in out.items():
            if len(series) != len(ref_steps):
                series = np.interp(ref_steps, steps, series)
            stacks[g].append(series)
        n += 1
    if n == 0:
        return None
    result = {}
    for g, lst in stacks.items():
        arr = np.vstack(lst)
        mean = arr.mean(axis=0)
        se = arr.std(axis=0, ddof=1) / np.sqrt(n) if n > 1 else np.zeros_like(mean)
        result[g] = (mean, se)
    return ref_steps, result, n


# ---------------------------------------------------------------------------
# Trial-set construction
# ---------------------------------------------------------------------------
def main():
    df_post = pd.read_csv(POST_CSV)
    df_hub = pd.read_csv(HUB_CSV)
    with open(SEEDS_JSON) as f:
        selected = json.load(f)["selected"]

    first_seeds = set(selected[:N_FIRST_SEEDS])

    # Top-25% in-degree trials: in_degree at MANIP_STEP, threshold = 75th
    # percentile across ALL trials in this condition (== sensitivity-analysis).
    hub_onset = df_hub[df_hub["step"] == MANIP_STEP][
        ["seed", "target_sign", "in_degree"]
    ].copy()
    p75 = hub_onset["in_degree"].quantile(HUB_PERCENTILE)
    hub_trials = set(
        map(tuple, hub_onset[hub_onset["in_degree"] >= p75][["seed", "target_sign"]].values)
    )
    print(f"75th-pct in-degree at step {MANIP_STEP}: {p75:.1f}")
    print(f"Top-25% hub trials: {len(hub_trials)} of {len(hub_onset)}")

    def subset(seed_set=None, hub=False, one_direction=False):
        d = df_post
        if one_direction:
            d = d[d["target_sign"] == 1.0]
        if seed_set is not None:
            d = d[d["seed"].isin(seed_set)]
        if hub:
            keys = set(map(tuple, d[["seed", "target_sign"]].drop_duplicates().values))
            keep = keys & hub_trials
            d = d[d.apply(lambda r: (r["seed"], r["target_sign"]) in keep, axis=1)]
        return d

    panels = [
        ("A1: first 30 seeds | one direction (+1)", subset(first_seeds, one_direction=True)),
        ("A2: first 30 seeds | both directions", subset(first_seeds, one_direction=False)),
        ("B1: top-25% in-degree | one direction (+1)", subset(hub=True, one_direction=True)),
        ("B2: top-25% in-degree | both directions", subset(hub=True, one_direction=False)),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    for ax, (title, d) in zip(axes.ravel(), panels):
        agg = aggregate_bt(d)
        if agg is None:
            ax.set_title(title + "\n(no valid trials)")
            continue
        steps, mean_bt, se_bt, n = agg
        ax.axhline(0.0, color="grey", lw=0.8, ls=":")
        ax.axvline(MANIP_STEP, color="black", lw=1.0, ls="--", label="manipulation onset")
        ax.plot(steps, mean_bt, color="#d62728", lw=2.0, label=r"$\bar{b}(t)$")
        ax.fill_between(steps, mean_bt - se_bt, mean_bt + se_bt,
                        color="#d62728", alpha=0.25, label=r"$\pm$ SE")
        ax.set_title(f"{title}  (n={n})")
        ax.set_ylabel(r"backfire $b(t)$")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.3)
    for ax in axes[1]:
        ax.set_xlabel("simulation step")

    fig.suptitle(
        "Backfire metric $b(t)$ over time — HK($p_t$=0.3), $\\mu$=0.8, $\\epsilon_s$=0.5\n"
        r"$b(t)=\log\,[v_{opp}(t)/v_{opp}^{pre}] - \log\,[v_{tgt}(t)/v_{tgt}^{pre}]$, "
        f"PRE=[19000,20000], smoothing={SMOOTH_BINS}×100 steps",
        fontsize=11,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_PNG, dpi=150)
    print(f"Saved: {OUT_PNG}")

    # -----------------------------------------------------------------------
    # Sec 4.3-style 3-group figure: log-response of target / neutral / opposite
    # Same form as the original (3 lines over time) but each group normalized
    # to its own PRE baseline so the manipulation-induced change is the signal.
    # Note: opposite_line - target_line == b(t) of the figure above.
    # -----------------------------------------------------------------------
    fig2, axes2 = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    for ax, (title, d) in zip(axes2.ravel(), panels):
        agg = aggregate_group_logresp(d)
        if agg is None:
            ax.set_title(title + "\n(no valid trials)")
            continue
        steps, res, n = agg
        ax.axhline(0.0, color="grey", lw=0.8, ls=":")
        ax.axvline(MANIP_STEP, color="black", lw=1.0, ls="--")
        for g, (color) in [(g, c) for g, (_, c) in GROUPS_3.items()]:
            mean, se = res[g]
            ax.plot(steps, mean, color=color, lw=2.0, label=g)
            ax.fill_between(steps, mean - se, mean + se, color=color, alpha=0.2)
        ax.set_title(f"{title}  (n={n})")
        ax.set_ylabel(r"log response  $\log[v_g(t)/v_g^{pre}]$")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.3)

        # Inset: zoom on the post-manipulation window [20000, 40000], where the
        # backfire divergence is otherwise compressed by the pre-onset buildup.
        post_mask = (steps >= MANIP_STEP) & (steps <= 40000)
        axins = ax.inset_axes([0.52, 0.10, 0.45, 0.42])
        ymin, ymax = np.inf, -np.inf
        for g, (_, color) in GROUPS_3.items():
            mean, se = res[g]
            axins.plot(steps[post_mask], mean[post_mask], color=color, lw=1.8)
            axins.fill_between(steps[post_mask], (mean - se)[post_mask],
                               (mean + se)[post_mask], color=color, alpha=0.2)
            ymin = min(ymin, (mean - se)[post_mask].min())
            ymax = max(ymax, (mean + se)[post_mask].max())
        axins.axhline(0.0, color="grey", lw=0.6, ls=":")
        axins.set_xlim(MANIP_STEP, 40000)
        pad = 0.05 * (ymax - ymin)
        axins.set_ylim(ymin - pad, ymax + pad)
        axins.tick_params(labelsize=6)
        axins.set_title("post-onset zoom", fontsize=7)
        ax.indicate_inset_zoom(axins, edgecolor="black", alpha=0.4)
    for ax in axes2[1]:
        ax.set_xlabel("simulation step")
    fig2.suptitle(
        "Per-group log-response over time (Sec 4.3 form) — "
        "HK($p_t$=0.3), $\\mu$=0.8, $\\epsilon_s$=0.5\n"
        r"each group normalized to its own PRE baseline [19000,20000]; "
        r"opposite$-$target $= b(t)$",
        fontsize=11,
    )
    fig2.tight_layout(rect=[0, 0, 1, 0.95])
    fig2.savefig(OUT_PNG_3G, dpi=150)
    print(f"Saved: {OUT_PNG_3G}")


if __name__ == "__main__":
    main()
