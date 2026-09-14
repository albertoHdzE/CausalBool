"""adapters -- the only place that imports from the root CausalBool modules.

This module is the single import surface for everything the root owns.
If a future change requires touching the root, the import should be added
here and a thin wrapper exposed; the rest of the doppel-challenge package
imports the wrapper, never the root directly.

The root modules in use are:

  * ``causalbool`` (Network, repertoire, step, apply_gate, truth_table,
    node_output_column, input_vector, evolve_network)
    -- /index-deconvolution/src/causalbool.py
  * ``reprogramming`` (num_attractors, image_size, knockout)
    -- /index-deconvolution/src/reprogramming.py
  * ``deconvolution`` (essential_variables, reduce_column, identify_gate,
    minimal_dnf, deconvolve, verify_forward)
    -- /index-deconvolution/src/deconvolution.py
  * ``description_lengths`` (schema_normal_form_length, graph_gate_index_length)
    -- /src/description_lengths.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Add the root source trees to sys.path exactly once.  The doppel-challenge
# package is a sub-tree of the CausalBool repository, so the two
# index-deconvolution/src and src trees are siblings of the
# doppel-challenge/src tree, reachable by walking up three levels.
_IDX_DECONV_SRC = _REPO_ROOT / "index-deconvolution" / "src"
_CAUSALBOOL_SRC = _REPO_ROOT / "src"
for _p in (str(_IDX_DECONV_SRC), str(_CAUSALBOOL_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# --- forward CausalBool -----------------------------------------------------

from causalbool import (  # type: ignore
    Network,
    apply_gate,
    truth_table,
    node_output_column,
    input_vector,
    step,
    evolve_network,
    repertoire,
    GATE_TYPES,
    EXTENSION_GATE_TYPES,
    ALL_GATE_TYPES,
)

# --- attractor enumeration --------------------------------------------------

from reprogramming import (  # type: ignore
    num_attractors,
    image_size,
    knockout,
    spectrum,
    relative_reprogrammability,
)

# --- deconvolution ----------------------------------------------------------

from deconvolution import (  # type: ignore
    essential_variables,
    reduce_column,
    minimal_dnf,
    identify_gate,
    deconvolve,
    deconvolve_column,
    verify_forward,
    verify,
    NodeReconstruction,
    GateMatch,
)

# --- description lengths (algorithmic complexity) ---------------------------

from description_lengths import (  # type: ignore
    schema_normal_form_length,
    graph_gate_index_length,
    node_description_cost,
    row_run_index_set_length,
    bdm_2d,
)


__all__ = [
    "Network",
    "apply_gate",
    "truth_table",
    "node_output_column",
    "input_vector",
    "step",
    "evolve_network",
    "repertoire",
    "GATE_TYPES",
    "EXTENSION_GATE_TYPES",
    "ALL_GATE_TYPES",
    "num_attractors",
    "image_size",
    "knockout",
    "spectrum",
    "relative_reprogrammability",
    "essential_variables",
    "reduce_column",
    "minimal_dnf",
    "identify_gate",
    "deconvolve",
    "deconvolve_column",
    "verify_forward",
    "verify",
    "NodeReconstruction",
    "GateMatch",
    "schema_normal_form_length",
    "graph_gate_index_length",
    "node_description_cost",
    "row_run_index_set_length",
    "bdm_2d",
]
