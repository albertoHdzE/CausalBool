
import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class ContingencyMonitor:
    """
    Automated Decision Matrix for Project Contingency.
    Evaluates statistical signals against pre-defined thresholds (Level 4 Protocol).
    """
    
    ACTIONS = {
        "CONTINUE": "Signal is robust. Continue Phase 3.",
        "ITERATE": "Signal is noisy ($0.2 < \\rho < 0.4$). Increase N and refine features.",
        "PIVOT_HYBRID": "Theoretical Falsification (>= 5% of nulls as short as Bio, or Bio not shorter than the best null, or $BF_{01} > 10$). Pivot to Hybrid Encoding.",
        "PIVOT_CELL": "Clinical Weakness ($\\rho < 0.2$ and $MI \\approx 0$). Switch to Cell Lines.",
        "PUBLISH_EMERGENCE": "High Complexity but High Efficiency ($AER > 1.0$). Publish 'Edge of Chaos' finding."
    }

    @staticmethod
    def evaluate_checkpoint(metrics):
        """
        Evaluates the current project state based on aggregated metrics.
        
        Args:
            metrics (dict): {
                'gap_bits_deg': float,   # D(best null) - D(bio), in bits
                'exceed_deg': float,     # #{null <= bio} / n, in [0, 1]
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
        # AUDIT04-E, author directive 2026-09-07: the z-score is replaced by an
        # algorithmic gap and a distribution-free rank.
        #
        # The falsification branch below read `z < 2.0`, where z was
        # (mean_null - D_bio)/sd_null. Two defects rode on that. The measure
        # underneath it was Shannon (D_v2, retired: it ranked a random graph
        # simpler than a chain in 195 of 200 draws), and the OPERATOR discarded
        # the bits: on three nulls where bio beat 0 of 1000 in every case, z
        # said 5.07 / 0.00 / 0.31 and would have falsified two of them.
        #
        # Now:
        #   gap_bits_deg  D(best null) - D(bio). Positive means bio is shorter
        #                 than the single best null. By the coding theorem a gap
        #                 of g bits is a likelihood ratio of 2^g under the
        #                 universal distribution.
        #   exceed_deg    #{null <= bio}/n, the exact permutation tail.
        #
        # `z_score_deg` is still accepted so stored artefacts written before this
        # change keep resolving, but it is NOT used for the decision -- a value
        # computed from the retired measure must not steer a pivot.
        gap = metrics.get('gap_bits_deg')
        exceed = metrics.get('exceed_deg')
        bf01 = metrics.get('bayes_factor_01', 0.0)
        rho = metrics.get('rho_depmap', 0.0)
        mi = metrics.get('mi_depmap_bits', 0.0)
        aer = metrics.get('aer', 1.0)
        
        action = "CONTINUE"
        reasons = []

        # 1. Falsification: did the real network separate from its nulls?
        #
        # TWO conditions, because they fail differently. `exceed` says whether
        # bio beat the ensemble at all; `gap` says by how much. A result can
        # clear the rank while being one bit shorter, and a large gap means
        # nothing if part of the ensemble is shorter still.
        #
        # exceed >= 0.05 is the distribution-free analogue of the old two-sigma
        # threshold, and it is EXACT rather than approximate: it assumes nothing
        # about the ensemble's shape, which is precisely what the old operator
        # got wrong on the degenerate and heavy-tailed nulls.
        #
        # REFUSES on absent inputs. The old code defaulted z to -999.0, which
        # silently satisfied `z < 2.0` and would have pivoted the whole project
        # on a missing measurement.
        if gap is None or exceed is None:
            raise ValueError(
                "evaluate_checkpoint needs gap_bits_deg and exceed_deg "
                "(AUDIT04-E). The z-score they replace was computed from the "
                "retired Shannon measure; defaulting either would decide a "
                "pivot from an absent measurement."
            )

        if exceed >= 0.05:
            action = "PIVOT_HYBRID"
            reasons.append(
                f"{exceed:.1%} of nulls are as short as Bio or shorter (>= 5%): "
                f"failure to separate Bio from Null.")
        elif gap <= 0.0:
            action = "PIVOT_HYBRID"
            reasons.append(
                f"Bio is not shorter than the best null (gap {gap:.2f} bits): "
                f"failure to separate.")
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

        # 3. Emergence (rescue clause)
        #
        # The block this replaces was eleven lines of the author reasoning aloud
        # about the z-score's sign and reaching no conclusion ("Wait, if Z >
        # -2.0...", "Let's assume...", "Or maybe checking Lempel-Ziv?"). None of
        # it survives the operator it was reasoning about.
        #
        # The claim underneath is clear enough on its own: if the network failed
        # to separate on program LENGTH yet is still algorithmically efficient
        # (AER > 1.1), that is a finding rather than a falsification -- the
        # structure is near the boundary, not absent.
        if action == "PIVOT_HYBRID":
            if aer > 1.1:
                action = "PUBLISH_EMERGENCE"
                reasons.append(
                    f"Separation is weak (gap {gap:.2f} bits, {exceed:.1%} of "
                    f"nulls at least as short), but AER ({aer:.2f}) > 1.1 "
                    f"suggests Edge of Chaos efficiency.")

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
            "# Contingency Monitor Report",
            f"**Date:** {timestamp}",
            f"**Action:** {action}",
            f"**Description:** {ContingencyMonitor.ACTIONS.get(action, 'Unknown')}",
            "",
            "## Metrics",
            f"- Gap vs best null (Deg): {metrics.get('gap_bits_deg', 'N/A')} bits",
            f"- Nulls at least as short (Deg): {metrics.get('exceed_deg', 'N/A')}",
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
