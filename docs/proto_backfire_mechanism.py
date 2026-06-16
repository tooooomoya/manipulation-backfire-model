#!/usr/bin/env python3
"""
Prototype figure for Section 4.3 "Appearance of the Backfire Effect" (案2: mechanism-forward).

Baseline condition (matches the paper after switching from CNNR):
    HolmeKim p_t=0.3, mu_stub=0.8, epsilon_s=0.5  (exp_id 63f67d05, 50 seeds x 2 directions)
All panels use the already-summarized per-condition CSVs -> no re-simulation.

Design rationale (top-down):
  WHAT: a 1x3 causal-chain figure that makes the backfire legible AND supplies the
        mechanistic evidence promised in the Introduction.
  WHY : the raw posting-ratio plot hides the effect because backfire is a *relative*
        quantity. We therefore show, in direction-relative coordinates (target side vs
        opposite side; both +1.0 and -1.0 manipulations pooled):
          (a) OUTCOME b(t) - the per-trial log-response-ratio of Eq.(backfire), smoothed
                          and averaged across trials. b(t)>0 = opposite outgrows target.
                          This is the SAME estimator as the §4.4 Cohen's d, so figure and
                          statistic agree. (NB: the arithmetic-mean of normalized volume is
                          outlier-sensitive and can read <0 at the tail; b(t) is the honest one.)
          (b) DEFECTION - the manipulated hub's follower COUNT, opposite vs target camp:
                          a balanced bridge (opp == tgt) before manipulation; opposite
                          followers leave entirely afterward.
          (c) ECHO CHAMBER - the hub's follower_homophily_frac (fraction of followers on the
                          hub's own side) rises 0.55 -> 1.00: the hub's neighbourhood becomes
                          fully homogeneous.

NOTE on metrics NOT used here: the saved `betweenness` (directed follow-graph) and
`delta_lambda2` (full disconnected graph) columns are both ~0 by construction and must be
recomputed undirected / on the giant component before use (see betweenness fix). The
structural bridge erosion is therefore shown elsewhere, not in this prototype.
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

D = os.path.join(os.path.dirname(__file__), os.pardir,
                 "results/summary/HolmeKim/A_1_m_3_pt_0.3/63f67d05")
MANIP = 20000
PRE = (19000, 20000)
OPP = ["far_opposite", "near_opposite"]
TGT = ["near_target", "far_target"]


def trial_mean_sem(df, value_col):
    g = df.groupby("step")[value_col]
    return g.mean(), g.sem()


# -------------------------------------------------- (a) outcome b(t)
pc = pd.read_csv(os.path.join(D, "post_count_100step.csv"))
pc["opp"] = pc[OPP].sum(axis=1)
pc["tgt"] = pc[TGT].sum(axis=1)


def b_of_t(sub):
    """Per-trial b(t): log(opp_smoothed/opp_pre) - log(tgt_smoothed/tgt_pre)."""
    sub = sub.sort_values("step").copy()
    pre = sub[(sub.step >= PRE[0]) & (sub.step < PRE[1])]
    ow = sub.opp.rolling(11, min_periods=1).mean()   # ~1000-step trailing window
    tw = sub.tgt.rolling(11, min_periods=1).mean()
    sub["bt"] = np.log(ow / pre.opp.mean()) - np.log(tw / pre.tgt.mean())
    return sub[["step", "bt"]]


B = pc.groupby(["seed", "target_sign"], group_keys=False).apply(b_of_t)
bt_m, bt_s = trial_mean_sem(B, "bt")

# -------------------------------------------------- (b) defection (follower counts)
fc = pd.read_csv(os.path.join(D, "follower_composition_5000step.csv"))
fc["opp_n"] = (fc[OPP].sum(axis=1)) * fc.total_followers   # fraction -> count
fc["tgt_n"] = (fc[TGT].sum(axis=1)) * fc.total_followers
fo_m, fo_s = trial_mean_sem(fc, "opp_n")
ft_m, ft_s = trial_mean_sem(fc, "tgt_n")

# -------------------------------------------------- (c) echo chamber (hub homophily)
hm = pd.read_csv(os.path.join(D, "target_hub_metrics_5000step.csv"))
hh_m, hh_s = trial_mean_sem(hm, "follower_homophily_frac")

# ================================================== plot
fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
RED, BLUE, GREEN = "#d62728", "#1f77b4", "#2ca02c"


def vline(a):
    a.axvline(MANIP, color="gray", ls="--", lw=1, zorder=0)


# (a)
x = bt_m.index.values
vline(ax[0]); ax[0].axhline(0, color="k", lw=0.6, alpha=0.4)
ax[0].plot(x, bt_m, color="k")
ax[0].fill_between(x, bt_m - bt_s, bt_m + bt_s, color="gray", alpha=0.3)
ax[0].set_title("(a) Backfire signal $b(t)$")
ax[0].set_xlabel("step"); ax[0].set_ylabel(r"$\log\frac{v^{\rm opp}}{v^{\rm opp}_{\rm pre}}-\log\frac{v^{\rm tgt}}{v^{\rm tgt}_{\rm pre}}$")
ax[0].text(20500, ax[0].get_ylim()[1]*0.82, "manip.\nonset", fontsize=7, color="gray")

# (b)
xf = fo_m.index.values
vline(ax[1])
ax[1].plot(xf, fo_m, "o-", color=BLUE, label="Opposite camp")
ax[1].fill_between(xf, fo_m - fo_s, fo_m + fo_s, color=BLUE, alpha=0.2)
ax[1].plot(xf, ft_m, "o-", color=RED, label="Target camp")
ax[1].fill_between(xf, ft_m - ft_s, ft_m + ft_s, color=RED, alpha=0.2)
ax[1].set_title("(b) Hub follower count by camp")
ax[1].set_xlabel("step"); ax[1].set_ylabel("# followers of hub")
ax[1].legend(fontsize=8)

# (c)
xh = hh_m.index.values
vline(ax[2]); ax[2].axhline(0.5, color="k", lw=0.6, alpha=0.4)
ax[2].plot(xh, hh_m, "s-", color=GREEN)
ax[2].fill_between(xh, hh_m - hh_s, hh_m + hh_s, color=GREEN, alpha=0.2)
ax[2].set_title("(c) Hub neighbourhood homophily")
ax[2].set_xlabel("step"); ax[2].set_ylabel("follower homophily fraction")
ax[2].set_ylim(0.45, 1.03)

fig.suptitle(r"HolmeKim $p_t=0.3$, $\mu_{\rm stub}=0.8$, $\varepsilon_s=0.5$  "
             r"(50 seeds $\times$ 2 directions, pooled in target/opposite coords)", fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.95])

out = "/tmp/backfire_mechanism_proto"
fig.savefig(out + ".png", dpi=160); fig.savefig(out + ".pdf")
print("saved", out + ".png /", out + ".pdf")
print(f"[a] b(t): peak {bt_m.max():+.3f}@{bt_m.idxmax()}, end {bt_m.iloc[-1]:+.3f}")
print(f"[b] hub followers opp {fo_m.loc[20000]:.0f}->{fo_m.loc[40000]:.0f}, tgt {ft_m.loc[20000]:.0f}->{ft_m.loc[40000]:.0f}")
print(f"[c] homophily {hh_m.loc[20000]:.2f}->{hh_m.loc[40000]:.2f}")
