"""Plot publication-grade MIT paper replication figures from benchmark manifest."""
import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

TREE_COLORS = {
    "splay": "#1f77b4",       # Blue
    "tango": "#d62728",       # Red
    "multisplay": "#2ca02c",  # Green
    "rbtree": "#7f7f7f",      # Gray baseline
}

TREE_LABELS = {
    "splay": "Splay Tree",
    "tango": "Tango Tree",
    "multisplay": "Multi-Splay Tree",
    "rbtree": "Red-Black Tree (Static)",
}

TREE_MARKERS = {
    "splay": "o",
    "tango": "s",
    "multisplay": "^",
    "rbtree": "D",
}


def load_results_manifest(results_dir: Path = Path("data/results")) -> pd.DataFrame:
    manifest_path = results_dir / "results_manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing {manifest_path}. Run benchmark first.")

    records = []
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))
    df = pd.DataFrame(records)

    def extract_k(tid):
        m = re.search(r"_k(\d+)", str(tid))
        return int(m.group(1)) if m else np.nan

    df["k"] = df["trace_id"].apply(extract_k)
    df["lglgn"] = np.log2(np.log2(df["n"].astype(float)))
    df["lgn"] = np.log2(df["n"].astype(float))
    df["lgk"] = np.log2(df["k"].astype(float))
    return df


