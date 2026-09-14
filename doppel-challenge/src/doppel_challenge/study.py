"""Prespecified exact small-N study and its one-command reproduction entrypoint."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapters import Network
from .execution import run_catalogue
from .pilot_runner import make_network
from .repertoire import compute_repertoire
from .analysis import sensitivity_over_validated_study

PRESPECIFIED = {
    "schema_version": "2.0.0",
    "study_id": "exact_small_n6_v2",
    "observable": "basin_weighted_attractor_repertoire",
    "orientation": "A[target][source]",
    "N": [6],
    "families": ["ring", "sparse_random", "modular", "hub"],
    "seeds": [0, 1],
    "k": [1],
    "perturbation_kinds": ["EDGE_ADD", "EDGE_REMOVE"],
    "forbid_zero_indegree_nodes": True,
    "allow_self_loops": False,
    "max_indegree": 3,
    "C": 0.25,
    "loss": "L_SINGLE_TARGET",
    "target_selection": "support_sorted_index_seed_mod_cardinality",
    "replication_unit": "base_network",
    "perturbations_clustered_within_base": True,
    "approximation": "none_exact_full_state_space",
    "sensitivity_losses": ["L_SINGLE_TARGET", "L_LINEAR"],
    "sensitivity_KL_budgets": [0.0, 0.1, 0.25, 0.5],
    "historical_artifacts_in_denominator": False,
}


def run_prespecified_study(out_dir: str | Path, *, resume: bool = True) -> dict[str, Any]:
    """Run the declared N=4 topology study, retaining exclusions/failures."""
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "prespecification.json").write_text(json.dumps(PRESPECIFIED, indent=2, sort_keys=True) + "\n")
    runs: list[dict[str, Any]] = []
    for family in PRESPECIFIED["families"]:
        for seed in PRESPECIFIED["seeds"]:
            A, gates = make_network(family, 6, seed=seed)
            base = compute_repertoire(Network(6, A, gates, [{} for _ in gates]))
            target = base["support"][seed % len(base["support"])]
            for kind in PRESPECIFIED["perturbation_kinds"]:
                label = f"{family}_n6_s{seed}/{kind.lower()}"
                summary = run_catalogue(
                    A, gates, out_dir=root / label, kind=kind, k=1, seed=seed,
                    forbid_zero_indegree_nodes=PRESPECIFIED["forbid_zero_indegree_nodes"],
                    max_indegree=PRESPECIFIED["max_indegree"],
                    allow_self_loops=PRESPECIFIED["allow_self_loops"],
                    loss_params={"targets": [target]}, C=PRESPECIFIED["C"], resume=resume,
                )
                summary.update({"family": family, "seed": seed, "target_state": target})
                runs.append(summary)
    result = {"prespecification": PRESPECIFIED, "n_runs": len(runs), "runs": runs,
              "all_cases_accepted": all(run["n_failures"] == 0 for run in runs)}
    result["sensitivity"] = sensitivity_over_validated_study(
        root, budgets=tuple(PRESPECIFIED["sensitivity_KL_budgets"]),
        out_path=root / "sensitivity.json")
    (root / "study_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
