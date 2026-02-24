import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def analyze_and_plot_clustering_vs_indegree(step, output_path):

    degree_path = f"results/degrees/degree_result_{step}.csv"
    clustering_path = f"results/clusterings/clustering_result_{step}.csv"

    df_degree = pd.read_csv(degree_path)
    df_clust = pd.read_csv(clustering_path)

    df = pd.merge(df_degree, df_clust, on="agentId")

    df = df[df["inDegree"] > 0]

    avg_clust = df["clusteringCoefficient"].mean()
    print(f"avg clusterings coeff : {avg_clust:.4f}")

    plt.figure(figsize=(6, 4))
    plt.scatter(df["inDegree"], df["clusteringCoefficient"], color='black', alpha=0.5, label="Individual nodes")

    grouped = df.groupby("inDegree")["clusteringCoefficient"].mean()
    plt.plot(grouped.index, grouped.values, color='red', linewidth=2, label="Average by in-degree")

    plt.xscale('log')
    plt.xlabel(r'$k^{(\mathrm{in})}$', fontsize=14)
    plt.ylabel('Clustering Coefficient', fontsize=14)
    plt.grid(True, which='both', ls=':')
    plt.legend(fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"fig saved: {output_path}")

    return {
        'step': step,
        'average_clustering': avg_clust,
        'in_degree_unique': grouped.index.tolist(),
        'avg_clustering_by_in_degree': grouped.values.tolist()
    }

def main():
    analyze_and_plot_clustering_vs_indegree(5000, "results/figures/clusteringCoefficinet_dist.png")
 
if __name__ == "__main__":
    main()
