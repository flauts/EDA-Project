"""Convert NASA HTTP CLF logs to BST trace format.

Download gz files from ftp://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz
and ftp://ita.ee.lbl.gov/traces/NASA_access_log_Aug95.gz
"""
import argparse
import gzip
import json
import re
from pathlib import Path

# ponytail: single regex, no parser class, just extract URL path
CLF_RE = re.compile(
    r'^(\S+) (\S+) (\S+) \[([\w:/]+\s[+\-]\d{4})\] '
    r'"(\S+) (\S+)\s*(\S*)\s*" (\d{3}) (\S+)'
)


def _extract_url(line: str) -> str | None:
    m = CLF_RE.match(line)
    if not m:
        return None
    url = m.group(6)
    if url == "-" or url.startswith("http"):
        return None
    return url


def convert(log_path: Path, out_dir: Path, trace_id: str, category: str = "real_world") -> dict:
    """Parse CLF log, map URL paths to integer keys (alphabetically sorted), write trace.txt + trace.json."""
    out_dir.mkdir(parents=True, exist_ok=True)

    url_order: list[str] = []
    unique_urls: set[str] = set()

    opener = gzip.open if log_path.suffix == ".gz" else open
    with opener(log_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            url = _extract_url(line)
            if url is None:
                continue
            url_order.append(url)
            unique_urls.add(url)

    sorted_urls = sorted(unique_urls)
    url_to_key: dict[str, int] = {url: i + 1 for i, url in enumerate(sorted_urls)}
    accesses = [url_to_key[url] for url in url_order]

    n = len(sorted_urls)
    m = len(accesses)

    # Write trace.txt
    out_dir.joinpath("trace.txt").write_text("\n".join(map(str, accesses)) + "\n", encoding="utf-8")

    # Write trace.json metadata
    meta = {
        "trace_id": trace_id,
        "category": category,
        "n": n,
        "m": m,
        "format": "nasa_http_clf",
        "phases": [],
        "notes": "NASA Kennedy Space Center HTTP logs (1995). Phases: diurnal, shuttle launch (mid-July), hurricane Erin shutdown (Aug 1-3).",
    }
    out_dir.joinpath("trace.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"  {trace_id}: {m} accesses, {n} unique keys")
    return meta


def main():
    p = argparse.ArgumentParser(description="Convert NASA CLF logs to BST trace format")
    p.add_argument("--log-dir", type=Path, required=True, help="Directory with NASA_access_log_*.gz files")
    p.add_argument("--out-dir", type=Path, default=Path("data/traces"), help="Output traces directory")
    args = p.parse_args()

    real_world_dir = args.out_dir / "real_world"
    real_world_dir.mkdir(parents=True, exist_ok=True)

    manifestations = [
        ("NASA_access_log_Jul95.gz", "nasa_http_jul95", "July 1995 (shuttle launch)"),
        ("NASA_access_log_Aug95.gz", "nasa_http_aug95", "August 1995 (hurricane Erin)"),
    ]

    entries: list[dict] = []

    # ponytail: read main manifest once outside loop
    main_mf = args.out_dir / "manifest.jsonl"
    existing: dict[str, dict] = {}
    if main_mf.exists():
        for line in main_mf.read_text("utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                existing[r["trace_id"]] = r

    for fname, tid, desc in manifestations:
        log_file = args.log_dir / fname
        if not log_file.exists():
            print(f"  SKIP: {fname} not found in {args.log_dir}")
            continue

        print(f"Converting {fname} ({desc})...")
        meta = convert(log_file, real_world_dir / tid, tid)

        entries.append({
            "trace_id": tid,
            "family": tid,
            "n": meta["n"],
            "m": meta["m"],
            "trace_path": str((real_world_dir / tid / "trace.txt").resolve()),
            "metadata_path": str((real_world_dir / tid / "trace.json").resolve()),
        })

        existing[tid] = {
            "trace_id": tid,
            "family": tid,
            "category": "real_world",
            "n": meta["n"],
            "m": meta["m"],
            "path": str((real_world_dir / tid / "trace.txt").resolve()),
            "metadata_path": str((real_world_dir / tid / "trace.json").resolve()),
        }

    # Write main manifest once after all conversions
    with main_mf.open("w", encoding="utf-8", newline="\n") as f:
        for tid_k in sorted(existing.keys()):
            f.write(json.dumps(existing[tid_k], sort_keys=True) + "\n")

    # Write benchmark manifest inside real_world/ (field names: trace_path not path)
    mf_path = real_world_dir / "manifest.jsonl"
    with mf_path.open("w", encoding="utf-8", newline="\n") as f:
        for e in sorted(entries, key=lambda x: x["trace_id"]):
            f.write(json.dumps(e, sort_keys=True) + "\n")

    print(f"\nDone. Traces written to {real_world_dir}")
    print(f"Next: .\\build\\benchmark.exe --traces data/traces/real_world --out data/results --trees splay,tango,multisplay")


if __name__ == "__main__":
    main()
