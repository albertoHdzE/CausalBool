"""imp-prices: causality in time series by index-set deconvolution.

An index-set mirror of the Alvi (2018) crude oil forecasting pipeline, built on
the GWP3 partial replication. See ``PROTOCOL_causal_timeseries.md`` for the
pre-registered design and ``FINDINGS.md`` for the ledger of results.
"""

from .config import LABELS, N_STATES, SERIES, TARGET
from .data import Split, load_and_split, load_panel, split_summary
from .discretise import RegimeDiscretiser, regime_economics

__all__ = [
    "LABELS", "N_STATES", "SERIES", "TARGET",
    "Split", "load_and_split", "load_panel", "split_summary",
    "RegimeDiscretiser", "regime_economics",
]
