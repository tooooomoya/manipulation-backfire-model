"""
Shared helpers for the backfire/structural analysis notebooks:
  - structural-backfire-analysis.ipynb  (target-hub backfire effect)
  - structural-3arm-dynamics.ipynb      (manip vs control global/per-camp structure)
  - camp-echo-chamber-metrics.ipynb     (per-camp giant-component echo-chamber metrics)

All three notebooks start with `from bf_common import *` so the GEXF-parsing
and metric-computation logic lives in exactly one place.
"""
import os
import re
import glob
import json as _json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import xml.etree.ElementTree as ET
from scipy import stats
from scipy.stats import fisher_exact, ks_2samp, chi2_contingency

# `from bf_common import *` skips underscore-prefixed names unless listed here
# explicitly — several helpers below (_compute_modularity, _gexf_path, etc.)
# are relied on by the notebooks, so they must be included.
__all__ = [
    'os', 're', 'glob', 'np', 'pd', 'plt', 'nx', 'ET',
    'stats', 'fisher_exact', 'ks_2samp', 'chi2_contingency',
    'RESULTS_DIR', 'SUMMARY_DIR', 'BINS', 'ONSET_STEP', 'PRE_RANGE', 'POST_RANGE',
    'STRUCT_STEPS', '_POS_MAP', 'GROUP_ORDER', 'GROUP_LABELS',
    'CAMP_COLORS', 'CAMP_PALETTE', 'get_relative_group',
    '_gexf_has_target', 'build_valid_seeds', 'parse_gexf_for_target',
    '_parse_gexf_full', '_gexf_path', 'parse_gexf_agent_attrs',
    'parse_run_dirname', 'load_target_id',
    '_compute_modularity', '_algebraic_connectivity', '_undirected_simple',
    'compute_global_structural', 'compute_camp_structural',
    'compute_camp_giant_metrics', 'target_followers_by_camp',
    'get_target_structural_metrics', 'get_follower_opinion_metrics', 'average_metrics',
    'compute_backfire_effect', 'compute_run_agent_deltas',
    'load_unfollow_timeseries_local', 'load_post_timeseries_local', 'load_metric_timeseries',
    'classify_seed', 'make_seed_row', 'SEEDS',
]

# =========================================================================
# Global Constants
# =========================================================================
RESULTS_DIR = "./results"
SUMMARY_DIR = os.path.join(RESULTS_DIR, "BF_analysis")
os.makedirs(SUMMARY_DIR, exist_ok=True)
BINS = ["bin_0", "bin_1", "bin_2", "bin_3", "bin_4"]

# Manipulation onset step: must match OpinionDynamics.java's `step == ONSET_STEP` check.
# All pre/post windows below are derived from this single constant.
ONSET_STEP = 15000

# step window just before intervention = baseline; end of simulation = outcome
PRE_RANGE  = (ONSET_STEP - 1000, ONSET_STEP)
POST_RANGE = (39000, 40000)

STRUCT_STEPS = list(range(0, 40001, 5000))   # GEXF snapshot cadence

# Direction-relative bin labels, ordered from most-opposing to most-aligned.
# dir=+1: bin0→strong_opposite, bin1→weak_opposite, bin2→neutral, bin3→weak_target, bin4→strong_target
# dir=−1: bins are mirrored
_POS_MAP = {
     1.0: {0: 'strong_opposite', 1: 'weak_opposite', 2: 'neutral', 3: 'weak_target', 4: 'strong_target'},
    -1.0: {0: 'strong_target',   1: 'weak_target',   2: 'neutral', 3: 'weak_opposite', 4: 'strong_opposite'},
}
GROUP_ORDER  = ['strong_opposite', 'weak_opposite', 'neutral', 'weak_target', 'strong_target']
GROUP_LABELS = ['Strong\nOpposite', 'Weak\nOpposite', 'Neutral', 'Weak\nTarget', 'Strong\nTarget']

