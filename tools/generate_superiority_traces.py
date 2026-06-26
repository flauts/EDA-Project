"""Generate superiority frontier synthetic access traces."""
import json
from pathlib import Path
from tqdm import tqdm

from generate_traces import make_ycsb_zipfian, make_working_set, write_trace


def generate_superiority_traces(out_dir: Path = Path("data/traces"), seed: int = 2026):
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

    # Sweep 1: theta in [1.6, 1.8, 2.0, 2.2, 2.5] on n=131072, m=100000 (using make_ycsb_zipfian)
    n_fixed = 131072
    m_fixed = 100000
    theta_values = [1.6, 1.8, 2.0, 2.2, 2.5]
    for theta in theta_values:
        cases.append(make_ycsb_zipfian(n_fixed, theta, seed, m=m_fixed))

    # Sweep 2: k in [1, 2, 4, 8, 16, 32, 64, 128] on n=131072, m=100000 (using make_working_set)
    k_values = [1, 2, 4, 8, 16, 32, 64, 128]
    for k in k_values:
        cases.append(make_working_set(n_fixed, k, seed, m=m_fixed))

    new_count = 0
    for case in tqdm(cases, desc="Generating Superiority Traces", unit="trace"):
        if case.trace_id not in existing_records:
            record = write_trace(case, out_dir)
            record["category"] = "superiority_frontier"
            existing_records[case.trace_id] = record
            new_count += 1
        else:
            existing_records[case.trace_id]["category"] = "superiority_frontier"

    with manifest_path.open("w", encoding="utf-8", newline="\n") as f:
        for tid in sorted(existing_records.keys()):
            f.write(json.dumps(existing_records[tid], sort_keys=True) + "\n")

    print(
        f"Successfully generated {new_count} new superiority traces. "
        f"Total trace manifest entries: {len(existing_records)}"
    )


if __name__ == "__main__":
    generate_superiority_traces()
