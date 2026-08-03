"""Replication of Zenil, Kiani, Zea and Tegner (2018),
"Algorithmic Causal Deconvolution of Intertwined Data and Networks by Generating
Mechanism", arXiv:1802.09904v8.

Two layers:

* a faithful transcription of the paper's own algorithms and estimators
  (:mod:`complexity`, :mod:`ca`, :mod:`footprint`, :mod:`graphs`,
  :mod:`deconvolution`, :mod:`strings`, :mod:`experiments`);
* a mirror of the same results using the CausalBool index-set causal calculus
  developed in the root of this project (:mod:`causalbool_mirror`).
"""

from __future__ import annotations

__version__ = "0.1.0"

from . import (  # noqa: F401
    ca,
    causal_models,
    causalbool_mirror,
    complexity,
    deconvolution,
    experiments,
    fastbdm,
    figures,
    footprint,
    graph_mechanism,
    graphs,
    measure,
    official,
    strings,
)

__all__ = [
    "ca",
    "causal_models",
    "causalbool_mirror",
    "complexity",
    "deconvolution",
    "experiments",
    "fastbdm",
    "figures",
    "footprint",
    "graph_mechanism",
    "graphs",
    "measure",
    "official",
    "strings",
    "__version__",
]