# Canonical per-camp colors: target side warm (red/orange), opposite side cool
# (blue/light-blue), neutral grey. Used wherever camps are drawn as series.
CAMP_COLORS = {
    'strong_opposite': '#1f4e9c',   # blue
    'weak_opposite':   '#7fb3d5',   # light blue
    'neutral':         '#27ae60',   # green
    'weak_target':     '#e67e22',   # orange
    'strong_target':   '#c0392b',   # red
}
CAMP_PALETTE = [CAMP_COLORS[g] for g in GROUP_ORDER]

def get_relative_group(opinionclass, target_sign):
    return _POS_MAP[target_sign].get(opinionclass, 'unknown')

# =========================================================================
# GEXF parsing helpers
# =========================================================================
def _gexf_has_target(fpath):
    """Return True if any node in the GEXF has target=True."""
    try:
        tree = ET.parse(fpath)
        root = tree.getroot()
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        attr_map = {}
        for attr in root.findall(".//attributes[@class='node']/attribute"):
            attr_map[attr.get('id')] = attr.get('title')
        for node in root.findall(".//node"):
            for av in node.findall(".//attvalue"):
                title = attr_map.get(av.get('for'), av.get('for'))
                if title == 'target' and av.get('value', '').lower() == 'true':
                    return True
    except Exception:
        pass
    return False

def build_valid_seeds(results_dir, check_step=ONSET_STEP):
    """
    Exclude seeds where no run has a target=True node in step_{check_step}.gexf.
    Mirrors the exclusion logic in result-summary.ipynb.
    """
    seed_dirs = glob.glob(os.path.join(results_dir, "run_*_dir_*"))
    seeds_found = set()
    for d in seed_dirs:
        m = re.match(r'run_(\d+)_dir_', os.path.basename(d))
        if m:
            seeds_found.add(int(m.group(1)))

    valid, excluded = [], []
    for seed in sorted(seeds_found):
        gexf_files = glob.glob(
            os.path.join(results_dir, f"run_{seed}_dir_*", "GEXF", "*", f"step_{check_step}.gexf")
        )
        if any(_gexf_has_target(f) for f in gexf_files):
            valid.append(seed)
        else:
            excluded.append(seed)

    print(f"Seeds with target nodes   : {valid}")
    print(f"Seeds excluded (no target): {excluded}")
    return valid

def parse_gexf_for_target(fpath):
    try:
        tree = ET.parse(fpath)
        root = tree.getroot()
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]

        attr_map = {}
        for attr in root.findall(".//attributes[@class='node']/attribute"):
            attr_map[attr.get('id')] = attr.get('title')

        G = nx.DiGraph()
        target_nodes = []
        node_opinions = {}

        for node in root.findall(".//node"):
            nid = node.get('id')
            G.add_node(nid)
            for av in node.findall(".//attvalue"):
                title = attr_map.get(av.get('for'), av.get('for'))
                if title == 'target' and av.get('value', '').lower() == 'true':
                    target_nodes.append(nid)
                if title == 'opinion':
                    try:
                        node_opinions[nid] = float(av.get('value'))
                    except (TypeError, ValueError):
                        pass

        for edge in root.findall(".//edge"):
            G.add_edge(edge.get('source'), edge.get('target'))

        return G, target_nodes, node_opinions
    except Exception as e:
        print(f"  [WARN] GEXF parse failed ({fpath}): {e}")
        return None, [], {}

def _parse_gexf_full(fpath):
    """One-pass GEXF parse -> (DiGraph, target_ids, {nid: {opinion, opinionclass, postprob}})."""
    try:
        tree = ET.parse(fpath); root = tree.getroot()
        for elem in root.iter():
            if '}' in elem.tag: elem.tag = elem.tag.split('}', 1)[1]
        attr_map = {a.get('id'): a.get('title') for a in root.findall(".//attributes[@class='node']/attribute")}
        G = nx.DiGraph(); target_ids, agents = [], {}
        for node in root.findall(".//node"):
            nid = node.get('id'); G.add_node(nid)
            d = {'opinion': np.nan, 'opinionclass': -1, 'postprob': np.nan}
            for av in node.findall(".//attvalue"):
                t, v = attr_map.get(av.get('for'), av.get('for')), av.get('value', '')
                if t == 'opinion':
                    try: d['opinion'] = float(v)
                    except: pass
                elif t == 'opinionClass':
                    try: d['opinionclass'] = int(v)
                    except: pass
                elif t == 'postProb':
                    try: d['postprob'] = float(v)
                    except: pass
                elif t == 'target' and v.lower() == 'true': target_ids.append(nid)
            agents[nid] = d
        for edge in root.findall(".//edge"): G.add_edge(edge.get('source'), edge.get('target'))
        return G, target_ids, agents
    except Exception: return None, [], {}

