
import networkx as nx
import numpy as np
import random

def compute_metrics(G):
    # Total degree
    degrees = [d for n, d in G.degree()]
    avg_degree = np.mean(degrees)
    
    # Path length and Diameter on giant component of undirected version
    G_und = G.to_undirected()
    if len(G_und) == 0:
        return avg_degree, np.nan, np.nan, np.nan, np.nan
        
    giant_nodes = max(nx.connected_components(G_und), key=len)
    G_giant = G_und.subgraph(giant_nodes)
    
    if len(G_giant) > 1:
        avg_path = nx.average_shortest_path_length(G_giant)
        diameter = nx.diameter(G_giant)
    else:
        avg_path = np.nan
        diameter = np.nan
        
    # Clustering (directed)
    clustering = nx.average_clustering(G)
    
    # Power-law exponent (gamma) for in-degree
    in_degrees = [d for n, d in G.in_degree() if d > 0]
    if len(in_degrees) > 50:
        k_min = min(in_degrees)
        # Simple Hill estimator
        gamma = 1 + len(in_degrees) / sum(np.log(np.array(in_degrees) / (k_min - 0.5)))
    else:
        gamma = np.nan
        
    return avg_degree, avg_path, diameter, gamma, clustering

def generate_er(n, p, seed):
    return nx.gnp_random_graph(n, p, seed=seed, directed=True)

def generate_ws(n, k, p, seed):
    # Java implementation of WS:
    # halfK = k // 2
    # Connect to right halfK neighbors
    # Then rewire with prob p
    random.seed(seed)
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    halfK = k // 2
    for i in range(n):
        for j in range(1, halfK + 1):
            G.add_edge(i, (i + j) % n)
            
    # Rewire
    edges = list(G.edges())
    for u, v in edges:
        if random.random() < p:
            G.remove_edge(u, v)
            attempts = 0
            while attempts < n:
                new_v = random.randint(0, n - 1)
                if new_v != u and not G.has_edge(u, new_v):
                    G.add_edge(u, new_v)
                    break
                attempts += 1
            else:
                G.add_edge(u, v) # restore if failed
    return G

def generate_hk(n, m, A, pt, seed):
    # Java implementation of HK
    random.seed(seed)
    G = nx.DiGraph()
    pool = []
    
    seedSize = min(m + 1, n)
    for i in range(seedSize):
        for _ in range(A): pool.append(i)
        
    for i in range(seedSize):
        for j in range(seedSize):
            if i != j:
                G.add_edge(i, j)
                pool.append(j)
                
    for newNode in range(seedSize, n):
        for _ in range(A): pool.append(newNode)
        targets = set()
        while len(targets) < m:
            # PA step
            u = -1
            attempts = 0
            while attempts < len(pool) * 2:
                candidate = random.choice(pool)
                if candidate != newNode and candidate not in targets:
                    u = candidate
                    break
                attempts += 1
            if u == -1: break
            
            G.add_edge(newNode, u)
            pool.append(u)
            targets.add(u)
            
            if len(targets) == m: break
            
            # TF step
            if random.random() < pt:
                out_neighbors = [v for v in range(newNode) if G.has_edge(u, v) and v not in targets]
                if out_neighbors:
                    v = random.choice(out_neighbors)
                    G.add_edge(newNode, v)
                    pool.append(v)
                    targets.add(v)
    return G

def generate_cnnr(n, p, r, seed):
    # Java implementation of CNNR
    random.seed(seed)
    G = nx.DiGraph()
    G.add_node(0)
    G.add_node(1)
    G.add_edge(0, 1)
    
    potential_edges = set()
    current_size = 2
    
    while current_size < n:
        if random.random() < 1 - p:
            # add node
            new_node = current_size
            current_size += 1
            v = random.randint(0, new_node - 1)
            G.add_edge(new_node, v)
            for neighbor in range(new_node):
                if G.has_edge(v, neighbor) and neighbor != new_node:
                    potential_edges.add((new_node, neighbor))
        else:
            if random.random() < 1 - r:
                if potential_edges:
                    edge = random.choice(list(potential_edges))
                    G.add_edge(edge[0], edge[1])
                    potential_edges.remove(edge)
            else:
                a = random.randint(0, current_size - 1)
                attempts = 0
                while attempts < 100:
                    b = random.randint(0, current_size - 1)
                    if a != b and not G.has_edge(a, b):
                        G.add_edge(a, b)
                        break
                    attempts += 1
    return G

topologies = {
    "CNNR": lambda s: generate_cnnr(1000, 0.3, 0.01, s),
    "HK (pt=0.0)": lambda s: generate_hk(1000, 3, 1, 0.0, s),
    "HK (pt=0.3)": lambda s: generate_hk(1000, 3, 1, 0.3, s),
    "WS": lambda s: generate_ws(1000, 4, 0.1, s),
    "ER": lambda s: generate_er(1000, 0.003, s)
}

results = {}
for name, gen in topologies.items():
    print(f"Processing {name}...")
    metrics_list = []
    for seed in range(20):
        G = gen(seed)
        metrics_list.append(compute_metrics(G))
    results[name] = np.mean(metrics_list, axis=0)

print("\nFinal Results (Mean over 20 seeds):")
print("Topology | Avg Deg | Avg Path | Diameter | Gamma | Clustering")
print("-" * 60)
for name, res in results.items():
    print(f"{name:10} | {res[0]:7.2f} | {res[1]:8.2f} | {res[2]:8.2f} | {res[3]:5.2f} | {res[4]:10.4f}")
