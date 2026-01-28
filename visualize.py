import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json


def create_vertical_report():
    # Load data directly from your latest JSON results
    files = {"Polars": "./benchmark_results/polars.json", "Pandas 3": "./benchmark_results/pandas3.json", "Pandas 2": "./benchmark_results/pandas2.json"}
    results = {}
    for backend, fname in files.items():
        with open(fname) as f:
            raw = json.load(f)
            results[backend] = {
                "CSV Load": {"time": raw["partA"]["csv_time"], "mem": raw["partA"]["csv_mem"]},
                "Slicing": {"time": raw["partB"]["slice_time"], "mem": raw["partB"]["slice_mem"]},
                "Join & GroupBy": {"time": raw["partC"]["join_time"], "mem": raw["partC"]["join_mem"]}
            }

    metrics_list = ["CSV Load", "Slicing", "Join & GroupBy"]
    backends = ["Polars", "Pandas 2", "Pandas 3"]
    colors = {"Polars": "#0077b6", "Pandas 2": "#ee964b", "Pandas 3": "#2d3142"}

    for unit in ["Ratio", "Memory (MB)"]:
        fig, ax = plt.subplots(figsize=(12, 8))
        bar_width, group_gap = 0.22, 0.05
        indices = np.arange(len(metrics_list))

        for i, backend in enumerate(backends):
            if unit == "Ratio":
                # Relative Performance Ratio
                values = [results[backend][m]["time"] / min([results[b][m]["time"] for b in backends]) for m in
                          metrics_list]
            else:
                # Peak Memory Usage
                values = [results[backend][m]["mem"] for m in metrics_list]

            # Calculate horizontal positions for vertical bars
            pos = [idx + (i * (bar_width + group_gap)) for idx in indices]

            # Vertical bars with no outlines
            bars = ax.bar(pos, values, width=bar_width, label=backend,
                          color=colors[backend], alpha=0.95, edgecolor='none', linewidth=0)

            # Data labels on top of the bars
            for bar in bars:
                height = bar.get_height()
                label = f'{height:.1f}x' if unit == "Ratio" else f'{height:,.0f}'
                ax.text(bar.get_x() + bar.get_width() / 2, height + (height * 0.02),
                        label, ha='center', va='bottom', fontweight='bold', fontsize=9)

        # Formatting X-axis for vertical orientation
        ax.set_xticks(indices + (bar_width + group_gap))
        ax.set_xticklabels(metrics_list, fontweight='bold', fontsize=12)

        if unit == "Ratio":
            plt.ylabel("Performance Ratio (Lower is Better | 1.0x = Baseline)", fontweight='bold')
            plt.title("Execution Time: Performance Gap Ratio", fontsize=18, fontweight='bold', loc='left', pad=25)
        else:
            plt.ylabel("Peak RAM Usage (MB)", fontweight='bold')
            plt.title("Memory Efficiency: Peak RAM Usage", fontsize=18, fontweight='bold', loc='left', pad=25)

        # Legend Top Right
        ax.legend(title="Engine", loc='upper right', frameon=True, shadow=True)

        ax.spines[['top', 'right']].set_visible(False)
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        plt.tight_layout()

        file_name = f"linkedin_vertical_{unit.lower().split()[0]}.png"
        plt.savefig(file_name, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Successfully saved {file_name}")


if __name__ == "__main__":
    create_vertical_report()