"""screen_s3b_multi_step.py -- identification screen, step 4: S3b and gate H2 (S3b).

PROTOCOL sec.2 row S3b: questions over many steps.  Three classes, posed on
every network of the frozen corpus (35 synthetic, n = 10..200; 20 biological):

  fixed  all fixed points
  attr   all attractors of the synchronous map
  reach  does ANY state reach the target T within 3 steps?  T fixes 4 nodes
         (the owner's T2 node choice, choose_query_nodes(n, 4, idx + 5));
         two targets per network: T+ = the successor bits of the owner's pinned
         witness state (reachable by construction, a sanity check) and T- = T+
         with every bit flipped (answer unknown in advance).

Arms:
  ours       num_attractors (src/reprogramming.py) for `attr` ONLY.  It visits
             all 2**n states: EXHAUSTIVE, and labelled so.  No index-based arm
             exists for any S3b class, and none is built here (PROTOCOL sec.2;
             kick-off rules).  For `fixed` and `reach` our entry is "none exists".
  pyboolnet  compute_steady_states (ASP), compute_attractors(update=
             "synchronous"), model_checking with NuSMV:
             INIT TRUE; CTLSPEC !(EBF 0..3 T)  -- false iff some state reaches T.
  boolnet    getAttractors(type="synchronous"): method "sat.restricted" with
             maxAttractorLength=1 for `fixed`, "sat.exhaustive" for `attr`.
             BoolNet offers no reachability query.
  z3_bmc     cross-check for `reach` only (bounded model checking, 4 unrolled
             copies of the state).  Not one of the protocol's S3b competitors;
             reported to verify PyBoolNet's answers.

Checks: every reported fixed point and every reported attractor is verified
state by state with causalbool.step; attractor and fixed-point counts must agree
across the tools that answered; T+ must be answered "reachable".

Model loading (bnet2primes, loadNetwork) is not timed.  Time: median of 3 runs,
one process per run, 60 s limit per run (killed and recorded as a timeout).

Usage: venv/bin/python index-deconvolution/experiments/screen_s3b_multi_step.py [--quiet]
"""

from __future__ import annotations

import json
import os
import random
import statistics
import subprocess
import sys
import time

from screen_common import (CORPUS, HERE, RES, RSCRIPT, load_entry, load_manifest, log,
                           tool_versions, write_json)

import scalability_resource_envelope as sre
from causalbool import step

LIMIT_S = 60.0
REPS = 3
T_STEPS = 3
PY = sys.executable


# ---------------------------------------------------------------------------
# questions
# ---------------------------------------------------------------------------

def reach_targets(entry, net):
    idx = int(entry["id"].rsplit("_s", 1)[1]) if entry["kind"] == "synthetic" else 0
    w_rng = random.Random(10_000 + net.n * 97 + idx)          # owner's witness rule
    witness = [w_rng.randint(0, 1) for _ in range(net.n)]
    nodes = [k - 1 for k in sre.choose_query_nodes(net.n, 4, idx + 5)]
    succ = step(net, witness)
    plus = {k: succ[k] for k in nodes}
    return {"T+": plus, "T-": {k: 1 - v for k, v in plus.items()}}


def target_expr(target: dict) -> str:
    return " & ".join((f"v{k:03d}" if v else f"!v{k:03d}") for k, v in sorted(target.items()))


# ---------------------------------------------------------------------------
# worker: one timed run of one tool on one question, in its own process
# ---------------------------------------------------------------------------

