"""Plot publication-grade MIT paper replication figures from benchmark manifest."""
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


def plot_zipfian_suite(df: pd.DataFrame, out_dir: Path):
    zdf = df[df["family"] == "ycsb_zipfian"].copy()
    if zdf.empty:
        return

    def get_theta(tid):
        m = re.search(r"_theta([0-9.]+)", str(tid))
        return float(m.group(1)) if m else np.nan

    zdf["theta"] = zdf["trace_id"].apply(get_theta)

    # Plot A (fig7_zipfian_skew_scaling.png)
    plot_a_df = zdf[zdf["n"] == 131072].copy()
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    for tree in ["splay", "multisplay", "tango", "rbtree"]:
        tdf = plot_a_df[plot_a_df["tree"] == tree].sort_values("theta")
        if tdf.empty:
            continue
        c = TREE_COLORS.get(tree, "#333333")
        lbl = TREE_LABELS.get(tree, tree)
        m = TREE_MARKERS.get(tree, "o")
        ax.plot(tdf["theta"], tdf["avg_ops_per_access"], label=lbl, color=c, marker=m, linewidth=2, markersize=6)

    ax.set_title("Cloud Cache Sensitivity: Search Cost vs. Zipfian Skew (Fig. 7)", fontsize=13, pad=10)
    ax.set_xlabel(r"Zipfian Skew Parameter ($\theta$)", fontsize=12)
    ax.set_ylabel("Operations / Access", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True)

    plt.tight_layout()
    plt.savefig(out_dir / "fig7_zipfian_skew_scaling.png")
    plt.close()

    # Plot B (fig8_zipfian_universe_scaling.png)
    plot_b_df = zdf[(zdf["theta"] > 1.19) & (zdf["theta"] < 1.21)].copy()
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    for tree in ["splay", "multisplay", "tango", "rbtree"]:
        tdf = plot_b_df[plot_b_df["tree"] == tree].sort_values("n")
        if tdf.empty:
            continue
        c = TREE_COLORS.get(tree, "#333333")
        lbl = TREE_LABELS.get(tree, tree)
        m = TREE_MARKERS.get(tree, "o")
        ax.plot(tdf["lgn"], tdf["avg_ops_per_access"], label=lbl, color=c, marker=m, linewidth=2, markersize=6)

    ax.set_title(r"Hyperscale Cache Scaling at Viral Skew ($\theta=1.2$) (Fig. 8)", fontsize=13, pad=10)
    ax.set_xlabel(r"$\log_2(n)$ (Universe Bits)", fontsize=12)
    ax.set_ylabel("Operations / Access", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True)

    plt.tight_layout()
    plt.savefig(out_dir / "fig8_zipfian_universe_scaling.png")
    plt.close()


def plot_superiority_suite(df: pd.DataFrame, out_dir: Path):
    sdf = df[(df["family"] == "ycsb_zipfian") & (df["n"] == 131072)].copy()
    if sdf.empty:
        return

    def get_theta(tid):
        m = re.search(r"_theta([0-9.]+)", str(tid))
        return float(m.group(1)) if m else np.nan

    sdf["theta"] = sdf["trace_id"].apply(get_theta)
    plot_df = sdf[sdf["theta"] >= 0.8].copy()
    if plot_df.empty:
        return

    # Plot A (fig9_zipfian_victory_crossover.png)
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    for tree in ["splay", "multisplay", "tango", "rbtree"]:
        tdf = plot_df[plot_df["tree"] == tree].sort_values("theta")
        if tdf.empty:
            continue
        c = TREE_COLORS.get(tree, "#333333")
        lbl = TREE_LABELS.get(tree, tree)
        m = TREE_MARKERS.get(tree, "o")
        ax.plot(tdf["theta"], tdf["avg_ops_per_access"], label=lbl, color=c, marker=m, linewidth=2, markersize=6)

    ax.set_title("Victorious Frontier: Online BSTs Overtake Static Red-Black Trees (Fig. 9)", fontsize=13, pad=10)
    ax.set_xlabel(r"Zipfian Skew Parameter ($\theta$)", fontsize=12)
    ax.set_ylabel("Operations / Access", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True)

    plt.tight_layout()
    plt.savefig(out_dir / "fig9_zipfian_victory_crossover.png")
    plt.close()

    # Plot B (fig10_relative_speedup_multiplier.png)
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    rb_df = plot_df[plot_df["tree"] == "rbtree"].sort_values("theta")
    if not rb_df.empty:
        rb_ops = rb_df.groupby("theta")["avg_ops_per_access"].mean()
        for tree in ["splay", "multisplay", "tango"]:
            tdf = plot_df[plot_df["tree"] == tree].sort_values("theta")
            if tdf.empty:
                continue
            tree_ops = tdf.groupby("theta")["avg_ops_per_access"].mean()
            common_thetas = sorted(rb_ops.index.intersection(tree_ops.index))
            if not common_thetas:
                continue
            speedup = rb_ops.loc[common_thetas] / tree_ops.loc[common_thetas]

            c = TREE_COLORS.get(tree, "#333333")
            lbl = TREE_LABELS.get(tree, tree)
            m = TREE_MARKERS.get(tree, "o")
            ax.plot(common_thetas, speedup.values, label=lbl, color=c, marker=m, linewidth=2, markersize=6)

    ax.axhline(1.0, color="black", linewidth=2.5, linestyle="-", label="Static Baseline ($1.0\\times$)")
    ax.axhspan(1.0, 10.0, color="#2ecc71", alpha=0.12)
    ax.axhspan(0.0, 1.0, color="#e74c3c", alpha=0.12)
    ax.set_ylim(0, 8.0)
    ax.set_title("Relative Speedup Frontier over Red-Black Baseline (Fig. 10)", fontsize=13, pad=10)
    ax.set_xlabel(r"Zipfian Skew Parameter ($\theta$)", fontsize=12)
    ax.set_ylabel("Speedup Multiplier over Red-Black Tree", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(frameon=True)

    plt.tight_layout()
    plt.savefig(out_dir / "fig10_relative_speedup_multiplier.png")
    plt.close()


def generate_paper_plots():
    out_dir = Path("data/analysis/plots/paper_replication")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_results_manifest()
    print(f"Loaded {len(df)} total benchmark manifest entries.")

    plot_sequential_suite(df, out_dir)
    plot_random_suite(df, out_dir)
    plot_working_set_suite(df, out_dir)
    plot_crossover_zoom(df, out_dir)
    plot_zipfian_suite(df, out_dir)
    plot_superiority_suite(df, out_dir)
    print(f"Publication figures successfully written to {out_dir}")


if __name__ == "__main__":
    generate_paper_plots()