def _gexf_path(run_dir, step):
    fs = glob.glob(os.path.join(run_dir, 'GEXF', '*', f'step_{step}.gexf'))
    return fs[0] if fs else None

def parse_gexf_agent_attrs(fpath):
    """Parse one GEXF snapshot. Returns {node_id: {opinion, postprob, opinionclass, is_target}}."""
    try:
        tree = ET.parse(fpath); root = tree.getroot()
        for elem in root.iter():
            if '}' in elem.tag: elem.tag = elem.tag.split('}', 1)[1]
        attr_map = {a.get('id'): a.get('title') for a in root.findall(".//attributes[@class='node']/attribute")}
        agents = {}
        for node in root.findall(".//node"):
            nid = node.get('id')
            d = {'opinion': np.nan, 'postprob': np.nan, 'opinionclass': np.nan, 'is_target': False}
            for av in node.findall(".//attvalue"):
                t, v = attr_map.get(av.get('for'), av.get('for')), av.get('value', '')
                if t == 'opinion':
                    try: d['opinion'] = float(v)
                    except: pass
                elif t == 'postProb':
                    try: d['postprob'] = float(v)
                    except: pass
                elif t == 'opinionClass':
                    try: d['opinionclass'] = int(v)
                    except: pass
                elif t == 'target': d['is_target'] = (v.lower() == 'true')
            agents[nid] = d
        return agents
    except Exception: return {}

def parse_run_dirname(dirname):
    """run_<seed>_dir_<sign>_manip_<0|1>  ->  (seed, sign, manip).
    Falls back to manip=1 for legacy dirs without the suffix. Returns None if
    the name is not a run dir."""
    m = re.match(r'run_(\d+)_dir_([+-]?\d+\.?\d*)_manip_([01])$', dirname)
    if m:
        return int(m.group(1)), float(m.group(2)), int(m.group(3))
    m = re.match(r'run_(\d+)_dir_([+-]?\d+\.?\d*)$', dirname)   # legacy
    if m:
        return int(m.group(1)), float(m.group(2)), 1
    return None

def load_target_id(run_dir):
    """Unified would-be-target id: target_id.json (both arms) first, then a
    GEXF target=true scan as a fallback. Returns a str node id or None."""
    p = os.path.join(run_dir, 'target_id.json')
    if os.path.exists(p):
        try:
            t = _json.load(open(p)).get('targets', [])
            if t:
                return str(t[0])
        except Exception:
            pass
    fp = _gexf_path(run_dir, ONSET_STEP)
    if fp:
        _, tids, _ = _parse_gexf_full(fp)
        if tids:
            return tids[0]
    return None

# =========================================================================
# Graph-level structural helpers
# =========================================================================
def _compute_modularity(G):
    """
    Directed modularity Q (Leicht & Newman 2008) with Louvain partition.
    """
    if G is None or len(G.nodes) < 4:
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

def _algebraic_connectivity(U):
    """Fiedler lambda2: nan for <2 nodes, 0.0 if disconnected, else lambda2."""
    n = U.number_of_nodes()
    if n < 2:
        return np.nan
    if not nx.is_connected(U):
        return 0.0
    try:
        return nx.algebraic_connectivity(U, tol=1e-6, seed=42)
    except Exception:
        return np.nan

def _undirected_simple(G):
    U = G.to_undirected()
    U.remove_edges_from(nx.selfloop_edges(U))
    return U

