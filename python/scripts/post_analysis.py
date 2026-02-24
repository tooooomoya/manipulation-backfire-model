import pandas as pd
import matplotlib.pyplot as plt
import os

def smooth_ratios(ratios, window_size=100):
    smoothed = {bin_name: [] for bin_name in ratios}
    num_steps = len(next(iter(ratios.values())))

    for i in range(0, num_steps, window_size):
        for bin_name in ratios:
            window = ratios[bin_name][i:i+window_size]
            if window:
                avg = sum(window) / len(window)
                smoothed[bin_name].append(avg)

    return smoothed

def smooth_counts(counts, window_size=100):
    smoothed = []
    for i in range(0, len(counts), window_size):
        window = counts[i:i+window_size]
        if window:
            avg = sum(window) / len(window)
            smoothed.append(avg)
    return smoothed

def read_and_compute_ratios(data_dir, bins, max_index=10000):
    ratios = {bin_name: [] for bin_name in bins}
    counts = []
    x = []

    for i in range(max_index + 1):
        filename = f"post_result_{i}.csv"
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            print(f"[{i:02d}] cannot find the file: {filename}")
            continue

        try:
            df = pd.read_csv(filepath)
            row = df.iloc[0]

            total = sum([int(row[bin_name]) for bin_name in bins])
            if total == 0:
                continue  

            for bin_name in bins:
                count = int(row[bin_name])
                ratios[bin_name].append(count / total)

            counts.append(total)
            x.append(i)
        except Exception as e:
            print(f"[{i:02d}] error: {e}")

    if x:
        print("finish ")
    else:
        print("no data")

    return x, ratios, counts

def plot_ratio_bins(x, ratios, counts, bin_labels=None, window_size=100):
    if not x:
        print("no data available")
        return

    smoothed_ratios = smooth_ratios(ratios, window_size)
    smoothed_counts = smooth_counts(counts, window_size)
    smoothed_x = [x[i] for i in range(0, len(x), window_size)]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    colors = ["blue", "dodgerblue", "green", "orange", "red"]

    # left axis : ratio
    for idx, (bin_name, values) in enumerate(smoothed_ratios.items()):
        label = bin_labels[idx] if bin_labels and idx < len(bin_labels) else bin_name
        color = colors[idx % len(colors)]
        ax1.plot(smoothed_x, values, label=label, color=color, alpha=0.6)

    ax1.set_xlabel("Step", fontsize=14)
    ax1.set_ylabel("Post Ratio (100-step average)", fontsize=14)
    ax1.set_ylim(0, 1)
    ax1.grid(True)

    # right axis: % of post counts
    ax2 = ax1.twinx()
    ax2.plot(smoothed_x, smoothed_counts, color="black", linestyle="--", label="Post Count", alpha = 0.5)
    ax2.set_ylabel("Post Count (100-step average)", fontsize=14)

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, fontsize=12)

    plt.tight_layout()
    output_path = "./results/figures/ratio_bins_with_counts.png"
    plt.savefig(output_path)
    print(f"fig saved: {output_path}")

def main():
    data_dir = "./results/posts"
    bins = ["bin_0", "bin_1", "bin_2", "bin_3", "bin_4"]
    bin_labels = ["-1.0 ~ -0.6", "-0.6 ~ -0.2", "-0.2 ~ 0.2", "0.2 ~ 0.6", "0.6 ~ 1.0"]

    x, ratios, counts = read_and_compute_ratios(data_dir, bins)
    plot_ratio_bins(x, ratios, counts, bin_labels)

if __name__ == "__main__":
    main()
