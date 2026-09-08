
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
        "SWITCH_TO_HYBRID_ENCODING": "Theoretical Falsification (>= 5% of nulls as short as Bio, or Bio not shorter than the best null, or $BF_{01} > 10$). Switch to Hybrid Encoding.",
        "SWITCH_TO_CELL_LINES": "Clinical Weakness ($\\rho < 0.2$ and $MI \\approx 0$). Switch to Cell Lines.",
        "PUBLISH_EMERGENCE": "High Complexity but High Efficiency ($AER > 1.0$). Publish 'Edge of Chaos' finding.",
        "UNDECIDED": "The two comparison measures disagree on falsification. No action, because a single measure must not decide this on its own."
    }

    # AUDIT04-F, GLOSSARY sec.1e (author ruling 2026-09-07). These action codes
    # carried the retired word. GLOSSARY sec.8 had checked them in context,
    # ruled them ordinary English, and kept them, on the argument that adopting
    # a two-word technical term for the finance sense frees the bare word. That
    # argument is sound in principle and failed three times in practice, each
    # failure costing an adjudication of which sense was meant. The word is now
    # retired outright; these names say what they do and need no adjudication.
    #
    # Stored artefacts written under the old codes are NOT rewritten:
    # results/bio/Contingency_Report.md is regenerated, and doc/ is an archive.
    RETIRED_ACTION_CODES = {
        "PIVOT_HYBRID": "SWITCH_TO_HYBRID_ENCODING",
        "PIVOT_CELL": "SWITCH_TO_CELL_LINES",
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
        # computed from the retired measure must not steer a redirection.
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
        # silently satisfied `z < 2.0` and would have redirected the whole project
        # on a missing measurement.
        if gap is None or exceed is None:
            raise ValueError(
                "evaluate_checkpoint needs gap_bits_deg and exceed_deg "
                "(AUDIT04-E). The z-score they replace was computed from the "
                "retired Shannon measure; defaulting either would redirect the "
                "whole programme from an absent measurement."
            )

        # AUDIT04-F: the falsification verdict now requires the TWO comparison
        # measures to agree, and reports UNDECIDED when they do not.
        #
        # `gap`/`exceed` come from the index-set program length; `gap_bits_bdm`/
        # `exceed_bdm` from BDM. Neither dominates the other, and that is
        # measured rather than assumed: at n = 16 against random matrices of
        # identical edge count, the index-set length ranks a checkerboard
        # (1050.5 bits) and column stripes (1050.5) as roughly twice as complex
        # as noise (563.9, 568.4), where BDM ranks both correctly (34.3 vs
        # 489.9; 34.2 vs 485.2); on a 12-node chain against 200 random graphs
        # with 11 edges the index-set length calls random simpler in 14/200 and
        # BDM in 0/200. A measure that is right on one family and wrong on
        # another must not falsify a programme by itself.
        #
        # The BDM pair is OPTIONAL, because networks below pybdm's 4x4 partition
        # floor have no BDM at all. Absent, the index-set verdict stands alone
        # and says so; present and disagreeing, the answer is UNDECIDED.
        gap_bdm = metrics.get('gap_bits_bdm')
        exceed_bdm = metrics.get('exceed_bdm')

        def _falsified(g, e):
            return e >= 0.05 or g <= 0.0

        falsified_index = _falsified(gap, exceed)
        if gap_bdm is not None and exceed_bdm is not None:
            falsified_bdm = _falsified(gap_bdm, exceed_bdm)
            if falsified_index != falsified_bdm:
                return ContingencyMonitor._undecided(
                    metrics, gap, exceed, gap_bdm, exceed_bdm,
                    falsified_index, falsified_bdm)
        else:
            reasons.append(
                "BDM unavailable for this network (below the 4x4 partition "
                "floor); the verdict rests on the index-set length alone.")

        if exceed >= 0.05:
            action = "SWITCH_TO_HYBRID_ENCODING"
            reasons.append(
                f"{exceed:.1%} of nulls are as short as Bio or shorter (>= 5%): "
                f"failure to separate Bio from Null.")
        elif gap <= 0.0:
            action = "SWITCH_TO_HYBRID_ENCODING"
            reasons.append(
                f"Bio is not shorter than the best null (gap {gap:.2f} bits): "
                f"failure to separate.")
        elif bf01 > 10.0:
            action = "SWITCH_TO_HYBRID_ENCODING"
            reasons.append(f"Bayes Factor BF01 ({bf01:.2f}) > 10 strongly favors Null Model.")

        # 2. Check Clinical Relevance (if not already redirecting)
        if action == "CONTINUE":
            if rho < 0.2 and mi < 0.1:
                action = "SWITCH_TO_CELL_LINES"
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
        if action == "SWITCH_TO_HYBRID_ENCODING":
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
    def _undecided(metrics, gap, exceed, gap_bdm, exceed_bdm,
                   falsified_index, falsified_bdm):
        """The two measures disagree, so no action is taken and both are quoted.

        Reporting the disagreement is the point. Silently resolving it to one
        measure is what the retired ``z = -999.0`` default already did once: it
        satisfied ``z < 2.0`` from an absent measurement and would have redirected
        the whole project.
        """
        reasons = [
            f"Index-set program length {'falsifies' if falsified_index else 'supports'} "
            f"(gap {gap:.2f} bits, {exceed:.1%} of nulls at least as short); "
            f"BDM {'falsifies' if falsified_bdm else 'supports'} "
            f"(gap {gap_bdm:.2f} bits, {exceed_bdm:.1%} of nulls at least as short). "
            f"The two comparison measures disagree, so the verdict is withheld."
        ]
        report = ContingencyMonitor._generate_report(metrics, "UNDECIDED", reasons)
        return {
            'action_code': "UNDECIDED",
            'reason': "; ".join(reasons),
            'report_content': report,
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
            f"- Gap vs best null (Deg, index-set): {metrics.get('gap_bits_deg', 'N/A')} bits",
            f"- Nulls at least as short (Deg, index-set): {metrics.get('exceed_deg', 'N/A')}",
            f"- Gap vs best null (Deg, BDM): {metrics.get('gap_bits_bdm', 'N/A')} bits",
            f"- Nulls at least as short (Deg, BDM): {metrics.get('exceed_bdm', 'N/A')}",
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