def compute_global_structural(G):
    """Global echo-chamber structure (direction-independent)."""
    U = _undirected_simple(G)
    n = U.number_of_nodes()
    out = {'n_nodes': n, 'n_edges': U.number_of_edges(),
           'giant_frac': np.nan, 'lambda2_gc': np.nan,
           'transitivity': np.nan, 'modularity': np.nan}
    if n == 0:
        return out
    comps = list(nx.connected_components(U))
    if comps:
        giant = max(comps, key=len)
        out['giant_frac'] = len(giant) / n
        out['lambda2_gc'] = _algebraic_connectivity(U.subgraph(giant).copy())
    out['transitivity'] = nx.transitivity(U) if n > 2 else np.nan
    out['modularity'] = _compute_modularity(G)
    return out

def compute_camp_structural(G, agents, target_sign):
    """Per direction-relative camp: size, within-camp density, E-I homophily
    index, camp-induced lambda2 cohesion, and intra-camp transitivity.
    E-I = (external - internal)/(external + internal); +1 = all ties external
    (heterophilous), -1 = fully inward (echo chamber)."""
    U = _undirected_simple(G)
    grp = {nid: get_relative_group(agents.get(nid, {}).get('opinionclass', -1), target_sign)
           for nid in U.nodes}
    rows = {}
    for g in GROUP_ORDER:
        members = [n for n in U.nodes if grp[n] == g]
        k = len(members)
        base = {'camp_n': k, 'intra_edges': np.nan, 'density': np.nan,
                'ei_index': np.nan, 'lambda2': np.nan, 'transitivity': np.nan,
                'mean_intra_deg': np.nan, 'camp_giant_frac': np.nan}
        if k >= 2:
            H = U.subgraph(members)
            intra = H.number_of_edges()
            deg_sum = sum(dict(U.degree(members)).values())
            ext = deg_sum - 2 * intra                 # ties with one endpoint outside
            base['intra_edges'] = intra
            base['density'] = 2 * intra / (k * (k - 1))
            base['mean_intra_deg'] = 2 * intra / k
            denom = ext + intra
            base['ei_index'] = (ext - intra) / denom if denom > 0 else np.nan
            base['lambda2'] = _algebraic_connectivity(H.copy())
            base['transitivity'] = nx.transitivity(H) if k > 2 else np.nan
            # camps are internally sparse (lambda2 is ~0 / degenerate), so use
            # the fraction of the camp inside its own largest component as the
            # informative within-camp cohesion measure.
            _cc = list(nx.connected_components(H))
            base['camp_giant_frac'] = (len(max(_cc, key=len)) / k) if _cc else np.nan
        rows[g] = base
    return rows

