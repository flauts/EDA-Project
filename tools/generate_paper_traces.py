"""Generate clean asymptotic complexity traces matching MIT reference paper."""
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm

from generate_traces import (
    write_trace,
    make_sequential,
    make_uniform_random,
    make_static_working_set,
)


def generate_paper_traces(out_dir: Path = Path("data/traces"), seed: int = 2026):
    paper_dir = out_dir / "paper_replication"
    paper_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = paper_dir / "manifest.jsonl"

    existing_records = {}
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    existing_records[rec["trace_id"]] = rec

    cases = []

    # Suite B1: Asymptotic scaling sweeps (n = 2^10 to 2^17)
    n_values = [2**i for i in range(10, 18)]  # 1,024 to 131,072
    for n in n_values:
        cases.append(make_sequential(n, seed, passes=25))
        cases.append(make_uniform_random(n, seed, length_factor=25))

    # Extended Sequential Scaling sweeps (n = 2^18 to 2^20) to demonstrate RBTree crossover (<70MB disk)
    n_extended = [2**i for i in range(18, 21)]  # 262,144 to 1,048,576
    for n in n_extended:
        cases.append(make_sequential(n, seed, passes=5))

    # Suite B2: Working Set scaling sweeps (k = 2^0 to 2^16 on n = 131072)
    n_fixed = 131072
    k_values = [2**i for i in range(0, 17)]  # 1 to 65,536
    for k in k_values:
        cases.append(
            make_static_working_set(
                n_fixed, k, seed, paper_protocol=True, passes=20
            )
        )

    new_count = 0
    pending_cases = [c for c in cases if c.trace_id not in existing_records]
    with ProcessPoolExecutor() as pool:
        futures = [pool.submit(write_trace, case, paper_dir) for case in pending_cases]
        for f in tqdm(as_completed(futures), total=len(futures), desc="Writing Paper Workloads", unit="trace"):
            record = f.result()
            existing_records[record["trace_id"]] = record
            new_count += 1

    with manifest_path.open("w", encoding="utf-8", newline="\n") as f:
        for tid in sorted(existing_records.keys()):
            f.write(json.dumps(existing_records[tid], sort_keys=True) + "\n")

    print(
        f"Successfully generated {new_count} new asymptotic traces. "
        f"Total trace manifest entries: {len(existing_records)}"
    )


if __name__ == "__main__":
    generate_paper_traces()
