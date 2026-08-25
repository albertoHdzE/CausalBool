#!/usr/bin/env python
"""Phase 1, ledger entry B5 — how stable is the belief network's structure?

GWP3 section 7 judges the dissertation's policy-relevance claim "partially
achieved; the framework is appropriate, the evidential standard is not", on the
grounds that the edge count ranged from 2 to 25 across the eighteen validated
configurations and no bootstrap edge stability was ever computed.

This script measures a stronger and more uncomfortable instability. Structure
learning by greedy search breaks score ties in the iteration order of a hashed
collection, so **the same configuration on the same data can return a different
graph in a different interpreter process**. The variation is measured here across
`PYTHONHASHSEED` values by re-executing this script as a subprocess, which is the
only way to vary a hash seed: it is fixed at interpreter start-up.

Run:
    .venv/bin/python scripts/phase1_stability.py [--seeds N] [--quiet]

Internal use:
    PYTHONHASHSEED=<n> .venv/bin/python scripts/phase1_stability.py --emit
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore")


def build_grids():
    """The two validation grids, stripped of the fitted model objects."""
    from imp_prices import RegimeDiscretiser, load_and_split
    from imp_prices.belief_network import frame_A, frame_B, tune_on_validation

    split = load_and_split()
    out = {}
    for spec, kind, maker, shift in [("A", "parity", frame_A, True),
                                     ("B", "gaussian", frame_B, False)]:
        fr = RegimeDiscretiser(kind).fit(split.train).transform(split.full)
        w = {k: maker(fr.reindex(p.index).dropna().astype(int))
             for k, p in [("train", split.train), ("val", split.val),
                          ("test", split.test)]}
        grid = tune_on_validation(w["train"], w["val"], "forecast", shift=shift)
        out[spec] = dict(
            rows=[{k: v for k, v in r.items() if k != "model"} for r in grid],
            selected_edges=sorted(tuple(e) for e in grid[0]["model"].edges()),
            selected_blanket=sorted(grid[0]["model"].get_markov_blanket("forecast")),
        )
    return out


def config_key(row):
    return f"{row['scoring']}/{row['max_indegree']}/{row['expert_seeded']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--emit", action="store_true",
                    help="internal: print one grid as JSON and exit")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.emit:
        print("@@GRID@@" + json.dumps(build_grids()))
        return 0

    here = os.path.abspath(__file__)
    runs = {}
    for seed in range(args.seeds):
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        proc = subprocess.run([sys.executable, here, "--emit"], env=env,
                              capture_output=True, text=True)
        line = [l for l in proc.stdout.splitlines() if l.startswith("@@GRID@@")]
        if not line:                                        # pragma: no cover
            print(proc.stderr[-2000:], file=sys.stderr)
            raise RuntimeError(f"seed {seed} produced no grid")
        runs[seed] = json.loads(line[0][len("@@GRID@@"):])
        if not args.quiet:
            print(f"  hash seed {seed:2d} done", flush=True)

    report = {"n_seeds": args.seeds}
    for spec in ("A", "B"):
        # Per configuration, what varies across hash seeds?
        by_cfg = collections.defaultdict(lambda: collections.defaultdict(set))
        for seed, r in runs.items():
            for row in r[spec]["rows"]:
                k = config_key(row)
                by_cfg[k]["n_edges"].add(row["n_edges"])
                by_cfg[k]["val_accuracy"].add(row["val_accuracy"])

        unstable_edges = {k: sorted(v["n_edges"]) for k, v in by_cfg.items()
                          if len(v["n_edges"]) > 1}
        unstable_acc = {k: sorted(v["val_accuracy"]) for k, v in by_cfg.items()
                        if len(v["val_accuracy"]) > 1}

        sel_cfg = {json.dumps(r[spec]["rows"][0], sort_keys=True) for r in runs.values()}
        sel_edges = {json.dumps(r[spec]["selected_edges"]) for r in runs.values()}
        sel_blanket = {json.dumps(r[spec]["selected_blanket"]) for r in runs.values()}
        grids = {json.dumps(r[spec]["rows"], sort_keys=True) for r in runs.values()}

        report[spec] = dict(
            n_configurations=len(by_cfg),
            n_distinct_full_grids=len(grids),
            n_configurations_with_unstable_edge_count=len(unstable_edges),
            n_configurations_with_unstable_val_accuracy=len(unstable_acc),
            unstable_edge_counts=unstable_edges,
            unstable_val_accuracies=unstable_acc,
            selected_configuration_is_stable=len(sel_cfg) == 1,
            selected_edge_set_is_stable=len(sel_edges) == 1,
            selected_blanket_is_stable=len(sel_blanket) == 1,
            n_distinct_selected_edge_sets=len(sel_edges),
            edge_count_range=[min(e for v in by_cfg.values() for e in v["n_edges"]),
                              max(e for v in by_cfg.values() for e in v["n_edges"])],
        )

        if not args.quiet:
            d = report[spec]
            print(f"\nspecification {spec}")
            print(f"  distinct full validation grids over {args.seeds} hash seeds: "
                  f"{d['n_distinct_full_grids']}")
            print(f"  configurations whose edge count varies: "
                  f"{d['n_configurations_with_unstable_edge_count']} of {d['n_configurations']}")
            print(f"  configurations whose validation accuracy varies: "
                  f"{d['n_configurations_with_unstable_val_accuracy']} of {d['n_configurations']}")
            print(f"  edge count range across everything: {d['edge_count_range']}")
            print(f"  selected configuration stable: {d['selected_configuration_is_stable']}; "
                  f"selected edge set stable: {d['selected_edge_set_is_stable']} "
                  f"({d['n_distinct_selected_edge_sets']} distinct); "
                  f"blanket stable: {d['selected_blanket_is_stable']}")
            for k, v in list(d["unstable_edge_counts"].items())[:8]:
                print(f"    {k:<24s} edge counts {v}")

    from imp_prices.config import RESULTS
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "phase1_stability.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
