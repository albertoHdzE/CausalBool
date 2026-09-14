"""driver -- end-to-end stage runners for the doppel-challenge laboratory.

Stage 1 (this file, run_stage1_two_nets) exercises the entire pipeline
on two hand-picked base networks at N=10, k=1, with a single-edge
perturbation as the focus.  It writes the configuration record, the
base-network records, the catalogue rows (one per perturbation), the
per-stage statistics rows, the joint rows, and a sweep aggregate.

The driver is intentionally explicit so the intermediate results can be
inspected step by step.  Every stage returns its records in memory; the
caller chooses to print or write.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .adapters import Network
from .attractors import enumerate_attractors
from .compression import encode_repertoire, ncd as ncd_pair
from .io import ensure_dir, write_json, write_jsonl
from .perturbations import ball, graph_distance, index as perturb_index
from .records import make_envelope, seal
from .repertoire import compute_repertoire
from .stats import expected_loss, in_catalogue, jaccard, kl


# ---------------------------------------------------------------------------
# Stage 1 -- two N=10 networks, k=1, full protocol stats
# ---------------------------------------------------------------------------


def _make_config_record(n: int, k: int, loss_id: str,
                        loss_params: dict[str, Any],
                        config_id: str) -> dict[str, Any]:
    rec = make_envelope("configuration", config_id=config_id, sweep_id=None)
    rec.update({
        "N": n,
        "k": k,
        "library_id": "L0",
        "library_gates": ["AND", "OR", "MAJORITY", "XOR", "NOT"],
        "library_max_arity": 3,
        "graph_constraint": {
            "min_in_degree": 0,
            "max_in_degree": 3,
            "min_cycle_count": 1,
            "min_high_in_degree_fraction": 0.3,
        },
        "loss_id": loss_id,
        "loss_params": loss_params,
        "C_policy": "MEDIAN_KL_AT_K1",
        "sampling": {"mode": "EXHAUSTIVE", "M": None, "seed": None},
        "budget": {"wallclock_seconds": 3600, "max_memory_mb": 4096},
    })
    return seal(rec)


def _make_base_record(A: list[list[int]], theta: list[str],
                      params: list[dict], config_id: str,
                      label: str) -> dict[str, Any]:
    n = len(A)
    net = Network(n=n, C=A, gates=theta, params=params)
    rep = compute_repertoire(net)
    att = enumerate_attractors(net)
    cab = encode_repertoire(rep, include_schema=True)
    rec = make_envelope("base_network", config_id=config_id, sweep_id=None)
    rec.update({
        "label": label,
        "A": A,
        "theta": theta,
        "params": params,
        "N": n,
        "n_attractors": att["n_attractors"],
        "attractor_sizes": att["attractor_sizes"],
        "n_attractor_states": len(att["support"]),
        "repertoire": {
            "rows": rep["rows"],
            "cols": rep["cols"],
            "matrix_lsb_first": rep["matrix_lsb_first"],
            "support": rep["support"],
            "counts": rep["counts"],
            "probs": rep["probs"],
        },
        "compressed": {
            "decimal_bits": cab["decimal_bits"],
            "summandos_bits": cab["summandos_bits"],
            "L_CB_bits": cab["L_CB_bits"],
            "schema_length": cab["schema_length"],
        },
    })
    # Verify that the repertoire's support equals the attractor support.
    if sorted(rep["support"]) != att["support"]:
        raise AssertionError(
            f"repertoire support != attractor support for {label}"
        )
    return seal(rec)


def _make_catalogue_row(A: list[list[int]], theta: list[str],
                        params: list[dict], A0: list[list[int]],
                        graph_dist: int, pert_index: int,
                        config_id: str) -> dict[str, Any]:
    n = len(A)
    net = Network(n=n, C=A, gates=theta, params=params)
    rep = compute_repertoire(net)
    att = enumerate_attractors(net)
    cab = encode_repertoire(rep, include_schema=False)
    rec = make_envelope("catalogue_row", config_id=config_id, sweep_id=None)
    rec.update({
        "A": A,
        "graph_distance": graph_dist,
        "perturbation_kind": "EDGE_FLIP",
        "perturbation_index": pert_index,
        "repertoire": {
            "rows": rep["rows"],
            "cols": rep["cols"],
            "matrix_lsb_first": rep["matrix_lsb_first"],
            "support": rep["support"],
            "counts": rep["counts"],
            "probs": rep["probs"],
        },
        "n_attractors": att["n_attractors"],
        "attractor_sizes": att["attractor_sizes"],
        "compressed": {
            "decimal_bits": cab["decimal_bits"],
            "summandos_bits": cab["summandos_bits"],
            "L_CB_bits": cab["L_CB_bits"],
            "schema_length": cab["schema_length"],
        },
    })
    return seal(rec)


def _make_stat_rows(cat_row: dict[str, Any],
                    base_rep: dict[str, Any],
                    config_id: str,
                    loss_id: str,
                    loss_params: dict[str, Any]
                    ) -> tuple[dict[str, Any], dict[str, Any],
                               dict[str, Any], dict[str, Any]]:
    A = cat_row["A"]
    rep = {
        "rows": cat_row["repertoire"]["rows"],
        "cols": cat_row["repertoire"]["cols"],
        "matrix_lsb_first": True,
        "support": cat_row["repertoire"]["support"],
        "counts": cat_row["repertoire"]["counts"],
        "probs": cat_row["repertoire"]["probs"],
    }
    # KL
    k = kl(rep, base_rep)
    kl_row = make_envelope("kl_row", config_id=config_id, sweep_id=None)
    kl_row.update({
        "A": A,
        "graph_distance": cat_row["graph_distance"],
        "perturbation_kind": cat_row["perturbation_kind"],
        "perturbation_index": cat_row["perturbation_index"],
        "D_KL_nats": k["D_KL_nats"],
        "support_disjoint": k["support_disjoint"],
        "support_intersection_size": k["support_intersection_size"],
    })
    seal(kl_row)
    # Jaccard
    j = jaccard(rep, base_rep)
    support_row = make_envelope("support_row", config_id=config_id, sweep_id=None)
    support_row.update({
        "A": A,
        "graph_distance": cat_row["graph_distance"],
        "perturbation_kind": cat_row["perturbation_kind"],
        "perturbation_index": cat_row["perturbation_index"],
        "support_jaccard": j["support_jaccard"],
        "support_size_A": j["support_size_A"],
        "support_size_0": j["support_size_0"],
        "support_intersection": j["support_intersection"],
    })
    seal(support_row)
    # Expected loss
    ell = expected_loss(rep, loss_id, loss_params, q_dict=base_rep)
    loss_row = make_envelope("loss_row", config_id=config_id, sweep_id=None)
    loss_row.update({
        "A": A,
        "graph_distance": cat_row["graph_distance"],
        "perturbation_kind": cat_row["perturbation_kind"],
        "perturbation_index": cat_row["perturbation_index"],
        "ell": ell,
        "loss_id": loss_id,
        "loss_params": loss_params,
    })
    seal(loss_row)
    # NCD
    n = ncd_pair(rep, base_rep)
    ncd_row = make_envelope("ncd_row", config_id=config_id, sweep_id=None)
    ncd_row.update({
        "A": A,
        "graph_distance": cat_row["graph_distance"],
        "perturbation_kind": cat_row["perturbation_kind"],
        "perturbation_index": cat_row["perturbation_index"],
        "L_CB_A": n["L_CB_A"],
        "L_CB_0": n["L_CB_0"],
        "L_CB_concat": n["L_CB_concat"],
        "NCD": n["NCD"],
    })
    seal(ncd_row)
    return loss_row, kl_row, support_row, ncd_row


def _make_joint_row(cat_row: dict[str, Any], loss_row: dict[str, Any],
                    kl_row: dict[str, Any], support_row: dict[str, Any],
                    ncd_row: dict[str, Any], config_id: str
                    ) -> dict[str, Any]:
    rec = make_envelope("joint_row", config_id=config_id, sweep_id=None)
    rec.update({
        "A": cat_row["A"],
        "graph_distance": cat_row["graph_distance"],
        "perturbation_kind": cat_row["perturbation_kind"],
        "perturbation_index": cat_row["perturbation_index"],
        "ell": loss_row["ell"],
        "D_KL_nats": kl_row["D_KL_nats"],
        "support_disjoint": kl_row["support_disjoint"],
        "support_jaccard": support_row["support_jaccard"],
        "L_CB_A": ncd_row["L_CB_A"],
        "L_CB_0": ncd_row["L_CB_0"],
        "L_CB_concat": ncd_row["L_CB_concat"],
        "NCD": ncd_row["NCD"],
        "n_attractors": cat_row["n_attractors"],
        "attractor_sizes": cat_row["attractor_sizes"],
    })
    return seal(rec)


# --- two hand-picked base networks at N=10 ----------------------------------


def _net_A() -> tuple[list[list[int]], list[str], list[dict]]:
    """A mixed network: AND/OR/MAJ/XOR/NOT mix, with cycles."""
    A = [
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],  # node 0
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # node 1
        [0, 1, 0, 0, 1, 0, 0, 0, 0, 0],  # node 2
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],  # node 3
        [0, 0, 0, 1, 0, 1, 0, 0, 0, 0],  # node 4
        [0, 0, 0, 0, 0, 0, 1, 1, 0, 0],  # node 5
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],  # node 6
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],  # node 7
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],  # node 8
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],  # node 9
    ]
    theta = [
        "AND", "OR", "MAJORITY", "XOR", "AND",
        "OR", "MAJORITY", "XOR", "AND", "OR",
    ]
    params: list[dict] = [{} for _ in range(10)]
    return A, theta, params


def _net_B() -> tuple[list[list[int]], list[str], list[dict]]:
    """A different mixed network: lower connectivity, more NOTs."""
    A = [
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    theta = ["OR", "AND", "OR", "AND", "OR", "AND", "OR", "AND", "OR", "XOR"]
    params: list[dict] = [{} for _ in range(10)]
    return A, theta, params


def _pick_target(base: dict[str, Any], seed: int) -> list[int]:
    """Pick a single target state from the support using a deterministic rule."""
    support = base["repertoire"]["support"]
    return [support[seed % len(support)]]


def _legacy_run_stage1_two_nets(out_dir: os.PathLike) -> dict[str, Any]:
    """Run Stage 1: two N=10 networks, k=1, full stats.  Returns a summary.

    The function writes records under ``out_dir/<label>/...`` and returns
    a JSON-serialisable summary that names every artefact and every
    headline number, so a caller can inspect the result without re-reading
    the JSONL.
    """
    root = Path(out_dir)
    summary: dict[str, Any] = {"stage": "1_two_nets_N10_k1", "nets": []}
    n = 10
    k = 1
    nets = [("A", _net_A()), ("B", _net_B())]
    for label, (A, theta, params) in nets:
        t0 = time.time()
        cat_dir = root / label
        ensure_dir(cat_dir / "base")
        # Pick a target state deterministically.
        net0 = Network(n=n, C=A, gates=theta, params=params)
        base_rep_preview = compute_repertoire(net0)
        target = base_rep_preview["support"][0]
        loss_params = {"targets": [target]}
        config_id = f"stage1-{label}-{int(time.time() * 1000)}"
        # Configuration record
        config = _make_config_record(n, k, "L_SINGLE_TARGET", loss_params,
                                     config_id)
        write_json(cat_dir / "config.json", config)
        # Base network
        base = _make_base_record(A, theta, params, config_id, label)
        write_json(cat_dir / "base" / "base.json", base)
        # Catalogue at k=1
        pert_mats = ball(A, k, "EDGE_FLIP")
        cat_rows: list[dict[str, Any]] = []
        for mat in pert_mats:
            gd = graph_distance(A, mat)
            pidx = perturb_index(A, mat, "EDGE_FLIP")
            cat_rows.append(_make_catalogue_row(
                mat, theta, params, A, gd, pidx, config_id
            ))
        write_jsonl(cat_dir / "catalogue.jsonl", cat_rows)
        # Stats rows
        loss_rows: list[dict[str, Any]] = []
        kl_rows: list[dict[str, Any]] = []
        support_rows: list[dict[str, Any]] = []
        ncd_rows: list[dict[str, Any]] = []
        joint_rows: list[dict[str, Any]] = []
        base_rep = {
            "rows": base["repertoire"]["rows"],
            "cols": base["repertoire"]["cols"],
            "matrix_lsb_first": True,
            "support": base["repertoire"]["support"],
            "counts": base["repertoire"]["counts"],
            "probs": base["repertoire"]["probs"],
        }
        for crow in cat_rows:
            lr, kr, sr, nr = _make_stat_rows(
                crow, base_rep, config_id, "L_SINGLE_TARGET", loss_params
            )
            loss_rows.append(lr)
            kl_rows.append(kr)
            support_rows.append(sr)
            ncd_rows.append(nr)
            joint_rows.append(_make_joint_row(crow, lr, kr, sr, nr, config_id))
        write_jsonl(cat_dir / "loss.jsonl", loss_rows)
        write_jsonl(cat_dir / "kl.jsonl", kl_rows)
        write_jsonl(cat_dir / "support.jsonl", support_rows)
        write_jsonl(cat_dir / "ncd.jsonl", ncd_rows)
        write_jsonl(cat_dir / "joint.jsonl", joint_rows)
        # Headline numbers
        D_KL_defined = [r["D_KL_nats"] for r in kl_rows
                        if r["D_KL_nats"] is not None]
        D_KL_mean = (sum(D_KL_defined) / len(D_KL_defined)
                     if D_KL_defined else None)
        disjoint = sum(1 for r in kl_rows if r["support_disjoint"])
        max_ell = max((r["ell"] for r in loss_rows), default=0.0)
        # Optimal attacker = catalogue element with highest ell whose
        # D_KL is defined (so the loss is real, not nan).
        opt = None
        for r in joint_rows:
            if r["D_KL_nats"] is not None and (opt is None or r["ell"] > opt["ell"]):
                opt = r
        # Detector rule -- catalogue membership: every catalogue row
        # is in the catalogue by construction; the interesting test
        # is whether the *base* of net B is in net A's catalogue.
        summary_entry = {
            "label": label,
            "config_id": config_id,
            "n_attractors": base["n_attractors"],
            "n_attractor_states": base["n_attractor_states"],
            "support_size": len(base["repertoire"]["support"]),
            "L_CB_bits": base["compressed"]["L_CB_bits"],
            "schema_length": base["compressed"]["schema_length"],
            "catalogue_size": len(cat_rows),
            "D_KL_mean_over_defined": D_KL_mean,
            "support_disjoint_count": disjoint,
            "max_ell": max_ell,
            "optimal_attacker": {
                "graph_distance": opt["graph_distance"] if opt else None,
                "perturbation_index": opt["perturbation_index"] if opt else None,
                "ell": opt["ell"] if opt else None,
                "D_KL_nats": opt["D_KL_nats"] if opt else None,
            },
            "runtime_seconds": time.time() - t0,
            "artefacts": {
                "config": str(cat_dir / "config.json"),
                "base": str(cat_dir / "base" / "base.json"),
                "catalogue": str(cat_dir / "catalogue.jsonl"),
                "loss": str(cat_dir / "loss.jsonl"),
                "kl": str(cat_dir / "kl.jsonl"),
                "support": str(cat_dir / "support.jsonl"),
                "ncd": str(cat_dir / "ncd.jsonl"),
                "joint": str(cat_dir / "joint.jsonl"),
            },
        }
        summary["nets"].append(summary_entry)
    # Cross-check: is each base in the other's catalogue?
    a_base = summary["nets"][0]
    b_base = summary["nets"][1]
    cat_a = list(_iter_catalogue_reps(Path(a_base["artefacts"]["catalogue"])))
    cat_b = list(_iter_catalogue_reps(Path(b_base["artefacts"]["catalogue"])))
    # We need the base repertoire for net A and net B; read the
    # base.json files.
    a_base_json = _read_base_rep(Path(a_base["artefacts"]["base"]))
    b_base_json = _read_base_rep(Path(b_base["artefacts"]["base"]))
    summary["cross_check"] = {
        "b_base_in_a_catalogue": in_catalogue(b_base_json, cat_a, tol=0.0),
        "a_base_in_b_catalogue": in_catalogue(a_base_json, cat_b, tol=0.0),
    }
    summary_path = root / "summary.json"
    write_json(summary_path, summary)
    return summary


def _iter_catalogue_reps(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            r = obj["repertoire"]
            yield {
                "rows": r["rows"],
                "cols": r["cols"],
                "matrix_lsb_first": True,
                "support": r["support"],
                "counts": r["counts"],
                "probs": r["probs"],
            }


def _read_base_rep(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text())
    r = obj["repertoire"]
    return {
        "rows": r["rows"],
        "cols": r["cols"],
        "matrix_lsb_first": True,
        "support": r["support"],
        "counts": r["counts"],
        "probs": r["probs"],
    }


# The historical implementation remains addressable only for reproducing old
# pilot layouts. New callers get the durable, standard-KL execution path.
from .execution import run_catalogue


def run_stage1_two_nets(out_dir: os.PathLike) -> dict[str, Any]:
    """Run the repaired two-network smoke study through the canonical runner."""
    root = Path(out_dir)
    runs = []
    for label, (A, gates, params) in (("A", _net_A()), ("B", _net_B())):
        base = compute_repertoire(Network(len(A), A, gates, params))
        target = base["support"][0]
        summary = run_catalogue(A, gates, params=params, out_dir=root / label,
                                network_label=label, kind="EDGE_ADD", k=1,
                                loss_params={"targets": [target]}, C=0.25,
                                allow_self_loops=False, max_indegree=3)
        runs.append(summary)
    summary = {"stage": "repaired_two_nets", "nets": runs,
               "historical_pilots": "exploratory_preserved"}
    (root / "summary.json").parent.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary
