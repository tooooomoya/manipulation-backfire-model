import os
import pandas as pd
import matplotlib.pyplot as plt
import imageio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def create_histogram_gif(input_dir='results/opinion', output_gif='./results/figures/histogram.gif', duration=0.5, step_interval=100, y_max=2000):
    files = sorted([
        f for f in os.listdir(input_dir)
        if f.startswith("opinion_result_") and f.endswith(".csv")
    ], key=lambda x: int(x.split('_')[-1].split('.')[0]))

    images = []

    for file in files:
        step = int(file.split('_')[-1].split('.')[0])
        if step % step_interval != 0:
            continue

        df = pd.read_csv(os.path.join(input_dir, file))
        bin_labels = [float(col.replace("bin_", "")) for col in df.columns[1:]]
        values = df.iloc[0, 1:]

        normed_labels = np.linspace(-1, 1, len(bin_labels))

        cmap = mcolors.LinearSegmentedColormap.from_list("custom_cmap", ['blue', 'green', 'red'])
        colors = [cmap((val + 1) / 2) for val in normed_labels]  # [-1, 1] → [0, 1]

        plt.figure(figsize=(8, 4))
        plt.bar(bin_labels, values, color=colors)
        plt.title(f'Opinion Histogram - Step {step}')
        plt.xlabel('Opinion')
        plt.ylabel('Frequency')
        plt.ylim(0, y_max)

        n_bins = len(bin_labels)
        xticks = [bin_labels[0], bin_labels[n_bins // 2], bin_labels[-1]]
        plt.xticks(xticks, ['-1', '0', '1'])

        plt.tight_layout()
        tmp_path = f'temp_hist_{step}.png'
        plt.savefig(tmp_path)
        plt.close()

        images.append(imageio.v2.imread(tmp_path))
        os.remove(tmp_path)

    if images:
        imageio.mimsave(output_gif, images, duration=duration)
        print(f'GIF saved as {output_gif}')
    else:
        print("No images were created. Please check your input files and step interval.")


def save_histogram_for_step(step, input_dir='results/opinion', output_path=None):

    file = os.path.join(input_dir, f'opinion_result_{step}.csv')
    if not os.path.exists(file):
        raise FileNotFoundError(f"No file found for step {step}: {file}")

    df = pd.read_csv(file)
    bins = df.columns[1:]
    values = df.iloc[0, 1:]

    plt.figure()
    plt.bar(bins, values, color='coral')
    plt.title(f'Opinion Histogram - Step {step}')
    plt.xlabel('Opinion Bins')
    plt.ylabel('Frequency')
    plt.tight_layout()

    if output_path is None:
        output_path = f'opinion_histogram_step_{step}.png'

    plt.savefig(output_path)
    plt.close()
    print(f'Histogram for step {step} saved as {output_path}')

def main():
    create_histogram_gif(step_interval=100, y_max=1000)


if __name__ == "__main__":
    main()