import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import powerlaw

def analyze_and_plot_indegree_fit(in_degrees, output_path):

    filtered = in_degrees[in_degrees > 0]

    # fittings
    fit = powerlaw.Fit(filtered, discrete=True, verbose=False)
    alpha = fit.power_law.alpha
    #xmin = fit.power_law.xmin
    xmin = 1

    # comparison with lognormal
    R, p = fit.distribution_compare('power_law', 'lognormal')

    print(f"estimated alpha in power law fit: {alpha:.3f}")
    print(f"xmin: {xmin}")
    print(f"likelihood ratio R = L_powerlaw - L_lognormal = {R:.3f}")
    print(f"p-value = {p:.3f}")
    if p < 0.05:
        print("Statistically significant better fit with the log-normal distribution.")
    else:
        print("There is also a possibility that the power-law distribution provides a sufficiently good fit.")

    plt.figure(figsize=(6, 4))
    ax = plt.gca() 

    # real data (black)
    fit.plot_ccdf(ax=ax, color='black', marker='o', linestyle='None', label='Empirical')

    # Power-law fit (red)
    fit.power_law.plot_ccdf(ax=ax, color='red', linestyle='--', linewidth=2, label='Power-law fit')

    # Log-normal fit (blue)
    #fit.lognormal.plot_ccdf(ax=ax, color='blue', linestyle='-', linewidth=2, label='Log-normal fit')

    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel(r'$k^{(\mathrm{in})}$', fontsize=14)
    plt.ylabel(r'$P(k^{(\mathrm{in})} \geq x)$', fontsize=14)
    plt.grid(True, which='both', ls=':')
    plt.legend(fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"fig saved: {output_path}")

    return {
        'alpha': alpha,
        'xmin': xmin,
        'R': R,
        'p_value': p
    }


def main():
    df = pd.read_csv("results/degrees/degree_result_5000.csv")
    in_degrees = df["inDegree"]
    results = analyze_and_plot_indegree_fit(
        in_degrees,
        "./results/figures/indegree_ccdf_fit.png"
    )
 
if __name__ == "__main__":
    main()
