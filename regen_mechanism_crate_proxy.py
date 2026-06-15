"""Regenerate crate_100step.csv and follower_crate_proxy_5000step.csv for the
HK mu=0.8 baseline (exp_id 63f67d05) from the on-disk GEXF/metrics.

No simulation is run. Logic is copied verbatim from save-results.ipynb Items 9
and 10 so the outputs are identical to those produced for other conditions.
"""
import os, glob
import numpy as np
import pandas as pd
import networkx as nx
import xml.etree.ElementTree as ET
import json

RESULTS_DIR = "./results"
DEST_DIR    = "./results/summary/HolmeKim/A_1_m_3_pt_0.3/63f67d05"
WINDOW      = 100
GEXF_STEPS  = [0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000]
GROUP_ORDER = ['far_opposite', 'near_opposite', 'neutral', 'near_target', 'far_target']
_POS_MAP = {
     1.0: {0: 'far_opposite', 1: 'near_opposite', 2: 'neutral', 3: 'near_target', 4: 'far_target'},
    -1.0: {0: 'far_target',   1: 'near_target',   2: 'neutral', 3: 'near_opposite', 4: 'far_opposite'},
}
CRATE_THRESHOLD = 0.2  # Const.MINIMUM_BC

SELECTED_SEEDS = json.load(open(os.path.join(DEST_DIR, 'selected_seeds.json')))['selected']
print(f'seeds: {len(SELECTED_SEEDS)}')


def _strip_ns(root):
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]


def _gexf_path(run_dir, step):
    fs = glob.glob(os.path.join(run_dir, 'GEXF', '*', f'step_{step}.gexf'))
    return fs[0] if fs else None


def _parse_gexf_all_attrs(fpath):
    try:
        tree = ET.parse(fpath); root = tree.getroot(); _strip_ns(root)
        attr_map = {a.get('id'): a.get('title')
                    for a in root.findall(".//attributes[@class='node']/attribute")}
        G = nx.DiGraph(); target_id = None; agents = {}
        for node in root.findall('.//node'):
            nid = node.get('id'); G.add_node(nid)
            d = {'opinion': np.nan, 'opinionclass': -1, 'postprob': np.nan}
            for av in node.findall('.//attvalue'):
                t = attr_map.get(av.get('for'), av.get('for')); v = av.get('value', '')
                if t == 'opinion':
                    try: d['opinion'] = float(v)
                    except: pass
                elif t == 'opinionClass':
                    try: d['opinionclass'] = int(v)
                    except: pass
                elif t == 'postProb':
                    try: d['postprob'] = float(v)
                    except: pass
                elif t == 'target' and v.lower() == 'true':
                    target_id = nid
            agents[nid] = d
        for edge in root.findall('.//edge'):
            G.add_edge(edge.get('source'), edge.get('target'))
        return G, target_id, agents
    except Exception:
        return None, None, {}


# --------------------------------------------------------------------------
# Item 9: cRate timeseries (from metrics result_*.csv)
# --------------------------------------------------------------------------
CR_COLS = [f'cRateMean_{i}' for i in range(5)]


def load_crate_timeseries(run_dir, target_sign, window=WINDOW):
    files = glob.glob(os.path.join(run_dir, 'metrics', 'result_*.csv'))
    if not files:
        return None
    dfs = []
    for f in files:
        try: dfs.append(pd.read_csv(f))
        except Exception: pass
    if not dfs:
        return None
    df = pd.concat(dfs).sort_values('step').reset_index(drop=True)
    if [c for c in CR_COLS if c not in df.columns]:
        return None
    pmap = _POS_MAP[target_sign]
    for i in range(5):
        df[pmap[i]] = df[f'cRateMean_{i}']
    df['window_idx'] = df['step'] // window
    agg = df.groupby('window_idx')[GROUP_ORDER].mean()
    agg['step'] = agg.index * window
    return agg.reset_index(drop=True)


