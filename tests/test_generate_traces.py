import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import generate_traces as traces  # noqa: E402


class TraceGeneratorTests(unittest.TestCase):
    def assert_valid(self, case: traces.TraceCase) -> None:
        traces.validate_trace(case)
        self.assertTrue(all(1 <= key <= case.n for key in case.accesses))
        self.assertEqual(case.phases[0].start, 0)
        self.assertEqual(case.phases[-1].end, case.m)

    def test_determinism_for_same_seed_and_parameters(self) -> None:
        a = traces.make_transition(n=127, k=8, seed=2026, properties=("S", "W"), phase_length=64)
        b = traces.make_transition(n=127, k=8, seed=2026, properties=("S", "W"), phase_length=64)
        c = traces.make_transition(n=127, k=8, seed=2027, properties=("S", "W"), phase_length=64)

        self.assertEqual(a.accesses, b.accesses)
        self.assertEqual(a.metadata(), b.metadata())
        self.assertNotEqual(a.accesses, c.accesses)

    def test_sequential_trace_cycles_through_keys(self) -> None:
        case = traces.make_sequential(n=5, seed=2026, passes=3)
        self.assert_valid(case)
        self.assertEqual(case.accesses, tuple([1, 2, 3, 4, 5] * 3))

    def test_uniform_random_is_approximately_distributed(self) -> None:
        case = traces.make_uniform_random(n=7, seed=2026, length_factor=1000)
        self.assert_valid(case)
        counts = {key: case.accesses.count(key) for key in range(1, case.n + 1)}
        expected = case.m / case.n

        self.assertTrue(all(count > 0 for count in counts.values()))
        self.assertLess(max(abs(count - expected) for count in counts.values()), expected * 0.12)

    def test_static_working_set_uses_only_active_set(self) -> None:
        case = traces.make_static_working_set(n=127, k=8, seed=2026)
        self.assert_valid(case)
        active_set = set(case.phases[0].parameters["active_set"])
        self.assertEqual(len(active_set), 8)
        self.assertTrue(set(case.accesses).issubset(active_set))

    def test_transition_pair_has_two_phases(self) -> None:
        case = traces.make_transition(n=31, k=4, seed=2026, properties=("S", "W"), phase_length=64)
        self.assert_valid(case)
        self.assertEqual(len(case.phases), 2)
        self.assertEqual(case.phases[0].parameters["property"], "S")
        self.assertEqual(case.phases[1].parameters["property"], "W")
        self.assertEqual(case.m, 128)  # 2 * 64

    def test_transition_triple_has_three_phases(self) -> None:
        case = traces.make_transition(n=31, k=4, seed=2026, properties=("S", "W", "S"), phase_length=64)
        self.assert_valid(case)
        self.assertEqual(len(case.phases), 3)
        self.assertEqual(case.phases[0].parameters["property"], "S")
        self.assertEqual(case.phases[1].parameters["property"], "W")
        self.assertEqual(case.phases[2].parameters["property"], "S")
        self.assertEqual(case.m, 192)  # 3 * 64

    def test_transition_all_properties_valid(self) -> None:
        for prop in ("S", "W", "F", "R"):
            case = traces.make_transition(n=31, k=4, seed=2026, properties=(prop,), phase_length=64)
            self.assert_valid(case)
            self.assertTrue(all(1 <= key <= 31 for key in case.accesses))

    def test_transition_unknown_property_raises(self) -> None:
        with self.assertRaises(ValueError):
            traces.make_transition(n=31, k=4, seed=2026, properties=("X",), phase_length=64)

    def test_transition_pair_count_is_8(self) -> None:
        self.assertEqual(len(traces.TRANSITION_PAIRS), 8)

    def test_transition_triple_count_is_7(self) -> None:
        self.assertEqual(len(traces.TRANSITION_TRIPLES), 7)

    def test_transition_traces_in_suite(self) -> None:
        cases = list(traces.iter_suite(
            "quick", seed=2026, n_values=(31,), k_values=(4,),
            length_factor=4, phase_factor=2,
        ))
        transition_families = [c.family for c in cases if c.family.startswith("transition_")]
        # 8 pairs + 7 triples = 15 transition traces
        self.assertEqual(len(transition_families), 15)

    def test_transition_phases_are_contiguous(self) -> None:
        for case in traces.iter_suite(
            "quick", seed=2026, n_values=(31,), k_values=(4,),
            length_factor=4, phase_factor=2,
        ):
            if not case.family.startswith("transition_"):
                continue
            with self.subTest(case=case.trace_id):
                self.assert_valid(case)

    def test_unified_total_length_is_2_passes_times_n(self) -> None:
        n, k, passes = 31, 4, 10
        case = traces.make_unified(n=n, k=k, seed=2026, passes=passes)
        self.assert_valid(case)
        self.assertEqual(case.m, 2 * passes * n)

    def test_unified_alternates_working_set_and_finger(self) -> None:
        # Small case where we can verify the pattern
        case = traces.make_unified(n=8, k=4, seed=2026, passes=1)
        self.assert_valid(case)
        # Total = 2 * 1 * 8 = 16 accesses
        self.assertEqual(case.m, 16)
        # Even indices (0,2,4,...) are working-set accesses from shuffled permutation
        # Odd indices (1,3,5,...) are finger accesses
        # All keys must be in [1, n]
        self.assertTrue(all(1 <= key <= case.n for key in case.accesses))

    def test_unified_raises_when_n_too_small(self) -> None:
        with self.assertRaises(ValueError):
            traces.make_unified(n=7, k=4, seed=2026, passes=10)  # n < 2*k

    def test_paper_working_set_visits_all_blocks(self) -> None:
        n, k, passes = 16, 4, 5
        case = traces.make_static_working_set(n=n, k=k, seed=2026, paper_protocol=True, passes=passes)
        self.assert_valid(case)
        self.assertEqual(case.m, passes * n)
        self.assertEqual(case.family, "paper_working_set")
        # Each element should be accessed exactly `passes` times
        for key in range(1, n + 1):
            self.assertEqual(case.accesses.count(key), passes)

    def test_paper_working_set_no_repeats_within_pass(self) -> None:
        n, k, passes = 16, 4, 1
        case = traces.make_static_working_set(n=n, k=k, seed=2026, paper_protocol=True, passes=passes)
        self.assert_valid(case)
        # With passes=1, each key appears exactly once
        self.assertEqual(len(set(case.accesses)), n)

    def test_default_working_set_unchanged(self) -> None:
        # Verify existing behavior is preserved when paper_protocol=False
        case = traces.make_static_working_set(n=127, k=8, seed=2026)
        self.assert_valid(case)
        self.assertEqual(case.family, "static_working_set")
        active_set = set(case.phases[0].parameters["active_set"])
        self.assertTrue(set(case.accesses).issubset(active_set))

    def test_write_suite_emits_manifest_trace_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            count = traces.write_suite(
                "quick",
                out_dir,
                seed=2026,
                n_values=(7,),
                k_values=(2,),
                length_factor=3,
                phase_factor=1,
            )
            manifest_path = out_dir / "manifest.jsonl"
            records = [
                json.loads(line)
                for line in manifest_path.read_text(encoding="utf-8").splitlines()
                if line
            ]

            self.assertEqual(count, len(records))
            self.assertGreater(count, 0)
            for record in records:
                trace_path = out_dir / record["trace_path"]
                metadata_path = out_dir / record["metadata_path"]
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                trace_values = [
                    int(line)
                    for line in trace_path.read_text(encoding="utf-8").splitlines()
                    if line
                ]

                self.assertEqual(len(trace_values), metadata["m"])
                self.assertEqual(record["m"], metadata["m"])
                self.assertEqual(record["trace_id"], metadata["trace_id"])


if __name__ == "__main__":
    unittest.main()
