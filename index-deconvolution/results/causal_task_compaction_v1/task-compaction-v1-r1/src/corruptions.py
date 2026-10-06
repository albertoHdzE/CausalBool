"""task-compaction-v1-r1 -- four manifested semantic corruptions of COPIES of a production.

Each copy gets a manifest of the exact change; the audit runs on it with
--bypass-integrity so that the seal mismatch cannot be what rejects it: the named
scientific assertion must fire. The original production is never written.
Usage: python corruptions.py <production dir> <out dir>
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 5))
PY = os.path.join(REPO, "venv", "bin", "python")


def rw(path, fn):
    d = json.load(open(path))
    change = fn(d)
    with open(path, "w") as fh:
        json.dump(d, fh, sort_keys=True, separators=(",", ":"))
        fh.write("\n")
    return change


def pick_cell(prod):
    for f in sorted(os.listdir(os.path.join(prod, "cells"))):
        d = json.load(open(os.path.join(prod, "cells", f)))
        if d["regime"] == "INTERVENTION" and max(d["alpha"]) >= 1:
            return f
    raise RuntimeError("no INTERVENTION cell with K >= 2")


def cor1(p, cell):
    def f(d):
        old = d["decoder"][0]
        d["decoder"][0] = 1 - old
        return {"file": f"cells/{cell}", "field": "decoder[0]", "old": old, "new": d["decoder"][0]}
    return rw(os.path.join(p, "cells", cell), f), ["decoder value check"]


def cor2(p, cell):
    def f(d):
        q = len(d["macro"]) - 1
        K = len(d["macro"][q])
        old = d["macro"][q][0]
        d["macro"][q][0] = (old + 1) % K
        return {"file": f"cells/{cell}", "field": f"macro[{q}][0]", "old": old, "new": d["macro"][q][0]}
    return rw(os.path.join(p, "cells", cell), f), ["macro-transition check"]


def cor3(p, _):
    def f(d):
        old = {k: d[k] for k in ("alpha", "stages", "K", "strict_rounds", "representatives", "decoder",
                                 "macro", "coarsening")}
        ident = list(range(len(d["outputs"])))
        d.update({"alpha": ident, "stages": [d["stages"][0], ident, ident], "K": len(ident), "strict_rounds": 1,
                  "representatives": ident, "decoder": list(d["outputs"]), "macro": [list(t) for t in d["transitions"]],
                  "coarsening": [d["stages"][0], ident]})
        return {"file": "fixtures/FX1_identity.json", "field": "certificate replaced by stable identity partition",
                "old": old, "new": {"alpha": ident}}
    return rw(os.path.join(p, "fixtures", "FX1_identity.json"), f), ["stage-induction check"]


def cor4(p, _):
    cells = sorted(os.listdir(os.path.join(p, "cells")))
    gone, hit = cells[3], cells[5]
    os.remove(os.path.join(p, "cells", gone))

    def f(d):
        old = d["summary"]["K_star"]
        d["summary"]["K_star"] = old + 1
        return {"field": "summary.K_star", "old": old, "new": old + 1}
    ch = rw(os.path.join(p, "cells", hit), f)
    return {"removed": f"cells/{gone}", "corrupted": f"cells/{hit}", **ch}, ["reported numbers differ"]


def main(prod, out):
    if os.path.exists(out):
        print(f"refusing: {out} exists")
        return 2
    os.makedirs(out)
    cell = pick_cell(prod)
    results = []
    for cid, fn in (("COR1_decoder_value", cor1), ("COR2_macro_entry", cor2),
                    ("COR3_identity_certificate_fx1", cor3), ("COR4_remove_and_corrupt", cor4)):
        copy = os.path.join(out, cid, "production")
        shutil.copytree(prod, copy)
        change, expect = fn(copy, cell)
        json.dump({"id": cid, "source": os.path.abspath(prod), "change": change},
                  open(os.path.join(out, cid, "CORRUPTION_MANIFEST.json"), "w"), indent=1, sort_keys=True)
        adir = os.path.join(out, cid, "audit")
        p = subprocess.run([PY, os.path.join(HERE, "audit.py"), copy, adir, "--bypass-integrity"],
                           capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        a = json.load(open(os.path.join(adir, "audit.json")))
        fired = [i for i in a["invalid"] if any(e in i["check"] for e in expect)]
        ok = a["status"] == "INVALID" and bool(fired)
        row = {"id": cid, "status": a["status"], "expected_assertion": expect, "fired": fired[:3],
               "n_invalid": a["n_invalid"], "n_missing": a["n_missing"], "missing": a["missing"],
               "integrity_mismatches_bypassed": a.get("integrity_mismatches"), "audit_returncode": p.returncode}
        if cid.startswith("COR3"):
            fx = a.get("fixture_FX1", {})
            row["fx1_validity"], row["fx1_minimality"] = fx.get("validity"), fx.get("minimality")
            ok = ok and fx.get("validity") is True and fx.get("minimality") is False
        if cid.startswith("COR4"):
            ok = ok and a["n_missing"] > 0
        row["as_required"] = ok
        results.append(row)
        print(cid, a["status"], "as_required" if ok else "NOT AS REQUIRED", [f["check"][:60] for f in fired[:1]])
    doc = {"n": len(results), "as_required": sum(r["as_required"] for r in results), "results": results}
    json.dump(doc, open(os.path.join(out, "corruptions.json"), "w"), indent=1, sort_keys=True)
    print(f"as required {doc['as_required']} / {doc['n']}")
    return 0 if doc["as_required"] == doc["n"] == 4 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