crate_records = []
for seed in SELECTED_SEEDS:
    for target_sign in [1.0, -1.0]:
        run_dir = os.path.join(RESULTS_DIR, f'run_{seed}_dir_{target_sign}')
        if not os.path.isdir(run_dir):
            continue
        df_ts = load_crate_timeseries(run_dir, target_sign)
        if df_ts is None:
            continue
        df_ts.insert(0, 'target_sign', target_sign)
        df_ts.insert(0, 'seed', seed)
        crate_records.append(df_ts)

df_crate = pd.concat(crate_records, ignore_index=True)
df_crate = df_crate[['seed', 'target_sign', 'step'] + GROUP_ORDER]
df_crate.to_csv(os.path.join(DEST_DIR, 'crate_100step.csv'), index=False)
print(f'crate_100step.csv saved ({len(df_crate)} rows)')


# --------------------------------------------------------------------------
# Item 10: structural cRate proxy (followers vs non-followers, from GEXF)
# --------------------------------------------------------------------------
def _structural_crate(G, agents, threshold):
    result = {}
    for nid in G.nodes():
        my_op = agents.get(nid, {}).get('opinion', np.nan)
        if np.isnan(my_op):
            result[nid] = (np.nan, np.nan); continue
        followees = list(G.successors(nid))
        if not followees:
            result[nid] = (np.nan, np.nan); continue
        ops   = np.array([agents.get(j, {}).get('opinion',  np.nan) for j in followees])
        probs = np.array([agents.get(j, {}).get('postprob', np.nan) for j in followees])
        similar = np.abs(ops - my_op) < threshold
        valid_u = ~np.isnan(ops)
        sc_u = float(similar[valid_u].mean()) if valid_u.any() else np.nan
        valid_w = valid_u & ~np.isnan(probs)
        if valid_w.any() and probs[valid_w].sum() > 0:
            sc_w = float((similar[valid_w] * probs[valid_w]).sum() / probs[valid_w].sum())
        else:
            sc_w = np.nan
        result[nid] = (sc_u, sc_w)
    return result


scrate_records = []
print('Item 10: structural cRate proxy ...')
for seed in SELECTED_SEEDS:
    for target_sign in [1.0, -1.0]:
        run_dir = os.path.join(RESULTS_DIR, f'run_{seed}_dir_{target_sign}')
        if not os.path.isdir(run_dir):
            continue
        fp_20k = _gexf_path(run_dir, 20000)
        if not fp_20k:
            continue
        G_20k, tid, _ = _parse_gexf_all_attrs(fp_20k)
        if G_20k is None or tid is None:
            continue
        followers_at_manip = set(G_20k.predecessors(tid))
        for step in GEXF_STEPS:
            fp = _gexf_path(run_dir, step)
            if not fp:
                continue
            G, _, agents = _parse_gexf_all_attrs(fp)
            if G is None or tid not in G:
                continue
            scrates = _structural_crate(G, agents, CRATE_THRESHOLD)
            buckets = {}
            for nid, (sc_u, sc_w) in scrates.items():
                if nid == tid:
                    continue
                oc = agents.get(nid, {}).get('opinionclass', -1)
                if oc not in range(5):
                    continue
                grp = _POS_MAP[target_sign].get(oc, 'unknown')
                is_fol = int(nid in followers_at_manip)
                buckets.setdefault((grp, is_fol), []).append((sc_u, sc_w))
            for (grp, is_fol), vals in buckets.items():
                arr = np.array(vals, dtype=float)
                scrate_records.append({
                    'seed': seed, 'target_sign': target_sign, 'step': step,
                    'opinion_group': grp, 'is_follower': is_fol,
                    'mean_scrate_unweighted': float(np.nanmean(arr[:, 0])),
                    'mean_scrate_weighted':   float(np.nanmean(arr[:, 1])),
                    'n_agents': len(vals),
                })

df_proxy = pd.DataFrame(scrate_records)
df_proxy.to_csv(os.path.join(DEST_DIR, 'follower_crate_proxy_5000step.csv'), index=False)
print(f'follower_crate_proxy_5000step.csv saved ({len(df_proxy)} rows)')
