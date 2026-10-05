"""screen_s1_full_table.py -- identification screen, step 2: S1 and gate H3.

PROTOCOL sec.2 row S1: the learner reads all 2**n state-successor pairs
(n <= 20).  Our arm is ``deconvolve`` (src/deconvolution.py).  Competitors,
run as their own software: BoolNet ``reconstructNetwork`` with
method="reveal" (BoolNet reconstruction [11]) and method="bestfit" (the
best-fit extension of Laehdesmaeki et al. [10], as implemented in BoolNet).

Every recovered model is checked by ``verify_forward`` against the true
repertoire before it is scored; an inexact model scores nothing.

Fairness notes, recorded in the output:
  * BoolNet is given maxK = the true maximum in-degree of the network (an
    oracle advantage for the competitor; ``deconvolve`` is given no bound).
  * Only the reconstruction call is timed on either side; building the
    repertoire (ours) or the R input list (BoolNet) is not.

Time: median of 3 runs, 600 s limit per run (a run over the limit is
recorded as a timeout and is not repeated).

Usage: venv/bin/python index-deconvolution/experiments/screen_s1_full_table.py [--quiet]
"""

from __future__ import annotations

import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from screen_common import (HERE, RES, RSCRIPT, canonical_names, load_entry,
                           load_manifest, log, write_json)

from causalbool import repertoire
from bnet import parse_bnet
from deconvolution import deconvolve, verify_forward

MAX_N = 20
REPS = 3
LIMIT_S = 600


def run_ours(rep):
    times, net = [], None
    for _ in range(REPS):
        t0 = time.perf_counter()
        net, _ = deconvolve(rep)
        times.append(time.perf_counter() - t0)
        if times[-1] > LIMIT_S:
            break
    return times, net


def full_table_pairs(rep, n):
    """All 2**n (state, successor) pairs of a repertoire, state LSB-first."""
    return [([(x >> i) & 1 for i in range(n)], succ) for x, succ in enumerate(rep)]


def run_boolnet(pair_list, n, max_k, method, work: Path, reps=None, limit_s=None):
    """BoolNet reconstructNetwork on (state, successor) pairs; also used by S2."""
    reps = REPS if reps is None else reps
    limit_s = LIMIT_S if limit_s is None else limit_s
    names = canonical_names(n)
    pairs = work / "pairs.bin"
    buf = bytearray()
    for state, succ in pair_list:
        buf.extend(state)
        buf.extend(succ)
    pairs.write_bytes(bytes(buf))
    out = work / f"boolnet_{method}.bnet"
    out.unlink(missing_ok=True)
    import os
    env = {**os.environ, "R_LIBS_USER": os.path.expanduser("~/Library/R/arm64/4.6/library")}
    # One R process per repeat, so that a run over the limit is killed rather
    # than waited for (BoolNet's C core does not honour R's setTimeLimit).
    # The process limit adds 300 s for loading the input list, which is untimed.
    times, info = [], {}
    for _ in range(reps):
        cmd = [RSCRIPT, "--vanilla", str(HERE / "screen_boolnet_reconstruct.R"), str(pairs),
               str(n), str(len(pair_list)), str(max_k), method, "1", str(out), ",".join(names)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=limit_s + 300, env=env)
        except subprocess.TimeoutExpired:
            return {"status": f"timeout (> {limit_s} s)", "times": times or None, "net": None}
        info = dict(ln.split("\t", 1) for ln in proc.stdout.splitlines() if "\t" in ln)
        if "STATUS" not in info:
            return {"status": f"error: {proc.stderr.strip()[-300:]}", "times": None, "net": None}
        times.append(float(info["TIMES"]))
        if times[-1] > limit_s:
            return {"status": f"timeout (> {limit_s} s)", "times": times, "net": None}
    net = None
    if info["STATUS"] == "ok":
        net, got_names = parse_bnet(str(out))
        if got_names != names:
            return {"status": f"gene order changed: {got_names[:5]}", "times": times, "net": None}
    return {"status": info["STATUS"], "times": times, "net": net,
            "ambiguous_genes": int(info["AMBIGUOUS_GENES"]),
            "max_functions": int(info["MAX_FUNCTIONS"])}


def main() -> None:
    manifest = load_manifest()
    entries = [e for e in manifest["entries"] if e["n"] <= MAX_N]
    work = Path(tempfile.mkdtemp(prefix="screen_s1_"))
    rows = []
    for e in entries:
        net = load_entry(e)
        rep = repertoire(net)
        max_k = max(sum(r) for r in net.C)
        row = {"id": e["id"], "kind": e["kind"], "n": e["n"], "max_indegree": max_k,
               "rows_read": len(rep)}
        # ours
        times, rec = run_ours(rep)
        vf = verify_forward(rep, rec)
        row["deconvolve"] = {"times_s": times, "median_s": statistics.median(times),
                             "exact": vf["exact"], "mismatched_nodes": vf["mismatched_nodes"]}
        # competitors
        for method in ("reveal", "bestfit"):
            r = run_boolnet(full_table_pairs(rep, e["n"]), e["n"], max_k, method, work)
            cell = {"status": r["status"], "times_s": r["times"], "maxK_given": max_k}
            if r["times"]:
                cell["median_s"] = statistics.median(r["times"])
            if r["net"] is not None:
                vf = verify_forward(rep, r["net"])
                cell["exact"] = vf["exact"]
                cell["mismatched_nodes"] = vf["mismatched_nodes"]
                cell["ambiguous_genes"] = r["ambiguous_genes"]
            else:
                cell["exact"] = False
            row[f"boolnet_{method}"] = cell
        rows.append(row)
        log(e["id"], e["n"], {k: (row[k].get("median_s"), row[k].get("exact"))
                              for k in ("deconvolve", "boolnet_reveal", "boolnet_bestfit")})
        write_json(RES / "s1_full_table.json", {"partial": True, "rows": rows})

    # H3: at n <= 20, is deconvolve at least as fast as the best exact competitor?
    h3 = []
    for r in rows:
        ours = r["deconvolve"]["median_s"] if r["deconvolve"]["exact"] else None
        comp = [r[k]["median_s"] for k in ("boolnet_reveal", "boolnet_bestfit")
                if r[k].get("exact") and r[k].get("median_s") is not None]
        best = min(comp) if comp else None
        h3.append({"id": r["id"], "n": r["n"], "ours_s": ours, "best_competitor_s": best,
                   "ours_at_least_as_fast": (ours is not None and (best is None or ours <= best))})
    n_fast = sum(x["ours_at_least_as_fast"] for x in h3)
    out = {
        "protocol": "PROTOCOL_screen_identification.md S1, H3",
        "script": "index-deconvolution/experiments/screen_s1_full_table.py",
        "tool_versions": manifest["tool_versions"],
        "settings": {"max_n": MAX_N, "reps": REPS, "limit_s": LIMIT_S,
                     "boolnet_maxK": "true maximum in-degree (oracle, favours BoolNet)"},
        "rows": rows,
        "h3": {"per_network": h3, "ours_at_least_as_fast": n_fast, "denominator": len(h3),
               "gate": "H3 holds (our advantage is an advantage in time) iff ours is at least as fast on every network"},
    }
    write_json(RES / "s1_full_table.json", out)
    ex = {k: sum(bool(r[k].get("exact")) for r in rows)
          for k in ("deconvolve", "boolnet_reveal", "boolnet_bestfit")}
    print(f"S1: {len(rows)} networks; exact: {ex}")
    print(f"H3: deconvolve at least as fast as best exact competitor on {n_fast}/{len(h3)}")


if __name__ == "__main__":
    main()
