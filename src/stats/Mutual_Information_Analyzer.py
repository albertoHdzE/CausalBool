
import numpy as np
from sklearn.feature_selection import mutual_info_regression, mutual_info_classif
from scipy import stats

class MutualInformationAnalyzer:
    """
    Computes Mutual Information (MI) to detect non-linear dependencies
    that Pearson correlation might miss.
    Uses Kraskov et al. (KSG) estimator via scikit-learn.
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