def plot_sequential_suite(df: pd.DataFrame, out_dir: Path):
    seq_df = df[df["family"] == "sequential"].copy()
    if seq_df.empty:
        return

    trees = [t for t in ["splay", "multisplay", "tango", "rbtree"] if t in seq_df["tree"].unique()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    for tree in trees:
        tdf = seq_df[seq_df["tree"] == tree].sort_values("n")
        x = tdf["lglgn"].values
        y_cost = tdf["avg_ops_per_access"].values
        y_ratio = tdf["ratio_ops_ib1"].values

        c = TREE_COLORS.get(tree, "#333333")
        lbl = TREE_LABELS.get(tree, tree)
        m = TREE_MARKERS.get(tree, "o")

        ax1.plot(x, y_cost, label=lbl, color=c, marker=m, linewidth=2, markersize=6)
        ax2.plot(x, y_ratio, label=lbl, color=c, marker=m, linewidth=2, markersize=6)

        if tree == "tango" and len(x) > 2:
            res = stats.linregress(x, y_cost)
            ax1.plot(x, res.intercept + res.slope * x, "--", color=c, alpha=0.6,
                     label=f"Tango Fit ($R^2={res.rvalue**2:.3f}$)")

    ax1.set_title("Sequential Workload: Amortized Search Cost (Fig. 3a)", fontsize=13, pad=10)
    ax1.set_xlabel(r"$\log_2(\log_2 n)$", fontsize=12)
    ax1.set_ylabel("Operations / Access", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(frameon=True)

    ax2.set_title("Sequential Workload: Competitiveness Ratio (Fig. 3b)", fontsize=13, pad=10)
    ax2.set_xlabel(r"$\log_2(\log_2 n)$", fontsize=12)
    ax2.set_ylabel("Total Operations / Wilber-1 Bound", fontsize=12)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(frameon=True)

    plt.tight_layout()
    plt.savefig(out_dir / "fig3_sequential_scaling.png")
    plt.close()


def plot_random_suite(df: pd.DataFrame, out_dir: Path):
    rnd_df = df[df["family"] == "uniform_random"].copy()
    if rnd_df.empty:
        return

    trees = [t for t in ["splay", "multisplay", "tango", "rbtree"] if t in rnd_df["tree"].unique()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    for tree in trees:
        tdf = rnd_df[rnd_df["tree"] == tree].sort_values("n")
        x = tdf["lgn"].values
        y_cost = tdf["avg_ops_per_access"].values
        y_ratio = tdf["ratio_ops_ib1"].values

        c = TREE_COLORS.get(tree, "#333333")
        lbl = TREE_LABELS.get(tree, tree)
        m = TREE_MARKERS.get(tree, "o")

        ax1.plot(x, y_cost, label=lbl, color=c, marker=m, linewidth=2, markersize=6)
        ax2.plot(x, y_ratio, label=lbl, color=c, marker=m, linewidth=2, markersize=6)

    ax1.set_title("Uniform Random Workload: Amortized Search Cost (Fig. 4a)", fontsize=13, pad=10)
    ax1.set_xlabel(r"$\log_2 n$", fontsize=12)
    ax1.set_ylabel("Operations / Access", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(frameon=True)

    ax2.set_title("Uniform Random Workload: Competitiveness Ratio (Fig. 4b)", fontsize=13, pad=10)
    ax2.set_xlabel(r"$\log_2 n$", fontsize=12)
    ax2.set_ylabel("Total Operations / Wilber-1 Bound", fontsize=12)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(frameon=True)

    plt.tight_layout()
    plt.savefig(out_dir / "fig4_random_scaling.png")
    plt.close()


def plot_working_set_suite(df: pd.DataFrame, out_dir: Path):
    ws_df = df[df["family"] == "paper_working_set"].copy()
    if ws_df.empty:
        return

    trees = [t for t in ["splay", "multisplay", "tango", "rbtree"] if t in ws_df["tree"].unique()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    for tree in trees:
        tdf = ws_df[ws_df["tree"] == tree].sort_values("k")
        x = tdf["lgk"].values
        y_cost = tdf["avg_ops_per_access"].values
        y_ratio = tdf["ratio_ops_ib1"].values

        c = TREE_COLORS.get(tree, "#333333")
        lbl = TREE_LABELS.get(tree, tree)
        m = TREE_MARKERS.get(tree, "o")

        ax1.plot(x, y_cost, label=lbl, color=c, marker=m, linewidth=2, markersize=6)
        ax2.plot(x, y_ratio, label=lbl, color=c, marker=m, linewidth=2, markersize=6)

    ax1.set_title("Working Set Scaling: Amortized Search Cost (Fig. 5-9a)", fontsize=13, pad=10)
    ax1.set_xlabel(r"$\log_2 k$ (Working Set Size)", fontsize=12)
    ax1.set_ylabel("Operations / Access", fontsize=12)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(frameon=True)

    ax2.set_title("Working Set Scaling: Competitiveness Ratio (Fig. 5-9b)", fontsize=13, pad=10)
    ax2.set_xlabel(r"$\log_2 k$ (Working Set Size)", fontsize=12)
    ax2.set_ylabel("Total Operations / Wilber-1 Bound", fontsize=12)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(frameon=True)

    plt.tight_layout()
    plt.savefig(out_dir / "fig5_working_set_scaling.png")
    plt.close()


def plot_crossover_zoom(df: pd.DataFrame, out_dir: Path):
    seq_df = df[(df["family"] == "sequential") & df["tree"].isin(["splay", "rbtree"])].copy()
    if seq_df.empty:
        return

    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)

    for tree in ["splay", "rbtree"]:
        tdf = seq_df[seq_df["tree"] == tree].sort_values("n")
        ax.plot(tdf["lgn"], tdf["avg_ops_per_access"], label=TREE_LABELS[tree],
                color=TREE_COLORS[tree], marker=TREE_MARKERS[tree], linewidth=2.5, markersize=7)

    ax.axvline(x=18.0, color="#d62728", linestyle=":", alpha=0.8, label="Asymptotic Crossover ($n=262,144$)")

    ax.set_title("Sequential Scan Crossover: Splay vs. Red-Black Tree (Fig. 6)", fontsize=13, pad=10)
    ax.set_xlabel(r"$\log_2(n)$ (Universe Bits)", fontsize=12)
    ax.set_ylabel("Operations / Access", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True, fontsize=11)

    plt.tight_layout()
    plt.savefig(out_dir / "fig6_splay_vs_rbtree_crossover.png")
    plt.close()


def generate_paper_plots(results_dir: Path = Path("data/results/paper_replication"), base_out: Path = Path("data/analysis")):
    if base_out.name in ("paper_replication", "plots"):
        root_out = base_out.parent
    else:
        root_out = base_out
    out_dir = root_out / "plots" / "paper_replication"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not (results_dir / "results_manifest.jsonl").exists() and (Path("data/results") / "results_manifest.jsonl").exists():
        results_dir = Path("data/results")

    df = load_results_manifest(results_dir)
    print(f"Loaded {len(df)} total benchmark manifest entries from {results_dir}.")

    plot_sequential_suite(df, out_dir)
    plot_random_suite(df, out_dir)
    plot_working_set_suite(df, out_dir)
    plot_crossover_zoom(df, out_dir)
    print(f"Publication figures successfully written to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot paper replication comparisons.")
    parser.add_argument("--results", default="data/results/paper_replication", help="Path to results directory")
    parser.add_argument("--out", default="data/analysis", help="Path to analysis output directory")
    args = parser.parse_args()
    generate_paper_plots(Path(args.results), Path(args.out))
