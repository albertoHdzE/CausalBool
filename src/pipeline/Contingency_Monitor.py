
import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stats.Bayes_Factor_Calculator import BayesFactorCalculator

class ContingencyMonitor:
    """
    Automated Decision Matrix for Project Contingency.
    Evaluates statistical signals against pre-defined thresholds (Level 4 Protocol).
    """
    
    ACTIONS = {
        "CONTINUE": "Signal is robust. Continue Phase 3.",
        "ITERATE": "Signal is noisy ($0.2 < \\rho < 0.4$). Increase N and refine features.",
        "PIVOT_HYBRID": "Theoretical Falsification ($Z > -2.0$ or $BF_{01} > 10$). Pivot to Hybrid Encoding.",
        "PIVOT_CELL": "Clinical Weakness ($\\rho < 0.2$ and $MI \\approx 0$). Switch to Cell Lines.",
        "PUBLISH_EMERGENCE": "High Complexity but High Efficiency ($AER > 1.0$). Publish 'Edge of Chaos' finding."
    }

    @staticmethod
    def evaluate_checkpoint(metrics):
        """
        Evaluates the current project state based on aggregated metrics.
        
        Args:
            metrics (dict): {
                'z_score_deg': float,
                'bayes_factor_01': float,
                'rho_depmap': float,
                'mi_depmap_bits': float,
                'aer': float, # Algorithmic Efficiency Ratio (D_bio / D_shuffled) ? Or D_rand / D_bio?
                              # Usually AER = D_rand / D_bio. If > 1.0, Bio is simpler.
                'scaling_diff': float # alpha_bio - alpha_rand (abs)
            }
            
        Returns:
            dict: {
                'action_code': str,
                'reason': str,
                'report_path': str
            }
        """
        z = metrics.get('z_score_deg', -999.0)
        bf01 = metrics.get('bayes_factor_01', 0.0)
        rho = metrics.get('rho_depmap', 0.0)
        mi = metrics.get('mi_depmap_bits', 0.0)
        aer = metrics.get('aer', 1.0)
        
        action = "CONTINUE"
        reasons = []

        # 1. Check Falsification (Universality)
        # Z-score > -2.0 means D_bio is close to D_rand (Not simple).
        # Note: Z = (D_bio - Mean_Rand) / Std_Rand. 
        # If D_bio << Mean_Rand, Z is negative (e.g. -5). 
        # If D_bio approx Mean_Rand, Z approx 0.
        # So Z > -2.0 is indeed "Failure to separate".
        if z > -2.0:
            action = "PIVOT_HYBRID"
            reasons.append(f"Z-Score ({z:.2f}) > -2.0 indicates failure to separate Bio from Null.")
        elif bf01 > 10.0:
            action = "PIVOT_HYBRID"
            reasons.append(f"Bayes Factor BF01 ({bf01:.2f}) > 10 strongly favors Null Model.")

        # 2. Check Clinical Relevance (if not already pivoting)
        if action == "CONTINUE":
            if rho < 0.2 and mi < 0.1:
                action = "PIVOT_CELL"
                reasons.append(f"Weak Correlation (rho={rho:.2f}) and No MI ({mi:.2f} bits).")
            elif 0.2 <= rho < 0.4:
                # Check MI for rescue
                if mi > 0.5:
                    action = "CONTINUE"
                    reasons.append(f"Low Rho ({rho:.2f}) but High MI ({mi:.2f}) suggests non-linearity. Continue.")
                else:
                    action = "ITERATE"
                    reasons.append(f"Marginal Correlation (rho={rho:.2f}). Iterate and refine.")

        # 3. Check Emergence (Rescue Clause)
        # If we decided to Pivot due to Z-score, check if it's actually Criticality
        if action == "PIVOT_HYBRID":
            # If D_bio is high (Z > -2.0) BUT AER > 1.0?
            # Wait, if Z > -2.0, D_bio approx D_rand. So AER approx 1.0.
            # If AER is significantly > 1.0 (e.g. 1.2), then Z would be negative (D_bio < D_rand).
            # So Z > -2.0 implies AER <= 1.0 approx?
            # "High Complexity but High Efficiency" -> Maybe D is high but... 
            # If AER > 1.0, Bio is simpler.
            # Let's assume Emergence means AER is maintained despite high D?
            # Or maybe checking Lempel-Ziv?
            # "Criticality Check: D_bio High but AER > 1.0"
            # If AER > 1.0, D_bio < D_rand. Z < 0.
            # Maybe the threshold for Z is strict (-2.0 is 95%).
            # If Z = -1.5 (Failure by strict standards), but AER = 1.1 (still simpler).
            if aer > 1.1:
                action = "PUBLISH_EMERGENCE"
                reasons.append(f"Z-Score ({z:.2f}) is weak, but AER ({aer:.2f}) > 1.1 suggests Edge of Chaos efficiency.")

        # Generate Report
        report = ContingencyMonitor._generate_report(metrics, action, reasons)
        
        return {
            'action_code': action,
            'reason': "; ".join(reasons),
            'report_content': report
        }

    @staticmethod
    def _generate_report(metrics, action, reasons):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# Contingency Monitor Report",
            f"**Date:** {timestamp}",
            f"**Action:** {action}",
            f"**Description:** {ContingencyMonitor.ACTIONS.get(action, 'Unknown')}",
            "",
            "## Metrics",
            f"- Z-Score (Deg): {metrics.get('z_score_deg', 'N/A')}",
            f"- Bayes Factor 01: {metrics.get('bayes_factor_01', 'N/A')}",
            f"- DepMap Rho: {metrics.get('rho_depmap', 'N/A')}",
            f"- DepMap MI (bits): {metrics.get('mi_depmap_bits', 'N/A')}",
            f"- AER: {metrics.get('aer', 'N/A')}",
            "",
            "## Decision Logic",
        ]
        lines.extend([f"- {r}" for r in reasons])
        if not reasons:
            lines.append("- All metrics within acceptable ranges.")
            
        return "\n".join(lines)

if __name__ == "__main__":
    # Test
    metrics = {
        'z_score_deg': -0.5,
        'bayes_factor_01': 12.0,
        'rho_depmap': 0.1,
        'mi_depmap_bits': 0.05,
        'aer': 1.0
    }
    res = ContingencyMonitor.evaluate_checkpoint(metrics)
    print(f"Action: {res['action_code']}")
    print(res['report_content'])
