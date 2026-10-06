"""task-compaction-v1-r1 -- freeze before the single production run, and verify it.

Usage: python freeze.py write | python freeze.py verify <out.json>
Freezes: protocol snapshot, cases, fixtures, THEORY/SOURCES, every file of the isolated
tree (core revision, adopted study, tests, mirrored inputs), run-local orchestration,
audit, tests, the 21 declared input identities, the result schema and the expected ID sets.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(RUN, *[".."] * 4))
ISO = os.path.join(RUN, "isolated")
RUN_FILES = ["fixtures.json", "THEORY.md", "SOURCES.md", "protocol/CASES.json", "protocol/PROTOCOL.md",
             "protocol/THEORY_AND_FIXTURES.md", "protocol/OWNERSHIP.md", "protocol/NEXT_CLAUDE.md",
             "protocol/manifest.json", "src/produce.py", "src/audit.py", "src/corruptions.py",
             "src/mutations.py", "src/owner_check.py", "src/freeze.py", "src/preserve.py",
             "tests/test_audit_labels.py", "run.sh"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def current():
    iso = {}
    for d, dirs, fs in os.walk(ISO):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        for f in fs:
            p = os.path.join(d, f)
            iso[os.path.relpath(p, ISO)] = sha(p)
    man = json.load(open(os.path.join(RUN, "protocol", "manifest.json")))
    inputs = {k: sha(os.path.join(REPO, k)) for k in man["inputs_relative_to_repository_root"]}
    run = {k: sha(os.path.join(RUN, k)) for k in RUN_FILES}
    return iso, inputs, run, man


def schema():
    cases = json.load(open(os.path.join(RUN, "protocol", "CASES.json")))
    ids = sorted(c["cell_id"] * 1000 + k for c in cases["cells"] for k in range(c["n_candidates"]))
    cells = [f"cells/cell_{c['cell_id']:02d}.json" for c in cases["cells"]]
    cands = [f"candidates/cell_{c['cell_id']:02d}.jsonl" for c in cases["cells"]]
    models = ["M1", "M2", "M3", "M4"]
    det = (["cases.json", "imports.json", "summary.json", "seal.json", "fixtures/FX1_identity.json"]
           + [f"tables/{m}.json" for m in models] + [f"candidate_alphas/{m}.json" for m in models] + cells + cands)
    return {"expected_cell_ids": list(range(len(cases["cells"]))), "expected_record_id_count": len(ids),
            "expected_record_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
            "deterministic_production_artifacts": sorted(det), "nondeterministic_production_artifacts": ["cost.json"],
            "deterministic_audit_artifacts": ["audit.json"],
            "cell_fields": ["cell_id", "model", "task", "regime", "n", "N", "action_ids", "outputs", "alpha",
                            "stages", "strict_rounds", "representatives", "decoder", "macro", "coarsening",
                            "witnesses", "summary"],
            "record_fields": ["record_id", "cell_id", "candidate_id", "candidate", "K_candidate", "decodable",
                              "decode_conflict", "closed", "failing_actions", "closure_witnesses",
                              "task_sufficient", "is_control", "factors_through", "K_minus_Kstar", "K_ratio",
                              "identical_to_optimum", "null_reason"]}


def main(argv):
    iso, inputs, run, man = current()
    if argv[0] == "write":
        out = os.path.join(RUN, "freeze.json")
        if os.path.exists(out):
            print("refusing: freeze.json exists")
            return 2
        bad = [k for k, v in man["inputs_relative_to_repository_root"].items() if inputs[k] != v]
        if bad:
            print("refusing: input identity differs from manifest", bad)
            return 1
        doc = {"run_id": "task-compaction-v1-r1", "isolated": iso, "inputs": inputs, "run_files": run,
               "schema": schema(), "python": sys.version, "platform": platform.platform(),
               "interpreter": os.path.relpath(sys.executable, REPO)}
        json.dump(doc, open(out, "w"), indent=1, sort_keys=True)
        print(f"frozen: {len(iso)} isolated, {len(inputs)} inputs, {len(run)} run files")
        return 0
    fz = json.load(open(os.path.join(RUN, "freeze.json")))
    diff = {k: sorted(x for x in set(fz[k]) | set(cur) if fz[k].get(x) != cur.get(x))
            for k, cur in (("isolated", iso), ("inputs", inputs), ("run_files", run))}
    res = {"ok": not any(diff.values()), "differences": diff,
           "checked": {k: len(fz[k]) for k in ("isolated", "inputs", "run_files")}}
    json.dump(res, open(argv[1], "w"), indent=1, sort_keys=True)
    print(json.dumps({"ok": res["ok"], "checked": res["checked"]}))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
