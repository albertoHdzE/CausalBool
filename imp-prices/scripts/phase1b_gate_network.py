#!/usr/bin/env python
"""Phase 1b — B4 and B5 redone with the method as it actually is.

Phase 1 compared a parent set plus an arbitrary lookup table against a
conditional probability table. That is not the index-set method. This script
uses the real gate family, builds a whole network rather than one conditional,
and scores it algorithmically with BDM rather than by counting.

Design fixed in PROTOCOL section 1b before any run. All three binarisations are
reported whatever they show.

Run:
    .venv/bin/python scripts/phase1b_gate_network.py [--boot N] [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from imp_prices import RegimeDiscretiser, SERIES, load_and_split
from imp_prices.algorithmic import (bdm_bits, resolution_check, structure_axis,
                                    two_part_algorithmic)
from imp_prices.binarise import WIDTH, encode_frame, reachable_codes, round_trip_ok
from imp_prices.config import RESULTS
from imp_prices.controls import random_frame, rule110_frame
from imp_prices.gate_network import (connectivity_matrix, fit_network,
                                     gate_catalogue, parameter_array,
                                     truth_table_array)
from imp_prices.index_set import residual_bits

MAX_INDEGREE = 3


def banner(t, quiet):
    if not quiet:
        print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def score_network(frame, columns, quiet, label):
    """Fit both model classes over the same nodes, and score both ways."""
    gate_fits = fit_network(frame, columns, "gate", MAX_INDEGREE)
    cpt_fits = fit_network(frame, columns, "cpt", MAX_INDEGREE)

    C_gate = connectivity_matrix(gate_fits, columns)
    C_cpt = connectivity_matrix(cpt_fits, columns)

    alg_gate = two_part_algorithmic(C_gate, truth_table_array(gate_fits, MAX_INDEGREE),
                                    sum(f.data_bits for f in gate_fits))
    alg_cpt = two_part_algorithmic(C_cpt, parameter_array(cpt_fits, MAX_INDEGREE),
                                   sum(f.data_bits for f in cpt_fits))
    cnt_gate = sum(f.total for f in gate_fits)
    cnt_cpt = sum(f.total for f in cpt_fits)

    named = [f for f in gate_fits if f.gate not in ("LUT",)]
    out = dict(
        label=label, n_nodes=len(columns),
        algorithmic=dict(gate=alg_gate, cpt=alg_cpt,
                         gate_minus_cpt=round(alg_gate["total_bits"]
                                              - alg_cpt["total_bits"], 3),
                         gate_wins=bool(alg_gate["total_bits"] < alg_cpt["total_bits"])),
        counting=dict(gate=round(cnt_gate, 2), cpt=round(cnt_cpt, 2),
                      gate_minus_cpt=round(cnt_gate - cnt_cpt, 2),
                      gate_wins=bool(cnt_gate < cnt_cpt)),
        structure=structure_axis(C_gate, C_cpt, "gate", "cpt"),
        gates_named=len(named), gates_lut=len(gate_fits) - len(named),
        gate_counts={g: int(sum(1 for f in gate_fits if f.gate == g))
                     for g in sorted({f.gate for f in gate_fits})},
        total_errors=int(sum(f.n_errors for f in gate_fits)),
        total_bits_possible=int(sum(f.n for f in gate_fits)),
    )
    if not quiet:
        a, c = alg_gate, alg_cpt
        print(f"  {label}   ({len(columns)} binary nodes)")
        print(f"    ALGORITHMIC (BDM model + data)")
        print(f"      gate network  {a['total_bits']:9.2f} = struct {a['structure_bdm']:7.2f}"
              f" + tables {a['table_bdm']:7.2f} + data {a['data_bits']:8.2f}")
        print(f"      CPT network   {c['total_bits']:9.2f} = struct {c['structure_bdm']:7.2f}"
              f" + params {c['table_bdm']:7.2f} + data {c['data_bits']:8.2f}")
        print(f"      difference {out['algorithmic']['gate_minus_cpt']:+.2f} bits -> "
              f"{'GATE NETWORK WINS' if out['algorithmic']['gate_wins'] else 'CPT wins'}")
        print(f"    COUNTING  gate {cnt_gate:9.2f} | cpt {cnt_cpt:9.2f} | "
              f"{out['counting']['gate_minus_cpt']:+.2f} -> "
              f"{'gate wins' if out['counting']['gate_wins'] else 'cpt wins'}")
        print(f"    STRUCTURE AXIS (identical 14x14 shape) "
              f"gate BDM {out['structure']['bdm_gate']:.2f} ({out['structure']['edges_gate']} edges) | "
              f"cpt BDM {out['structure']['bdm_cpt']:.2f} ({out['structure']['edges_cpt']} edges)")
        print(f"    gates named {out['gates_named']}/{len(gate_fits)}; "
              f"{out['gate_counts']}")
        print(f"    map errors {out['total_errors']}/{out['total_bits_possible']} "
              f"= {100 * out['total_errors'] / out['total_bits_possible']:.1f}%")
    return out, gate_fits, cpt_fits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    out = {"config": dict(max_indegree=MAX_INDEGREE, n_boot=args.boot,
                          gate_catalogue={k: len(gate_catalogue(k)) for k in (1, 2, 3)})}

    # ---- controls ---------------------------------------------------------
    banner("CONTROLS (protocol 1b.4) — the verdict is void without these", args.quiet)
    out["resolution"] = {s: resolution_check((r, c))
                         for s, (r, c) in {"14x14": (14, 14), "14x8": (14, 8),
                                           "4x4": (4, 4)}.items()}
    if not args.quiet:
        for k, v in out["resolution"].items():
            print(f"  BDM resolution at {k}: separation {v['separation_sigma']:5.1f} sigma "
                  f"-> usable {v['usable']}")

    ca = rule110_frame(width=14, steps=400)
    out["control_rule110"], ca_fits, _ = score_network(
        ca, list(ca.columns), args.quiet, "rule 110 (deterministic network)")
    rnd = pd.DataFrame(
        np.random.default_rng(42).integers(0, 2, size=(400, 14)),
        columns=[f"c{i}" for i in range(14)])
    out["control_random"], rnd_fits, _ = score_network(
        rnd, list(rnd.columns), args.quiet, "random binary (must not compress)")

    # Falsifiability of the gate class (rule R4): a random Boolean function must
    # cost materially more to describe than a real gate.
    rng = np.random.default_rng(7)
    named_tables = {t for _, _, t in gate_catalogue(3)}
    random_tables = [tuple(rng.integers(0, 2, 8)) for _ in range(2000)]
    hit = sum(1 for t in random_tables if t in named_tables)
    out["gate_class_falsifiability"] = dict(
        arity=3, n_named_functions=len(named_tables), n_possible=256,
        random_draws=len(random_tables), matched_a_named_gate=hit,
        expected_fraction=round(len(named_tables) / 256, 4),
        observed_fraction=round(hit / len(random_tables), 4))
    if not args.quiet:
        f = out["gate_class_falsifiability"]
        print(f"  gate class covers {f['n_named_functions']}/256 arity-3 functions "
              f"({100 * f['expected_fraction']:.1f}%); random draws matched "
              f"{100 * f['observed_fraction']:.1f}% -> the class does NOT fit anything")

    # ---- the panel, all three binarisations -------------------------------
    split = load_and_split()
    fr = RegimeDiscretiser("gaussian").fit(split.train).transform(split.full)
    train = fr.reindex(split.train.index).dropna().astype(int)

    out["panel"] = {}
    for kind in ("thermometer", "binary", "onehot"):
        banner(f"THE PANEL — {kind} binarisation ({WIDTH[kind]} bits per series)",
               args.quiet)
        assert round_trip_ok(train, kind), kind
        B = encode_frame(train, kind)
        res, gate_fits, cpt_fits = score_network(B, list(B.columns), args.quiet,
                                                 f"panel / {kind}")
        res["codes"] = reachable_codes(kind)
        res["forecast_nodes"] = [
            dict(node=f.node, parents="+".join(f.parents), gate=f.gate,
                 errors=f.n_errors, n=f.n)
            for f in gate_fits if f.node.startswith("WTI_Spot")]
        out["panel"][kind] = res
        if not args.quiet:
            print("    the two target nodes:")
            for r in res["forecast_nodes"]:
                print(f"      {r['node']:<24s} <- {r['parents']:<44s} "
                      f"{r['gate']:<12s} errors {r['errors']}/{r['n']}")

    # ---- verdict ----------------------------------------------------------
    banner("VERDICT (ledger B4, redone)", args.quiet)
    ctrl_ok = (out["control_rule110"]["algorithmic"]["gate_wins"]
               and out["resolution"]["14x14"]["usable"])
    out["controls_pass"] = bool(ctrl_ok)
    prim = out["panel"]["thermometer"]
    out["b4b_gate_wins_algorithmic"] = bool(prim["algorithmic"]["gate_wins"])
    out["b4b_gate_wins_counting"] = bool(prim["counting"]["gate_wins"])
    out["b4b_instruments_agree"] = bool(
        prim["algorithmic"]["gate_wins"] == prim["counting"]["gate_wins"])
    out["b4b_all_binarisations"] = {
        k: dict(algorithmic=out["panel"][k]["algorithmic"]["gate_wins"],
                counting=out["panel"][k]["counting"]["gate_wins"])
        for k in out["panel"]}
    if not args.quiet:
        print(f"  controls pass                          : {out['controls_pass']}")
        print(f"  gate network wins, algorithmic (primary): {out['b4b_gate_wins_algorithmic']}")
        print(f"  gate network wins, counting             : {out['b4b_gate_wins_counting']}")
        print(f"  instruments agree                       : {out['b4b_instruments_agree']}")
        print(f"  across binarisations                    : {out['b4b_all_binarisations']}")

    out["content_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    out["provenance"] = dict(runtime_seconds=round(time.time() - t0, 1))
    if not args.quiet:
        print(f"  content sha256 {out['content_sha256'][:16]} "
              f"(runtime {out['provenance']['runtime_seconds']}s)")

    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "phase1b_gate_network.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
