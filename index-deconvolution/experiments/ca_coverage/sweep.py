"""ca_coverage sweep — AUDIT01/T4.3 (executes the frozen PROTOCOL.md).

For each (rule, seed, level k): greedily select ICs until the interior cell's
pooled samples exhibit >= k distinct radius-1 window patterns, deconvolve that
diagram ensemble, and test elementwise global-map equality against the true ECA
global map over all 2^12 states.

Deterministic: rng seeded per (seed0, rule); no wall-clock inputs.
Output: results/ca_coverage/summary.json (+ figure by --figure).
"""
from __future__ import annotations

import json
import os
import random
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
IDX_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(IDX_ROOT, "src"))

from ca_deconvolution import evolve_eca, deconvolve_ca, verify_ca  # noqa: E402

RULES = [254, 90, 30, 110, 232, 204, 250, 150, 170, 57, 45, 73]
WIDTH = 12
STEPS = 10
SEEDS = list(range(1, 21))
LEVELS = [4, 5, 6, 7, 8]
MAX_RADIUS = 3
MAX_CANDIDATES_WITHOUT_GAIN = 40
INTERIOR = WIDTH // 2
RESULTS_DIR = os.path.join(IDX_ROOT, "results", "ca_coverage")
FIG_DIR = os.path.join(IDX_ROOT, "..", "figures", "ca_coverage")


def cell_patterns(diagram: list[list[int]]) -> list[set[tuple[int, int, int]]]:
    """Per-cell radius-1 window patterns observed across all row transitions."""
    w = len(diagram[0])
    pats: list[set[tuple[int, int, int]]] = [set() for _ in range(w)]
    for t in range(len(diagram) - 1):
        cur = diagram[t]
        for c in range(w):
            pats[c].add((cur[(c - 1) % w], cur[c], cur[(c + 1) % w]))
    return pats


def select_diagrams(rule: int, seed0: int, target_k: int):
    """Greedy IC selection per PROTOCOL (as amended by D3): stop when the MINIMUM
    per-cell distinct-pattern count reaches target_k. Returns (diagrams, stats)."""
    # PROTOCOL DEVIATION D1: random.Random rejects tuple seeds; canonical string form.
    rng = random.Random(f"{seed0}:{rule}")
    chosen: list[list[list[int]]] = []
    seen: list[set[tuple[int, int, int]]] = [set() for _ in range(WIDTH)]
    stale = 0
    while min(len(s) for s in seen) < target_k and stale < MAX_CANDIDATES_WITHOUT_GAIN:
        ic = [rng.randint(0, 1) for _ in range(WIDTH)]
        d = evolve_eca(rule, ic, STEPS)
        new = cell_patterns(d)
        gain = any(new[c] - seen[c] for c in range(WIDTH))
        if gain:
            for c in range(WIDTH):
                seen[c] |= new[c]
            chosen.append(d)
            stale = 0
        else:
            stale += 1
    covs = sorted(len(s) / 8 for s in seen)
    stats = {
        "achieved_min_k": min(len(s) for s in seen),
        "min_cell_coverage": covs[0],
        "max_cell_coverage": covs[-1],
        "cells_below_target": sum(1 for s in seen if len(s) < target_k),
    }
    return chosen, stats


def run_rule_level(rule: int, seed0: int, level: int) -> dict:
    diagrams, stats = select_diagrams(rule, seed0, level)
    net, reports = deconvolve_ca(diagrams, max_radius=MAX_RADIUS)
    vr = verify_ca(diagrams, net, rule=rule)
    rep = reports[INTERIOR]
    return {
        "rule": rule,
        "seed": seed0,
        "level": level,
        "n_diagrams": len(diagrams),
        "global_map_exact": bool(vr.get("global_map_exact")),
        "trajectory_exact": bool(vr["trajectory_exact"]),
        "interior_support_size": len(rep.support),
        "interior_gate": rep.canonical.as_dict(),
        **stats,
    }


def main() -> int:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    records = []
    for rule in RULES:
        for seed0 in SEEDS:
            for level in LEVELS:
                rec = run_rule_level(rule, seed0, level)
                records.append(rec)
            print(f"rule {rule} seed {seed0}: done", flush=True)

    # Recovery curves by TARGET level (protocol, as amended by D2).
    curve: dict[int, dict[int, dict[str, int]]] = {}
    for rule in RULES:
        curve[rule] = {}
        for k in LEVELS:
            rows = [r for r in records if r["rule"] == rule and r["level"] == k]
            exact = sum(1 for r in rows if r["global_map_exact"])
            curve[rule][k] = {"runs": len(rows), "exact": exact}
        for k, v in curve[rule].items():
            print(f"rule {rule} level {k}/8: {v['exact']}/{v['runs']} global-exact")

    classification = {
        str(rule): ("saturating" if curve[rule][8]["exact"] == len(SEEDS)
                    else "non-saturating")
        for rule in RULES
    }
    all_full_exact = all(
        r["global_map_exact"] for r in records if r["level"] == 8
    )
    summary = {
        "experiment": "ca_coverage_sweep",
        "protocol": "experiments/ca_coverage/PROTOCOL.md (frozen 2026-08-25; "
                    "deviations D1-D3 logged)",
        "width": WIDTH, "steps": STEPS, "seeds": SEEDS, "levels": LEVELS,
        "rules": RULES, "max_radius": MAX_RADIUS,
        "coverage_definition": "min over cells of distinct radius-1 window "
                               "patterns at that cell (D3)",
        "success_criterion": "elementwise equality of recovered network repertoire "
                             "vs true ca_global_map on all 2^12 states",
        "all_rules_20_of_20_at_level8": all_full_exact,
        "classification": classification,
        "recovery_curve": {str(r): {str(k): v for k, v in kv.items()}
                           for r, kv in curve.items()},
        "records": records,
    }
    out = os.path.join(RESULTS_DIR, "summary.json")
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)
    print("written:", out)

    if "--figure" in sys.argv:
        os.makedirs(FIG_DIR, exist_ok=True)
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for rule in RULES:
            xs = LEVELS
            ys = [100.0 * curve[rule][k]["exact"] / max(1, curve[rule][k]["runs"]) for k in xs]
            ax.plot([x / 8 for x in xs], ys, marker="o", ms=3, lw=1, label=str(rule))
        ax.set_xlabel("neighbourhood coverage level k/8 (min over cells)")
        ax.set_ylabel("seeds with exact global-map recovery (%)")
        ax.set_title("CA->network identifiability envelope (12 rules x 20 seeds)")
        ax.set_ylim(-2, 102)
        ax.legend(ncol=2, fontsize=7, title="ECA rule", title_fontsize=8)
        fig.tight_layout()
        figp = os.path.join(FIG_DIR, "recovery_vs_coverage.png")
        fig.savefig(figp, dpi=160)
        print("written:", figp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
