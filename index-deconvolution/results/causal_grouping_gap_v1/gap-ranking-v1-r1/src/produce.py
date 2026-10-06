"""gap-ranking-v1-r1 -- score/rank process.  No access to outcomes.

Usage (PYTHONPATH = the declared route, see routes.py / run.sh):
    python produce.py <destination>
Writes trajectories.json, occurrences.jsonl, scores.json, ranks.json, imports.json,
cost.json and seal.json into <destination>.  The outcome guard is installed before any
study code is imported.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE) if HERE not in sys.path else None
import routes  # noqa: E402


def dump(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh, sort_keys=True, separators=(",", ":"))
        fh.write("\n")


def main(dest: str) -> int:
    dest = os.path.abspath(dest)
    if os.path.exists(dest) and os.listdir(dest):
        raise SystemExit(f"refusing to overwrite non-empty {dest}")
    os.makedirs(dest, exist_ok=True)
    routes.install_outcome_guard(writable=dest)
    # route check: sys.path[0] is this directory, then the declared three entries
    imports = routes.assert_route()
    import study as S
    import gapscore as G

    t0 = time.perf_counter()
    trajs = {}
    models = {}
    for mid in S.MODEL_IDS:
        m = S.Model(mid)
        models[mid] = m
        trajs[mid] = [G.trajectory(m.F, x0) for x0 in G.start_states(m.n)]
    t_traj = time.perf_counter() - t0

    t1 = time.perf_counter()
    occ_path = os.path.join(dest, "occurrences.jsonl")
    scores, ranks = [], []
    with open(occ_path, "w") as occ:
        for mid in S.MODEL_IDS:
            n = models[mid].n
            cands = [c for c in S.candidates(n) if G.is_ranked(c)]
            for tau in S.TAUS:
                sampled = [G.sample(xs, tau) for xs in trajs[mid]]
                wo_scores = {}
                for w in S.WIDTHS:
                    for o in range(w):
                        blocks = S.partition(w, o, n)
                        recs = G.occurrence_records(sampled, blocks)
                        sc = G.pooled_score(recs)
                        wo_scores[(w, o)] = sc
                        scores.append({"model": mid, "tau": tau, "w": w, "o": o,
                                       "frames": len(sampled[0]), "blocks": blocks,
                                       "n_sets": len(recs), **sc})
                        for r in recs:
                            occ.write(json.dumps({"model": mid, "tau": tau, "w": w, "o": o,
                                                  **r}, sort_keys=True,
                                                 separators=(",", ":")) + "\n")
                order = G.rank(cands, wo_scores)
                cand_rows = []
                for c in cands:
                    s = G.candidate_score(c, wo_scores)
                    cand_rows.append({
                        "id": c["id"], "candidate": {k: v for k, v in c.items() if k != "id"},
                        "score": None if s is None or not s["available"]
                        else [s["regular"], s["eligible"]]})
                ranks.append({"model": mid, "tau": tau, "N": len(cands),
                              "gap_order": order, "canonical_order": G.canonical(cands),
                              "candidates": cand_rows})
    t_score = time.perf_counter() - t1

    dump(os.path.join(dest, "trajectories.json"),
         {mid: [{"x0": xs[0], "states": xs} for xs in trajs[mid]] for mid in trajs})
    dump(os.path.join(dest, "scores.json"), scores)
    dump(os.path.join(dest, "ranks.json"), ranks)
    dump(os.path.join(dest, "imports.json"), imports)
    dump(os.path.join(dest, "cost.json"), {"trajectory_seconds": round(t_traj, 4),
                                           "scoring_and_ranking_seconds": round(t_score, 4)})
    seal = {f: routes.sha256(os.path.join(dest, f)) for f in
            ("trajectories.json", "occurrences.jsonl", "scores.json", "ranks.json",
             "imports.json")}
    seal["counts"] = {"scores": len(scores), "ranked_lists": len(ranks),
                      "rank_positions": sum(len(r["gap_order"]) for r in ranks),
                      "trajectories": sum(len(v) for v in trajs.values())}
    dump(os.path.join(dest, "seal.json"), seal)
    print(json.dumps(seal["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
