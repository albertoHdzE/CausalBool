"""Evidence checker of the Phase 2 next round (protocol 1.0).

Structural integrity of the run directory, not its estimates (the separate
``next_round_audit`` recomputes numbers without importing any of this code):

- package: the locked next-round package verifies;
- per stage: expected-key ledger equal to the one re-derived by the runner's
  schedule and, for C stages, to the frozen ledger; every expected key has
  exactly one row, no unexpected key; no failed row; J = C * S; every row's
  manifest hash equals its stage manifest; stage sources unchanged at the end
  of the stage and equal now; the stage's commands journal has one entry per row;
- isolation: successor rows import ``research/next_round_search.py`` from this
  tree and never the frozen solver; earlier-optimizer rows import this tree's
  ``research/optimization_search.py`` with the hash frozen at its release;
  frozen-control rows import the run's frozen workspace;
- repaired accounting present in every successor row;
- freezes: FROZEN_SELECTION precedes the first C row; LEARNING_FREEZE precedes
  the first ordering row; sources named in the freeze are unchanged;
- learning: ranker processes load no oracle module; ranker inputs carry no
  identity, label or oracle field;
- ledger: every stage row is charged; the total is under the 24-hour cap.

Every check is counted; an empty stage is a finding. Usage::

    PYTHONPATH=.reference:. python -m research.next_round_checker --run DIR [--output PATH]
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
from pathlib import Path
from typing import List

from research import next_round_common as nrc
from research import next_round_runner as nrr
from research import optimization_common as oc

EARLIER_SEARCH_SHA256 = "296ecd2de750b5959cf207010ca82fe4bd337a8c5b656e3c9866bee284933224"


class Checker:
    def __init__(self, run: Path) -> None:
        self.run = Path(run).resolve()
        self.checks = 0
        self.findings: List[dict] = []

    def ok(self, what: str) -> None:
        self.checks += 1

    def fail(self, code: str, detail: str) -> None:
        self.checks += 1
        self.findings.append({"code": code, "detail": detail})

    def expect(self, condition: bool, code: str, detail: str) -> None:
        if condition:
            self.ok(code)
        else:
            self.fail(code, detail)

    # ------------------------------------------------------------------

    def package(self) -> None:
        proc = subprocess.run([oc.PYTHON, str(nrc.PACKAGE / "verify_package.py")],
                              cwd=str(oc.ROOT), capture_output=True, text=True)
        self.expect(proc.returncode == 0, "PACKAGE_VERIFY", proc.stderr[-300:])

    def stage(self, stage: str) -> None:
        directory = self.run / "stages" / stage
        rows_path = directory / "rows.jsonl"
        if not rows_path.exists():
            self.fail("STAGE_MISSING", stage)
            return
        rows = oc.read_rows(rows_path)
        self.expect(len(rows) > 0, "STAGE_EMPTY", stage)
        expected = json.loads((directory / "EXPECTED_KEYS.json").read_text())["keys"]
        manifest = json.loads((directory / "STAGE_MANIFEST.json").read_text())
        frozen_ledger = self.run / "frozen_expected" / f"{stage}.json"
        if frozen_ledger.exists():
            self.expect(json.loads(frozen_ledger.read_text())["keys"] == expected,
                        "FROZEN_LEDGER_DIFFERS", stage)
        try:
            rebuilt = nrr.STAGES[stage](self.run).expected
            self.expect(rebuilt == expected, "LEDGER_NOT_REDERIVABLE", stage)
        except Exception as exc:  # a stage whose inputs moved is itself a finding
            self.fail("LEDGER_REBUILD_ERROR", f"{stage}: {type(exc).__name__}: {exc}")
        counts = collections.Counter(r["key"] for r in rows)
        self.expect(set(counts) == set(expected), "KEY_SET_DIFFERS",
                    f"{stage}: missing {len(set(expected) - set(counts))}, unexpected "
                    f"{len(set(counts) - set(expected))}")
        duplicates = [k for k, n in counts.items() if n > 1]
        self.expect(not duplicates, "DUPLICATE_ROWS", f"{stage}: {duplicates[:3]}")
        commands = oc.read_rows(directory / "commands.jsonl")
        self.expect(len(commands) == len(rows), "COMMANDS_ROWS_MISMATCH",
                    f"{stage}: {len(commands)} commands, {len(rows)} rows")
        current = {name: oc.file_sha256(oc.ROOT / name) for name in manifest["measured_sources"]}
        self.expect(current == manifest["measured_sources"], "SOURCE_DRIFT_SINCE_STAGE",
                    f"{stage}: {[n for n in current if current[n] != manifest['measured_sources'][n]]}")
        resume = oc.read_rows(directory / "resume_log.jsonl")
        ends = [r for r in resume if r.get("event") == "end"]
        self.expect(bool(ends) and all(r["sources_unchanged_during_stage"] for r in ends),
                    "SOURCE_CHANGED_DURING_STAGE", stage)
        for row in rows:
            key = row["key"]
            self.expect(not row["failed_row"], "FAILED_ROW", f"{stage}: {key}")
            self.expect(row["manifest_sha256"] == manifest["manifest_sha256"],
                        "ROW_MANIFEST_MISMATCH", f"{stage}: {key}")
            result = row.get("result") or {}
            if result.get("cycles") is not None:
                self.expect(row["product"] == row["cycles"] * row["scratch"],
                            "PRODUCT_MISMATCH", key)
                self.expect(result.get("discrepancy_count", 0) == 0, "DISCREPANCY", key)
            self.isolation(stage, row, result)
        self.stage_rows = getattr(self, "stage_rows", {})
        self.stage_rows[stage] = rows

    def isolation(self, stage: str, row: dict, result: dict) -> None:
        arm = row["arm"]
        imported = result.get("imported_sources") or {}
        research_dir = str((oc.ROOT / "research").resolve())
        workspace = str((self.run / "frozen_control_workspace").resolve())
        if stage in ("L_orderings",):
            self.expect(not result.get("loaded_modules_with_oracle_access"), "ORACLE_LEAK",
                        row["key"])
            return
        if stage in ("D_profile", "L_acquisition"):
            return
        if arm in nrc.CELLS or arm.endswith("+engineered"):
            path = imported.get("research.next_round_search") or ""
            self.expect(path.startswith(research_dir), "SUCCESSOR_WRONG_SOURCE", row["key"])
            self.expect("research.objective_index_search" not in imported,
                        "FROZEN_SOLVER_LOADED", row["key"])
            if arm.endswith("+engineered"):
                self.expect((imported.get("research.next_round_engineered") or "")
                            .startswith(research_dir), "VARIANT_WRONG_SOURCE", row["key"])
            self.expect("interrupted_validation_total" in (result.get("optimisation") or {}),
                        "REPAIRED_ACCOUNTING_MISSING", row["key"])
        elif arm == nrc.EARLIER:
            path = imported.get("research.optimization_search") or ""
            self.expect(path.startswith(research_dir), "EARLIER_WRONG_SOURCE", row["key"])
            self.expect(result.get("config") == nrc.EARLIER_SPEC["config"]
                        and result.get("build") == nrc.EARLIER_SPEC["build"]
                        and result.get("search_arm") == nrc.EARLIER_SPEC["search_arm"],
                        "EARLIER_WRONG_CONFIG", row["key"])
        elif arm in ("classical", "accepted_bootstrap", "serial"):
            path = imported.get("research") or ""
            if isinstance(path, dict):
                path = path.get("path") or ""
            if path:
                self.expect(str(path).startswith(workspace), "CONTROL_NOT_ISOLATED", row["key"])

    def earlier_source(self) -> None:
        self.expect(oc.file_sha256(oc.ROOT / "research" / "optimization_search.py")
                    == EARLIER_SEARCH_SHA256, "EARLIER_SOURCE_CHANGED", "optimization_search.py")

    def freezes(self) -> None:
        frozen_path = self.run / "FROZEN_SELECTION.json"
        if not frozen_path.exists():
            self.fail("FREEZE_MISSING", "FROZEN_SELECTION.json")
            return
        frozen = json.loads(frozen_path.read_text())
        drift = [name for name, digest in frozen["sources"]["research"].items()
                 if oc.file_sha256(oc.ROOT / name) != digest]
        self.expect(not drift, "FROZEN_SOURCE_CHANGED", str(drift))
        for stage in ("C_confirmation", "C_public"):
            rows = getattr(self, "stage_rows", {}).get(stage, [])
            if rows:
                first = min(r["started_utc"] for r in rows)
                self.expect(first >= frozen["frozen_utc"], "ROW_BEFORE_FREEZE", stage)
                self.expect(all(r["freeze_sha256"] == oc.file_sha256(frozen_path) for r in rows),
                            "ROW_FREEZE_HASH", stage)
        learning = self.run / "LEARNING_FREEZE.json"
        rows = getattr(self, "stage_rows", {}).get("L_orderings", [])
        if rows:
            self.expect(learning.exists(), "LEARNING_FREEZE_MISSING", "L_orderings")
            if learning.exists():
                lf = json.loads(learning.read_text())
                self.expect(min(r["started_utc"] for r in rows) >= lf["frozen_utc"],
                            "ORDERING_BEFORE_LEARNING_FREEZE", "L_orderings")
                for fixture in lf["fixtures"]:
                    path = self.run / "learning" / "design" / "evaluation" / fixture[
                        "fixture_id"] / "RANKER_INPUT.json"
                    self.expect(oc.file_sha256(path) == fixture["ranker_input_sha256"],
                                "RANKER_INPUT_CHANGED", fixture["fixture_id"])
                    text = path.read_text()
                    self.expect(not any(word in text for word in ('"identity', '"heldout',
                                                                  '"useful', '"oracle')),
                                "RANKER_INPUT_LEAKS_LABELS", fixture["fixture_id"])

    def ledger(self) -> None:
        charged = collections.Counter((r["stage"], r["key"]) for r in
                                      oc.read_rows(nrc.ledger_path(self.run)))
        for stage, rows in getattr(self, "stage_rows", {}).items():
            missing = [r["key"] for r in rows if charged.get((stage, r["key"]), 0) < 1]
            self.expect(not missing, "ROW_NOT_CHARGED", f"{stage}: {len(missing)}")
        self.expect(nrc.measured_hours(self.run) < nrc.WALL_CAP_HOURS, "WALL_CAP_EXCEEDED",
                    str(nrc.measured_hours(self.run)))

    def run_all(self) -> dict:
        self.package()
        self.earlier_source()
        for stage in sorted(nrr.STAGES):
            if (self.run / "stages" / stage).exists():
                self.stage(stage)
        self.freezes()
        self.ledger()
        codes = collections.Counter(f["code"] for f in self.findings)
        return {"status": "PASS" if self.checks and not self.findings else "FAIL",
                "checks": self.checks, "finding_codes": dict(codes),
                "findings": self.findings[:200],
                "stages_checked": sorted(getattr(self, "stage_rows", {}))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = Checker(Path(args.run)).run_all()
    out = Path(args.output) if args.output else Path(args.run) / "CHECKER_REPORT.json"
    oc.write_json(out, report)
    print(json.dumps({k: report[k] for k in ("status", "checks", "finding_codes")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
