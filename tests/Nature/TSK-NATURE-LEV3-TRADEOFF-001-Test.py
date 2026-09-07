import unittest
import numpy as np

# AUDIT04-E. The same pair of defects as TSK-NATURE-LEV3-TRADEOFF-002, and here
# the circularity is sharper.
#
# The path walked up THREE levels from tests/Nature, which is two levels below
# the root, so it resolved outside this repository and the import below ALWAYS
# raised ImportError. The `except` branch then supplied a mock
# `EssentialityPredictor` whose `run_cv` scored genes by
# `delta_d * 0.7 + degree * 0.3` -- a formula written in this test file. So
# `test_prediction_performance` asserted that a high AUC comes out of an
# expression chosen, in the same file, to produce one. It was not a weak test of
# src/analysis/Essentiality_Prediction_v3.py; it was not a test of it at all,
# which is why coverage reported that module at 0%.
#
# The fallback is deleted rather than repaired, so an ImportError is now an
# error. sys.path is set once by the root conftest.py.
from analysis.Essentiality_Prediction_v3 import EssentialityPredictor

class TestEssentialityPrediction(unittest.TestCase):
    def setUp(self):
        self.predictor = EssentialityPredictor()
        
        # Create synthetic data
        # 10 networks, 10 genes each
        self.networks = []
        for i in range(10):
            net = {'name': f'net_{i}', 'genes': []}
            for j in range(10):
                is_ess = (j < 3) # First 3 are essential
                # Essential genes have higher delta_d and degree
                delta_d = np.random.normal(5, 1) if is_ess else np.random.normal(1, 1)
                delta_k = np.random.normal(10, 2) if is_ess else np.random.normal(2, 2)
                degree = np.random.randint(5, 10) if is_ess else np.random.randint(1, 5)
                betweenness = np.random.random() * (0.5 if is_ess else 0.1)
                
                net['genes'].append({
                    'name': f'g_{j}',
                    'delta_d': delta_d,
                    'delta_k': delta_k,
                    'degree': degree,
                    'betweenness': betweenness,
                    'is_essential': is_ess
                })
            self.networks.append(net)

    def test_data_loading(self):
        df = self.predictor.load_data(self.networks)
        self.assertEqual(len(df), 100) # 10 nets * 10 genes
        self.assertIn('delta_d', df.columns)
        self.assertIn('is_essential', df.columns)

    def test_prediction_performance(self):
        self.predictor.load_data(self.networks)
        auc = self.predictor.run_cv(k=5)
        print(f"Test AUC: {auc}")
        self.assertGreater(auc, 0.85)

if __name__ == '__main__':
    unittest.main()
