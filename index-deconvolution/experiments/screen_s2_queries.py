"""screen_s2_queries.py -- identification screen, step 5: S2 and gate H1.

PROTOCOL sec.2 row S2: the learner asks for the successor of states, under a
budget.  Our arm: NONE EXISTS -- an oracle-mode deconvolution would be new
work and is not built here (PROTOCOL sec.2, kick-off rules).

Competitors, in the order of the protocol's row:
  1. Akutsu 2003, strategic disruptions and over-expressions [9]: no released
     software could be found to install; recorded and replaced by the next
     competitor in the row, as PROTOCOL sec.2 prescribes.
  2. Akutsu 1999, identification from random state-successor samples [8].
     Its consistency problem is solved by BoolNet's reconstructNetwork
     (method "bestfit", the best-fit extension of [10], which reduces to
     consistency on noise-free data; and method "reveal"), run as its own
     software.  Each sample is one query: a uniformly random state and its
     successor.  BoolNet is given maxK = k = 3, the in-degree bound of the
     corpus and of Q_LB.

Measure: the smallest number of samples m at which the
recovered network is exact, checked by verify_forward (n <= 15) or by its
owner's symbolic twin verify_forward_symbolic (canonical decision-diagram
identity over all 2**n states) above that; both are run at n <= 15 as a parity
guard.  Two criteria are reported:
  lenient  BoolNet's first-listed solution is exact;
  unique   it is exact AND BoolNet lists a single solution for every gene
           (the learner can certify it is done).
H1 is applied to the lenient criterion, which favours the competitor.

Samples are nested prefixes of one pinned random stream per network, so m is
searched by galloping (doubling) then integer bisection (monotone in m is assumed;
every probe is recorded so any non-monotonicity is visible).

Q_LB = ceil(log2 C(n, k) + 2**k), PROTOCOL sec.3.

Usage: venv/bin/python index-deconvolution/experiments/screen_s2_queries.py [--quiet]
"""

from __future__ import annotations

import math
import random
import tempfile
from pathlib import Path

from screen_common import RES, load_entry, load_manifest, log, write_json

from causalbool import repertoire, step
from deconvolution import (network_roots, symbolic_manager, verify_forward,
                           verify_forward_symbolic)
from screen_s1_full_table import run_boolnet

K = 3
M_START, M_MAX = 8, 4096
PROBE_LIMIT_S = 600
FULL_VERIFY_MAX_N = 15


def q_lb(n: int, k: int = K) -> int:
    return math.ceil(math.log2(math.comb(n, k)) + 2 ** k)


def exact_check(net, rec, rep):
    mgr = symbolic_manager(net.n)
    sym = verify_forward_symbolic(mgr, network_roots(mgr, net), rec)["exact"]
    if rep is not None:
        full = verify_forward(rep, rec)["exact"]
        return full, {"verify_forward": full, "symbolic": sym}
    return sym, {"symbolic": sym}


def search(probe, key):
    """Smallest integer m with probe(m)[key] True: gallop by doubling from
    M_START up to M_MAX, then bisect on the integers."""
    lo, m = 0, M_START
    while True:
        r = probe(m)
        if r.get("timeout"):
            return None, "timeout"
        if r[key]:
            break
        lo = m
        if m >= M_MAX:
            return None, f"not reached within {M_MAX} samples"
        m = min(2 * m, M_MAX)
    hi = m
    while hi - lo > 1:
        mid = (lo + hi) // 2
        r = probe(mid)
        if r.get("timeout"):
            return None, "timeout"
        if r[key]:
            hi = mid
        else:
            lo = mid
    return hi, "ok"


