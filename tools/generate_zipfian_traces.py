"""Generate synthetic YCSB Zipfian access traces."""
import json
from pathlib import Path
from tqdm import tqdm

from generate_traces import make_ycsb_zipfian, write_trace


def generate_zipfian_traces(out_dir: Path = Path("data/traces"), seed: int = 2026):
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"

    existing_records = {}
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    existing_records[rec["trace_id"]] = rec

    cases = []

    # Sweep A: theta in [0.0, 0.5, 0.8, 0.99, 1.2, 1.5] on fixed n=131072, m=100000
    n_fixed = 131072
    m_fixed = 100000
    theta_values = [0.0, 0.5, 0.8, 0.99, 1.2, 1.5]
    for theta in theta_values:
        cases.append(make_ycsb_zipfian(n_fixed, theta, seed, m=m_fixed))

    # Sweep B: n in [1024, 4096, 16384, 65536, 262144, 1048576] on fixed theta=1.2, m=100000
    theta_fixed = 1.2
    n_values = [1024, 4096, 16384, 65536, 262144, 1048576]
    for n in n_values:
        cases.append(make_ycsb_zipfian(n, theta_fixed, seed, m=m_fixed))

    new_count = 0
    for case in tqdm(cases, desc="Generating Zipfian Workloads", unit="trace"):
        full_tid = f"ycsb_cloud/{case.trace_id}"
        if full_tid not in existing_records and case.trace_id not in existing_records:
            record = write_trace(case, out_dir, category="ycsb_cloud")
            existing_records[record["trace_id"]] = record
            new_count += 1

    with manifest_path.open("w", encoding="utf-8", newline="\n") as f:
        for tid in sorted(existing_records.keys()):
            f.write(json.dumps(existing_records[tid], sort_keys=True) + "\n")

    print(
        f"Successfully generated {new_count} new YCSB Zipfian traces. "
        f"Total trace manifest entries: {len(existing_records)}"
    )


if __name__ == "__main__":
    generate_zipfian_traces()