def worker(tool: str, question: str, entry_id: str, target_json: str) -> dict:
    manifest = load_manifest()
    entry = next(e for e in manifest["entries"] if e["id"] == entry_id)
    net = load_entry(entry)
    text = (CORPUS / entry["bnet"]).read_text()
    if tool == "ours":
        from reprogramming import num_attractors
        t0 = time.perf_counter()
        count = num_attractors(net)
        return {"time_s": time.perf_counter() - t0, "count": count}
    if tool == "pyboolnet":
        import logging
        logging.disable(logging.CRITICAL)
        from pyboolnet.file_exchange import bnet2primes
        primes = bnet2primes("\n".join(text.splitlines()[1:]))
        if question == "fixed":
            from pyboolnet.trap_spaces import compute_steady_states
            t0 = time.perf_counter()
            ss = compute_steady_states(primes, max_output=100000)
            dt = time.perf_counter() - t0
            names = sorted(primes)
            return {"time_s": dt, "count": len(ss),
                    "states": ["".join(str(int(s[nm])) for nm in names) for s in ss]}
        if question == "attr":
            from pyboolnet.attractors import compute_attractors
            t0 = time.perf_counter()
            a = compute_attractors(primes, "synchronous", max_output=100000)
            dt = time.perf_counter() - t0
            return {"time_s": dt, "count": len(a["attractors"]),
                    "is_complete": a.get("is_complete"),
                    "states": [x["state"]["str"] for x in a["attractors"]]}
        if question == "reach":
            from pyboolnet.model_checking import model_checking
            target = {int(k): v for k, v in json.loads(target_json).items()}
            spec = f"CTLSPEC !(EBF 0..{T_STEPS} ({target_expr(target)}))"
            t0 = time.perf_counter()
            holds = model_checking(primes, "synchronous", "INIT TRUE", spec)
            return {"time_s": time.perf_counter() - t0, "reachable": not holds}
    if tool == "z3_bmc":
        import z3
        rules = [ln.split(",", 1)[1].strip() for ln in text.splitlines()[1:]]
        target = {int(k): v for k, v in json.loads(target_json).items()}
        t0 = time.perf_counter()
        layers = [{f"v{i:03d}": z3.Bool(f"s{t}_{i}") for i in range(net.n)}
                  for t in range(T_STEPS + 1)]
        s = z3.Solver()
        for t in range(T_STEPS):
            for i, r in enumerate(rules):
                e = (z3.BoolVal(r == "1") if r in ("0", "1")
                     else eval(r.replace("!", "~"), {"__builtins__": {}}, layers[t]))  # noqa: S307
                s.add(layers[t + 1][f"v{i:03d}"] == e)
        hit = [z3.And([layers[t][f"v{k:03d}"] if v else z3.Not(layers[t][f"v{k:03d}"])
                       for k, v in target.items()]) for t in range(T_STEPS + 1)]
        s.add(z3.Or(hit))
        res = s.check()
        return {"time_s": time.perf_counter() - t0, "reachable": res == z3.sat}
    raise ValueError(tool)


def boolnet_run(entry, question):
    env = {**os.environ, "R_LIBS_USER": os.path.expanduser("~/Library/R/arm64/4.6/library")}
    times, attrs = [], []
    for _ in range(REPS):
        try:
            proc = run_killable([RSCRIPT, "--vanilla", str(HERE / "screen_boolnet_attractors.R"),
                                 str(CORPUS / entry["bnet"]), question, "1"],
                                timeout=LIMIT_S + 20, env=env)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "times_s": times or None}
        tl = [ln.split("\t", 1)[1] for ln in proc.stdout.splitlines() if ln.startswith("TIMES\t")]
        if not tl:
            return {"status": f"error: {proc.stderr.strip()[-200:]}", "times_s": None}
        times.append(float(tl[0]))
        attrs = [ln.split("\t", 1)[1].split(",") for ln in proc.stdout.splitlines()
                 if ln.startswith("ATTR\t")]
        if times[-1] > LIMIT_S:
            return {"status": "timeout", "times_s": times}
    return {"status": "ok", "times_s": times, "median_s": statistics.median(times),
            "count": len(attrs), "attractors": attrs}


