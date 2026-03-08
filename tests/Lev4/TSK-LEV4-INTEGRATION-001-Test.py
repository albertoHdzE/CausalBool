
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
            'z_score_deg': -5.0,
            'bayes_factor_01': 0.01,
            'rho_depmap': 0.6,
            'mi_depmap_bits': 0.8,
            'aer': 1.5
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "CONTINUE")

    def test_falsification_zscore(self):
        """Test Z-score failure triggers Pivot"""
        metrics = {
            'z_score_deg': -0.5, # > -2.0
            'bayes_factor_01': 0.5,
            'rho_depmap': 0.6,
            'aer': 1.0
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "PIVOT_HYBRID")
        self.assertIn("Z-Score", res['reason'])

    def test_clinical_weakness(self):
        """Test low correlation triggers Cell Line pivot"""
        metrics = {
            'z_score_deg': -5.0,
            'bayes_factor_01': 0.01,
            'rho_depmap': 0.1,
            'mi_depmap_bits': 0.05,
            'aer': 1.5
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "PIVOT_CELL")

    def test_nonlinear_rescue(self):
        """Test low Rho but high MI prevents pivot"""
        metrics = {
            'z_score_deg': -5.0,
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
            'z_score_deg': -1.5, # > -2.0 (Fail)
            'bayes_factor_01': 0.5,
            'aer': 1.2 # > 1.1 (Efficiency exists)
        }
        res = ContingencyMonitor.evaluate_checkpoint(metrics)
        self.assertEqual(res['action_code'], "PUBLISH_EMERGENCE")

if __name__ == '__main__':
    unittest.main()