def compute_camp_giant_metrics(G, agents, target_sign):
    """Per direction-relative camp, restricted to that camp's OWN giant
    component (largest connected component of the camp-induced subgraph;
    same camp-first split as compute_camp_structural). Complements it with
    metrics that are only well-defined on a connected subgraph (path length)
    or read cleaner without stray disconnected singletons diluting them
    (modularity, local/global clustering, E-I, disagreement, opinion
    variance, reciprocity).

    gc_frac (== camp_giant_frac) doubles as a coverage diagnostic: if it's
    low for a camp/step, the giant component is a poor stand-in for the
    whole camp and the other gc_* metrics should be read cautiously (or the
    full connected-component size distribution inspected directly).

    gc_disagreement = sum_{i<j} (op_i - op_j)^2 over giant-component members,
    computed via the closed form n*sum(x^2) - (sum(x))^2 (== n^2 * population
    variance of opinion, which is reported alongside as gc_opinion_var).
    """
    U = _undirected_simple(G)
    grp = {nid: get_relative_group(agents.get(nid, {}).get('opinionclass', -1), target_sign)
           for nid in U.nodes}
    rows = {}
    for g in GROUP_ORDER:
        members = [n for n in U.nodes if grp[n] == g]
        k = len(members)
        base = {
            'gc_n': np.nan, 'gc_frac': np.nan, 'gc_density': np.nan,
            'gc_clustering_local': np.nan, 'gc_clustering_global': np.nan,
            'gc_modularity': np.nan, 'gc_path_length': np.nan,
            'gc_ei_index': np.nan, 'gc_reciprocity': np.nan,
            'gc_disagreement': np.nan, 'gc_opinion_var': np.nan,
        }
        if k >= 2:
            H = U.subgraph(members)
            comps = list(nx.connected_components(H))
            if comps:
                giant_nodes = max(comps, key=len)
                gk = len(giant_nodes)
                base['gc_n'] = gk
                base['gc_frac'] = gk / k
                if gk >= 2:
                    GC = H.subgraph(giant_nodes).copy()

                    base['gc_density'] = nx.density(GC)
                    base['gc_clustering_local'] = nx.average_clustering(GC)
                    base['gc_clustering_global'] = nx.transitivity(GC) if gk > 2 else np.nan

                    # modularity/reciprocity are scored on the ORIGINAL DIRECTED
                    # subgraph restricted to giant-component nodes (mirrors
                    # compute_global_structural's use of _compute_modularity).
                    D_giant = G.subgraph(giant_nodes)
                    base['gc_modularity'] = _compute_modularity(D_giant)
                    try:
                        base['gc_reciprocity'] = nx.reciprocity(D_giant)
                    except Exception:
                        base['gc_reciprocity'] = np.nan

                    # path length is well-defined because GC is connected by construction
                    try:
                        base['gc_path_length'] = nx.average_shortest_path_length(GC)
                    except Exception:
                        base['gc_path_length'] = np.nan

                    # E-I restricted to giant-component members: internal ties =
                    # within GC; external = degree in the full network minus
                    # internal (same formula as compute_camp_structural's ei_index).
                    intra = GC.number_of_edges()
                    deg_sum = sum(dict(U.degree(giant_nodes)).values())
                    ext = deg_sum - 2 * intra
                    denom = ext + intra
                    base['gc_ei_index'] = (ext - intra) / denom if denom > 0 else np.nan

                    ops = np.array([agents[n]['opinion'] for n in giant_nodes
                                    if n in agents and not np.isnan(agents[n].get('opinion', np.nan))])
                    if len(ops) >= 2:
                        base['gc_disagreement'] = len(ops) * np.sum(ops ** 2) - np.sum(ops) ** 2
                        base['gc_opinion_var'] = float(np.var(ops))
        rows[g] = base
    return rows

def target_followers_by_camp(G, tid, agents, target_sign):
    """Share and count of the target hub's followers (in-neighbours) coming
    from each direction-relative camp. This is the structural counterpart of
    link A in the spiral hypothesis (weak-target camp sheds the hub)."""
    empty = {g: {'tgt_follower_count': np.nan, 'tgt_follower_frac': np.nan}
             for g in GROUP_ORDER}
    if tid is None or tid not in G:
        return empty
    followers = list(G.predecessors(tid))     # edge a->b == a follows b
    total = len(followers)
    counts = {g: 0 for g in GROUP_ORDER}
    for f in followers:
        g = get_relative_group(agents.get(f, {}).get('opinionclass', -1), target_sign)
        if g in counts:
            counts[g] += 1
    return {g: {'tgt_follower_count': counts[g],
                'tgt_follower_frac': (counts[g] / total if total else np.nan)}
            for g in GROUP_ORDER}

# =========================================================================
# Target-hub / backfire helpers
# =========================================================================
def get_target_structural_metrics(G, target_id):
    """Node-level structural indices for the targeted agent."""
    if G is None or target_id is None or target_id not in G:
        return {}

    in_degree = G.in_degree(target_id)
    bc_all = nx.betweenness_centrality(G, normalized=True)
    betweenness = bc_all.get(target_id, np.nan)
    clustering = nx.clustering(G, target_id)
    pr_all = nx.pagerank(G, alpha=0.85, max_iter=200)
    pagerank = pr_all.get(target_id, np.nan)

    try:
        ec_all = nx.eigenvector_centrality(G, max_iter=1000, tol=1e-6)
        eigenvector = ec_all.get(target_id, np.nan)
    except nx.PowerIterationFailedConvergence:
        eigenvector = np.nan

    return {
        'in_degree':   in_degree,
        'betweenness': betweenness,
        'clustering':  clustering,
        'pagerank':    pagerank,
        'eigenvector': eigenvector,
    }

