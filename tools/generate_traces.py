#!/usr/bin/env python3
"""Generate reproducible BST access traces for non-stationary workloads.

Each emitted trace uses the static key universe {1, ..., n}. Trace files contain
one 1-indexed key per line, and metadata records the parameters and phase
boundaries needed by later benchmark and analysis modules.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from tqdm import tqdm


DEFAULT_FULL_N = (1023, 8191, 32767)
DEFAULT_FULL_K = (8, 64)
DEFAULT_QUICK_N = (31, 127)
DEFAULT_QUICK_K = (2, 4, 8)
DEFAULT_SEED_COUNT = 2
DEFAULT_LENGTH_FACTOR = 25
DEFAULT_PHASE_FACTOR = 5


@dataclass(frozen=True)
class Phase:
    name: str
    start: int
    end: int
    parameters: dict

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "length": self.end - self.start,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class TraceCase:
    trace_id: str
    family: str
    n: int
    seed: int
    accesses: tuple[int, ...]
    parameters: dict
    phases: tuple[Phase, ...]

    @property
    def m(self) -> int:
        return len(self.accesses)

    def metadata(self, trace_path: str = "trace.txt") -> dict:
        return {
            "trace_id": self.trace_id,
            "family": self.family,
            "n": self.n,
            "m": self.m,
            "seed": self.seed,
            "key_universe": {"min": 1, "max": self.n},
            "access_indexing": "0-based positions, 1-indexed keys",
            "trace_path": trace_path,
            "parameters": self.parameters,
            "phases": [phase.to_json() for phase in self.phases],
        }


def _phase(name: str, start: int, accesses: Sequence[int], parameters: dict) -> Phase:
    return Phase(name=name, start=start, end=start + len(accesses), parameters=parameters)


def _trace_id(family: str, n: int, seed: int, **parts: object) -> str:
    tokens = [family, f"n{n}", f"seed{seed}"]
    for key in sorted(parts):
        value = parts[key]
        if value is not None:
            tokens.append(f"{key}{value}")
    return "_".join(str(token).replace(" ", "-") for token in tokens)


def _bounded_k(n: int, k: int) -> int:
    if k < 1:
        raise ValueError(f"k must be positive, got {k}")
    return min(k, n)


def _length(n: int, factor: int = DEFAULT_LENGTH_FACTOR) -> int:
    return n * factor


def _sample_active_set(rng: random.Random, n: int, k: int) -> tuple[int, ...]:
    k = _bounded_k(n, k)
    return tuple(sorted(rng.sample(range(1, n + 1), k)))


def _sample_from_keys(rng: random.Random, keys: Sequence[int], length: int) -> tuple[int, ...]:
    return tuple(rng.choice(keys) for _ in range(length))


def _sequential_segment(n: int, length: int) -> tuple[int, ...]:
    return tuple((i % n) + 1 for i in range(length))


def _uniform_segment(rng: random.Random, n: int, length: int) -> tuple[int, ...]:
    return tuple(rng.randint(1, n) for _ in range(length))


def _spatial_segment(
    rng: random.Random,
    n: int,
    length: int,
    radius: int,
    local_probability: float,
    start_key: int | None = None,
) -> tuple[int, ...]:
    radius = max(1, min(radius, n))
    current = start_key if start_key is not None else rng.randint(1, n)
    accesses: list[int] = []

    for _ in range(length):
        if rng.random() < local_probability:
            lo = max(1, current - radius)
            hi = min(n, current + radius)
            current = rng.randint(lo, hi)
        else:
            current = rng.randint(1, n)
        accesses.append(current)

    return tuple(accesses)


def _working_set_phase(rng: random.Random, n: int, k: int, length: int) -> tuple[int, ...]:
    """W property: access k random keys repeatedly (temporal locality)"""
    k = _bounded_k(n, k)
    active_set = _sample_active_set(rng, n, k)
    return _sample_from_keys(rng, active_set, length)


def _finger_phase(
    rng: random.Random, n: int, k: int, length: int,
    local_probability: float = 0.85, start_key: int | None = None,
) -> tuple[int, ...]:
    """F property: random walk with radius k (spatial locality / dynamic finger)"""
    return _spatial_segment(rng, n, length, radius=k, local_probability=local_probability, start_key=start_key)


def _random_phase(rng: random.Random, n: int, length: int) -> tuple[int, ...]:
    """R property: uniform random (no locality)"""
    return _uniform_segment(rng, n, length)


def make_sequential(n: int, seed: int, passes: int = DEFAULT_LENGTH_FACTOR) -> TraceCase:
    accesses = tuple(key for _ in range(passes) for key in range(1, n + 1))
    phases = (_phase("sequential", 0, accesses, {"passes": passes}),)
    return TraceCase(
        trace_id=_trace_id("sequential", n, seed, passes=passes),
        family="sequential",
        n=n,
        seed=seed,
        accesses=accesses,
        parameters={"passes": passes},
        phases=phases,
    )


def make_uniform_random(
    n: int, seed: int, length_factor: int = DEFAULT_LENGTH_FACTOR
) -> TraceCase:
    rng = random.Random(seed)
    accesses = _uniform_segment(rng, n, _length(n, length_factor))
    phases = (_phase("uniform_random", 0, accesses, {"length_factor": length_factor}),)
    return TraceCase(
        trace_id=_trace_id("uniform_random", n, seed, lf=length_factor),
        family="uniform_random",
        n=n,
        seed=seed,
        accesses=accesses,
        parameters={"length_factor": length_factor},
        phases=phases,
    )


def make_static_working_set(
    n: int, k: int, seed: int, length_factor: int = DEFAULT_LENGTH_FACTOR,
    *, paper_protocol: bool = False, passes: int = 100
) -> TraceCase:

    if paper_protocol:
        rng = random.Random(seed)
        k = _bounded_k(n, k)
        v = list(range(1, n + 1))
        rng.shuffle(v)
        acc: list[int] = []
        for startingI in range(0, n, k):
            for _pass_i in range(passes):
                for shiftI in range(min(k, n - startingI)):
                    acc.append(v[startingI + shiftI])
        accesses_tuple = tuple(acc)
        phase_params = {"k": k, "passes": passes, "protocol": "paper"}
        phases = (_phase("paper_working_set", 0, accesses_tuple, phase_params),)
        return TraceCase(
            trace_id=_trace_id("paper_working_set", n, seed, k=k, passes=passes),
            family="paper_working_set",
            n=n,
            seed=seed,
            accesses=accesses_tuple,
            parameters={"k": k, "passes": passes, "protocol": "paper"},
            phases=phases,
        )
    rng = random.Random(seed)
    k = _bounded_k(n, k)
    active_set = _sample_active_set(rng, n, k)
    accesses = _sample_from_keys(rng, active_set, _length(n, length_factor))
    phase_params = {"k": k, "active_set": list(active_set), "length_factor": length_factor}
    phases = (_phase("static_working_set", 0, accesses, phase_params),)
    return TraceCase(
        trace_id=_trace_id("static_working_set", n, seed, k=k, lf=length_factor),
        family="static_working_set",
        n=n,
        seed=seed,
        accesses=accesses,
        parameters={"k": k, "length_factor": length_factor},
        phases=phases,
    )


def make_spatial_locality(
    n: int,
    k: int,
    seed: int,
    length_factor: int = DEFAULT_LENGTH_FACTOR,
    local_probability: float = 0.85,
) -> TraceCase:
    rng = random.Random(seed)
    radius = _bounded_k(n, k)
    accesses = _spatial_segment(
        rng,
        n,
        _length(n, length_factor),
        radius=radius,
        local_probability=local_probability,
    )
    phase_params = {
        "radius": radius,
        "local_probability": local_probability,
        "length_factor": length_factor,
    }
    phases = (_phase("spatial_locality", 0, accesses, phase_params),)
    return TraceCase(
        trace_id=_trace_id("spatial_locality", n, seed, radius=radius, lf=length_factor),
        family="spatial_locality",
        n=n,
        seed=seed,
        accesses=accesses,
        parameters=phase_params,
        phases=phases,
    )








def make_unified(n: int, k: int, seed: int, passes: int = 100) -> TraceCase:

    if n < 2 * k:
        raise ValueError(f"n ({n}) must be at least 2*k ({2 * k}) for unified trace")
    rng = random.Random(seed)
    v = list(range(1, n + 1))
    rng.shuffle(v)
    finger = rng.randint(1, n)
    accesses: list[int] = []
    for startingI in range(0, n, k):
        for _pass_i in range(passes):
            for shiftI in range(min(k, n - startingI)):
                accesses.append(v[startingI + shiftI])
                finger = ((finger - 1 + rng.randint(1, k)) % n) + 1
                accesses.append(finger)
    accesses_tuple = tuple(accesses)
    phases = (_phase("unified", 0, accesses_tuple, {"k": k, "passes": passes, "protocol": "unified_hybrid"}),)
    return TraceCase(
        trace_id=_trace_id("unified", n, seed, k=k, passes=passes),
        family="unified",
        n=n,
        seed=seed,
        accesses=accesses_tuple,
        parameters={"k": k, "passes": passes},
        phases=phases,
    )


def _combine_segments(
    segments: Sequence[tuple[str, tuple[int, ...], dict]]
) -> tuple[tuple[int, ...], tuple[Phase, ...]]:
    accesses: list[int] = []
    phases: list[Phase] = []

    for name, segment, parameters in segments:
        start = len(accesses)
        accesses.extend(segment)
        phases.append(_phase(name, start, segment, parameters))

    return tuple(accesses), tuple(phases)




# 8 directed pairs of {S, W, F, R}
TRANSITION_PAIRS: tuple[tuple[str, str], ...] = (
    ("S", "W"), ("S", "F"),
    ("W", "S"), ("W", "F"), ("W", "R"),
    ("F", "S"), ("F", "W"),
    ("R", "W"),
)

# 12 triples: 6 return (A->B->A) + 6 chain permutations (A->B->C)
RETURN_TRIPLES: tuple[tuple[str, str, str], ...] = (
    # 6 return triples -- measure structural memory (R excluded: it erases all structure)
    ("S", "W", "S"), ("S", "F", "S"), ("W", "S", "W"), ("W", "F", "W"),
    ("F", "S", "F"), ("F", "W", "F"),
)

CHAIN_TRIPLES: tuple[tuple[str, str, str], ...] = (
    # 6 chain triples -- all permutations of {S, W, F} measuring lingering effects
    ("S", "W", "F"), ("S", "F", "W"),
    ("W", "S", "F"), ("W", "F", "S"),
    ("F", "S", "W"), ("F", "W", "S"),
)

TRANSITION_TRIPLES: tuple[tuple[str, str, str], ...] = RETURN_TRIPLES + CHAIN_TRIPLES


def make_transition(n: int, k: int, seed: int, properties: tuple[str, ...],
                    phase_length: int) -> TraceCase:
    """Generate a transition trace with the given sequence of property phases.

    properties: tuple of single-char labels from {"S", "W", "F", "R"}
    phase_length: number of accesses per phase
    """
    rng = random.Random(seed)
    k = _bounded_k(n, k)
    segments: list[tuple[str, tuple[int, ...], dict]] = []

    for i, prop in enumerate(properties):
        if prop == "S":
            seg = _sequential_segment(n, phase_length)
            params = {"property": "S", "pattern": "sequential"}
        elif prop == "W":
            seg = _working_set_phase(rng, n, k, phase_length)
            params = {"property": "W", "pattern": "working_set", "k": k}
        elif prop == "F":
            seg = _finger_phase(rng, n, k, phase_length)
            params = {"property": "F", "pattern": "finger", "radius": k, "local_probability": 0.85}
        elif prop == "R":
            seg = _random_phase(rng, n, phase_length)
            params = {"property": "R", "pattern": "uniform_random"}
        else:
            raise ValueError(f"Unknown property: {prop}")
        segments.append((f"phase{i}_{prop}", seg, params))

    accesses, phases = _combine_segments(segments)
    transition_name = "_to_".join(properties)
    return TraceCase(
        trace_id=_trace_id(f"transition_{transition_name}", n, seed, k=k, pl=phase_length),
        family=f"transition_{transition_name}",
        n=n,
        seed=seed,
        accesses=accesses,
        parameters={"k": k, "phase_length": phase_length, "properties": list(properties)},
        phases=phases,
    )


def validate_trace(case: TraceCase) -> None:
    if case.n < 1:
        raise ValueError(f"{case.trace_id}: n must be positive")
    if not case.accesses:
        raise ValueError(f"{case.trace_id}: trace must not be empty")
    invalid = [key for key in case.accesses if key < 1 or key > case.n]
    if invalid:
        raise ValueError(f"{case.trace_id}: access key outside [1, {case.n}]: {invalid[0]}")

    cursor = 0
    for phase in case.phases:
        if phase.start != cursor:
            raise ValueError(f"{case.trace_id}: non-contiguous phase start at {phase.name}")
        if phase.end <= phase.start:
            raise ValueError(f"{case.trace_id}: empty phase {phase.name}")
        cursor = phase.end

    if cursor != case.m:
        raise ValueError(f"{case.trace_id}: phases end at {cursor}, trace length is {case.m}")


def iter_suite(
    suite: str,
    seed: int,
    *,
    n_values: Sequence[int] | None = None,
    k_values: Sequence[int] | None = None,
    length_factor: int = DEFAULT_LENGTH_FACTOR,
    phase_factor: int = DEFAULT_PHASE_FACTOR,
    paper_protocol: bool = False,
    phase_length: int | None = None,
) -> Iterator[TraceCase]:
    if suite not in {"quick", "full"}:
        raise ValueError("suite must be 'quick' or 'full'")

    if n_values is None:
        n_values = DEFAULT_QUICK_N if suite == "quick" else DEFAULT_FULL_N
    if k_values is None:
        k_values = DEFAULT_QUICK_K if suite == "quick" else DEFAULT_FULL_K

    seed_count = 1 if suite == "quick" else DEFAULT_SEED_COUNT
    seeds = tuple(seed + i for i in range(seed_count))

    for n in n_values:
        if n < 1:
            raise ValueError(f"n values must be positive, got {n}")
        pl = phase_length if phase_length is not None else n * phase_factor

        yield make_sequential(n, seed, passes=length_factor)

        for run_seed in seeds:
            yield make_uniform_random(n, run_seed, length_factor=length_factor)

            for k in k_values:
                if k > n:
                    continue
                if paper_protocol:
                    yield make_static_working_set(n, k, run_seed, paper_protocol=True, passes=100)
                else:
                    yield make_static_working_set(n, k, run_seed, length_factor=length_factor)
                yield make_spatial_locality(n, k, run_seed, length_factor=length_factor)
                for pair in TRANSITION_PAIRS:
                    yield make_transition(n, k, run_seed, pair, phase_length=pl)
                for triple in TRANSITION_TRIPLES:
                    yield make_transition(n, k, run_seed, triple, phase_length=pl)



def write_trace(case: TraceCase, out_dir: Path) -> dict:
    validate_trace(case)
    trace_dir = out_dir / case.trace_id
    trace_dir.mkdir(parents=True, exist_ok=True)

    trace_path = trace_dir / "trace.txt"
    metadata_path = trace_dir / "trace.json"

    with trace_path.open("w", encoding="utf-8", newline="\n") as handle:
        for key in case.accesses:
            handle.write(f"{key}\n")

    metadata = case.metadata(trace_path="trace.txt")
    with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return {
        "trace_id": case.trace_id,
        "family": case.family,
        "n": case.n,
        "m": case.m,
        "seed": case.seed,
        "parameters": case.parameters,
        "phase_count": len(case.phases),
        "trace_path": str(trace_path.relative_to(out_dir).as_posix()),
        "metadata_path": str(metadata_path.relative_to(out_dir).as_posix()),
    }


def write_suite(
    suite: str,
    out_dir: Path,
    seed: int,
    *,
    n_values: Sequence[int] | None = None,
    k_values: Sequence[int] | None = None,
    length_factor: int = DEFAULT_LENGTH_FACTOR,
    phase_factor: int = DEFAULT_PHASE_FACTOR,
    paper_protocol: bool = False,
    phase_length: int | None = None,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.jsonl"
    count = 0

    actual_n = n_values if n_values is not None else (DEFAULT_QUICK_N if suite == "quick" else DEFAULT_FULL_N)
    actual_k = k_values if k_values is not None else (DEFAULT_QUICK_K if suite == "quick" else DEFAULT_FULL_K)
    seed_count = 1 if suite == "quick" else DEFAULT_SEED_COUNT
    num_transitions = len(TRANSITION_PAIRS) + len(TRANSITION_TRIPLES)
    total_traces = len(actual_n) * (1 + seed_count * (1 + len(actual_k) * (2 + num_transitions)))

    with manifest_path.open("w", encoding="utf-8", newline="\n") as manifest:
        iterator = iter_suite(
            suite, seed, n_values=n_values, k_values=k_values,
            length_factor=length_factor, phase_factor=phase_factor,
            paper_protocol=paper_protocol, phase_length=phase_length
        )
        for case in tqdm(iterator, total=total_traces, desc="Generating Traces", unit="trace"):
            record = write_trace(case, out_dir)
            manifest.write(json.dumps(record, sort_keys=True) + "\n")
            count += 1

    return count


def _parse_int_list(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not parsed:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate reproducible BST access traces for static and dynamic workloads."
    )
    parser.add_argument("--suite", choices=("quick", "full"), default="quick")
    parser.add_argument("--out", type=Path, default=Path("data/traces"))
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--n-values", type=_parse_int_list, default=None)
    parser.add_argument("--k-values", type=_parse_int_list, default=None)
    parser.add_argument("--length-factor", type=int, default=DEFAULT_LENGTH_FACTOR)
    parser.add_argument("--phase-factor", type=int, default=DEFAULT_PHASE_FACTOR)
    parser.add_argument("--paper-protocol", action="store_true",
                        help="Use paper's working-set protocol (all n/k disjoint sets, passes=100)")
    parser.add_argument("--phase-length", type=int, default=None,
                        help="Phase length for transition traces (default: n * phase_factor).")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    count = write_suite(
        args.suite,
        args.out,
        args.seed,
        n_values=args.n_values,
        k_values=args.k_values,
        length_factor=args.length_factor,
        phase_factor=args.phase_factor,
        paper_protocol=args.paper_protocol,
        phase_length=args.phase_length,
    )
    print(f"Wrote {count} traces to {args.out}")
    print(f"Manifest: {args.out / 'manifest.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
