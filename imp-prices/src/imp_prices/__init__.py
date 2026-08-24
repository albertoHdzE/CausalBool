"""imp-prices: causality in time series by index-set deconvolution.

An index-set mirror of the Alvi (2018) crude oil forecasting pipeline, built on
the GWP3 partial replication. See ``PROTOCOL_causal_timeseries.md`` for the
pre-registered design and ``FINDINGS.md`` for the ledger of results.
"""

from .config import LABELS, N_STATES, SERIES, TARGET
from .data import Split, load_and_split, load_panel, split_summary

__all__ = [
    "LABELS", "N_STATES", "SERIES", "TARGET",
    "Split", "load_and_split", "load_panel", "split_summary",
    "RegimeDiscretiser", "regime_economics",
]


def __getattr__(name):
    """AUDIT01/T2.0: lazily import the HMM-backed module so the pivot/clock core
    is usable without hmmlearn (the eager import made every submodule fail
    collection in environments without it -- the phantom 'tests cannot run')."""
    if name in ("RegimeDiscretiser", "regime_economics"):
        from . import discretise
        return getattr(discretise, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
