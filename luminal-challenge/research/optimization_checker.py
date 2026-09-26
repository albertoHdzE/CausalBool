"""Evidence checker for optimization protocol 1.0.

Checks provenance and accounting, not arithmetic (the independent auditor
recomputes the numbers): package and freeze integrity, post-freeze source
changes, stage manifests and resume records, exact key ledgers, row identity
and isolation, hidden-split exposure, the public-score denominator, and whether
any reported status claims more than its gate allows.

Every finding carries a code, so a planted defect can be shown to raise exactly
the finding it should. Exit 0 only with zero findings.

Usage::

    PYTHONPATH=.reference:. python -m research.optimization_checker --run DIR
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
from pathlib import Path
import subprocess
import sys
from typing import Dict, List

from research import optimization_common as oc


PROTOCOL_COUNTS = {
    "B_search_development": 9300, "B_engineering_pair": 1800, "B_bound_ablation": 1800,
    "C_model_development": 270, "D_fresh_compiler": 36000, "D_public": 1560,
    "C_model_evaluation": 17550,
}
POST_FREEZE_STAGES = ("D_fresh_compiler", "D_public", "C_model_evaluation",
                      "C_model_evaluation_depth1_descriptive", "D_fresh_model_compiler",
                      "D_public_model_compiler")
FROZEN_ARMS = {"frozen_phase2", "accepted_budgeted", "accepted_default", "accepted_bootstrap",
               "classical", "serial"}
# Files whose change after the freeze would alter what was measured or estimated.
FROZEN_MEASURED = (
    "research/__init__.py", "research/optimization_common.py", "research/optimization_search.py",
    "research/optimization_worker.py", "research/optimization_frozen_worker.py",
    "research/optimization_models.py", "research/optimization_model_worker.py",
    "research/optimization_fixtures.py", "research/optimization_analysis.py",
    "research/optimization_report.py", "research/optimization_export.py",
    "research/run_structural_experiments.py", "research/structural_encoding.py",
    "research/structural_search.py", "research/structural_models.py",
    "research/structural_oracle.py", "research/structural_evidence.py",
    "research/physical_probes.py", "research/classical_measurement_worker.py",
)


class Checker:
    def __init__(self, run: Path, root: Path = oc.ROOT) -> None:
        self.run = Path(run)
        self.root = Path(root)
        self.findings: List[dict] = []
        self.counts: Dict[str, int] = collections.Counter()

    def fail(self, code: str, detail: object) -> None:
        self.findings.append({"code": code, "detail": str(detail)[:400]})

    def ok(self, code: str) -> None:
        self.counts[code] += 1

    # -- sections ---------------------------------------------------------------

    AUTHORIZED_EDITS = {"research/run_structural_experiments.py",
                        "research/structural_encoding.py"}

    def package(self) -> None:
        # After authorized edits the package's own policy-only mode applies; the
        # full starting-hash mode passed before any edit (stage_a/commands).
        proc = subprocess.run([sys.executable, "plan/phase2_optimization/verify_package.py",
                               "--policy-only"], cwd=str(self.root), capture_output=True,
                              text=True)
        if proc.returncode != 0:
            self.fail("PACKAGE_VERIFY", proc.stdout[-300:] + proc.stderr[-300:])
        state = json.loads((self.root / "plan/phase2_optimization/STARTING_STATE.json").read_text())
        changed = sorted(name for name, digest in state["source_sha256"].items()
                         if oc.file_sha256(self.root / name) != digest)
        self.starting_changes = changed
        unauthorized = [name for name in changed if name not in self.AUTHORIZED_EDITS]
        if unauthorized:
            self.fail("UNAUTHORIZED_STARTING_SOURCE_CHANGE", unauthorized)
        self.ok("package")

    def freeze(self) -> dict:
        path = self.run / "FROZEN_SELECTION.json"
        if not path.exists():
            self.fail("FREEZE_MISSING", path)
            return {}
        frozen = json.loads(path.read_text())
        digest = oc.file_sha256(path)
        research = frozen["sources"]["research"]
        for name in FROZEN_MEASURED:
            now = oc.file_sha256(self.root / name)
            if name not in research:
                self.fail("POST_FREEZE_SOURCE_ADDED", name)
            elif research[name] != now:
                self.fail("POST_FREEZE_SOURCE_CHANGE", name)
            self.ok("frozen_source")
        for name, expected in frozen["sources"]["production"].items():
            if oc.file_sha256(self.root / name) != expected:
                self.fail("PRODUCTION_CHANGED", name)
        for name, expected in frozen["sources"]["frozen_snapshot"].items():
            if oc.file_sha256(oc.FROZEN_SNAPSHOT / name) != expected:
                self.fail("SNAPSHOT_CHANGED", name)
        for stage in POST_FREEZE_STAGES:
            rows_path = self.run / "stages" / stage / "rows.jsonl"
            if not rows_path.exists():
                continue
            for row in oc.read_rows(rows_path):
                if row.get("freeze_sha256") != digest:
                    self.fail("ROW_WITHOUT_FREEZE", row["key"])
                    break
                if row["started_utc"] < frozen["frozen_utc"]:
                    self.fail("ROW_BEFORE_FREEZE", row["key"])
                    break
        self.ok("freeze")
        return frozen

    def stages(self, frozen: dict) -> Dict[str, List[dict]]:
        out = {}
        for directory in sorted((self.run / "stages").iterdir()):
            stage = directory.name
            rows = oc.read_rows(directory / "rows.jsonl")
            out[stage] = rows
            expected = json.loads((directory / "EXPECTED_KEYS.json").read_text())["keys"]
            if not expected:
                self.fail("EMPTY_LEDGER", stage)
            if stage in PROTOCOL_COUNTS and len(expected) != PROTOCOL_COUNTS[stage]:
                self.fail("LEDGER_COUNT", f"{stage}: {len(expected)} != {PROTOCOL_COUNTS[stage]}")
            frozen_ledger = self.run / "frozen_expected" / f"{stage}.json"
            if stage in POST_FREEZE_STAGES:
                if not frozen_ledger.exists():
                    self.fail("LEDGER_NOT_FROZEN", stage)
                elif json.loads(frozen_ledger.read_text())["keys"] != expected:
                    self.fail("LEDGER_CHANGED_AFTER_FREEZE", stage)
            counts = collections.Counter(row["key"] for row in rows)
            missing = set(expected) - set(counts)
            if missing:
                self.fail("MISSING_ROWS", f"{stage}: {len(missing)}")
            dups = [k for k, n in counts.items() if n > 1]
            if dups:
                self.fail("DUPLICATE_ROWS", f"{stage}: {dups[:3]}")
            extra = set(counts) - set(expected)
            if extra:
                self.fail("UNEXPECTED_ROWS", f"{stage}: {len(extra)}")
            manifest = json.loads((directory / "STAGE_MANIFEST.json").read_text())
            for row in rows:
                if row["manifest_sha256"] != manifest["manifest_sha256"]:
                    self.fail("ROW_MANIFEST_MISMATCH", row["key"])
                    break
            ends = [e for e in oc.read_rows(directory / "resume_log.jsonl") if e["event"] == "end"]
            if not ends or not ends[-1].get("sources_unchanged_during_stage"):
                self.fail("SOURCES_CHANGED_DURING_STAGE", stage)
            self.rows(stage, rows)
            self.ok("stage")
        return out

    def rows(self, stage: str, rows: List[dict]) -> None:
        workspace = str((self.run / "frozen_control_workspace").resolve())
        research = str((self.root / "research").resolve())
        for row in rows:
            key = row["key"]
            if row["failed_row"]:
                self.fail("FAILED_ROW", f"{stage}: {key}: {row.get('failure')}")
            result = row.get("result") or {}
            if result.get("cycles") is not None and row["product"] != row["cycles"] * row["scratch"]:
                self.fail("PRODUCT_MISMATCH", key)
            if result.get("discrepancy_count") and not row["failed_row"]:
                self.fail("DISCREPANCY_NOT_FAILED", key)
            imported = result.get("imported_sources") or {}
            path = imported.get("research")
            if isinstance(path, dict):
                path = path.get("path")
            if stage.startswith(("B_", "D_")) and not stage.startswith("D_public_model") and path:
                if row["arm"] in FROZEN_ARMS and not str(path).startswith(workspace):
                    self.fail("CONTROL_NOT_ISOLATED", key)
                if row["arm"] not in FROZEN_ARMS and not str(path).startswith(research):
                    self.fail("NEW_ARM_WRONG_SOURCE", key)
            if stage.startswith("C_") and result:
                if result.get("discoveries", {}).get("train"):
                    self.fail("TRAINING_OBJECT_REPORTED_NEW", key)
                if result.get("discoveries", {}).get("absent"):
                    self.fail("DISCOVERY_ABSENT_FROM_ORACLE", key)
                if result.get("best_test_J", 0) > result.get("min_training_J", 0):
                    self.fail("ENDPOINT_ABOVE_TRAINING", key)
            if row["arm"] not in FROZEN_ARMS and stage.startswith(("B_", "D_")) and result:
                opt = result.get("optimisation") or {}
                if opt.get("aggregate", {}).get("nodes", 0) > 1_000_000:
                    self.fail("NODE_CEILING_EXCEEDED", key)
                if opt.get("aggregate", {}).get("validations", 0) > 100_000:
                    self.fail("VALIDATION_CEILING_EXCEEDED", key)

    def learner_isolation(self) -> None:
        tree = ast.parse((self.root / "research" / "optimization_models.py").read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                if any(b in name for b in ("structural_oracle", "optimization_fixtures",
                                           "optimization_model_worker")):
                    self.fail("LEARNER_IMPORTS_EVALUATOR", name)
        self.ok("learner_isolation")

    def claims(self, frozen: dict) -> None:
        comparison = self.run / "COMPARISON.json"
        if comparison.exists():
            c = json.loads(comparison.read_text())
            low, high = c["primary"]["interval_95"]
            allowed = ("SUPPORTS_IMPROVEMENT" if low > 0 else "SUPPORTS_DEGRADATION"
                       if high < 0 else "INCONCLUSIVE")
            if c["primary"]["verdict"] not in (allowed, "IDENTITY_CONTROL"):
                self.fail("FALSE_PRIMARY_VERDICT", c["primary"]["verdict"])
            if c["primary"]["verdict"] == "SUPPORTS_IMPROVEMENT" and \
                    not c["primary"]["confirmatory_eligible"]:
                self.fail("CONFIRMATORY_WITHOUT_ELIGIBILITY", "primary")
        model = self.run / "MODEL_EVALUATION.json"
        h4_pass = False
        if model.exists():
            m = json.loads(model.read_text())
            gate = m["gate"]
            passed = (gate["all_30_fixtures_accounted"] and gate["at_least_3_families"] and
                      gate["correctness_or_evidence_defects"] == 0 and
                      gate["both_lower_bounds_positive"])
            h4_pass = m["H4_NEW"] == "PASS"
            if h4_pass and not passed:
                self.fail("FALSE_H4_PASS", gate)
            if m["original_H4"]["verdict"] != "INCONCLUSIVE":
                self.fail("ORIGINAL_H4_RELABELLED", m["original_H4"])
        for stage in ("D_fresh_model_compiler", "D_public_model_compiler"):
            if (self.run / "stages" / stage).exists() and not h4_pass:
                self.fail("MODEL_COMPILER_RUN_WITHOUT_H4", stage)
        public = self.run / "PUBLIC_SCORE.json"
        if public.exists():
            p = json.loads(public.read_text())
            if not p["scores"]["serial_matches_frozen"]:
                self.fail("SERIAL_DENOMINATOR_MISMATCH", "serial rows differ from frozen")
            # The denominator must be serial: recompute one score with serial and
            # confirm the reported value, which a classical denominator would not give.
            serial = p["scores"]["serial"]
            arm = p["scores"]["arms"].get("selected_nonmodel@0.1")
            if arm and arm["scores"][0] is not None:
                import math

                cs = arm["per_program_distinct_CSJ"]
                names = sorted(cs)
                sp = math.exp(sum(math.log(serial[n][0] / cs[n][0][0]) for n in names) / 8)
                sc = math.exp(sum(math.log(serial[n][1] / cs[n][0][1]) for n in names) / 8)
                if len(set(tuple(v[0]) for v in cs.values())) and \
                        all(len(v) == 1 for v in cs.values()) and \
                        abs(math.sqrt(sp * sc) - arm["scores"][0]) > 1e-12:
                    self.fail("SCORE_DENOMINATOR", "reported score is not the serial formula")
            for key, entry in p["paired_score_ratios"].items():
                strict = all(r is not None and r > 1 + 1e-12 for r in entry["ratios"])
                if entry["strict_improvement_every_repetition"] != strict:
                    self.fail("FALSE_PUBLIC_STRICT_GAIN", key)
        self.ok("claims")

    def run_all(self) -> dict:
        self.package()
        frozen = self.freeze()
        self.stages(frozen)
        self.learner_isolation()
        self.claims(frozen)
        codes = collections.Counter(f["code"] for f in self.findings)
        return {"checker": "research/optimization_checker.py",
                "checker_sha256": oc.file_sha256(Path(__file__)),
                "run": str(self.run), "checks": dict(self.counts),
                "starting_sources_changed_by_authorized_parameterisation":
                    getattr(self, "starting_changes", None),
                "findings": self.findings[:500], "finding_codes": dict(codes),
                "status": "PASS" if not self.findings and sum(self.counts.values()) else "FAIL"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = Checker(Path(args.run).resolve()).run_all()
    out = Path(args.output) if args.output else Path(args.run) / "CHECKER_REPORT.json"
    oc.write_json(out, report)
    print(json.dumps({"status": report["status"], "finding_codes": report["finding_codes"]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
