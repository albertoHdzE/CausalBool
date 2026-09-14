"""doppel_challenge

Adversarial-repertoire laboratory for the doppel-challenge project.

The package is a thin adapter layer over the root CausalBool code:
``causalbool``, ``reprogramming``, ``deconvolution`` from
``index-deconvolution/src/``, and ``description_lengths`` from ``src/``.
No root module is modified; every dependency is imported, never patched.
New functionality specific to the laboratory is implemented here under
``doppel_challenge/`` only.
"""
__version__ = "0.1.0"

from .repertoire_program import (
    RepertoireProgram, ProgramLimits, ResourceLimitError,
    compile_repertoire_program, compile_schema_program, evaluate_program,
    iter_output_rows, serialize_program, deserialize_program, export_output_schemata,
    program_metadata,
)

from .serial_validation import (
    run_guarded_experiment_suite,
    run_validation_series,
    sample_network_10_a,
    sample_network_10_b,
)
from .boundary_sweep import sweep_single_edge_boundary
from .add_edge_catalogue import run_add_edge_catalogue
from .catalogue_analysis import analyse_joint_catalogue
from .pilot_runner import (
    make_hub_network,
    make_mixed_ring_network,
    make_modular_network,
    make_network,
    make_sparse_random_network,
    run_add_edge_pilot,
)
from .execution import run_catalogue
from .estimator import estimate_repertoire
from .scaling import make_scale_benchmark_cases, run_scale_benchmark, run_scale_pilot
from .full_behaviour_scaling import (
    make_full_behaviour_benchmark_cases,
    run_full_behaviour_scaling_benchmark,
    validate_full_behaviour_scaling_benchmark,
)
from .adapters import Network
from .study import run_prespecified_study
from .validation import compare_long_run_owners, validate_catalogue_manifest, validate_repertoire
from .release import run_release_gate
from .full_behaviour import (
    compute_full_behaviour_encoding,
    decode_full_behaviour,
    one_step_statistics_from_encoding,
    unfold_decimal_sumandos,
    unfold_full_behaviour_encoding,
)
from .whole_repertoire import compute_whole_repertoire_encoding
from .whole_repertoire_scaling import (
    run_whole_repertoire_scaling_benchmark,
    validate_whole_repertoire_scaling_benchmark,
)

__all__ = [
    "RepertoireProgram", "ProgramLimits", "ResourceLimitError",
    "compile_repertoire_program", "compile_schema_program", "evaluate_program",
    "iter_output_rows", "serialize_program", "deserialize_program", "export_output_schemata",
    "program_metadata",
    "__version__",
    "Network",
    "analyse_joint_catalogue",
    "make_hub_network",
    "make_mixed_ring_network",
    "make_modular_network",
    "make_network",
    "make_sparse_random_network",
    "run_add_edge_catalogue",
    "run_add_edge_pilot",
    "run_catalogue",
    "estimate_repertoire",
    "run_scale_benchmark",
    "run_scale_pilot",
    "make_scale_benchmark_cases",
    "make_full_behaviour_benchmark_cases",
    "run_full_behaviour_scaling_benchmark",
    "validate_full_behaviour_scaling_benchmark",
    "run_prespecified_study",
    "compare_long_run_owners",
    "validate_repertoire",
    "validate_catalogue_manifest",
    "run_release_gate",
    "run_guarded_experiment_suite",
    "run_validation_series",
    "sample_network_10_a",
    "sample_network_10_b",
    "sweep_single_edge_boundary",
    "compute_full_behaviour_encoding",
    "unfold_decimal_sumandos",
    "unfold_full_behaviour_encoding",
    "decode_full_behaviour",
    "one_step_statistics_from_encoding",
    "compute_whole_repertoire_encoding",
    "run_whole_repertoire_scaling_benchmark",
    "validate_whole_repertoire_scaling_benchmark",
]
