"""catalogue_analysis -- rank and compare perturbations in a validated catalogue."""
from __future__ import annotations

import os
from typing import Any

from .io import read_jsonl, write_json


def _top_rows(rows: list[dict[str, Any]], key: str, n: int = 5) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: (r[key], -r["perturbation_index"]), reverse=True)
    out: list[dict[str, Any]] = []
    for row in ordered[:n]:
        out.append(
            {
                "perturbation_index": row["perturbation_index"],
                "graph_distance": row["graph_distance"],
                "metric": key,
                "value": row[key],
                "ell": row["ell"],
                "D_KL_nats": row["D_KL_nats"],
                "support_jaccard": row["support_jaccard"],
                "NCD": row["NCD"],
                "n_attractors": row["n_attractors"],
                "attractor_sizes": row["attractor_sizes"],
            }
        )
    return out


def analyse_joint_catalogue(
    joint_path: os.PathLike[str],
    *,
    out_path: os.PathLike[str] | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """Analyse a validated joint catalogue and rank perturbations by key metrics."""
    rows = list(read_jsonl(joint_path))
    if not rows:
        raise ValueError("joint catalogue is empty")

    dkl_top = _top_rows(rows, "D_KL_nats", n=top_n)
    jaccard_top = _top_rows(rows, "support_jaccard", n=top_n)
    loss_top = _top_rows(rows, "ell", n=top_n)
    ncd_top = _top_rows(rows, "NCD", n=top_n)

    summary = {
        "n_rows": len(rows),
        "top_by_D_KL_nats": dkl_top,
        "top_by_support_jaccard": jaccard_top,
        "top_by_ell": loss_top,
        "top_by_NCD": ncd_top,
        "leader_overlap": {
            "D_KL_vs_support_jaccard": dkl_top[0]["perturbation_index"] == jaccard_top[0]["perturbation_index"],
            "D_KL_vs_ell": dkl_top[0]["perturbation_index"] == loss_top[0]["perturbation_index"],
            "D_KL_vs_NCD": dkl_top[0]["perturbation_index"] == ncd_top[0]["perturbation_index"],
            "support_jaccard_vs_ell": jaccard_top[0]["perturbation_index"] == loss_top[0]["perturbation_index"],
            "support_jaccard_vs_NCD": jaccard_top[0]["perturbation_index"] == ncd_top[0]["perturbation_index"],
            "ell_vs_NCD": loss_top[0]["perturbation_index"] == ncd_top[0]["perturbation_index"],
        },
    }

    if out_path is not None:
        write_json(out_path, summary)
    return summary
