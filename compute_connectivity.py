#!/usr/bin/env python3
"""
Compute connectivity_5000step.csv for a single experimental condition.

Usage:
    python3 compute_connectivity.py <dest_dir>

<dest_dir> is the condition summary directory, e.g.:
    results/summary/HolmeKim/A_1_m_3_pt_0.0/37e71a37

Seeds are read from <dest_dir>/selected_seeds.json (the original selection)
so this CSV is consistent with all other CSVs already saved for that condition.
Raw GEXF files must be present in ./results/run_* (written by the Java sim).

Exits with code 1 if the CSV already exists, so the shell driver can skip
conditions that were completed between runs.
"""
import sys
import os
import glob
import json
import numpy as np
import pandas as pd
import networkx as nx
import xml.etree.ElementTree as ET

RESULTS_DIR = "./results"
GEXF_STEPS  = [0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000]


# ── GEXF helpers (verbatim from save-results.ipynb) ─────────────────────────

def _strip_ns(root):
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]


def _gexf_path(run_dir, step):
    fs = glob.glob(os.path.join(run_dir, 'GEXF', '*', f'step_{step}.gexf'))
    return fs[0] if fs else None


def parse_gexf_full(fpath):
    try:
        tree = ET.parse(fpath)
        root = tree.getroot()
        _strip_ns(root)
        attr_map = {a.get('id'): a.get('title')
                    for a in root.findall(".//attributes[@class='node']/attribute")}
        G = nx.DiGraph()
        target_id = None
        agents = {}
        for node in root.findall('.//node'):
            nid = node.get('id')
            G.add_node(nid)
            d = {'opinionclass': -1, 'postprob': np.nan}
            for av in node.findall('.//attvalue'):
                t = attr_map.get(av.get('for'), av.get('for'))
                v = av.get('value', '')
                if t == 'opinionClass':
                    try:
                        d['opinionclass'] = int(v)
                    except Exception:
                        pass
                elif t == 'postProb':
                    try:
                        d['postprob'] = float(v)
                    except Exception:
                        pass
                elif t == 'target' and v.lower() == 'true':
                    target_id = nid
            agents[nid] = d
        for edge in root.findall('.//edge'):
            G.add_edge(edge.get('source'), edge.get('target'))
        return G, target_id, agents
    except Exception:
        return None, None, {}


# ── Connectivity helpers (verbatim from save-results.ipynb) ─────────────────

def _algebraic_connectivity(G_und):
    """Fiedler lambda2; 0.0 for disconnected, nan for < 2 nodes."""
    n = G_und.number_of_nodes()
    if n < 2:
        return np.nan
    if not nx.is_connected(G_und):
        return 0.0
    try:
        return nx.algebraic_connectivity(G_und, tol=1e-6, seed=42)
    except Exception:
        return np.nan


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 compute_connectivity.py <dest_dir>")
        sys.exit(2)

    dest_dir = sys.argv[1]

    out_path = os.path.join(dest_dir, 'connectivity_5000step.csv')
    if os.path.exists(out_path):
        print(f"Already exists, skipping: {out_path}")
        sys.exit(1)

    seeds_path = os.path.join(dest_dir, 'selected_seeds.json')
    if not os.path.exists(seeds_path):
        print(f"ERROR: {seeds_path} not found")
        sys.exit(2)

    with open(seeds_path) as f:
        selected_seeds = json.load(f)['selected']
    print(f"Seeds ({len(selected_seeds)}): {selected_seeds}")

    records = []
    for seed in selected_seeds:
        for target_sign in [1.0, -1.0]:
            run_dir = os.path.join(RESULTS_DIR, f"run_{seed}_dir_{target_sign}")
            if not os.path.isdir(run_dir):
                print(f"  WARN: {run_dir} not found — skipping")
                continue

            fp_20k = _gexf_path(run_dir, 20000)
            if not fp_20k:
                print(f"  WARN: step_20000.gexf missing  seed={seed} dir={target_sign}")
                continue

            _, tid, _ = parse_gexf_full(fp_20k)
            if tid is None:
                print(f"  WARN: no target node at step 20000  seed={seed} dir={target_sign}")
                continue

            for step in GEXF_STEPS:
                fp = _gexf_path(run_dir, step)
                if not fp:
                    continue
                G, _, _ = parse_gexf_full(fp)
                if G is None or tid not in G:
                    continue

                G_und = G.to_undirected()
                G_und.remove_edges_from(nx.selfloop_edges(G_und))

                l2_G   = _algebraic_connectivity(G_und)
                ap_set = set(nx.articulation_points(G_und))
                is_ap  = int(tid in ap_set)

                G_mt   = G_und.copy()
                G_mt.remove_node(tid)
                l2_mt  = _algebraic_connectivity(G_mt)
                delta  = (l2_G - l2_mt) if not (np.isnan(l2_G) or np.isnan(l2_mt)) else np.nan

                records.append({
                    'seed':                   seed,
                    'target_sign':            target_sign,
                    'step':                   step,
                    'lambda2_G':              l2_G,
                    'lambda2_G_minus_target': l2_mt,
                    'delta_lambda2':          delta,
                    'target_is_ap':           is_ap,
                })

    df = pd.DataFrame(records)
    df.to_csv(out_path, index=False)
    print(f"Saved: {out_path}  ({len(df)} rows)")


if __name__ == '__main__':
    main()