def py_run(tool, question, entry, target=None):
    times, last = [], None
    for _ in range(REPS):
        try:
            proc = run_killable([PY, __file__, "--worker", tool, question, entry["id"],
                                 json.dumps(target or {})], timeout=LIMIT_S + 20)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "times_s": times or None}
        out = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT\t")]
        if not out:
            return {"status": f"error: {proc.stderr.strip()[-200:]}", "times_s": None}
        last = json.loads(out[0].split("\t", 1)[1])
        times.append(last["time_s"])
        if times[-1] > LIMIT_S:
            return {"status": "timeout", "times_s": times}
    res = {"status": "ok", "times_s": times, "median_s": statistics.median(times)}
    res.update({k: v for k, v in last.items() if k != "time_s"})
    return res


def run_killable(cmd, timeout, env=None):
    """subprocess.run with a timeout that kills the whole process group, so
    that solver grandchildren (NuSMV, clasp) do not outlive the limit."""
    import signal
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         env=env, start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------

def _bits(sx: str) -> list[int]:
    return [int(c) for c in sx]


def verify_fixed(net, states) -> bool:
    return all(step(net, _bits(s)) == _bits(s) for s in states)


def verify_cycle(net, seq) -> bool:
    st = [_bits(s) for s in seq]
    return all(step(net, st[i]) == st[(i + 1) % len(st)] for i in range(len(st)))


def verify_on_attractor(net, s: str, limit: int = 100000) -> bool:
    """PyBoolNet reports one state per attractor: check it lies on a cycle."""
    x0 = _bits(s)
    x = step(net, x0)
    for _ in range(limit):
        if x == x0:
            return True
        x = step(net, x)
    return False


# ---------------------------------------------------------------------------