def get_follower_opinion_metrics(G, target_id, node_opinions, target_sign):
    """
    Opinion-based homophily metrics for the target's follower set.
    """
    if G is None or target_id is None or target_id not in G:
        return {}

    target_op = node_opinions.get(target_id, np.nan)
    followers = list(G.predecessors(target_id))
    follower_ops = np.array([node_opinions[f] for f in followers if f in node_opinions])

    if len(follower_ops) == 0:
        return {
            'target_opinion':          target_op,
            'follower_mean_opinion':   np.nan,
            'follower_opinion_std':    np.nan,
            'follower_homophily_frac': np.nan,
            'follower_dir_alignment':  np.nan,
        }

    same_sign_as_target = np.sign(follower_ops) == np.sign(target_op) if not np.isnan(target_op) else np.nan
    same_sign_as_dir    = np.sign(follower_ops) == np.sign(target_sign)

    return {
        'target_opinion':          target_op,
        'follower_mean_opinion':   float(np.mean(follower_ops)),
        'follower_opinion_std':    float(np.std(follower_ops)),
        'follower_homophily_frac': float(np.mean(same_sign_as_target)) if not np.isnan(target_op) else np.nan,
        'follower_dir_alignment':  float(np.mean(same_sign_as_dir)),
    }

def average_metrics(metric_list):
    """Average a list of metric dicts across targets, ignoring NaN per key."""
    if not metric_list:
        return {}
    keys = metric_list[0].keys()
    result = {}
    for k in keys:
        vals = [m[k] for m in metric_list
                if k in m and not (isinstance(m[k], float) and np.isnan(m[k]))]
        result[k] = float(np.mean(vals)) if vals else np.nan
    return result

def compute_backfire_effect(run_dir, target_sign, pre_range, post_range):
    post_dir = os.path.join(run_dir, "posts")
    files = glob.glob(os.path.join(post_dir, "post_result_*.csv"))
    if not files: return np.nan
    dfs = []
    for f in files:
        try: dfs.append(pd.read_csv(f))
        except: pass
    if not dfs: return np.nan
    df = pd.concat(dfs, ignore_index=True).sort_values('step')

    if target_sign > 0:
        target_bins, opposite_bins = ["bin_3", "bin_4"], ["bin_0", "bin_1"]
    else:
        target_bins, opposite_bins = ["bin_0", "bin_1"], ["bin_3", "bin_4"]

    def mean_share(df, bins, step_range):
        mask = (df['step'] >= step_range[0]) & (df['step'] <= step_range[1])
        sub = df[mask].copy()
        if sub.empty: return np.nan
        total = sub[BINS].sum(axis=1).replace(0, np.nan)
        return (sub[bins].sum(axis=1) / total).mean()

    t_pre, t_post = mean_share(df, target_bins, pre_range), mean_share(df, target_bins, post_range)
    o_pre, o_post = mean_share(df, opposite_bins, pre_range), mean_share(df, opposite_bins, post_range)
    return (o_post - o_pre) - (t_post - t_pre)

def compute_run_agent_deltas(run_dir, pre_steps, post_steps,
                              class_ref_step=ONSET_STEP - 5000, target_ref_step=ONSET_STEP):
    gexf_base = os.path.join(run_dir, "GEXF")
    def _load(step):
        fs = glob.glob(os.path.join(gexf_base, "*", f"step_{step}.gexf"))
        return parse_gexf_agent_attrs(fs[0]) if fs else {}
    ref_class, ref_target = _load(class_ref_step), _load(target_ref_step)
    if not ref_class: return []
    pre_snaps, post_snaps = [_load(s) for s in pre_steps if _load(s)], [_load(s) for s in post_steps if _load(s)]
    if not pre_snaps or not post_snaps: return []
    rows = []
    for nid, ref_c in ref_class.items():
        if ref_target.get(nid, {}).get('is_target', False): continue
        p_ops = [sn[nid]['opinion']  for sn in pre_snaps  if nid in sn and not np.isnan(sn[nid]['opinion'])]
        p_pps = [sn[nid]['postprob'] for sn in pre_snaps  if nid in sn and not np.isnan(sn[nid]['postprob'])]
        q_ops = [sn[nid]['opinion']  for sn in post_snaps if nid in sn and not np.isnan(sn[nid]['opinion'])]
        q_pps = [sn[nid]['postprob'] for sn in post_snaps if nid in sn and not np.isnan(sn[nid]['postprob'])]
        if not p_ops or not p_pps or not q_ops or not q_pps: continue
        oc = ref_c['opinionclass']
        rows.append({
            'node_id': nid, 'opinionclass': int(oc) if not np.isnan(oc) else -1,
            'pre_opinion': np.mean(p_ops), 'post_opinion': np.mean(q_ops), 'delta_opinion': np.mean(q_ops) - np.mean(p_ops),
            'pre_postprob': np.mean(p_pps), 'post_postprob': np.mean(q_pps), 'delta_postprob': np.mean(q_pps) - np.mean(p_pps)
        })
    return rows

