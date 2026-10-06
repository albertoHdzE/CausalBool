"""task-compaction-v1-r1 -- the six declared semantic mutants of the isolated owner.

Each mutant is one exact textual replacement in a disposable copy of the isolated tree
(/tmp), followed by the owner fixture tests. A mutant is KILLED only if pytest exits 1
(test failures), not 2+ (collection/import error). Failing test ids and the first
error line of each are recorded.  Usage: python mutations.py <out.json>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
ISO = os.path.join(RUN, "isolated")
REPO = os.path.abspath(os.path.join(RUN, *[".."] * 4))
PY = os.path.join(REPO, "venv", "bin", "python")

MUTANTS = [
    ("MUT1_one_group_init", "    p = canonical_partition(outputs)\n    stages = [p]",
     "    p = [0] * N\n    stages = [p]"),
    ("MUT2_stop_after_first_update", "        if nxt == p:\n            break\n        p = nxt\n",
     "        p = nxt\n        break\n"),
    ("MUT3_first_action_only", "tuple(p[t[x]] for t in transitions)",
     "tuple(p[t[x]] for t in transitions[:1])"),
    ("MUT4_drop_state", "for t in transitions) for x in range(N)]",
     "for t in transitions) for x in range(N - 1)]"),
    ("MUT5_reverse_replay", "    for q in word:\n        if not _is_index(q)",
     "    for q in reversed(word):\n        if not _is_index(q)"),
    ("MUT6_identity_as_minimal", "    alpha = p\n    K = max(alpha) + 1",
     "    alpha = list(range(N))\n    K = max(alpha) + 1"),
]


def run_one(mid, old, new, base):
    work = os.path.join(base, mid)
    shutil.copytree(ISO, work)
    owner = os.path.join(work, "index-deconvolution", "src", "deconvolution.py")
    text = open(owner).read()
    if text.count(old) != 1:
        return {"id": mid, "error": f"anchor occurs {text.count(old)} times"}
    open(owner, "w").write(text.replace(old, new))
    idd = os.path.join(work, "index-deconvolution")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=os.path.join(idd, "src"))
    xml = os.path.join(work, "junit.xml")
    p = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--tb=short", "-rf",
                        "--junitxml", xml,
                        "-c", os.devnull, "--rootdir", idd,
                        os.path.join(idd, "tests", "test_task_compaction.py")],
                       capture_output=True, text=True, env=env, timeout=300)
    failed = re.findall(r"^FAILED (\S+)(?: - (.*))?$", p.stdout, re.M)
    caught = []
    if os.path.exists(xml):
        for tc in ET.parse(xml).iter("testcase"):
            for f in list(tc.iter("failure")) + list(tc.iter("error")):
                body = (f.text or "").splitlines()
                where = [ln.strip() for ln in body if re.match(r"^\S*test_task_compaction\.py:\d+", ln.strip())
                         or re.match(r"^\S*deconvolution\.py:\d+", ln.strip())]
                caught.append({"test": tc.get("name"), "message": (f.get("message") or "")[:240],
                               "assertion_site": where[-1] if where else None})
    return {"id": mid, "returncode": p.returncode, "killed": p.returncode == 1 and bool(failed),
            "n_failed": len(failed),
            "failures": caught,
            "summary": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-300:]}


def main(out):
    base = tempfile.mkdtemp(prefix="tc_mut_")
    res = [run_one(m, o, n, base) for m, o, n in MUTANTS]
    shutil.rmtree(base)
    doc = {"n_mutants": len(res), "killed": sum(r.get("killed", False) for r in res), "mutants": res}
    json.dump(doc, open(out, "w"), indent=1)
    for r in res:
        print(r["id"], "KILLED" if r.get("killed") else "SURVIVED", r.get("n_failed"), r.get("summary"))
    print(f"killed {doc['killed']} / {doc['n_mutants']}")
    return 0 if doc["killed"] == doc["n_mutants"] == 6 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
