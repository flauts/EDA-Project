#!/usr/bin/env python3
"""Orchestrator script to run C++ benchmarks in parallel across CPU cores."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess
import sys

from tqdm import tqdm


def _run_single_task(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nStdout: {res.stdout}\nStderr: {res.stderr}")


def main() -> int:
    default_workers = max(1, (os.cpu_count() or 2) - 1)

    parser = argparse.ArgumentParser(description="Run C++ BST benchmarks in parallel.")
    parser.add_argument("--traces", default="data/traces", help="Directory containing traces and manifest.jsonl")
    parser.add_argument("--out", default="data/results", help="Directory to store results")
    parser.add_argument("--trees", default="splay,tango,multisplay,rbtree", help="Comma-separated list of trees to benchmark")
    parser.add_argument("--workers", type=int, default=default_workers, help="Number of worker processes")
    parser.add_argument("--exe", default="build/benchmark.exe", help="Path to benchmark executable")
    parser.add_argument("--compact", action="store_true", help="Pass --compact to benchmark executable (skip CSV output)")

    args = parser.parse_args()

    traces_dir = Path(args.traces)
    manifest_path = traces_dir / "manifest.jsonl"
    if not manifest_path.exists():
        print(f"Error: Traces manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results_manifest_path = out_dir / "results_manifest.jsonl"

    trace_ids: list[str] = []
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            trace_ids.append(data["trace_id"])

    processed_pairs: set[tuple[str, str]] = set()
    if results_manifest_path.exists():
        with results_manifest_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    processed_pairs.add((data["trace_id"], data["tree"]))
                except json.JSONDecodeError:
                    continue

    trees_list = [t.strip() for t in args.trees.split(",") if t.strip()]

    pending_tasks: list[tuple[str, str]] = []
    for tid in trace_ids:
        for tree in trees_list:
            if (tid, tree) not in processed_pairs:
                pending_tasks.append((tid, tree))

    if not pending_tasks:
        print("All benchmark tasks already processed.")
        return 0

    print(f"Submitting {len(pending_tasks)} benchmark tasks across {args.workers} workers...")

    futures = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for task_idx, (tid, tree) in enumerate(pending_tasks):
            cmd = [
                args.exe,
                "--traces", str(traces_dir),
                "--trace", tid,
                "--trees", tree,
                "--out", str(out_dir),
                "--manifest-suffix", f"_{task_idx}",
            ]
            if args.compact:
                cmd.append("--compact")
            futures.append(executor.submit(_run_single_task, cmd))

        for future in tqdm(as_completed(futures), total=len(futures), desc="Benchmarking", unit="task"):
            future.result()

    # Merge temporary manifest files
    temp_files = sorted(out_dir.glob("results_manifest_*.jsonl"))
    if temp_files:
        print(f"Merging {len(temp_files)} temporary manifest files into {results_manifest_path}...")
        with results_manifest_path.open("a", encoding="utf-8", newline="\n") as main_mf:
            for temp_file in temp_files:
                if temp_file.exists():
                    with temp_file.open("r", encoding="utf-8") as tf:
                        content = tf.read()
                        if content:
                            main_mf.write(content)
                            if not content.endswith("\n"):
                                main_mf.write("\n")
                    temp_file.unlink()

    print("Benchmarking complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
