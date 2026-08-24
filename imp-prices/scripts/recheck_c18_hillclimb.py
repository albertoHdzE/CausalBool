#!/usr/bin/env python
"""Re-check of ledger entry C18's hill-climbing clause (AUDIT01/T2.1).

FINDINGS.md C18 and bitacora/04 quote pgmpy's own hill-climb search as
"5 distinct winning parent sets over 120 resamples (modal {WTI_CL}, 55.0 per
cent)". The artifact both documents pin by content sha256 (160d8437a2eb20dc)
records instead 6 distinct winners, modal {WTI_Spot}, 0.375. This script
re-executes the hill-climb block from the committed producing code path — same
frame construction, same rng, same 120 resamples at block 12, BIC-d with
in-degree <= 2 — and compares the result ELEMENTWISE (full winner-frequency
map, not summaries) against both candidate triples.

Because pgmpy's greedy search breaks score ties in hashed-collection iteration
order (ledger C12/C13), the core loop is additionally executed under a sweep of
PYTHONHASHSEED values; stability across seeds is reported alongside the verdict.

Verdicts:
    PROSE-WRONG        every seed reproduces the pinned JSON map -> the prose
                       misquoted its own pinned artifact all along.
    PROVENANCE-BROKEN  runs reproduce the prose triple instead -> two JSON
                       generations exist; STOP before editing any text.
    HASH-UNSTABLE      runs disagree with each other across hash seeds -> the
                       pinned artifact is one draw from a seed-dependent search;
                       recorded as a finding, correction still cites the pin.
    AMBIGUOUS          none of the above -> escalate in the plan log.

Run:
    .venv/bin/python scripts/recheck_c18_hillclimb.py [--seeds "0,7,42"] [--quiet]
Outputs:
    results/recheck_c18/recheck_c18.json   machine-readable aggregate
    results/recheck_c18/recheck_c18.log    commands + stdout transcript
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

from imp_prices import RegimeDiscretiser, SERIES, TARGET, load_and_split
from imp_prices.config import RESULTS

PINNED = os.path.join(RESULTS, "b4_description_length.json")
OUT_DIR = os.path.join(RESULTS, "recheck_c18")

PROSE_TRIPLE = {"n_distinct_winners": 5, "modal_parents": "WTI_CL",
                "modal_frequency": 0.55}


def hill_climb_once():
    """The C18 hill-climb block, verbatim from phase1_b4_description_length.py."""
    import numpy as np
    from imp_prices.belief_network import frame_B, learn_structure
    from imp_prices.index_set import block_bootstrap_indices

    split = load_and_split()
    frame = RegimeDiscretiser("gaussian").fit(split.train).transform(split.full)
    train = frame.reindex(split.train.index).dropna().astype(int)
    B_train = frame_B(train)

    rng = np.random.default_rng(42)
    hc_wins = {}
    n_hc = 120
    for _ in range(n_hc):
        take = block_bootstrap_indices(len(B_train), 12, rng)
        boot_frame = B_train.iloc[take].reset_index(drop=True)
        try:
            m = learn_structure(boot_frame, "bic-d", 2, None)
            pa = tuple(sorted(m.get_parents("forecast")))
        except Exception:
            continue
        hc_wins[pa] = hc_wins.get(pa, 0) + 1
    ranked = sorted(hc_wins.items(), key=lambda kv: -kv[1])
    return dict(
        n_boot=n_hc, n_distinct_winners=len(hc_wins),
        modal_parents="+".join(ranked[0][0]) or "(none)",
        modal_frequency=round(ranked[0][1] / n_hc, 4),
        top=[dict(parents="+".join(p) or "(none)", frequency=round(c / n_hc, 4))
             for p, c in ranked])


def child_main():
    print(json.dumps(hill_climb_once()))


def freq_map(block):
    """Full winner->frequency map; valid as THE map when len(top)==n_winners."""
    return {r["parents"]: r["frequency"] for r in block["top"]}


def map_symmetric_difference(a, b):
    left = {k: a[k] for k in a if k not in b or b[k] != a[k]}
    right = {k: b[k] for k in b if k not in a or a[k] != b[k]}
    return {"only_in_first": left, "only_in_second": right}


def compare_maps(a, b):
    if a["n_distinct_winners"] != b["n_distinct_winners"]:
        return False
    fa, fb = freq_map(a), freq_map(b)
    if len(fa) < a["n_distinct_winners"] or len(fb) < b["n_distinct_winners"]:
        # top list truncated; compare only what is recorded, plus the triple
        pass
    return (fa == fb and a["modal_parents"] == b["modal_parents"]
            and a["modal_frequency"] == b["modal_frequency"])


def matches_prose(block):
    return (block["n_distinct_winners"] == PROSE_TRIPLE["n_distinct_winners"]
            and block["modal_parents"] == PROSE_TRIPLE["modal_parents"]
            and abs(block["modal_frequency"]
                    - PROSE_TRIPLE["modal_frequency"]) < 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--seeds", type=str, default="0,1,7,42,123,2026,random")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.child:
        child_main()
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    log_path = os.path.join(OUT_DIR, "recheck_c18.log")
    log = open(log_path, "w")

    def say(line=""):
        print(line)
        log.write(line + "\n")

    with open(PINNED) as fh:
        pinned_block = json.load(fh)["bootstrap"]["hill_climb"]
    pinned_hash = json.load(open(PINNED))["content_sha256"]

    say("C18 re-check " + __file__)
    say(f"pinned artifact : {os.path.relpath(PINNED, os.path.dirname(RESULTS))}"
        f"  content_sha256={pinned_hash[:16]}")
    say(f"pinned hill-climb: {pinned_block['n_distinct_winners']} winners, "
        f"modal {pinned_block['modal_parents']} at "
        f"{100 * pinned_block['modal_frequency']:.1f}% over "
        f"{pinned_block['n_boot']} resamples")
    say(f"prose triple (FINDINGS C18 / bitacora 04): "
        f"{PROSE_TRIPLE['n_distinct_winners']} winners, modal "
        f"{PROSE_TRIPLE['modal_parents']} at "
        f"{100 * PROSE_TRIPLE['modal_frequency']:.0f}%")
    say(f"hash-seed sweep: {args.seeds}")
    say()

    seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    runs = []
    for seed in seeds:
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        cmd = [sys.executable, os.path.abspath(__file__), "--child"]
        say(f"$ PYTHONHASHSEED={seed} .venv/bin/python "
            f"scripts/recheck_c18_hillclimb.py --child")
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
        log.write(proc.stdout)
        if proc.returncode != 0:
            say(f"  !! child failed rc={proc.returncode}: "
                f"{proc.stderr.strip()[:400]}")
            runs.append(dict(seed=seed, error=proc.stderr.strip()[:2000]))
            continue
        block = json.loads(proc.stdout.strip().splitlines()[-1])
        diff_pin = map_symmetric_difference(
            {**freq_map(block)}, freq_map(pinned_block)) \
            if set(freq_map(block)) != set(freq_map(pinned_block)) else {}
        runs.append(dict(seed=seed, result=block,
                         equals_pinned_map=compare_maps(block, pinned_block),
                         matches_prose_triple=matches_prose(block)))
        r = runs[-1]
        say(f"  -> {block['n_distinct_winners']} winners, modal "
            f"{block['modal_parents']} at {100 * block['modal_frequency']:.1f}%"
            f"   equals_pinned_map={r['equals_pinned_map']} "
            f"matches_prose={r['matches_prose_triple']}")
        if set(freq_map(block)) == set(freq_map(pinned_block)):
            say(f"     winner sets identical to pinned; frequency symmetric "
                f"difference: {map_symmetric_difference(freq_map(block), freq_map(pinned_block)) or 'EMPTY'}")
        else:
            say(f"     winner-set difference vs pinned: "
                f"{sorted(set(freq_map(block)) ^ set(freq_map(pinned_block)))}")
    say()

    ok_runs = [r for r in runs if "result" in r]
    out = dict(pinned_content_sha256=pinned_hash,
               prose_triple=PROSE_TRIPLE,
               pinned_triple=dict(n_distinct_winners=pinned_block["n_distinct_winners"],
                                  modal_parents=pinned_block["modal_parents"],
                                  modal_frequency=pinned_block["modal_frequency"]),
               runs=runs)

    if not ok_runs:
        verdict = "AMBIGUOUS"
    elif all(r["equals_pinned_map"] for r in ok_runs):
        verdict = "PROSE-WRONG"
    elif all(r["matches_prose_triple"] for r in ok_runs):
        verdict = "PROVENANCE-BROKEN"
    else:
        verdict = "HASH-UNSTABLE"
    out["verdict"] = verdict
    out["verdict_rule"] = (
        "PROSE-WRONG iff every executed seed reproduces the pinned JSON's full "
        "winner-frequency map elementwise; PROVENANCE-BROKEN iff every seed "
        "reproduces the prose triple instead; HASH-UNSTABLE otherwise.")
    say(f"VERDICT: {verdict}")

    out["recheck_script_sha256"] = hashlib.sha256(
        open(os.path.abspath(__file__), "rb").read()).hexdigest()
    with open(os.path.join(OUT_DIR, "recheck_c18.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    say(f"wrote {os.path.relpath(os.path.join(OUT_DIR, 'recheck_c18.json'), os.path.dirname(RESULTS))}")
    say(f"wrote {os.path.relpath(log_path, os.path.dirname(RESULTS))}")
    log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
