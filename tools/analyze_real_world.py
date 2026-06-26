"""Standalone plots for real-world trace analysis."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TREE_COLORS = {
    "splay": "#1f77b4",
    "tango": "#d62728",
    "multisplay": "#2ca02c",
}

TREE_LABELS = {
    "splay": "Splay Tree",
    "tango": "Tango Tree",
    "multisplay": "Multi-Splay Tree",
}


def _load_manifest(results_dir: Path) -> pd.DataFrame:
    path = results_dir / "results_manifest.jsonl"
    records = []
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line.strip())
                    if d.get("family", "").startswith("nasa_http"):
                        records.append(d)
    return pd.DataFrame(records)


def _read_csv(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path, comment="#", engine="python")


def plot_cost_curves(manifest: pd.DataFrame, out_dir: Path):
    """Per-access cost curves with rolling average (subsampled for performance)."""
    step = 100  # ponytail: plot every 100th access to avoid timeout on 1.9M-point CSVs

    for trace_id in sorted(manifest["trace_id"].unique()):
        tdf = manifest[manifest["trace_id"] == trace_id]
        if tdf.empty:
            continue

        trace_name = trace_id.split("/")[-1] if "/" in trace_id else trace_id
        fig, ax = plt.subplots(figsize=(12, 5), dpi=150)
        window = 10000  # default

        for _, row in tdf.iterrows():
            csv_path = Path(row["csv_path"])
            if not csv_path.exists():
                continue
            tree = row["tree"]
            df = _read_csv(csv_path)
            window = min(10000, len(df) // 20)
            rolling = df["ops"].rolling(window=window, min_periods=1).mean()
            # ponytail: subsample for plotting
            idx = df["access_index"].values[::step]
            rv = rolling.values[::step]

            ax.plot(
                idx, rv,
                color=TREE_COLORS.get(tree, "#333"),
                label=TREE_LABELS.get(tree, tree),
                linewidth=0.8, alpha=0.9,
            )

        ax.set_title(f"Real-World Cost Curve: {trace_name}", fontsize=13)
        ax.set_xlabel("Access Index", fontsize=12)
        ax.set_ylabel(f"Operations / Access (rolling mean, window={window})", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend(frameon=True, fontsize=9)

        plt.tight_layout()
        plt.savefig(out_dir / f"fig_cost_curve_{trace_name}.png")
        plt.close()


def plot_ib1_ratio(manifest: pd.DataFrame, out_dir: Path):
    """Bar chart: ops_total and avg_ops per tree per trace from manifest aggregates."""
    if manifest.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), dpi=150)

    for ax, col, ylabel in [(axes[0], "ops_total", "Total Operations"),
                              (axes[1], "avg_ops_per_access", "Avg Operations / Access")]:
        # ponytail: use aggregate values already in manifest, no CSV re-read
        pivot = manifest.pivot_table(index="trace_id", columns="tree", values=col, aggfunc="first")
        x = np.arange(len(pivot))
        width = 0.25
        for i, tree in enumerate(pivot.columns):
            ax.bar(x + i * width - width, pivot[tree].values, width,
                    color=TREE_COLORS.get(tree, "#999"), label=TREE_LABELS.get(tree, tree))
        ax.set_xticks(x)
        ax.set_xticklabels(pivot.index, rotation=20, ha="right", fontsize=9)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.legend(fontsize="small")

    axes[0].set_title("Real-World: Total Operations by Tree")
    axes[1].set_title("Real-World: Average Operations per Access by Tree")
    plt.tight_layout()
    plt.savefig(out_dir / "fig_ops_comparison.png")
    plt.close()


def plot_ops_distribution(manifest: pd.DataFrame, out_dir: Path):
    """Histogram of per-access operation counts per tree, per trace (subsampled)."""
    step = 50  # ponytail: subsample to avoid timeout

    for trace_id in sorted(manifest["trace_id"].unique()):
        tdf = manifest[manifest["trace_id"] == trace_id]
        if tdf.empty:
            continue

        trace_name = trace_id.split("/")[-1] if "/" in trace_id else trace_id
        trees = sorted(tdf["tree"].unique())
        fig, axes = plt.subplots(1, len(trees), figsize=(5 * len(trees), 4), dpi=150)
        if len(trees) == 1:
            axes = [axes]

        for ax, tree in zip(axes, trees):
            rows = tdf[tdf["tree"] == tree]
            all_ops = []
            for _, row in rows.iterrows():
                csv_path = Path(row["csv_path"])
                if csv_path.exists():
                    df = _read_csv(csv_path)
                    all_ops.extend(df["ops"].values[::step])

            if all_ops:
                ax.hist(all_ops, bins=100, density=True, alpha=0.7,
                        color=TREE_COLORS.get(tree, "#999"), edgecolor="white")
            ax.set_title(f"{TREE_LABELS.get(tree, tree)}\nmean={np.mean(all_ops):.1f}, std={np.std(all_ops):.1f}", fontsize=10)
            ax.set_xlabel("Ops / Access")
            ax.set_ylabel("Density")
            ax.grid(axis="y", linestyle="--", alpha=0.3)

        fig.suptitle(f"Operations Distribution: {trace_name}", fontsize=12)
        plt.tight_layout()
        plt.savefig(out_dir / f"fig_ops_distribution_{trace_name}.png")
        plt.close()


def main():
    p = argparse.ArgumentParser(description="Generate real-world analysis plots")
    p.add_argument("--results", type=Path, default=Path("data/results"))
    p.add_argument("--out", type=Path, default=Path("data/analysis"))
    args = p.parse_args()

    out_dir = args.out / "plots" / "real_world"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(args.results)
    if manifest.empty:
        print("No real-world results found. Run benchmark on real_world traces first.")
        return

    print(f"Loaded {len(manifest)} real-world result entries.")
    plot_cost_curves(manifest, out_dir)
    plot_ib1_ratio(manifest, out_dir)
    plot_ops_distribution(manifest, out_dir)
    print(f"Plots written to {out_dir}")


if __name__ == "__main__":
    main()
