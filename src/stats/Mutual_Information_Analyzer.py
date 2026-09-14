
"""Mutual information as a DEPENDENCE STATISTIC, never as a complexity measure.

AUDIT04-F, and this module needs the label because it is Shannon and it survived
the sweep that removed Shannon from our measures.

The author's directive of 2026-09-07 forbids any Shannon quantity from serving
as one of our complexity measures; the two comparison measures are the index-set
program length and BDM. Mutual information here is neither. It measures the
DEPENDENCE BETWEEN TWO VARIABLES -- a complexity score and a clinical outcome --
in exactly the role a Pearson correlation plays, and it sits beside `pearson_rho`
in the returned dict for that reason. Nothing here measures the complexity of
anything. So it falls under the same rule as H_total and ZIP: a labelled
statistic, permitted, and never quoted as a measure of ours.

WHY THE LABEL IS LOAD-BEARING. This file was invisible to
audit/AUDIT04_E_measures/census_shannon.py until 2026-09-07. That census works
by SHAPE -- p*log p, frequency tables, probability normalisation -- and none of
those shapes appears here, because the Kraskov estimator hides all of them
behind a library call. The census reported 86 sites over 628 files while missing
a Shannon quantity that feeds a live decision branch: `mi_depmap_bits` reaches
Contingency_Monitor through DepMap_Validation and helps decide the switch to
cell lines. A `library_entropy_estimator` detector now catches it.
"""
import numpy as np
from sklearn.feature_selection import mutual_info_regression, mutual_info_classif
from scipy import stats

class MutualInformationAnalyzer:
    """
    Computes Mutual Information (MI) to detect non-linear dependencies
    that Pearson correlation might miss.
    Uses Kraskov et al. (KSG) estimator via scikit-learn.

    This is a STATISTIC, not a measure of complexity -- see the module docstring.
    """

    @staticmethod
    def compute_mutual_information(x, y, discrete_y=False, random_seed=42):
        """
        Computes MI between x and y.
        
        Args:
            x (array-like): Feature vector (e.g., Delta D).
            y (array-like): Target vector (e.g., Essentiality Score).
            discrete_y (bool): If True, treats y as discrete labels (Classification).
                               If False, treats y as continuous (Regression).
            random_seed (int): Seed for reproducibility.
            
        Returns:
            dict: {
                'MI_nats': float,
                'MI_bits': float,
                'pearson_rho': float,
                'interpretation': str
            }
        """
        x = np.array(x).reshape(-1, 1)
        y = np.array(y)
        
        # Check constraints
        if len(x) != len(y):
            raise ValueError(f"Length mismatch: x({len(x)}) != y({len(y)})")
        
        if len(x) < 3:
            # Too few samples for KNN
            return {'MI_nats': 0.0, 'MI_bits': 0.0, 'pearson_rho': 0.0, 'interpretation': "Insufficient Data"}

        # Compute Pearson Rho for comparison
        # Handle constant input to avoid warnings
        if np.std(x) == 0 or np.std(y) == 0:
            rho = 0.0
        else:
            rho, _ = stats.pearsonr(x.flatten(), y.flatten())

        # Compute MI
        # random_state is available in recent sklearn versions
        if discrete_y:
            mi_nats = mutual_info_classif(x, y, random_state=random_seed)[0]
        else:
            mi_nats = mutual_info_regression(x, y, random_state=random_seed)[0]
            
        mi_bits = mi_nats / np.log(2)
        
        # Interpretation
        interpretation = MutualInformationAnalyzer._interpret(mi_bits, rho)
        
        return {
            # Declared in the payload, not only in the docstring, so a consumer
            # reading this dict cannot mistake it for one of our two measures.
            'kind': 'statistic',
            'quantity': 'shannon_mutual_information_ksg',
            'is_complexity_measure': False,
            'MI_nats': mi_nats,
            'MI_bits': mi_bits,
            'pearson_rho': rho,
            'interpretation': interpretation
        }

    @staticmethod
    def _interpret(mi_bits, rho):
        """
        Interprets the relationship based on MI and Correlation.
        """
        # Thresholds are heuristic
        if mi_bits < 0.1:
            return "No Dependency"
        
        # Check for non-linearity
        # If High MI but Low Rho -> Non-Linear
        # Approx: MI for Gaussian = -0.5 * log(1 - rho^2) in nats
        # expected_mi_nats = -0.5 * np.log(1 - rho**2 + 1e-9)
        # expected_mi_bits = expected_mi_nats / np.log(2)
        
        # If actual MI >> expected MI, it implies non-Gaussian/Non-Linear dependency
        # But simply:
        if abs(rho) < 0.3 and mi_bits > 0.5:
            return "Hidden Non-Linear Dependency"
        elif mi_bits > 0.5:
            return "Strong Dependency"
        else:
            return "Weak Dependency"

if __name__ == "__main__":
    # Self-test with Sine Wave
    x = np.linspace(0, 4*np.pi, 100)
    y = np.sin(x)
    
    # Add small noise to avoid perfect determinism issues in estimators
    y += np.random.normal(0, 0.1, 100)
    
    res = MutualInformationAnalyzer.compute_mutual_information(x, y)
    print(f"Sine Wave: Rho={res['pearson_rho']:.4f}, MI={res['MI_bits']:.4f} bits")
    print(f"Interpretation: {res['interpretation']}")
