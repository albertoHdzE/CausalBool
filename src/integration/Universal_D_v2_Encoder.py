"""D_v2 -- RETIRED AS A MEASURE. Forwards to the index-set program length.

AUDIT04-E, author directive 2026-09-07: this programme is ALGORITHMIC
(Kolmogorov/AID). No Shannon quantity may serve as one of our complexity
measures. The two comparison measures are the INDEX-SET PROGRAM LENGTH (ours)
and BDM. Shannon quantities survive only as explicitly labelled statistical
BASELINES that our measure is compared against -- H_total and ZIP in comp_paper
Table 2 -- never as a measure of ours.

WHAT THIS FILE USED TO COMPUTE, AND WHY IT HAD TO GO

    p = ones / size
    h = -(p*log2(p) + (1-p)*log2(1-p))      # Shannon binary entropy
    return h * size

plus `_block_key = (size, ones)`, which keyed every block by its DENSITY and
discarded the arrangement. Binary entropy is MAXIMISED at density one half and
minimised at the extremes, which is the reverse of what a program length does.
The consequence was measured on 2026-09-07 rather than argued -- 200 random
12-node networks, each carrying exactly the 11 edges of a 12-node chain, asking
how often each measure calls the RANDOM graph simpler-or-equal than the chain:

    D_v2 (this file, as it was)     195 / 200   97.5 %
    BDM                               0 / 200    0.0 %
    index-set program length         14 / 200    7.0 %

A measure that ranks a random graph as simpler than a chain in 97.5 per cent of
draws is not mis-tuned, it is inverted. Every claim of the form "the real
network is simpler than its randomised nulls" computed through this file was
reading the opposite of what it stated. It also assigned IDENTICAL lengths to a
network and its transpose (difference exactly 0.0), so "the hub drives everyone"
and "everyone drives the hub" scored the same in a causality-first programme.

WHY A FORWARDER RATHER THAN A DELETION

Thirteen production files call this encoder, including DepMap_Validation,
Cancer_Corruption, KRB_Corruption_Anchors and Null_Generator_HPC. Under the
collapse protocol in GOVERNANCE/CORE.md section 6 a forwarder preserves the
provenance of every result already produced under the old name, and it moves all
thirteen consumers with ONE change site instead of thirteen that can drift apart.

`row_run_index_set_length` takes an adjacency matrix and nothing else -- the same
signature this encoder was always called with -- so the substitution is exact at
every call site. The OWNER is src/description_lengths.py; nothing is
reimplemented here.

THE NUMBERS MOVE, AND THAT IS THE POINT. Over 210 corpus networks the median
goes 106.32 -> 334.43 bits. No number in either active manuscript is affected:
D_v2 appears in neither `method_paper.tex` nor `comp_paper.tex`, only in
results/bio/simplicity_v2_real.json and results/lev3/setup001.json.

Guarded by tests/analysis/test_complexity_measures_are_algorithmic.py, which
fails any measure that ranks random above structured.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


class UniversalDv2Encoder:
    """Adjacency -> index-set program length in bits.

    The class name and the ``dv2`` result key are retained so existing callers
    and stored artefacts keep resolving; the QUANTITY is now algorithmic.
    """

    def __init__(self, adjacency_matrix, block_sizes: List[int] | None = None,
                 stride: int = 1):
        self.cm = np.array(adjacency_matrix).astype(int)
        self.n = self.cm.shape[0]
        # Retained only to keep the old signature callable. A program length has
        # no block decomposition, so a caller that VARIES these is asking a
        # question this measure cannot answer -- see compute().
        self.block_sizes = block_sizes
        self.stride = stride

    def compute(self) -> Dict[str, Any]:
        # Imported here rather than at module scope: description_lengths reaches
        # into a sibling package on first use, and this module is imported by
        # scripts that must stay import-safe (AUDIT04 P2).
        #
        # The repo root is put on sys.path EXPLICITLY rather than relying on
        # `from src...` resolving. A bare `from src.description_lengths import`
        # works under pytest, because the root conftest.py puts the root on
        # sys.path -- and fails everywhere else. It failed in exactly one place:
        # TSK-NATURE-LEV3-SETUP-002 is a Wolfram test that shells out to Python
        # through BioBridgeV2, where no conftest runs, and the whole MUnit suite
        # went red with `ModuleNotFoundError: No module named 'src'`. The pure
        # tier was 11/11 green throughout; only the pre-push Wolfram tier saw it.
        import sys as _sys
        from pathlib import Path as _Path
        _root = str(_Path(__file__).resolve().parents[2])
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from src.description_lengths import bdm_2d, row_run_index_set_length

        bits = float(row_run_index_set_length(self.cm))

        # AUDIT04-F: BOTH comparison measures are reported, never combined.
        #
        # The author's directive of 2026-09-07 names two measures -- the
        # index-set program length and BDM -- and decision #96 forbids folding
        # two measures into one number with a selector bit. So they travel side
        # by side under their own names and every consumer sees both.
        #
        # This is not decoration. Measured 2026-09-07 at n = 16, structured
        # matrix against 20 random matrices of IDENTICAL edge count, the
        # index-set length calls a perfect checkerboard 1050.5 bits against
        # 563.9 for random, and column stripes 1050.5 against 568.4 -- it ranks
        # both periodic objects as roughly twice as complex as noise. BDM gets
        # both right (34.3 vs 489.9; 34.2 vs 485.2). The cause is structural
        # rather than a tuning error: the index-set code is a RUN-LENGTH code
        # over each row, and an alternating row costs n/2 runs, its maximum.
        # On the families that matter here the ordering is the other way round
        # -- on a 12-node chain against 200 random graphs with 11 edges, the
        # index-set length calls random simpler in 14/200 and BDM in 0/200 --
        # so neither measure is dropped and neither is trusted alone.
        #
        # bdm_2d refuses below its 4x4 partition floor rather than returning a
        # silent zero, and that refusal is surfaced as None with its reason,
        # because a network too small to measure must not read as "0 bits".
        bdm: float | None
        bdm_note = None
        if self.n < 4:
            bdm = None
            bdm_note = (f"BDM undefined for n={self.n}: pybdm's 2-D partition is "
                        f"4x4 and refuses smaller input. Not zero, unmeasured.")
        else:
            bdm = float(bdm_2d(self.cm, below_floor="raise"))

        return {
            # Retained key. It carries the index-set length, which is what the
            # thirteen existing callers and the stored artefacts expect to find
            # under this name.
            "dv2": bits,
            "index_set_bits": bits,
            "bdm": bdm,
            # AUDIT04-H2.5: the measure key is "index_set_program_length" for
            # backward compatibility with stored artefacts, but the QUANTITY
            # being returned is Variant A (row-run index-set length). The
            # degree-preserving invariance property belongs to Variant E
            # (D_schema), which appears in neither reported comparison measure
            # and is not what this encoder returns. Going forward the key
            # string is corrected in tandem with the `results/bio/null_stats.json`
            # regeneration; see GOVERNANCE/DESCRIPTION_LENGTHS.md §1b.
            "measure": "index_set_program_length",
            "measure_variant": "A",
            "measures": ("index_set_program_length", "bdm"),
            "n": self.n,
            "detail": {
                "note": "D_v2 retired 2026-09-07; `dv2` and `index_set_bits` are "
                        "Variant A (row-run index-set length) in bits, owned by "
                        "src/description_lengths.py. `bdm` is the second "
                        "comparison measure and is reported, never combined. "
                        "Variant E (D_schema) is the declared primary "
                        "mechanism-side measure and is NOT what this returns.",
                "bdm_note": bdm_note,
            },
            "blocks": None,
        }


def scaling_exponent_unavailable(*_args, **_kwargs):
    """The block-size sweep D(b) ~ b^alpha does not survive the change.

    ComplexityScaler.compute_scaling_exponent varied `block_sizes` and fitted a
    power law to the resulting D values. That question is meaningful only for a
    BLOCK-DECOMPOSED measure; a program length has no block size, so every point
    in the sweep would now return the same number and the fitted slope would be
    0.0 for every network.

    Refusing is the AUDIT02/P1 rule: a silent 0.0 is indistinguishable from a
    real measurement of zero scaling. If a scale-dependent algorithmic measure
    is wanted, BDM is already block-decomposed and is the natural owner.
    """
    raise NotImplementedError(
        "D(b) ~ b^alpha was a property of the retired Shannon block encoder. "
        "A program length has no block size, so this sweep would return slope "
        "0.0 for every network. Use BDM if a block-decomposed measure is needed."
    )
