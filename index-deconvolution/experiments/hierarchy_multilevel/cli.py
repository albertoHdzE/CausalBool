"""HID multilevel v1 commands (run from ``index-deconvolution/``)::

  P="PYTHONPATH=experiments:.:../src ../venv/bin/python -B -m hierarchy_multilevel.cli"
  $P fixtures           write the declared fixture inputs (hashes) for the engineering suite
  $P lock               implementation lock + source snapshot + environment + import probe
  $P run [--resume]     references, 96 A0 jobs, reproduction gate, 288 augmentation jobs
  $P report             tables, gap map, explanations, summary, REPORT.md, DECISION.json
  $P verify             lock re-check, read-only audit, row/archive/trace re-validation

Exit codes: 0 complete and valid; 2 invalid; 3 incomplete; 4 lock problem.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from hierarchy import benchmark as B

from . import ledger, preserve
from . import runner as RN
from .search import ARMS

D = RN.RUN_DIR
LOCK = D / "implementation_lock.json"
EXIT_OK, EXIT_INVALID, EXIT_INCOMPLETE, EXIT_LOCK = 0, 2, 3, 4
CHECKPOINT_OVERHEAD_S = 15.0


def log_to(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a")

    def log(msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        fh.write(line + "\n")
        fh.flush()
        if "--quiet" not in sys.argv:
            print(line, flush=True)
    return log


# ---------------------------------------------------------------------------
# lock
# ---------------------------------------------------------------------------

def write_lock() -> dict:
    if LOCK.exists():
        raise SystemExit("implementation_lock.json already exists; a lock is written once")
    members = preserve.lock_members()
    closure = {m: preserve.sha_file(preserve.REPO / m) for m in members if m.endswith(".py")}
    tar = preserve.snapshot_tar(members)
    B.atomic_write(D / "source_snapshot.tar", tar)
    fixtures = D / "fixtures" / "declared_inputs.json"
    lock = {"run_id": RN.RUN_ID, "schema": "hierarchy-multilevel-feasibility-v1",
            "kind": "reproducibility lock over exposed-data development; not blinded preregistration",
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_head": preserve.git_head(),
            "closure": closure,
            "members": {m: preserve.sha_file(preserve.REPO / m) for m in members},
            "snapshot_sha256": preserve.sha(tar), "snapshot_members": len(members),
            "arm_configs": {k: {"config": v.as_dict(), "sha256": v.sha256()} for k, v in ARMS.items()},
            "baseline": {"method": "hid_full", "registry": "search-v2",
                         "config_sha256": B.method_config_sha("hid_full", __import__(
                             "hierarchy.study", fromlist=["get_study"]).get_study("search-v2"))},
            "cases_sha256": preserve.sha_file(RN.PACKET / "CASES.json"),
            "contract_sha256": preserve.sha_file(RN.PACKET / "contract.json"),
            "fixtures_declared_sha256": preserve.sha_file(fixtures) if fixtures.exists() else None,
            "resources": {"child_wall_s": RN.WALL_S, "child_rss_bytes": RN.RSS,
                          "max_children": RN.MAX_CHILDREN},
            "environment": preserve.environment(),
            "import_probe": preserve.import_probe()}
    B.atomic_write(LOCK, (json.dumps(lock, indent=1, sort_keys=True) + "\n").encode())
    B.atomic_write(D / "implementation_lock.sha256", (preserve.sha_file(LOCK) + "\n").encode())
    return lock


def lock_problems() -> tuple[str | None, list[str]]:
    if not LOCK.exists():
        return None, ["no lock"]
    sha = preserve.sha_file(LOCK)
    rec = (D / "implementation_lock.sha256").read_text().strip()
    lock = json.loads(LOCK.read_text())
    bad = [] if sha == rec else ["lock file hash differs from implementation_lock.sha256"]
    bad += [f"changed: {m}" for m, h in lock["closure"].items()
            if not (preserve.REPO / m).is_file() or preserve.sha_file(preserve.REPO / m) != h]
    bad += [f"arm config changed: {k}" for k, v in ARMS.items() if v.sha256() != lock["arm_configs"][k]["sha256"]]
    if not lock["import_probe"]["all_inside_index_deconvolution"]:
        bad.append("import probe resolved outside index-deconvolution")
    return sha, bad


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def budget_ok():
    rem = ledger.remaining("benchmark")
    need = RN.WALL_S + CHECKPOINT_OVERHEAD_S
    return (rem > need, f"benchmark remaining {rem:.0f} s <= {need:.0f} s")


def run(resume: bool) -> int:
    log = log_to(D / "logs" / "run.log")
    sha, bad = lock_problems()
    if bad:
        log(f"LOCK PROBLEMS: {bad[:10]}")
        return EXIT_LOCK
    specs = RN.case_specs()
    cases = {}
    for s in specs:
        cases[s["case_id"]] = RN.load_input(s)
    log(f"inputs: {len(cases)} decoded and validated")
    # imported references (not jobs)
    refs_path = D / "references.jsonl"
    refs = [RN.validate_references(s, cases[s["case_id"]].bits) for s in specs]
    B.atomic_write(refs_path, "".join(json.dumps(r, sort_keys=True) + "\n" for r in refs).encode())
    log(f"references: {sum(len(r['methods']) - 2 for r in refs)} constituent records, "
        f"{sum(r['portfolio']['matches_saved_baseline_best'] for r in refs)} portfolio matches, "
        f"{sum(len(r['problems']) for r in refs)} problems")
    intended = {"baseline": [f"{s['case_id']}.A0" for s in specs],
                "augmentation": [f"{s['case_id']}.{a}" for s in specs for a in RN.AUG_ARMS]}
    RN.write_json(D / "intended_jobs.json", {"lock_sha256": sha, **intended,
                                             "counts": {k: len(v) for k, v in intended.items()}})
    # A0
    todo = []
    for s in specs:
        data, _, why = RN.a0_verified(D, s, cases[s["case_id"]].bits, sha)
        if resume and data is not None:
            continue
        todo.append(s)
    log(f"A0: {len(todo)} jobs to run ({len(specs) - len(todo)} verified rows kept)")

    def launch_a0(s):
        return B._Job(cases[s["case_id"]], "hid_full", D, registry="search-v2")

    def finish_a0(s, job):
        row = RN.finish_a0(job, D, sha, s)
        if "--quiet" not in sys.argv or not row["reproduction"]["reproduced"]:
            log(f"A0 {s['case_id']} {row['status']} {row['archive_bits']} reproduced="
                f"{row['reproduction']['reproduced']} {row['reproduction']['mismatched_fields']}")
    q = RN.run_queue(todo, launch_a0, finish_a0, log, budget_ok)
    log(f"A0 queue: {q}")
    a0 = {}
    gate_fail = []
    for s in specs:
        data, row, why = RN.a0_verified(D, s, cases[s["case_id"]].bits, sha)
        if data is None:
            gate_fail.append(f"{s['case_id']}: {why}")
        else:
            a0[s["case_id"]] = (data, row)
    RN.write_json(D / "baseline_gate.json", {"verified": len(a0), "intended": len(specs),
                                             "failures": gate_fail, "pass": not gate_fail})
    log(f"baseline gate: {len(a0)}/{len(specs)} verified; failures {gate_fail[:5]}")
    if gate_fail:
        log("baseline reproduction gate FAILED: augmentation queue blocked")
        return EXIT_INVALID
    # augmentation
    jobs = []
    for s in specs:
        for arm in RN.AUG_ARMS:
            if resume and RN.aug_row_valid_for_resume(D, s, arm, sha):
                continue
            jobs.append((s, arm))
    log(f"augmentation: {len(jobs)} jobs to run")

    def launch_aug(item):
        s, arm = item
        data, row = a0[s["case_id"]]
        rd, _, why = RN.a0_verified(D, s, cases[s["case_id"]].bits, sha)   # re-verify at launch
        if rd is None:
            RN.unavailable_row(D, s, arm, sha, why)
            return None
        return RN.launch_aug(cases[s["case_id"]], arm, D, D / row["archive_path"], str(LOCK))

    def finish_aug(item, job):
        s, arm = item
        row = RN.finish_aug(job, D, sha, a0[s["case_id"]][0], a0[s["case_id"]][1])
        if "--quiet" not in sys.argv or row["status"] != "ok":
            log(f"{arm} {s['case_id']} {row['status']} {row['archive_bits']} "
                f"(A0 {row['a0_archive_bits']}) {(row.get('selected') or {}).get('source')}")
    q = RN.run_queue(jobs, launch_aug, finish_aug, log, budget_ok)
    log(f"augmentation queue: {q}")
    RN.write_json(D / "queue_summary.json", {"augmentation": q})
    return EXIT_OK if not q["unlaunched"] else EXIT_INCOMPLETE


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def verify() -> int:
    from . import audit, report
    sha, bad = lock_problems()
    out = {"lock_sha256": sha, "lock_problems": bad}
    summ = report.build(D, write=False)
    saved = json.loads((D / "summary.json").read_text())
    out["summary_recomputed_equal"] = json.dumps(summ, sort_keys=True) == json.dumps(saved, sort_keys=True)
    out["evidence_state"] = summ["evidence_state"]["state"]
    out["audit"] = {k: v for k, v in audit.audit(D).items() if k != "recomputed"}
    # every stored trace and partial view file re-hashed
    tr_bad = []
    for p in sorted((D / "rows").glob("*.json")):
        row = json.loads(p.read_text())
        if row.get("trace_path") and preserve.sha_file(D / row["trace_path"]) != row["trace_sha256"]:
            tr_bad.append(p.name)
    out["trace_hash_problems"] = tr_bad
    out["nested_view_equality"] = summ["nested_view_equality"]
    ok = (not bad and out["summary_recomputed_equal"] and out["audit"]["pass"] and not tr_bad
          and not summ["nested_view_equality"]["mismatches"])
    out["verification_pass"] = ok
    RN.write_json(D / "verification.json", out)
    print(json.dumps({k: out[k] for k in ("lock_problems", "summary_recomputed_equal",
                                          "evidence_state", "trace_hash_problems",
                                          "verification_pass")}))
    print(json.dumps({k: out["audit"][k] for k in ("pass", "problem_count", "archives_read")}))
    if not ok:
        return EXIT_INVALID
    return {"VALID_COMPLETE": EXIT_OK, "INCOMPLETE": EXIT_INCOMPLETE}.get(out["evidence_state"], EXIT_INVALID)


def main(argv) -> int:
    cmd = argv[0]
    if cmd == "fixtures":
        from .tests import fixtures
        out = fixtures.declare(D / "fixtures" / "declared_inputs.json")
        print(json.dumps({"distinct_inputs": out["distinct_inputs"], "max_bits": out["max_bits"]}))
        return 0
    if cmd == "lock":
        lock = write_lock()
        print(json.dumps({"closure_files": len(lock["closure"]), "snapshot": lock["snapshot_sha256"],
                          "probe_ok": lock["import_probe"]["all_inside_index_deconvolution"]}))
        return 0 if lock["import_probe"]["all_inside_index_deconvolution"] else EXIT_LOCK
    if cmd == "run":
        return run("--resume" in argv)
    if cmd == "report":
        from . import report
        s = report.build(D)
        print(json.dumps({"state": s["evidence_state"]["state"], "label": s["recommendation"]["label"],
                          "counts": s["counts"]}))
        return 0
    if cmd == "verify":
        return verify()
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