def main() -> None:
    manifest = load_manifest()
    rows = []
    for e in manifest["entries"]:
        net = load_entry(e)
        row = {"id": e["id"], "kind": e["kind"], "n": e["n"]}
        # fixed points
        pb = py_run("pyboolnet", "fixed", e)
        bn = boolnet_run(e, "fixed")
        if pb["status"] == "ok":
            pb["verified"] = verify_fixed(net, pb.pop("states"))
        if bn["status"] == "ok":
            bn["verified"] = all(len(a) == 1 for a in bn["attractors"]) and verify_fixed(
                net, [a[0] for a in bn.pop("attractors")])
        row["fixed"] = {"ours": "none exists", "pyboolnet": pb, "boolnet": bn}
        # attractors
        pb = py_run("pyboolnet", "attr", e)
        bn = boolnet_run(e, "attr")
        if pb["status"] == "ok":
            pb["verified"] = all(verify_on_attractor(net, s) for s in pb.pop("states"))
        if bn["status"] == "ok":
            bn["verified"] = all(verify_cycle(net, a) for a in bn.pop("attractors"))
        ours = py_run("ours", "attr", e) if net.n <= 24 else {
            "status": "not run: exhaustive over 2^n states, n > 24"}
        ours["label"] = "exhaustive (2^n states)"
        row["attr"] = {"ours": ours, "pyboolnet": pb, "boolnet": bn}
        # reachability
        row["reach"] = {}
        for tname, target in reach_targets(e, net).items():
            row["reach"][tname] = {
                "target": {f"v{k:03d}": v for k, v in target.items()},
                "ours": "none exists",
                "pyboolnet": py_run("pyboolnet", "reach", e, target),
                "boolnet": "not offered",
                "z3_bmc": py_run("z3_bmc", "reach", e, target)}
        # agreement
        for q in ("fixed", "attr"):
            counts = {t: row[q][t]["count"] for t in ("ours", "pyboolnet", "boolnet")
                      if isinstance(row[q][t], dict) and row[q][t].get("status") == "ok"}
            row[q]["counts"] = counts
            row[q]["counts_agree"] = len(set(counts.values())) <= 1
        rows.append(row)
        log(e["id"], e["n"], {q: row[q]["counts"] for q in ("fixed", "attr")},
            {t: (row["reach"][t]["pyboolnet"].get("reachable"), row["reach"][t]["z3_bmc"].get("reachable"))
             for t in row["reach"]})
        write_json(RES / "s3b_multi_step.json", {"partial": True, "rows": rows})

    def tool_cells(q, tool):
        if q == "reach":
            return [(r, r["reach"][t][tool]) for r in rows for t in r["reach"]]
        return [(r, r[q][tool]) for r in rows]

    summary = {}
    for q, tools in (("fixed", ("pyboolnet", "boolnet")), ("attr", ("ours", "pyboolnet", "boolnet")),
                     ("reach", ("pyboolnet", "z3_bmc"))):
        summary[q] = {}
        for tool in tools:
            cells = tool_cells(q, tool)
            ok = [(r, c) for r, c in cells if isinstance(c, dict) and c.get("status") == "ok"]
            at200 = [(r, c) for r, c in cells if r["n"] == 200]
            summary[q][tool] = {
                "answered": f"{len(ok)}/{len(cells)}",
                "timeouts": sum(isinstance(c, dict) and c.get("status") == "timeout" for _, c in cells),
                "max_s_by_n": {str(n): max((c["median_s"] for r, c in ok if r["n"] == n), default=None)
                               for n in sorted({r["n"] for r in rows})},
                "all_under_1s_at_n200": bool(at200) and all(
                    isinstance(c, dict) and c.get("status") == "ok" and c["median_s"] < 1.0
                    and (q != "attr" or tool != "pyboolnet" or c.get("is_complete") == "yes")
                    for _, c in at200),
                "questions_at_n200": len(at200)}
    checks = {
        "fixed_counts_agree": f"{sum(r['fixed']['counts_agree'] for r in rows)}/{len(rows)}",
        "attr_counts_agree": f"{sum(r['attr']['counts_agree'] for r in rows)}/{len(rows)}",
        "T+_reachable_pyboolnet": f"{sum(r['reach']['T+']['pyboolnet'].get('reachable') is True for r in rows)}/{len(rows)}",
        "reach_pyboolnet_equals_z3": f"{sum(r['reach'][t]['pyboolnet'].get('reachable') == r['reach'][t]['z3_bmc'].get('reachable') for r in rows for t in r['reach'] if r['reach'][t]['pyboolnet'].get('status') == 'ok' and r['reach'][t]['z3_bmc'].get('status') == 'ok')}/{sum(1 for r in rows for t in r['reach'] if r['reach'][t]['pyboolnet'].get('status') == 'ok' and r['reach'][t]['z3_bmc'].get('status') == 'ok')}",
        "verified_false": [(r["id"], q, t) for r in rows for q in ("fixed", "attr")
                           for t in ("ours", "pyboolnet", "boolnet")
                           if isinstance(r[q][t], dict) and r[q][t].get("verified") is False],
    }
    h2 = {q: {"competitor_solves_class": any(summary[q][t]["all_under_1s_at_n200"]
                                            for t in summary[q] if t in ("pyboolnet", "boolnet"))}
          for q in summary}
    out = {"protocol": "PROTOCOL_screen_identification.md S3b, H2",
           "script": "index-deconvolution/experiments/screen_s3b_multi_step.py",
           "tool_versions": tool_versions(),
           "settings": {"limit_s": LIMIT_S, "reps": REPS, "reach_steps": T_STEPS},
           "arms": {"ours_attr": "num_attractors, EXHAUSTIVE over 2^n states",
                    "ours_fixed": "none exists", "ours_reach": "none exists",
                    "index_based_arm_for_any_S3b_class": "none exists"},
           "summary": summary, "checks": checks, "h2_s3b": h2, "rows": rows}
    write_json(RES / "s3b_multi_step.json", out)
    print("checks:", json.dumps(checks))
    print("H2(S3b):", json.dumps(h2))
    for q in summary:
        print(q, {t: (v["answered"], v["timeouts"], v["max_s_by_n"].get("200"))
                  for t, v in summary[q].items()})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        res = worker(*sys.argv[2:6])
        print("RESULT\t" + json.dumps(res))
    else:
        main()
