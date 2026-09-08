"""AUDIT04-E: this file no longer speaks in z-scores.

Two things were wrong and the first hid the second.

SIGN. The project's only producer of a z-score defined it as
(mean_null - D_bio)/sd, so "bio is simpler" was POSITIVE. This file passed
z = -5.0 and called it "ideal conditions", the opposite convention. Every
good-signal case therefore tripped the falsification branch and was then
rescued to PUBLISH_EMERGENCE by aer > 1.1 -- which is why three of five
failures all read the same word. Measured: 2/5 passing as written, 5/5 with the
sign flipped, and the 2 that "passed" did so through the sign-confused branch.

OPERATOR. That question is now moot. The z-score is replaced (author directive,
2026-09-07) by two quantities that need no ensemble shape:

    gap_bits_deg   D(best null) - D(bio), in bits. Positive means bio is
                   shorter than the single best null.
    exceed_deg     #{null <= bio} / n, the exact permutation tail.

Falsification is exceed >= 0.05 or gap <= 0. The cases below are written
directly in those terms: a separating network is (gap 40.0, exceed 0.0) and a
non-separating one is (gap 0.5, exceed 0.20).
"""

import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from pipeline.Contingency_Monitor import ContingencyMonitor

class TestContingencyMonitor(unittest.TestCase):

    def test_robust_signal(self):
        """Test ideal conditions: Strong Z, Strong Rho"""
        metrics = {
            'gap_bits_deg': 40.0, 'exceed_deg': 0.0,
            'bayes_factor_01': 0.01,
            'rho_depmap': 0.6,
            'mi_depmap_bits': 0.8,
            'aer': 1.5
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "CONTINUE")

    def test_failure_to_separate_triggers_hybrid_switch(self):
        """20% of nulls at least as short as Bio -> SWITCH_TO_HYBRID_ENCODING."""
        metrics = {
            'gap_bits_deg': 0.5, 'exceed_deg': 0.20,
            'bayes_factor_01': 0.5,
            'rho_depmap': 0.6,
            'aer': 1.0
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "SWITCH_TO_HYBRID_ENCODING")
        self.assertIn("failure to separate", res['reason'])

    def test_disagreeing_measures_yield_undecided_rather_than_a_verdict(self):
        """AUDIT04-F: neither comparison measure may falsify the programme alone.

        Measured 2026-09-07, the two disagree on real families: at n = 16 against
        random matrices of identical edge count, the index-set length ranks a
        checkerboard at 1050.5 bits against 563.9 for random -- it calls the
        structured object twice as complex as noise -- where BDM gives 34.3
        against 489.9; and on a 12-node chain against 200 random graphs with 11
        edges, the index-set length calls random simpler in 14/200 and BDM in
        0/200. Each is right where the other is wrong, so a disagreement is
        information and must be reported, not resolved.
        """
        metrics = {
            'gap_bits_deg': 40.0, 'exceed_deg': 0.0,      # index-set: supports
            'gap_bits_bdm': -3.0, 'exceed_bdm': 0.9,      # BDM: falsifies
            'bayes_factor_01': 0.01, 'rho_depmap': 0.6, 'aer': 1.5,
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "UNDECIDED")
        self.assertIn("disagree", res['reason'])
        # Both numbers must appear, so a reader can see WHICH disagreed and by how much.
        self.assertIn("40.00", res['reason'])
        self.assertIn("-3.00", res['reason'])

    def test_agreeing_measures_still_decide(self):
        """The agreement rule must not deadlock the monitor."""
        metrics = {
            'gap_bits_deg': 0.5, 'exceed_deg': 0.20,
            'gap_bits_bdm': 0.5, 'exceed_bdm': 0.20,
            'bayes_factor_01': 0.5, 'rho_depmap': 0.6, 'aer': 1.0,
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "SWITCH_TO_HYBRID_ENCODING")

    def test_absent_bdm_says_so_instead_of_pretending_to_two_measures(self):
        """Below pybdm's 4x4 floor there is no BDM, and the report must admit it."""
        metrics = {
            'gap_bits_deg': 0.5, 'exceed_deg': 0.20,
            'bayes_factor_01': 0.5, 'rho_depmap': 0.6, 'aer': 1.0,
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "SWITCH_TO_HYBRID_ENCODING")
        self.assertIn("BDM unavailable", res['reason'])

    def test_clinical_weakness(self):
        """Test low correlation triggers the switch to cell lines"""
        metrics = {
            'gap_bits_deg': 40.0, 'exceed_deg': 0.0,
            'bayes_factor_01': 0.01,
            'rho_depmap': 0.1,
            'mi_depmap_bits': 0.05,
            'aer': 1.5
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "SWITCH_TO_CELL_LINES")

    def test_nonlinear_rescue(self):
        """Test low Rho but high MI prevents the switch"""
        metrics = {
            'gap_bits_deg': 40.0, 'exceed_deg': 0.0,
            'bayes_factor_01': 0.01,
            'rho_depmap': 0.25, # < 0.3 threshold usually, but in Noise range
            'mi_depmap_bits': 0.6, # High MI
            'aer': 1.5
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "CONTINUE")
        self.assertIn("High MI", res['reason'])

    def test_emergence_rescue(self):
        """Test weak Z-score but high AER triggers Emergence"""
        metrics = {
            'gap_bits_deg': 0.5, 'exceed_deg': 0.20,
            'bayes_factor_01': 0.5,
            'aer': 1.2 # > 1.1 (Efficiency exists)
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "PUBLISH_EMERGENCE")

if __name__ == '__main__':
    unittest.main()
