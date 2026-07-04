#!/usr/bin/env python3
"""Analyze M3 benchmark results — adaptation cost vs static baseline."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm import tqdm

# -- Constants -----------------------------------------------------------------

STATIC_FAMILIES = {"sequential", "uniform_random", "static_working_set", "spatial_locality"}

PROPERTY_TO_FAMILY = {
    "S": "sequential", "W": "static_working_set",
    "F": "spatial_locality", "R": "uniform_random",
}

_K_RE = re.compile(r"_k(\d+)_")  # extract k from trace_id


# -- CLI -----------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Analyze M3 benchmark results — adaptation cost vs static baseline.")
    p.add_argument("--results", type=Path, default=Path("data/results/state_transitions"),
                   help="M3 results directory (default: data/results/state_transitions)")
    p.add_argument("--out", type=Path, default=Path("data/analysis"),
                   help="Output directory (default: data/analysis)")
    p.add_argument("--traces", type=Path, default=Path("data/traces/state_transitions"),
                   help="M1 traces directory (default: data/traces/state_transitions)")
    return p


# -- I/O -----------------------------------------------------------------------

def _load_manifest(results_dir: Path) -> pd.DataFrame:
    path = results_dir / "results_manifest.jsonl"
    records = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.DataFrame(records)


_csv_cache = {}


def _read_tree_csv(csv_path: Path) -> pd.DataFrame:
    key = str(csv_path)
    if key not in _csv_cache:
        _csv_cache[key] = pd.read_csv(
            csv_path, comment="#",
            dtype={"access_index": "int64", "key": "int64", "phase_id": "int64",
                   "phase_name": "string", "ops": "float64", "cum_ops": "float64"},
            engine="c")
    return _csv_cache[key]


def _load_trace_meta(traces_dir: Path, trace_id: str) -> dict:
    path = traces_dir / trace_id / "trace.json"
    with path.open("r", encoding="utf-8") as fh:
        return dict(json.load(fh))


# -- Helpers -------------------------------------------------------------------

def is_transition_family(family: str) -> bool:
    return family.startswith("transition_")


def parse_transition_properties(family: str) -> list[str]:
    suffix = family[len("transition_"):]
    return suffix.split("_to_")


def extract_k_from_trace_id(trace_id: str) -> int | None:
    m = _K_RE.search(trace_id)
    return int(m.group(1)) if m else None


def _build_static_index(manifest: pd.DataFrame) -> dict:
    idx = {}
    for _, row in manifest.iterrows():
        family = str(row["family"])
        if family not in STATIC_FAMILIES:
            continue
        n = int(row["n"])
        tree = str(row["tree"])
        tid = str(row["trace_id"])
        k = extract_k_from_trace_id(tid) if family == "static_working_set" else None
        key = (family, n, k, tree)
        idx.setdefault(key, []).append((tid, str(row["csv_path"])))
    return idx


def _mean_first_n(csv_path: Path, n_rows: int) -> float | None:
    if not csv_path.exists():
        return None
    df = _read_tree_csv(csv_path)
    n = min(n_rows, len(df))
    return float(df["ops"].iloc[:n].mean()) if n > 0 else None


def _baseline_entry(static_idx: dict, family: str, n: int, k: int | None, tree: str) -> tuple | None:
    entries = static_idx.get((family, n, k, tree),
                             static_idx.get((family, n, None, tree), []))
    return entries[0] if entries else None


def _phase_stats(df: pd.DataFrame, phase_id: int, L: int) -> tuple[float, float]:
    sub = df[df["phase_id"] == phase_id]
    if sub.empty:
        return float("nan"), 0.0
    total = float(sub["ops"].sum())
    mean_l = float(sub.head(L)["ops"].mean())
    return mean_l, total


# -- Grouped-bar helper (reused by cost bars and recovery bars) -----------------

def _draw_grouped_bars_on_ax(ax, pivot: pd.DataFrame, ylabel: str) -> None:
    n_items, n_trees = len(pivot), len(pivot.columns)
    x = np.arange(n_items)
    width = 0.8 / n_trees
    for i, tree in enumerate(pivot.columns):
        ax.bar(x + i * width - 0.4 + width / 2, pivot[tree].values, width, label=tree)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=30, ha="right", fontsize="small")
    ax.set_ylabel(ylabel)
    ax.axhline(y=0, color="gray", linewidth=0.5)
    ax.legend(fontsize="small")


def _plot_grouped_bars(pivot: pd.DataFrame, ylabel: str, title: str,
                       fname: Path) -> None:
    n_items, n_trees = len(pivot), len(pivot.columns)
    if n_items == 0 or n_trees == 0:
        return
    fig, ax = plt.subplots(figsize=(max(6, n_items * 1.2), 4))
    _draw_grouped_bars_on_ax(ax, pivot, ylabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(fname, dpi=150)
    plt.close(fig)


# -- Plots ---------------------------------------------------------------------

def _plot_heatmaps(summary: pd.DataFrame, plots_dir: Path) -> None:
    for n in sorted(summary["n"].unique()):
        for tree in sorted(summary["tree"].unique()):
            data = summary[(summary["n"] == n) & (summary["tree"] == tree)]
            if data.empty:
                continue
            valid = data.dropna(subset=["p1", "p2", "adaptation_cost_p2"])
            if valid.empty:
                continue
            pivot = valid.pivot_table(index="p1", columns="p2",
                                      values="adaptation_cost_p2", aggfunc="first")
            if pivot.empty:
                continue
            fig, ax = plt.subplots(figsize=(5, 4))
            vals = pivot.values
            cmap = plt.get_cmap("RdBu_r").copy()
            cmap.set_bad(color='lightgray')
            im = ax.imshow(vals, cmap=cmap, aspect="auto")
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
            ax.set_title(f"Adaptation cost (n={n}, {tree})")
            plt.colorbar(im, ax=ax, label="cost")
            vmax = np.nanmax(np.abs(vals)) if not np.isnan(vals).all() else 1
            for i in range(len(pivot.index)):
                for j in range(len(pivot.columns)):
                    v = vals[i, j]
                    if not np.isnan(v):
                        ax.text(j, i, f"{v:.2g}", ha="center", va="center",
                                fontsize=8, color="white" if abs(v) > 0.5 * vmax else "black")
                    else:
                        ax.text(j, i, "N/A", ha="center", va="center",
                                fontsize=8, color="dimgray", fontstyle="italic")
            fig.tight_layout()
            fig.savefig(plots_dir / f"adaptation_cost_heatmap_{n}_{tree}.png", dpi=150)
            plt.close(fig)


def _plot_cost_bars(summary: pd.DataFrame, plots_dir: Path) -> None:
    for n in sorted(summary["n"].unique()):
        data = summary[summary["n"] == n].copy()
        if data.empty:
            continue
        data["pair"] = data["p1"] + "\u2192" + data["p2"]
        grouped = data.groupby(["pair", "tree"], as_index=False)["adaptation_cost_p2"].mean()
        pivot = grouped.pivot(index="pair", columns="tree", values="adaptation_cost_p2").sort_index()
        _plot_grouped_bars(pivot, "Adaptation cost",
                           f"Adaptation cost by transition pair (n={n})",
                           plots_dir / f"adaptation_cost_bars_{n}.png")


def _plot_triple_cost_bars(summary: pd.DataFrame, plots_dir: Path) -> None:
    triples = summary[summary["transition_type"] == "triple"].copy()
    if triples.empty:
        return
    triples["triple_label"] = triples["p1"] + "\u2192" + triples["p2"] + "\u2192" + triples["p3"]

    ret = triples[triples["p1"] == triples["p3"]]
    chain = triples[triples["p1"] != triples["p3"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=150)

    if not ret.empty:
        g_ret = ret.groupby(["triple_label", "tree"], as_index=False)["recovery_cost"].mean()
        p_ret = g_ret.pivot(index="triple_label", columns="tree", values="recovery_cost").sort_index()
        _draw_grouped_bars_on_ax(ax1, p_ret, "Recovery cost")
        ax1.set_title("(a) Return triples ($A \\to B \\to A$)", fontsize=12)

    if not chain.empty:
        g_chain = chain.groupby(["triple_label", "tree"], as_index=False)["recovery_cost"].mean()
        p_chain = g_chain.pivot(index="triple_label", columns="tree", values="recovery_cost").sort_index()
        _draw_grouped_bars_on_ax(ax2, p_chain, "Net accumulated cost")
        ax2.set_title("(b) Chain triples ($A \\to B \\to C$)", fontsize=12)

    fig.tight_layout()
    fig.savefig(plots_dir / "triple_cost_bars.png", dpi=150)
    plt.close(fig)


def _plot_cost_curves(summary: pd.DataFrame, results_dir: Path,
                      traces_dir: Path, plots_dir: Path) -> None:
    families = sorted(summary["family"].unique())[:4]
    for family in families:
        fam_data = summary[summary["family"] == family]
        tids = sorted(fam_data["trace_id"].unique())
        if not tids:
            continue
        tid = tids[0]
        try:
            meta = _load_trace_meta(traces_dir, tid)
        except FileNotFoundError:
            continue
        boundaries = [p["start"] for p in meta.get("phases", [])]
        n_val = int(fam_data["n"].iloc[0])

        fig, ax = plt.subplots(figsize=(10, 5))
        for tree in sorted(fam_data[fam_data["trace_id"] == tid]["tree"].unique()):
            csv_path = results_dir / f"{tid}/{tree}.csv"
            if csv_path.exists():
                df = _read_tree_csv(csv_path)
                ax.plot(df["access_index"], df["ops"], label=tree, linewidth=0.7)
        for b in boundaries:
            ax.axvline(x=b, color="gray", linestyle="--", linewidth=0.5)
        ax.set_xlabel("Access index")
        ax.set_ylabel("Ops per access")
        ax.set_title(f"{family} (n={n_val})")
        ax.legend(fontsize="small")
        fig.tight_layout()
        fig.savefig(plots_dir / f"cost_curve_{family}_n{n_val}.png", dpi=150)
        plt.close(fig)


def _write_readme(out_dir: Path) -> None:
    out_dir.joinpath("README.md").write_text(
        "# Analysis output\n\n"
        "Regenerate with:\n"
        "    python tools/analyze.py --results data/results --out data/analysis\n\n"
        "Requires: pandas, matplotlib, numpy\n"
        "    pip install pandas matplotlib numpy\n",
        encoding="utf-8")


# -- Main ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results_dir = Path(args.results)
    out_dir = Path(args.out)
    traces_dir = Path(args.traces)

    if out_dir.name in ("state_transitions", "plots"):
        root_out_dir = out_dir.parent
    else:
        root_out_dir = out_dir
    root_out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = root_out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = results_dir / "results_manifest.jsonl"
    if not manifest_path.exists():
        print(f"Results manifest not found at {manifest_path}")
        _write_readme(out_dir)
        return 0

    manifest = _load_manifest(results_dir)
    if manifest.empty:
        print("No results found.")
        _write_readme(out_dir)
        return 0

    required = {"trace_id", "family", "n", "tree", "csv_path"}
    missing = required - set(manifest.columns)
    if missing:
        print(f"Manifest missing required columns: {missing}")
        return 1

    static_idx = _build_static_index(manifest)
    print(f"  Indexed {sum(len(v) for v in static_idx.values())} static baseline entries")

    trans_mask = manifest["family"].apply(lambda f: is_transition_family(str(f)))
    trans_manifest = manifest[trans_mask]
    if trans_manifest.empty:
        print("No transition-family results found — nothing to analyse.")
        _write_readme(out_dir)
        return 0

    print(f"  Found {len(trans_manifest)} transition result rows")

    rows: list[dict] = []
    unique_tids = sorted(trans_manifest["trace_id"].unique())
    for tid in tqdm(unique_tids, desc="Analyzing Traces", unit="trace"):
        try:
            meta = _load_trace_meta(traces_dir, tid)
        except FileNotFoundError:
            tqdm.write(f"  [skip] trace.json not found for {tid}")
            continue

        family = str(meta.get("family", ""))
        if not is_transition_family(family):
            continue

        props = parse_transition_properties(family)

        if len(props) not in (2, 3):
            continue

        p1, p2 = props[0], props[1]
        p3 = props[2] if len(props) == 3 else ""
        transition_type = "triple" if p3 else "pair"
        n_val = int(meta.get("n", 0))
        k_val = int(meta.get("parameters", {}).get("k", 0))
        phase_length = int(meta.get("parameters", {}).get("phase_length", 0))

        if phase_length <= 0:
            tqdm.write(f"  [skip] {tid}: invalid phase_length={phase_length}")
            continue

        p2_family = PROPERTY_TO_FAMILY.get(p2)
        p1_family = PROPERTY_TO_FAMILY.get(p1)
        if p2_family is None:
            tqdm.write(f"  [skip] {tid}: unknown property label '{p2}'")
            continue

        p2_k = k_val if p2_family == "static_working_set" else None
        p1_k = k_val if p1_family == "static_working_set" else None

        for _, rec in trans_manifest[trans_manifest["trace_id"] == tid].iterrows():
            tree = str(rec["tree"])
            csv_path = results_dir / Path(str(rec["csv_path"]))
            if not csv_path.exists():
                tqdm.write(f"  [skip] CSV not found: {csv_path}")
                continue

            df = _read_tree_csv(csv_path)
            phase_order = df[["phase_id"]].drop_duplicates()["phase_id"].values
            if len(phase_order) < 2:
                continue

            mean_mut, total_p2 = _phase_stats(df, phase_order[1], phase_length)
            mean_p1_t, total_p1 = _phase_stats(df, phase_order[0], phase_length)

            recovery_cost: float | str = ""
            total_p3: float | str = ""
            if p3 and len(phase_order) > 2:
                mean_p3_t, total_p3 = _phase_stats(df, phase_order[2], phase_length)
                recovery_cost = mean_p3_t - mean_p1_t

            p2_entry = _baseline_entry(static_idx, p2_family, n_val, p2_k, tree)
            if not p2_entry:
                tqdm.write(f"  [skip] {tid}/{tree}: no static baseline for p2={p2}")
                continue

            static_mean_p2 = _mean_first_n(results_dir / p2_entry[1], phase_length)
            if static_mean_p2 is None:
                continue

            adaptation_cost_p2 = mean_mut - static_mean_p2

            static_mean_p1: float | str = ""
            if p1_family:
                p1_entry = _baseline_entry(static_idx, p1_family, n_val, p1_k, tree)
                if p1_entry:
                    sm = _mean_first_n(results_dir / p1_entry[1], phase_length)
                    static_mean_p1 = sm if sm is not None else ""

            rows.append({
                "family": family, "n": n_val, "k": k_val, "tree": tree,
                "trace_id": tid, "transition_type": transition_type,
                "p1": p1, "p2": p2, "p3": p3, "phase_length": phase_length,
                "adaptation_cost_p2": adaptation_cost_p2,
                "recovery_cost": recovery_cost,
                "ops_total_p1": int(total_p1), "ops_total_p2": int(total_p2),
                "ops_total_p3": int(total_p3) if isinstance(total_p3, float) and not np.isnan(total_p3) else "",
                "static_baseline_p2": static_mean_p2,
                "static_baseline_p1": static_mean_p1,
            })

    if not rows:
        print("No data rows produced.")
        _write_readme(root_out_dir)
        return 1

    summary = pd.DataFrame(rows)
    csv_out = root_out_dir / "summary_state_transitions.csv"
    summary.to_csv(csv_out, index=False, float_format="%.6g")
    print(f"Wrote {len(summary)} rows to {csv_out}")

    print("Generating plots …")
    trans_plots_dir = plots_dir / "state_transitions"
    trans_plots_dir.mkdir(parents=True, exist_ok=True)
    _plot_heatmaps(summary, trans_plots_dir)
    _plot_cost_bars(summary, trans_plots_dir)
    _plot_triple_cost_bars(summary, trans_plots_dir)
    _plot_cost_curves(summary, results_dir, traces_dir, trans_plots_dir)
    print(f"Plots written to {plots_dir}")

    _write_readme(root_out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
