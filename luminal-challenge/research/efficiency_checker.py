"""Successor evidence checker: historical deviations versus unapproved failures (R3).

Plan ``CLAUDE_PHASE2_EFFICIENCY_PHASE.md`` section 3, R3. The historical
checker ``research/next_round_checker.py`` is NOT changed and NOT re-scored:
it is run as it is, in its own process, against the historical run, and its
complete finding list (not the 200-entry excerpt it writes) is retained. Each
finding is then classified:

- ``APPROVED_HISTORICAL_DEVIATION`` only when it matches a disposition in
  ``DISPOSITIONS`` EXACTLY -- finding code, detail, count, file, hashes and
  scope -- AND every evidentiary precondition of that disposition holds now;
- ``UNAPPROVED`` otherwise. A known code with a different detail, count, file
  or hash is unapproved. A disposition whose evidence fails leaves its
  findings unapproved; nothing is waived by code alone.

The two dispositions the lead allowed (``lead_next_round_review_20260925``):

D1 ``FROZEN_SOURCE_CHANGED`` x1, ``research/next_round_analysis.py``: the
   report-only None-filter. Preconditions: the at-freeze snapshot hashes
   ``a5ba2988...`` and equals the freeze's ``reporting`` hash; the live file
   hashes ``b6b69684...`` (POST_FREEZE_CHANGES.json); the ONLY AST difference is
   one ``if value is None: continue`` inside ``per_program_median``; the
   descriptive fields that differ are enumerated; the successor auditor
   independently reproduces the primary and candidate estimates (PASS, and no
   PRIMARY/CANDIDATE_ENDPOINTS finding).
D2 ``ORACLE_LEAK`` x420: dependency capability, not data access.
   Preconditions: the finding keys are exactly the 420 ``L_orderings`` keys; the
   guarded replay (``ranker_replay/REPLAY_EVALUATION.json``) is PASS on 420/420
   with those keys, its rows hash as evaluated, the guard refused both planted
   violations, and the replay workspace ran the extraction whose hash is live.

The checker also verifies that every pre-existing source and every historical
result still hashes as in this phase's starting manifests (``SOURCE_CHANGED``,
``HISTORICAL_RESULT_CHANGED``): those are never approvable.

Usage::

    PYTHONPATH=.reference:. python -m research.efficiency_checker --run EFFICIENCY_RUN
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import subprocess
from pathlib import Path

from research import efficiency_common as ec
from research import optimization_common as oc

HISTORICAL_RUN = ec.NEXT_ROUND_RUN
ANALYSIS = "research/next_round_analysis.py"
ANALYSIS_AT_FREEZE = HISTORICAL_RUN / "post_freeze" / "next_round_analysis.AT_FREEZE.py"
HASH_AT_FREEZE = "a5ba29881bc1a0f4458937122307d58c9fa50ed3827149231fb9327ebf9df6b8"
HASH_AFTER = "b6b6968428b4faefc421ce451d49590d162942b51eb212851756736902217bd7"
OWNED_PREFIXES = ("research/efficiency_", "research_tests/test_efficiency_")

DISPOSITIONS = {
    "D1": {"code": "FROZEN_SOURCE_CHANGED", "count": 1,
           "detail": "['research/next_round_analysis.py']",
           "scope": "report-only None filter in next_round_analysis.per_program_median"},
    "D2": {"code": "ORACLE_LEAK", "count": 420,
           "detail": "the 420 L_orderings row keys",
           "scope": "module-load capability in ranker processes; guarded replay reproduces"},
}

_DRIVER = r'''
import json, sys
from pathlib import Path
from research import next_round_checker as c
checker = c.Checker(Path(sys.argv[1]))
report = checker.run_all()
sys.stdout.write(json.dumps({"report": report, "all_findings": checker.findings}))
'''


def historical_findings(out: Path) -> dict:
    """Run the unchanged historical checker; keep every finding."""

    proc = subprocess.run([oc.PYTHON, "-c", _DRIVER, str(HISTORICAL_RUN)], cwd=str(ec.ROOT),
                          capture_output=True, text=True,
                          env={"PYTHONPATH": f"{ec.ROOT / '.reference'}:{ec.ROOT}",
                               "PATH": "/usr/bin:/bin", "HOME": str(Path.home())})
    (out / "historical_checker.stderr").write_text(proc.stderr)
    payload = dict(json.loads(proc.stdout), exit_code=proc.returncode)
    oc.write_json(out / "HISTORICAL_CHECKER_FULL.json", payload)
    return payload


# --------------------------------------------------------------------------
# Evidence for the dispositions
# --------------------------------------------------------------------------


def _function(tree: ast.Module, name: str):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


class _DropNoneSkip(ast.NodeTransformer):
    """Remove exactly ``if value is None: continue`` statements."""

    removed = 0

    def visit_If(self, node):
        self.generic_visit(node)
        test = node.test
        if (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
                and test.left.id == "value" and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Is) and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None and len(node.body) == 1
                and isinstance(node.body[0], ast.Continue) and not node.orelse):
            _DropNoneSkip.removed += 1
            return None
        return node


def analysis_scope(at_freeze_text: str, live_text: str) -> dict:
    before, after = ast.parse(at_freeze_text), ast.parse(live_text)
    names_before = [getattr(n, "name", None) or ast.dump(n) for n in before.body]
    names_after = [getattr(n, "name", None) or ast.dump(n) for n in after.body]
    changed = [getattr(a, "name", ast.dump(a)[:40]) for a, b in zip(after.body, before.body)
               if ast.dump(a) != ast.dump(b)]
    _DropNoneSkip.removed = 0
    stripped = _DropNoneSkip().visit(_function(ast.parse(live_text), "per_program_median"))
    equal_after_strip = ast.dump(stripped) == ast.dump(_function(before, "per_program_median"))
    return {"same_top_level_names": names_before == names_after,
            "changed_definitions": changed, "none_skips_removed": _DropNoneSkip.removed,
            "per_program_median_equal_after_removing_the_skip": equal_after_strip,
            "exact_scope": (names_before == names_after and changed == ["per_program_median"]
                            and _DropNoneSkip.removed == 1 and equal_after_strip)}


def affected_descriptive_fields() -> list:
    """(arm@budget, field) cost entries whose rows hold None: only these can differ."""

    rows = [json.loads(line) for line in
            (HISTORICAL_RUN / "stages/C_confirmation/rows.jsonl").read_text().splitlines()]
    affected = set()
    for r in rows:
        for field in ("compile_seconds", "bootstrap_seconds", "optimisation_seconds",
                      "validate_seconds", "import_seconds"):
            if (r.get("result") or {}).get(field, 0) is None:
                affected.add((f"{r['arm']}@{r['budget_seconds']}", field))
    return sorted(f"COMPARISON.json::costs.{a}.{f}" for a, f in affected)


def evidence(run: Path, audit_path: Path) -> dict:
    frozen = json.loads((HISTORICAL_RUN / "FROZEN_SELECTION.json").read_text())
    post = json.loads((HISTORICAL_RUN / "POST_FREEZE_CHANGES.json").read_text())["changes"]
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
    audit_codes = set((audit or {}).get("finding_codes", {}))
    replay_dir = Path(run) / "ranker_replay"
    replay = (json.loads((replay_dir / "REPLAY_EVALUATION.json").read_text())
              if (replay_dir / "REPLAY_EVALUATION.json").exists() else None)
    controls = (json.loads((replay_dir / "GUARD_CONTROLS.json").read_text())
                if (replay_dir / "GUARD_CONTROLS.json").exists() else None)
    workspace = (json.loads((replay_dir / "WORKSPACE_MANIFEST.json").read_text())
                 if (replay_dir / "WORKSPACE_MANIFEST.json").exists() else None)
    orderings = [json.loads(line)["key"] for line in
                 (HISTORICAL_RUN / "stages/L_orderings/rows.jsonl").read_text().splitlines()]
    return {
        "D1": {
            "at_freeze_sha256": oc.file_sha256(ANALYSIS_AT_FREEZE),
            "freeze_reporting_sha256": frozen["reporting"].get("next_round_analysis.py"),
            "live_sha256": oc.file_sha256(ec.ROOT / ANALYSIS),
            "post_freeze_record": [{k: c[k] for k in ("file", "hash_at_freeze", "hash_after")}
                                   for c in post],
            "scope": analysis_scope(ANALYSIS_AT_FREEZE.read_text(),
                                    (ec.ROOT / ANALYSIS).read_text()),
            "affected_descriptive_fields": affected_descriptive_fields(),
            "successor_audit_status": (audit or {}).get("status"),
            "successor_audit_primary_or_candidate_findings": sorted(
                audit_codes & {"PRIMARY", "CANDIDATE_ENDPOINTS", "C_COSTS", "PUBLIC_SCORE"}),
        },
        "D2": {
            "ordering_keys": orderings,
            "replay_status": (replay or {}).get("status"),
            "replay_rows": (replay or {}).get("rows"),
            "replay_passed": (replay or {}).get("passed"),
            "replay_keys_equal_source": (replay or {}).get("keys_equal_source"),
            "replay_rows_sha256_recorded": (replay or {}).get("rows_sha256"),
            "replay_rows_sha256_now": oc.file_sha256(replay_dir / "rows.jsonl"),
            "guard_controls": (controls or {}).get("status"),
            "workspace_ranker_sha256": ((workspace or {}).get("code", {})
                                        .get("efficiency_ranker.py", {}).get("copy_sha256")),
            "live_ranker_sha256": oc.file_sha256(ec.ROOT / "research/efficiency_ranker.py"),
        },
    }


def preconditions(ev: dict) -> dict:
    d1, d2 = ev["D1"], ev["D2"]
    one = {
        "at_freeze_hash": d1["at_freeze_sha256"] == HASH_AT_FREEZE,
        "freeze_records_at_freeze_hash": d1["freeze_reporting_sha256"] == HASH_AT_FREEZE,
        "live_hash_as_disclosed": d1["live_sha256"] == HASH_AFTER,
        "disclosure_names_this_change_only": d1["post_freeze_record"] == [
            {"file": ANALYSIS, "hash_at_freeze": HASH_AT_FREEZE, "hash_after": HASH_AFTER}],
        "exact_scope": d1["scope"]["exact_scope"],
        "affected_fields_are_control_costs_only": bool(d1["affected_descriptive_fields"]) and all(
            ".classical@None." in f or ".accepted_bootstrap@None." in f
            for f in d1["affected_descriptive_fields"]),
        "successor_audit_pass": d1["successor_audit_status"] == "PASS"
        and not d1["successor_audit_primary_or_candidate_findings"],
    }
    two = {
        "replay_pass": d2["replay_status"] == "PASS",
        "replay_complete": d2["replay_rows"] == d2["replay_passed"] == 420,
        "replay_keys_equal_source": d2["replay_keys_equal_source"] is True,
        "replay_rows_unchanged": d2["replay_rows_sha256_recorded"] is not None
        and d2["replay_rows_sha256_recorded"] == d2["replay_rows_sha256_now"],
        "guard_refused_planted_violations": d2["guard_controls"] == "PASS",
        "replayed_extraction_is_live": d2["workspace_ranker_sha256"] is not None
        and d2["workspace_ranker_sha256"] == d2["live_ranker_sha256"],
    }
    return {"D1": one, "D2": two}


def classify(findings: list, ev: dict) -> dict:
    """Exact matching of every historical finding against the two dispositions."""

    pre = preconditions(ev)
    by_code = collections.defaultdict(list)
    for f in findings:
        by_code[f["code"]].append(f)
    approved, unapproved, dispositions = [], [], {}
    d1 = by_code.pop("FROZEN_SOURCE_CHANGED", [])
    ok1 = (len(d1) == DISPOSITIONS["D1"]["count"]
           and all(f["detail"] == DISPOSITIONS["D1"]["detail"] for f in d1)
           and all(pre["D1"].values()))
    dispositions["D1"] = {"matched_findings": len(d1), "preconditions": pre["D1"],
                          "approved": ok1 and bool(d1)}
    (approved if ok1 else unapproved).extend(
        dict(f, disposition="D1" if ok1 else None) for f in d1)
    d2 = by_code.pop("ORACLE_LEAK", [])
    keys = [f["detail"] for f in d2]
    ok2 = (len(d2) == DISPOSITIONS["D2"]["count"] and len(set(keys)) == len(keys)
           and sorted(keys) == sorted(ev["D2"]["ordering_keys"]) and all(pre["D2"].values()))
    dispositions["D2"] = {"matched_findings": len(d2), "preconditions": pre["D2"],
                          "keys_equal_the_420_ordering_rows": sorted(keys) == sorted(
                              ev["D2"]["ordering_keys"]),
                          "approved": ok2 and bool(d2)}
    (approved if ok2 else unapproved).extend(
        dict(f, disposition="D2" if ok2 else None) for f in d2)
    for code, items in by_code.items():
        unapproved.extend(dict(f, disposition=None) for f in items)
    return {"approved": approved, "unapproved": unapproved, "dispositions": dispositions}


# --------------------------------------------------------------------------
# Immutability since the start of this phase
# --------------------------------------------------------------------------


def _manifest(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        digest, name = line.split(None, 1)
        out[name.strip()] = digest
    return out


def immutability(run: Path, source_manifest: Path = None, results_manifest: Path = None) -> dict:
    starting = Path(run) / "SOURCE_MANIFESTS" / "starting"
    sources = _manifest(source_manifest or starting / "source_sha256.txt")
    results = _manifest(results_manifest or starting / "historical_results_sha256.txt")
    changed_sources = sorted(n for n, d in sources.items()
                             if not n.startswith(OWNED_PREFIXES)
                             and oc.file_sha256(ec.ROOT / n) != d)
    changed_results = sorted(n for n, d in results.items() if oc.file_sha256(ec.ROOT / n) != d)
    return {"sources_checked": len(sources), "results_checked": len(results),
            "changed_sources": changed_sources, "changed_results": changed_results}


def run_checker(run: Path, audit_path: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    package = subprocess.run([oc.PYTHON, str(ec.PACKAGE / "verify_package.py")],
                             cwd=str(ec.ROOT), capture_output=True, text=True)
    historical = historical_findings(out)
    ev = evidence(run, audit_path)
    result = classify(historical["all_findings"], ev)
    immut = immutability(run)
    unapproved = list(result["unapproved"])
    unapproved += [{"code": "SOURCE_CHANGED", "detail": n} for n in immut["changed_sources"]]
    unapproved += [{"code": "HISTORICAL_RESULT_CHANGED", "detail": n}
                   for n in immut["changed_results"]]
    if package.returncode != 0:
        unapproved.append({"code": "PACKAGE_VERIFY", "detail": package.stderr[-300:]})
    if not immut["sources_checked"] or not immut["results_checked"]:
        unapproved.append({"code": "EMPTY_MANIFEST", "detail": "a manifest scanned zero files"})
    report = {
        "historical_checker": {"exit_code": historical["exit_code"],
                               "status": historical["report"]["status"],
                               "checks": historical["report"]["checks"],
                               "finding_codes": historical["report"]["finding_codes"],
                               "findings_total": len(historical["all_findings"]),
                               "note": "unchanged historical checker; its FAIL stands and is "
                                       "not rewritten"},
        "dispositions": result["dispositions"],
        "approved_historical_deviations": {
            code: n for code, n in collections.Counter(f["code"] for f in result["approved"])
            .items()},
        "unapproved": unapproved[:500], "unapproved_count": len(unapproved),
        "evidence": {"D1": {k: v for k, v in ev["D1"].items()},
                     "D2": {k: v for k, v in ev["D2"].items() if k != "ordering_keys"}},
        "immutability": immut,
        "status": ("PASS_WITH_APPROVED_HISTORICAL_DEVIATIONS" if not unapproved
                   and result["approved"] else "PASS" if not unapproved else "FAIL"),
    }
    oc.write_json(out / "EFFICIENCY_CHECKER.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--audit", required=True, help="SUCCESSOR_AUDIT.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = run_checker(Path(args.run), Path(args.audit), Path(args.output))
    print(json.dumps({"status": report["status"], "unapproved": report["unapproved_count"],
                      "approved": report["approved_historical_deviations"],
                      "historical": report["historical_checker"]["finding_codes"]}))
    return 0 if report["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
