
import numpy as np
from scipy import stats
import math

class BayesFactorCalculator:
    """
    Implements Bayesian Model Comparison for Complexity Science validation.
    Uses BIC approximation to estimate Bayes Factors between:
    H0: Data comes from the Null Distribution (Fixed mean/std)
    H1: Data comes from an Alternative Distribution (Estimated mean/std)
    """

    @staticmethod
    def calculate_bayes_factor(data, null_mean, null_std):
        """
        Computes Bayes Factor BF10 (Evidence for H1 over H0).
        
        Args:
            data (list or np.array): Observed data points (e.g., D_bio values).
            null_mean (float): Mean of the null distribution (e.g., D_rand).
            null_std (float): Standard deviation of the null distribution.
            
        Returns:
            dict: {
                'BF10': float,       # Evidence for H1 (Bio != Null)
                'BF01': float,       # Evidence for H0 (Bio == Null)
                'log10_BF10': float, # Log scale for numerical stability
                'evidence_strength': str
            }
        """
        data = np.array(data)
        n = len(data)
        
        if n < 2:
            raise ValueError("Bayes Factor calculation requires at least 2 data points.")

        # H0: Data follows Null Distribution N(null_mean, null_std)
        # 0 free parameters (relative to the specific null model hypothesis)
        # But strictly, we compare Model A (Fixed) vs Model B (Fitted).
        
        # Log-Likelihood of H0
        log_L0 = np.sum(stats.norm.logpdf(data, loc=null_mean, scale=null_std))
        k0 = 0 # No parameters estimated from data for H0
        
        # H1: Data follows Normal distribution with unknown parameters
        # Estimated from data (MLE)
        mu_hat = np.mean(data)
        sigma_hat = np.std(data, ddof=0) # MLE uses ddof=0
        
        # Handle case where sigma_hat is 0 (all data points identical)
        if sigma_hat == 0:
            # If data is constant and matches null_mean, L0 is high? 
            # If data is constant, density is Dirac delta (infinite).
            # We add a small epsilon for numerical stability if needed, 
            # or handle logically.
            # Ideally, if variance is 0, we can't fit a Gaussian in the standard sense without infinite likelihood.
            # Let's assume a minimum measurement error epsilon.
            sigma_hat = 1e-9
            
        log_L1 = np.sum(stats.norm.logpdf(data, loc=mu_hat, scale=sigma_hat))
        k1 = 2 # mu and sigma estimated
        
        # BIC Calculation
        # BIC = k * ln(n) - 2 * ln(L)
        bic0 = k0 * np.log(n) - 2 * log_L0
        bic1 = k1 * np.log(n) - 2 * log_L1
        
        # Bayes Factor Approximation
        # ln(BF10) approx -0.5 * (BIC1 - BIC0)
        log_BF10 = -0.5 * (bic1 - bic0)
        
        # Handle overflow
        try:
            bf10 = np.exp(log_BF10)
            bf01 = 1.0 / bf10 if bf10 != 0 else np.inf
        except OverflowError:
            bf10 = np.inf if log_BF10 > 0 else 0.0
            bf01 = 0.0 if log_BF10 > 0 else np.inf

        log10_bf10 = log_BF10 / np.log(10)
        
        return {
            'BF10': bf10,
            'BF01': bf01,
            'log10_BF10': log10_bf10,
            'interpretation': BayesFactorCalculator._interpret(bf10),
            'BIC0': bic0,
            'BIC1': bic1
        }

    @staticmethod
    def _interpret(bf10):
        """Kass and Raftery (1995) interpretation scale."""
        if bf10 < 1:
            return "Negative (Supports H0)"
        elif 1 <= bf10 < 3:
            return "Weak (Anecdotal)"
        elif 3 <= bf10 < 20:
            return "Positive"
        elif 20 <= bf10 < 150:
            return "Strong"
        else:
            return "Very Strong"

if __name__ == "__main__":
    # Simple self-test
    null_mean = 100
    null_std = 10
    
    # Case 1: Data matches Null
    data_h0 = np.random.normal(100, 10, 50)
    res_h0 = BayesFactorCalculator.calculate_bayes_factor(data_h0, null_mean, null_std)
    print(f"H0 Case: BF10={res_h0['BF10']:.4f} ({res_h0['interpretation']})")
    
    # Case 2: Data differs (H1)
    data_h1 = np.random.normal(120, 10, 50)
    res_h1 = BayesFactorCalculator.calculate_bayes_factor(data_h1, null_mean, null_std)
    print(f"H1 Case: BF10={res_h1['BF10']:.4e} ({res_h1['interpretation']})")
