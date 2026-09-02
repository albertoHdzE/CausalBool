#!/usr/bin/env python
"""Expressivity census of the index-set method over the FULL ECA space.

AUDIT02/P9-census. This is a NEW arm, not a modification of the D-7 arm:
`run_comparison.py` and its committed artefacts are untouched, per protocol
s5.4 (no outcome-dependent changes).

Why it exists
-------------
The D-7 arm reports "10/10 rules exact" on a criterion that the whole
population passes: running the identical pipeline over all 256 rules gives
256/256, because the gate search includes `LUT` (an explicit truth table) and
`REGULATORY_DNF` (a functionally complete normal form). A criterion no member
can fail carries no information about the ten sampled.

Reporting 256/256 instead would be a stronger version of the same defect. The
informative object is the same census STRATIFIED by gate class:

  * how many ECA rules the canonical twelve express exactly, and which;
  * for the rest, which extension family is required.

That is an expressivity map of the method over the entire elementary rule
space, and unlike a hit count it can come out any way at all.

Method
------
Identical pipeline, knobs and seeds to `run_comparison.py` (width 11, 30 steps,
60 pooled initial conditions, radius 1, per-rule seed SEED + rule), so the two
arms sit in a common coordinate and the ten D-7 rules must reproduce exactly.

Classification is EXACT, not a re-search: `identify_gate` already returns the
full equivalence class of every cell's reduced truth table, so a rule is
canonical-expressible iff every cell has at least one match inside the twelve.
No second deconvolution is run and no result is re-fitted.

Wolfram classes are carried ONLY for the ten rules where the repository already
records them (`run_comparison.py:144`). The other 246 are marked `null` rather
than invented; protocol s5 forbids invention.

Run:
    .venv/bin/python index_method_comparison/run_expressivity_census.py
"""

from __future__ import annotations

import datetime
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "index-deconvolution", "src"))

from ca_deconvolution import ca_global_map, deconvolve_ca, evolve_eca  # noqa: E402
from causalbool import GATE_TYPES, Network, repertoire  # noqa: E402
from deconvolution import identify_gate  # noqa: E402
from run_comparison import N_ICS, RADIUS, RULES, SEED, STEPS, WIDTH  # noqa: E402

OUT_DIR = os.path.join(HERE, "..", "results", "index_method_comparison")

# the only classes the repository actually sources (run_comparison.py:144)
KNOWN_CLASSES = {254: "IV*", 57: "II", 11: "II", 50: "II", 9: "I",
                 54: "IV", 75: "II", 73: "II", 45: "III", 30: "III"}

CANONICAL = set(GATE_TYPES)