def load_unfollow_timeseries_local(run_dir, target_sign, window=100):
    metric_dir = os.path.join(run_dir, 'metrics')
    files = glob.glob(os.path.join(metric_dir, 'result_*.csv'))
    if not files: return None
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs).sort_values('step').reset_index(drop=True)
    pmap = _POS_MAP[target_sign]

    for g in GROUP_ORDER:
        df[g] = 0.0

    for i in range(5):
        col = f'targetUnfollow_{i}'
        if col in df.columns:
            group = pmap[i]
            df[group] = df[group] + df[col]

    df['window_idx'] = df['step'] // window
    agg = df.groupby('window_idx')[GROUP_ORDER].sum()
    agg['step'] = agg.index * window
    return agg.reset_index(drop=True)

def load_post_timeseries_local(run_dir, target_sign, window=100):
    post_dir = os.path.join(run_dir, 'posts')
    files = glob.glob(os.path.join(post_dir, 'post_result_*.csv'))
    if not files: return None
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs).sort_values('step').reset_index(drop=True)
    pmap = _POS_MAP[target_sign]

    for g in GROUP_ORDER:
        df[g] = 0.0

    for i in range(5):
        col = f'bin_{i}'
        if col in df.columns:
            group = pmap[i]
            df[group] = df[group] + df[col]

    df['total_posts'] = df[[f'bin_{i}' for i in range(5)]].sum(axis=1)

    df['window_idx'] = df['step'] // window
    agg = df.groupby('window_idx')[GROUP_ORDER + ['total_posts']].mean()
    agg['step'] = agg.index * window
    return agg.reset_index(drop=True)

# shared per-bin metric timeseries loader (used by Analysis 2b, Unified Dynamics, Section 3.3)
def load_metric_timeseries(run_dir, target_sign, prefix, window=100):
    metric_dir = os.path.join(run_dir, "metrics")
    files = glob.glob(os.path.join(metric_dir, "result_*.csv"))
    if not files: return None
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs).sort_values("step").reset_index(drop=True)

    pmap = _POS_MAP[target_sign]
    res_df = pd.DataFrame({"step": df["step"]})
    for g in GROUP_ORDER:
        res_df[g] = np.nan

    for i in range(5):
        col = f"{prefix}_{i}"
        if col in df.columns:
            group = pmap[i]
            res_df[group] = df[col]

    res_df["window_idx"] = res_df["step"] // window
    agg = res_df.groupby("window_idx")[GROUP_ORDER].mean()
    agg["step"] = agg.index * window
    return agg.reset_index(drop=True)

def classify_seed(d):
    if -1.0 not in d or 1.0 not in d: return None
    b_neg, b_pos = d[-1.0]['backfire_effect'], d[1.0]['backfire_effect']
    if b_neg > 0 and b_pos > 0: return 'both'
    elif b_neg <= 0 and b_pos <= 0: return 'neither'
    else: return 'one'

def make_seed_row(seed, d, seed_class_dict):
    base = dict(d[-1.0])
    base['backfire_neg']  = d[-1.0]['backfire_effect']
    base['backfire_pos']  = d[1.0]['backfire_effect']
    base['mean_backfire'] = (d[-1.0]['backfire_effect'] + d[1.0]['backfire_effect']) / 2
    base['backfire_class'] = seed_class_dict[seed]
    return base

print("bf_common loaded.")
SEEDS = build_valid_seeds(RESULTS_DIR)
