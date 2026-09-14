import unittest

# AUDIT04-E. Two defects here, and the first one hid the second.
#
# The path walked up THREE levels from tests/Nature, which is two levels below
# the root, so it resolved to /Users/alberto/Documents/projects/src -- outside
# this repository, and non-existent. The import below therefore ALWAYS raised
# ImportError, and the `except` branch replaced the module under test with a
# forty-line mock defined in this file: `d_struct = 100` hard-coded, a
# `k_behav` marked `# Dummy`, and networks made of numpy noise.
#
# So this file passed for as long as it has existed while measuring NOTHING
# about src/analysis/Phase_Transition.py, which coverage duly reported at 0%.
# A test that silently substitutes a stub for its subject cannot fail for the
# right reason, so the fallback is deleted rather than repaired: an ImportError
# must now be an error.
#
# The path bootstrap itself is no longer this file's business either -- the root
# conftest.py puts src/ on sys.path once, for every test, ahead of the foreign
# trees that a .pth file injects into this venv.
from analysis.Phase_Transition import PhaseTransitionAnalyzer

class TestPhaseTransition(unittest.TestCase):
    def setUp(self):
        self.analyzer = PhaseTransitionAnalyzer()
        
    def test_sweep(self):
        results = self.analyzer.run_sweep(n_points=3)
        self.assertEqual(len(results), 3)
        self.assertIn("p_xor", results[0])
        self.assertIn("aer", results[0])
        
    def test_values(self):
        # Just check that it runs
        res = self.analyzer.run_sweep()
        self.assertTrue(len(res) > 0)

if __name__ == '__main__':
    unittest.main()