def main() -> None:
    manifest = load_manifest()
    entries = [e for e in manifest["entries"] if e["kind"] == "synthetic"]
    work = Path(tempfile.mkdtemp(prefix="screen_s2_"))
    rows, parity = [], []
    for e in entries:
        net = load_entry(e)
        n = net.n
        rng = random.Random(f"s2:{e['id']}")
        states = [[rng.randint(0, 1) for _ in range(n)] for _ in range(M_MAX)]
        pairs = [(s, step(net, s)) for s in states]
        rep = repertoire(net) if n <= FULL_VERIFY_MAX_N else None
        row = {"id": e["id"], "n": n, "k": K, "Q_LB": q_lb(n), "2xQ_LB": 2 * q_lb(n),
               "akutsu2003": "no released software found; replaced per PROTOCOL sec.2",
               "ours": "none exists (oracle-mode deconvolution would be new work)"}
        for method in ("bestfit", "reveal"):
            cache = {}

            def probe(m, method=method, cache=cache):
                if m in cache:
                    return cache[m]
                r = run_boolnet(pairs[:m], n, K, method, work, reps=1, limit_s=PROBE_LIMIT_S)
                res = {"m": m, "status": r["status"], "time_s": (r["times"] or [None])[0]}
                if str(r["status"]).startswith("timeout"):
                    res["timeout"] = True
                if r["net"] is not None:
                    ok, detail = exact_check(net, r["net"], rep)
                    if len(detail) == 2:
                        parity.append(detail["verify_forward"] == detail["symbolic"])
                    res.update(exact=ok, ambiguous_genes=r["ambiguous_genes"],
                               unique_exact=ok and r["ambiguous_genes"] == 0)
                else:
                    res.update(exact=False, unique_exact=False)
                cache[m] = res
                return res

            m_len, st_len = search(probe, "exact")
            m_uni, st_uni = search(probe, "unique_exact") if m_len is not None else (None, st_len)
            probes = [cache[i] for i in sorted(cache)]
            monotone = all(not (a.get("exact") and not b.get("exact"))
                           for a, b in zip(probes, probes[1:]))
            row[f"boolnet_{method}"] = {
                "m_exact_lenient": m_len, "status_lenient": st_len,
                "m_exact_unique": m_uni, "status_unique": st_uni,
                "ratio_to_Q_LB": None if m_len is None else round(m_len / row["Q_LB"], 2),
                "probes": probes, "probes_monotone": monotone}
        rows.append(row)
        log(e["id"], "Q_LB", row["Q_LB"], {m: (row[f"boolnet_{m}"]["m_exact_lenient"],
                                               row[f"boolnet_{m}"]["m_exact_unique"])
                                           for m in ("bestfit", "reveal")})
        write_json(RES / "s2_queries.json", {"partial": True, "rows": rows})

    # H1: at n >= 50, does the best competitor need at most 2 x Q_LB queries?
    h1_rows = []
    for r in rows:
        if r["n"] < 50:
            continue
        ms = [r[f"boolnet_{m}"]["m_exact_lenient"] for m in ("bestfit", "reveal")]
        ms = [m for m in ms if m is not None]
        best = min(ms) if ms else None
        h1_rows.append({"id": r["id"], "n": r["n"], "Q_LB": r["Q_LB"], "best_m": best,
                        "within_2xQ_LB": best is not None and best <= 2 * r["Q_LB"]})
    out = {"protocol": "PROTOCOL_screen_identification.md S2, H1",
           "script": "index-deconvolution/experiments/screen_s2_queries.py",
           "tool_versions": manifest["tool_versions"],
           "settings": {"k": K, "search": f"gallop by doubling from {M_START} to {M_MAX}, then integer bisection", "probe_limit_s": PROBE_LIMIT_S,
                        "boolnet_maxK": K, "sampling": "i.i.d. uniform states, nested prefixes"},
           "guards": {"verify_forward_equals_symbolic": f"{sum(parity)}/{len(parity)}"},
           "rows": rows,
           "h1": {"per_network": h1_rows,
                  "within_2xQ_LB": f"{sum(x['within_2xQ_LB'] for x in h1_rows)}/{len(h1_rows)}",
                  "no_headroom": bool(h1_rows) and all(x["within_2xQ_LB"] for x in h1_rows),
                  "gate": "H1 shows no S2 headroom iff the best competitor needs <= 2 x Q_LB at every n >= 50"}}
    write_json(RES / "s2_queries.json", out)
    print("guards:", out["guards"])
    print("H1:", out["h1"]["within_2xQ_LB"], "within 2xQ_LB at n>=50; no_headroom =", out["h1"]["no_headroom"])


if __name__ == "__main__":
    main()
