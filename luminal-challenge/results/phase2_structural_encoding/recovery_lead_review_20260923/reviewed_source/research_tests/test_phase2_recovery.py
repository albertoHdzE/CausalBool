"""Targeted regression tests for the frozen recovery policy plumbing."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from research import physical_probes  # noqa: E402
from research import run_structural_experiments as runner  # noqa: E402


class RecoveryPolicyTests(unittest.TestCase):
    def test_proposal_order_is_alternative_outer_and_time_then_producer(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        record = next(item for item in contract.fixtures if item.get("incumbent"))
        domain = runner.fixture_domain(record)
        proposals = list(physical_probes.proposals(domain))
        fields = []
        for op_id in sorted(domain.time_domains):
            origin = domain.incumbent_times[op_id]
            alternatives = [v for v in domain.time_domains[op_id] if v != origin]
            fields.append(("time", str(op_id), alternatives))
        for name in sorted(domain.address_domains, key=lambda n: domain.facts.producers[n]):
            origin = domain.incumbent_addresses[name]
            alternatives = [v for v in domain.address_domains[name] if v != origin]
            fields.append(("address", name, alternatives))
        expected = []
        for ordinal in range(max(len(values) for _, _, values in fields)):
            expected.extend((kind, name, ordinal, values[ordinal])
                            for kind, name, values in fields if ordinal < len(values))
        self.assertEqual(proposals, expected)

    def test_amendment_is_exactly_the_lead_pinned_policy(self):
        loaded = runner.load_amendment(Path("plan/phase2_recovery/AMENDMENT.json"))
        self.assertEqual(loaded["id"], "luminal-phase2-recovery-1.0")
        with self.assertRaises(runner.StageBlocked):
            runner.load_amendment(Path("plan/phase2/PROTOCOL.json"))

    def test_amended_p2_membership_is_1800_and_classical_is_unbudgeted(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        programs = [{"program_sha256": f"p{i}"} for i in range(8)]
        rows = runner.expected_keys(programs, contract.budgets["optimisation_seconds"],
                                    ("accepted_bootstrap", "accepted_default", "classical"),
                                    ("accepted_budgeted",) + runner.STRUCTURAL_ARMS,
                                    contract.statistics["timing_repetitions"])
        self.assertEqual(len(rows), 1800)
        self.assertEqual(sum(row[1] is None and row[2] == "classical" for row in rows), 120)
        self.assertFalse(any(row[1] is not None and row[2] == "classical" for row in rows))

    def test_no_flag_keeps_legacy_measurement_membership_and_cli_policy(self):
        contract = runner.Contract(ROOT / "plan/phase2")
        programs = [{"program_sha256": f"p{i}"} for i in range(8)]
        rows = runner.expected_keys(programs, contract.budgets["optimisation_seconds"],
                                    ("accepted_bootstrap", "accepted_default"),
                                    ("accepted_budgeted",) + runner.STRUCTURAL_ARMS,
                                    contract.statistics["timing_repetitions"])
        self.assertEqual(len(rows), 1680)
        args = runner.parse_args(["--stage", "p2", "--run-id", "compatibility_probe"])
        self.assertIsNone(args.amendment)
        with self.assertRaises(runner.StageBlocked):
            runner.run_measurement({"kind": "phase2_measurement", "arm": "classical"})


if __name__ == "__main__":
    unittest.main()