def census_rule(rule: int) -> dict:
    rng = np.random.default_rng(SEED + rule)
    diagrams = [evolve_eca(rule, [int(b) for b in rng.integers(0, 2, size=WIDTH)], STEPS)
                for _ in range(N_ICS)]
    net, reports = deconvolve_ca(diagrams, max_radius=RADIUS)

    # elementwise verification against the exhaustive global map
    truth = ca_global_map(rule, WIDTH)
    rec = repertoire(Network(n=WIDTH, C=net.C, gates=net.gates, params=net.params))
    mismatches = sum(1 for t, r in zip(truth, rec) for a, b in zip(t, r) if a != b)

    # EXACT stratification: identify_gate returns the whole equivalence class,
    # so "could the canonical twelve have named this cell?" is a lookup, not a
    # re-search.
    per_cell = []
    for rep in reports:
        matches, _ = identify_gate(rep.reduced_truth_table)
        fams = sorted({m.gate for m in matches})
        canon = sorted(set(fams) & CANONICAL)
        per_cell.append({"support": list(rep.support),
                         "chosen": rep.canonical.gate,
                         "canonical_options": canon})

    canonical_ok = all(c["canonical_options"] for c in per_cell)
    chosen = sorted({c["chosen"] for c in per_cell})
    # AUDIT02/P9-census: cells where a CANONICAL family matched but the priority
    # order picked an EXTENSION anyway. _CANONICAL_PRIORITY ranks REGULATORY
    # (index 11) ABOVE CANALISING (index 12), so a cell that a parity-proven
    # gate names can still be reported under a family with no Wolfram
    # counterpart. Counted, not corrected: reordering would change every
    # downstream gate-naming result (exp02's gate_function_correct_rate, exp03,
    # the D-7 arm, imp-prices), which is not a change to make mid-audit.
    displaced = [c for c in per_cell
                 if c["canonical_options"] and c["chosen"] not in CANONICAL]
    return {
        "rule": rule,
        "wolfram_class": KNOWN_CLASSES.get(rule),
        "exact_global_map": mismatches == 0,
        "mismatches": mismatches,
        "chosen_families": chosen,
        "canonical_expressible": canonical_ok,
        "extension_required": sorted(set(chosen) - CANONICAL),
        "cells_total": len(per_cell),
        "cells_canonical_displaced": len(displaced),
        "displaced_options": sorted({o for c in displaced for o in c["canonical_options"]}),
        "max_support": max((len(c["support"]) for c in per_cell), default=0),
        "in_d7_arm": rule in RULES,
    }


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = [census_rule(r) for r in range(256)]

    exact = [r for r in rows if r["exact_global_map"]]
    canon = [r for r in rows if r["canonical_expressible"]]
    d7 = [r for r in rows if r["in_d7_arm"]]
    d7_canon = [r for r in d7 if r["canonical_expressible"]]

    payload = {
        "arm": "expressivity_census",
        "relation_to_d7": "additive; run_comparison.py and its artefacts unmodified",
        "config": {"rules": "all 256", "width": WIDTH, "steps": STEPS,
                   "n_ics": N_ICS, "radius": RADIUS, "seed": SEED,
                   "note": "identical to the D-7 arm, so the two share a coordinate"},
        "generated": datetime.date.today().isoformat(),
        "summary": {
            "rules_total": 256,
            "exact_global_map": len(exact),
            "canonical_expressible": len(canon),
            "extension_required": 256 - len(canon),
            "d7_arm_exact": len(d7),
            "d7_arm_canonical_expressible": len(d7_canon),
            "canonical_rules": sorted(r["rule"] for r in canon),
            "cells_total": sum(r["cells_total"] for r in rows),
            "cells_canonical_displaced": sum(r["cells_canonical_displaced"] for r in rows),
            "rules_with_displacement": sum(1 for r in rows if r["cells_canonical_displaced"]),
        },
        "rows": rows,
    }
    with open(os.path.join(OUT_DIR, "expressivity_census.json"), "w") as fh:
        json.dump(payload, fh, indent=1)

    # full 256-row table
    lines = [
        "# Expressivity census — index-set method over all 256 ECA rules",
        "",
        "Generated by `index_method_comparison/run_expressivity_census.py`.",
        "Additive to the D-7 arm, which is unmodified.",
        "",
        f"- exact global map: **{len(exact)}/256** — uninformative on its own, because",
        "  the search includes `LUT` and `REGULATORY_DNF`, which are functionally",
        "  complete, so no rule can fail this criterion.",
        f"- expressible inside the canonical twelve: **{len(canon)}/256**",
        f"- requiring an extension family: **{256 - len(canon)}/256**",
        f"- of the ten D-7 rules, canonical-expressible: **{len(d7_canon)}/10**",
        "",
        "Wolfram classes are given only where the repository already sourced them;",
        "the rest are blank rather than invented.",
        "",
        "| rule | class | exact | canonical? | families chosen | extension needed | max support |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['rule']} | {r['wolfram_class'] or ''} | "
            f"{'YES' if r['exact_global_map'] else 'NO'} | "
            f"{'yes' if r['canonical_expressible'] else 'no'} | "
            f"{', '.join(r['chosen_families'])} | "
            f"{', '.join(r['extension_required'])} | {r['max_support']} |")
    lines.append("")
    lines.append("Canonical-expressible rules: "
                 + ", ".join(str(r) for r in payload["summary"]["canonical_rules"]))
    lines.append("")
    with open(os.path.join(OUT_DIR, "expressivity_census.md"), "w") as fh:
        fh.write("\n".join(lines))

    s = payload["summary"]
    print(f"exact global map              : {len(exact)}/256")
    print(f"canonical-expressible         : {len(canon)}/256")
    print(f"extension required            : {256 - len(canon)}/256")
    print(f"D-7 arm, canonical-expressible : {len(d7_canon)}/10")
    print(f"cells where a canonical match was displaced by an extension: "
          f"{s['cells_canonical_displaced']}/{s['cells_total']} "
          f"across {s['rules_with_displacement']} rules")
    print(f"written: {OUT_DIR}/expressivity_census.{{json,md}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
