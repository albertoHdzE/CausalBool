"""gap-ranking-v1-r1 -- mutation harness (PROTOCOL.md §6).

Each mutant is a textual substitution in a temporary copy of gapscore.py.  The focused
tests run against the copy (GGAP_SRC); a mutant is KILLED only if a declared relevant
test fails by assertion and the suite collected without error.
Usage: python mutations.py <log json>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
TESTS = os.path.join(RUN, "tests", "test_gap_ranking.py")

MUTANTS = [
    ("flip_indices",
     "                frames = token_occurrence_frames(toks, v)\n",
     "                frames = [i for i in range(1, len(toks)) if toks[i] != toks[i - 1] and toks[i] == v]\n",
     ["test_constant_tokens_keep_every_frame", "test_tok_fixture_frames_and_gaps"]),
    ("concatenate_trajectories",
     "    for t, states in enumerate(sampled):\n",
     "    for t, states in enumerate([[x for s in sampled for x in s]]):\n",
     ["test_trajectories_never_joined"]),
    ("average_trajectory_fractions",
     '    return {"regular": num, "eligible": den, "available": den > 0}\n',
     '    _fr = [Fraction(sum(1 for r in recs if r["traj"] == t and r["regular"]), e)'
     ' for t in sorted({r["traj"] for r in recs})'
     ' for e in [sum(1 for r in recs if r["traj"] == t and r["eligible"])] if e]\n'
     '    _m = sum(_fr) / len(_fr) if _fr else Fraction(0)\n'
     '    return {"regular": _m.numerator, "eligible": _m.denominator if _fr else 0,'
     ' "available": bool(_fr)}\n',
     ["test_counting_pool_differs_from_mean_of_fractions"]),
    ("float_tolerance_ties",
     "    avail.sort(key=lambda p: (-p[0], p[1]))\n",
     "    avail.sort(key=lambda p: (-round(float(p[0]), 6), p[1]))\n",
     ["test_rank_exact_rational_comparison"]),
    ("unavailable_first",
     "    return [cid for _, cid in avail] + [cid for _, cid in unavail]\n",
     "    return [cid for _, cid in unavail] + [cid for _, cid in avail]\n",
     ["test_rank_ties_zero_unavailable_inheritance_duplicates"]),
    ("deduplicate_candidates",
     "    avail, unavail = [], []\n",
     "    avail, unavail = [], []\n"
     "    cands = list({(c['family'], c.get('w'), c.get('o'), c.get('a'), c.get('len')): c"
     " for c in cands}.values())\n",
     ["test_rank_ties_zero_unavailable_inheritance_duplicates"]),
]


def run_mutant(name, old, new, relevant):
    tmp = tempfile.mkdtemp(prefix=f"ggap_mut_{name}_")
    try:
        shutil.copy(os.path.join(HERE, "gapscore.py"), tmp)
        p = os.path.join(tmp, "gapscore.py")
        src = open(p).read()
        if src.count(old) != 1:
            return {"mutant": name, "status": "NOT_APPLIED", "reason": "anchor not unique"}
        open(p, "w").write(src.replace(old, new))
        env = {**os.environ, "GGAP_SRC": tmp, "PYTHONDONTWRITEBYTECODE": "1"}
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--tb=line",
             "-c", os.devnull, "--rootdir", RUN, "--confcutdir", RUN, TESTS],
            capture_output=True, text=True, env=env)
        text = out.stdout + out.stderr
        failed = sorted(set(re.findall(r"FAILED \S*::(\w+)", text)))
        collect_error = "error" in text.splitlines()[-1].lower() if text.strip() else True
        killed_by = [t for t in relevant if t in failed]
        return {"mutant": name, "status": "KILLED" if killed_by and not collect_error
                else "SURVIVED", "killed_by": killed_by, "failed_tests": failed,
                "collect_error": collect_error, "summary": text.strip().splitlines()[-1]}
    finally:
        shutil.rmtree(tmp)


def main(log):
    res = [run_mutant(*m) for m in MUTANTS]
    with open(log, "w") as fh:
        json.dump(res, fh, indent=1)
        fh.write("\n")
    for r in res:
        print(r["mutant"], r["status"], r.get("killed_by"))
    return 0 if all(r["status"] == "KILLED" for r in res) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
