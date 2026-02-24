import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

def read_metrics_mean_var_series(data_dir, target_prefix, metric_prefix, var_prefix, count_prefix, num_classes=5, max_index=5000):
    class_means = {i: [] for i in range(num_classes)}
    class_sems = {i: [] for i in range(num_classes)}
    steps = []

    for i in range(max_index + 1):
        filename = f"{target_prefix}_{i}.csv"
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            df = pd.read_csv(filepath)
            row = df.iloc[0]
            steps.append(int(row["step"]))
            for c in range(num_classes):
                mean_key = f"{metric_prefix}_{c}"
                var_key = f"{var_prefix}_{c}"
                count_key = f"{count_prefix}_{c}"
                
                mean_val = float(row[mean_key])
                var_val = float(row[var_key])
                n = max(float(row.get(count_key, 1)), 1) 
                
                sem_val = np.sqrt(var_val) / np.sqrt(n)

                class_means[c].append(mean_val)
                class_sems[c].append(sem_val)
        except Exception as e:
            print(f"[{i:04d}] error: {e}")

    return steps, class_means, class_sems


def plot_smoothed_band(x, mean_dict, std_dict, title, ylabel, output_path, window_size=10, class_bins=None):
    smoothed_x = [x[i] for i in range(0, len(x), window_size)]

    plt.figure(figsize=(10, 6))
    colors = ["blue", "dodgerblue", "green", "orange", "red"]
    for c in mean_dict:
        mean = mean_dict[c]
        std = std_dict[c]
        color = colors[c % len(colors)]

        if class_bins is not None and c < len(class_bins) - 1:
            label = f"{class_bins[c]:.1f} ~ {class_bins[c+1]:.1f}"
        else:
            label = f"Class {c}"

        plt.plot(smoothed_x, mean, label=label, color=color)
        plt.fill_between(smoothed_x,
                         np.array(mean) - np.array(std),
                         np.array(mean) + np.array(std),
                         color=color, alpha=0.2)

    plt.xlabel("Step", fontsize=14)
    plt.ylabel(ylabel, fontsize=14)
    plt.grid(True)
    plt.legend(fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"fig saved: {output_path}")

def smooth(series_dict, window_size=100):
    smoothed = {}
    for c, values in series_dict.items():
        smoothed[c] = [
            np.mean(values[i:i+window_size])
            for i in range(0, len(values), window_size)
        ]
    return smoothed

def main():
    data_dir = "./results/metrics"
    prefix = "result"
    window_size = 100
    num_classes = 5

    metric_prefix = "feedPostOpinionMean"
    var_prefix = "feedPostOpinionVar"
    count_prefix = "feedPostCount" 
    
    ylabel = "Feed Post Opinion Mean"
    title = "Feed Post Opinion Mean per Class (Smoothed, ±1 SE)"
    filename = "feed_post_mean_with_SE.png"

    x, mean_series, sem_series = read_metrics_mean_var_series(
        data_dir, prefix, metric_prefix, var_prefix, count_prefix, num_classes
    )

    if not x:
        print(f"no data: {metric_prefix}")
        return

    smoothed_means = smooth(mean_series, window_size)
    smoothed_sems = smooth(sem_series, window_size)

    os.makedirs("./results/figures", exist_ok=True)
    output_path = os.path.join("./results/figures", filename)
    class_bins = [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0]
    plot_smoothed_band(
        x, smoothed_means, smoothed_sems,
        title, ylabel, output_path, window_size,
        class_bins=class_bins
    )
    
if __name__ == "__main__":
    main()
