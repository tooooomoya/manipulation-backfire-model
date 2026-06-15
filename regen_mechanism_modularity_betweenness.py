"""Add two GEXF-derived columns to the 63f67d05 summary CSVs (no simulation):

  1. nw_stats_5000step.csv          += 'modularity'    (Leicht-Newman directed Q,
                                       same logic as save-results.ipynb)
  2. target_hub_metrics_5000step.csv += 'betweenness_gc' (undirected GIANT-COMPONENT
                                       betweenness of the target hub, consistent
                                       with the giant-component lambda2 fix)

Existing columns are preserved; new columns are merged on (seed, target_sign, step).
"""
import os, glob
import numpy as np
import pandas as pd
import networkx as nx
import xml.etree.ElementTree as ET
import json

RESULTS_DIR = "./results"
DEST_DIR    = "./results/summary/HolmeKim/A_1_m_3_pt_0.3/63f67d05"
GEXF_STEPS  = [0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000]
N_AGENTS    = 1000
SELECTED_SEEDS = json.load(open(os.path.join(DEST_DIR, 'selected_seeds.json')))['selected']


def _strip_ns(root):
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]


def _gexf_path(run_dir, step):
    fs = glob.glob(os.path.join(run_dir, 'GEXF', '*', f'step_{step}.gexf'))
    return fs[0] if fs else None


def parse_gexf_full(fpath):
    """Return (DiGraph, target_id) — edges a->b mean a follows b."""
    try:
        tree = ET.parse(fpath); root = tree.getroot(); _strip_ns(root)
        attr_map = {a.get('id'): a.get('title')
                    for a in root.findall(".//attributes[@class='node']/attribute")}
        G = nx.DiGraph(); target_id = None
        for node in root.findall('.//node'):
            nid = node.get('id'); G.add_node(nid)
            for av in node.findall('.//attvalue'):
                t = attr_map.get(av.get('for'), av.get('for'))
                if t == 'target' and av.get('value', '').lower() == 'true':
                    target_id = nid
        for edge in root.findall('.//edge'):
            G.add_edge(edge.get('source'), edge.get('target'))
        return G, target_id
    except Exception:
        return None, None


def _compute_modularity(G):
    """Directed modularity Q (Leicht & Newman 2008); communities via Louvain on
    the undirected projection. Identical to save-results.ipynb."""
    if G is None or G.number_of_nodes() < 4:
        return np.nan
    try:
        G_und = G.to_undirected()
        try:
            communities = nx.community.louvain_communities(G_und, seed=42)
        except AttributeError:
            communities = list(nx.community.greedy_modularity_communities(G_und))
        return nx.community.modularity(G, communities)
    except Exception:
        return np.nan


def _betweenness_giant(G, tid):
    """Undirected giant-component betweenness of the target hub (normalized).

    The full follow-graph has isolated/peripheral nodes, so full-graph
    betweenness understates the hub's role within the connected core. We measure
    on the giant component (consistent with the lambda2 fix). If the target is
    NOT in the giant component, it bridges nothing central -> 0.0.
    """
    if G is None or tid is None or G.number_of_nodes() < 3:
        return np.nan
    G_und = G.to_undirected()
    G_und.remove_edges_from(nx.selfloop_edges(G_und))
    comps = list(nx.connected_components(G_und))
    if not comps:
        return np.nan
    giant = max(comps, key=len)
    if tid not in giant:
        return 0.0
    H = G_und.subgraph(giant)
    return nx.betweenness_centrality(H, normalized=True).get(tid, np.nan)


mod_records, bet_records = [], []
print(f'seeds: {len(SELECTED_SEEDS)}')
for seed in SELECTED_SEEDS:
    for target_sign in [1.0, -1.0]:
        run_dir = os.path.join(RESULTS_DIR, f'run_{seed}_dir_{target_sign}')
        if not os.path.isdir(run_dir):
            continue
        # Identify the target from step 20000 (the 'target' attribute is only set
        # at/after the manipulation onset) and track that same node at every step,
        # so the pre-onset betweenness trajectory is defined — matching the
        # existing 'betweenness' column in target_hub_metrics.
        fp_20k = _gexf_path(run_dir, 20000)
        tid_fixed = parse_gexf_full(fp_20k)[1] if fp_20k else None
        for step in GEXF_STEPS:
            fp = _gexf_path(run_dir, step)
            if not fp:
                continue
            G, _ = parse_gexf_full(fp)
            mod_records.append({'seed': seed, 'target_sign': target_sign, 'step': step,
                                'modularity': _compute_modularity(G)})
            bet_records.append({'seed': seed, 'target_sign': target_sign, 'step': step,
                                'betweenness_gc': _betweenness_giant(G, tid_fixed)})

df_mod = pd.DataFrame(mod_records)
df_bet = pd.DataFrame(bet_records)

# Merge modularity into nw_stats.
nw_path = os.path.join(DEST_DIR, 'nw_stats_5000step.csv')
nw = pd.read_csv(nw_path)
nw = nw.drop(columns=[c for c in ['modularity'] if c in nw.columns])
nw = nw.merge(df_mod, on=['seed', 'target_sign', 'step'], how='left')
nw.to_csv(nw_path, index=False)
print(f'nw_stats_5000step.csv updated (+modularity), {len(nw)} rows')

# Merge betweenness_gc into target_hub_metrics.
hub_path = os.path.join(DEST_DIR, 'target_hub_metrics_5000step.csv')
hub = pd.read_csv(hub_path)
hub = hub.drop(columns=[c for c in ['betweenness_gc'] if c in hub.columns])
hub = hub.merge(df_bet, on=['seed', 'target_sign', 'step'], how='left')
hub.to_csv(hub_path, index=False)
print(f'target_hub_metrics_5000step.csv updated (+betweenness_gc), {len(hub)} rows')

# Quick sanity print.
for nm, df, col in [('modularity', nw, 'modularity'), ('betweenness_gc', hub, 'betweenness_gc')]:
    g = df.groupby('step')[col].mean()
    print(f'{nm}: step0={g.get(0,np.nan):.4f} onset={g.get(20000,np.nan):.4f} end={g.get(40000,np.nan):.4f}')
