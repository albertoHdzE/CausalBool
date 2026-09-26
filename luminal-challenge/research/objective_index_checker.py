"""Evidence checker for the objective-index protocol 1.0.

Checks provenance and accounting, not statistics (``objective_index_audit``
re-derives the numbers independently): package and inherited locks, source
ownership since takeover, freeze integrity and post-freeze source changes,
stage manifests and resume records, exact key ledgers, row identity and
isolation, pool/order/label hashes, fabricated or leaked discoveries (checked
against the frozen oracle caches), the public-score denominator and whether
any reported verdict claims more than its gate allows.

Every finding carries a code, so a planted defect can be shown to raise exactly
the finding it should. Exit 0 only with zero findings and a nonzero number of
checks.

Usage::

    PYTHONPATH=.reference:. python -m research.objective_index_checker --run DIR
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Dict, List

from research import optimization_common as oc


LEDGER_COUNTS = {"DEV_compiler": 5700, "DEV_model": 2025, "EVAL_model_wall": 20250,
                 "EVAL_model_work": 450, "EVAL_compiler": 63000, "EVAL_public": 2520,
                 "EVAL_public_serial": 120, "EVAL_learned_tree": 9360,
                 "EVAL_learned_shuffled_tree": 9360}
POST_FREEZE_STAGES = ("EVAL_model_wall", "EVAL_model_work", "EVAL_compiler", "EVAL_public",
                      "EVAL_public_serial", "EVAL_learned_tree", "EVAL_learned_shuffled_tree")
FROZEN_ARMS = {"A0_frozen_phase2", "accepted_budgeted", "accepted_default",
               "accepted_bootstrap", "classical", "serial"}
OWNED_NEW = ("research/objective_index_", "research/schema_ranker.py",
             "research_tests/test_objective_index", "research_tests/test_schema_ranker.py")
LEARNER_MODULES = ("research/schema_ranker.py", "research/objective_index_learned.py")
LEARNER_FORBIDDEN = ("structural_oracle", "optimization_fixtures", "objective_index_fixtures",
                     "objective_index_ranker_worker", "optimization_model_worker")


class Checker:
    def __init__(self, run: Path, root: Path = oc.ROOT) -> None:
        self.run = Path(run)
        self.root = Path(root)
        self.findings: List[dict] = []
        self.counts: Dict[str, int] = collections.Counter()
        self._oracle_cache: Dict[str, dict] = {}

    def fail(self, code: str, detail: object) -> None:
        self.findings.append({"code": code, "detail": str(detail)[:400]})

    def ok(self, code: str, n: int = 1) -> None:
        self.counts[code] += n

    # -- package and ownership ---------------------------------------------------

    def package(self) -> None:
        proc = subprocess.run([sys.executable, "plan/phase2_research/verify_package.py"],
                              cwd=str(self.root), capture_output=True, text=True)
        if proc.returncode != 0:
            self.fail("PACKAGE_VERIFY", proc.stdout[-300:] + proc.stderr[-300:])
        start = self.run / "SOURCE_MANIFESTS" / "starting" / "SHA256SUMS.txt"
        if not start.exists():
            self.fail("STARTING_MANIFEST_MISSING", start)
            return
        changed = []
        for line in start.read_text().splitlines():
            digest, name = line.split(None, 1)
            if oc.file_sha256(self.root / name) != digest:
                changed.append(name)
        self.starting_changes = changed
        for name in changed:
            if not name.startswith(OWNED_NEW):
                self.fail("UNOWNED_SOURCE_CHANGED_SINCE_TAKEOVER", name)
        self.ok("package")

    def learner_isolation(self) -> None:
        for relative in LEARNER_MODULES:
            tree = ast.parse((self.root / relative).read_text())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [f"{node.module}.{a.name}" for a in node.names]
                for name in names:
                    if any(bad in name for bad in LEARNER_FORBIDDEN):
                        self.fail("LEARNER_IMPORTS_EVALUATOR", f"{relative}: {name}")
            self.ok("learner_isolation")

    # -- freeze ----------------------------------------------------------------

    def freeze(self) -> dict:
        path = self.run / "FROZEN_SELECTION.json"
        if not path.exists():
            self.fail("FREEZE_MISSING", path)
            return {}
        frozen = json.loads(path.read_text())
        self.freeze_digest = oc.file_sha256(path)
        research = frozen["sources"]["research"]
        for name, digest in research.items():
            if oc.file_sha256(self.root / name) != digest:
                self.fail("POST_FREEZE_SOURCE_CHANGE", name)
            self.ok("frozen_source")
        for name in sorted(p.relative_to(self.root).as_posix()
                           for folder in ("research", "research_tests")
                           for p in (self.root / folder).glob("*.py")):
            if name not in research:
                self.fail("POST_FREEZE_SOURCE_ADDED", name)
        for name, expected in frozen["sources"]["production"].items():
            if oc.file_sha256(self.root / name) != expected:
                self.fail("PRODUCTION_CHANGED", name)
        for name, expected in frozen["sources"]["frozen_snapshot"].items():
            if oc.file_sha256(oc.FROZEN_SNAPSHOT / name) != expected:
                self.fail("SNAPSHOT_CHANGED", name)
        for label, entry in frozen.get("inputs", {}).items():
            if oc.file_sha256(self.run / entry["path"]) != entry["sha256"]:
                self.fail("FROZEN_INPUT_CHANGED", label)
        self.ok("freeze")
        return frozen

    # -- stages ------------------------------------------------------------------

    def stages(self, frozen: dict) -> Dict[str, List[dict]]:
        out = {}
        stages_dir = self.run / "stages"
        if not stages_dir.exists():
            self.fail("NO_STAGES", stages_dir)
            return out
        for directory in sorted(stages_dir.iterdir()):
            stage = directory.name
            rows = oc.read_rows(directory / "rows.jsonl")
            out[stage] = rows
            expected = json.loads((directory / "EXPECTED_KEYS.json").read_text())["keys"]
            if not expected:
                self.fail("EMPTY_LEDGER", stage)
            if stage in LEDGER_COUNTS and len(expected) != LEDGER_COUNTS[stage]:
                self.fail("LEDGER_COUNT", f"{stage}: {len(expected)} != {LEDGER_COUNTS[stage]}")
            if stage in POST_FREEZE_STAGES:
                frozen_ledger = self.run / "frozen_expected" / f"{stage}.json"
                if not frozen_ledger.exists():
                    self.fail("LEDGER_NOT_FROZEN", stage)
                elif json.loads(frozen_ledger.read_text())["keys"] != expected:
                    self.fail("LEDGER_CHANGED_AFTER_FREEZE", stage)
                for row in rows:
                    if row.get("freeze_sha256") != getattr(self, "freeze_digest", None):
                        self.fail("ROW_WITHOUT_FREEZE", row["key"])
                        break
                    if frozen and row["started_utc"] < frozen["frozen_utc"]:
                        self.fail("ROW_BEFORE_FREEZE", row["key"])
                        break
            counts = collections.Counter(row["key"] for row in rows)
            missing = set(expected) - set(counts)
            if missing:
                self.fail("MISSING_ROWS", f"{stage}: {len(missing)}")
            duplicates = [k for k, n in counts.items() if n > 1]
            if duplicates:
                self.fail("DUPLICATE_ROWS", f"{stage}: {duplicates[:3]}")
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
            commands = {c["key"] for c in oc.read_rows(directory / "commands.jsonl")}
            if set(counts) - commands:
                self.fail("ROW_WITHOUT_COMMAND", f"{stage}: {len(set(counts) - commands)}")
            self.rows(stage, rows)
            if stage.endswith("_model") or stage.startswith("EVAL_model"):
                self.fixture_rows(stage, rows)
            self.ok("stage")
        learned = [s for s in out if s.startswith("EVAL_learned")]
        if learned:
            gate = self.run / "LEARNING.json"
            passed = gate.exists() and json.loads(gate.read_text())["H_LEARN"]["verdict"] == "PASS"
            if not passed:
                self.fail("LEARNED_COMPILER_RUN_WITHOUT_H_LEARN", learned)
        return out

    def rows(self, stage: str, rows: List[dict]) -> None:
        workspace = str((self.run / "frozen_control_workspace").resolve())
        research = str((self.root / "research").resolve())
        for row in rows:
            key = row["key"]
            self.ok("row")
            if row["failed_row"]:
                self.fail("FAILED_ROW", f"{stage}: {key}: {row.get('failure')}")
            result = row.get("result") or {}
            if result.get("cycles") is not None and \
                    row["product"] != row["cycles"] * row["scratch"]:
                self.fail("PRODUCT_MISMATCH", key)
            if result.get("discrepancy_count") and not row["failed_row"]:
                self.fail("DISCREPANCY_NOT_FAILED", key)
            if result and not row["failed_row"] and result.get("correctness") != "PASS":
                self.fail("FAILED_RESULT_NOT_FAILED_ROW", key)
            imported = result.get("imported_sources") or {}
            path = imported.get("research")
            if isinstance(path, dict):
                path = path.get("path")
            if path and not stage.endswith("model") and "_model_" not in stage:
                if row["arm"] in FROZEN_ARMS and not str(path).startswith(workspace):
                    self.fail("CONTROL_NOT_ISOLATED", key)
                if row["arm"] not in FROZEN_ARMS and not str(path).startswith(research):
                    self.fail("NEW_ARM_WRONG_SOURCE", key)
            opt = result.get("optimisation") or {}
            aggregate = opt.get("aggregate") or {}
            if row["arm"] not in FROZEN_ARMS:
                if aggregate.get("nodes", 0) > 1_000_000:
                    self.fail("NODE_CEILING_EXCEEDED", key)
                if aggregate.get("validations", 0) > 100_000:
                    self.fail("VALIDATION_CEILING_EXCEEDED", key)
                if opt.get("budget_renewals"):
                    self.fail("DEADLINE_RENEWED", key)

    def _oracle(self, row: dict) -> dict:
        fixture = row["fixture_id"]
        if fixture not in self._oracle_cache:
            cohort = fixture.split("_")[0]
            base = self.run / "fixtures" / cohort / fixture
            oracle = json.loads((base / "oracle.json").read_text())
            split = json.loads((base / "split.json").read_text())
            membership = {}
            for part in ("train", "validation", "test"):
                for identity in split[part]:
                    membership[identity] = part
            products = {x["identity"]: x["product"] for x in oracle["feasible"]}
            train_min = min(products[i] for i in split["train"])
            self._oracle_cache[fixture] = {"membership": membership, "products": products,
                                           "train_min": train_min}
        return self._oracle_cache[fixture]

    def fixture_rows(self, stage: str, rows: List[dict]) -> None:
        pools: Dict[str, set] = collections.defaultdict(set)
        orders: Dict[tuple, set] = collections.defaultdict(set)
        shuffled: Dict[str, set] = collections.defaultdict(set)
        for row in rows:
            result = row.get("result")
            if not result:
                continue
            key = row["key"]
            truth = self._oracle(row)
            if result["min_training_J"] != truth["train_min"]:
                self.fail("TRAINING_MINIMUM_MISMATCH", key)
            found_test = []
            for item in result.get("found", []):
                where = truth["membership"].get(item["identity"])
                if where is None:
                    self.fail("FABRICATED_DISCOVERY", key)
                    continue
                if where == "train":
                    self.fail("TRAINING_OBJECT_REPORTED_NEW", key)
                if truth["products"][item["identity"]] != item["product"]:
                    self.fail("DISCOVERY_PRODUCT_MISMATCH", key)
                if item["product"] >= truth["train_min"]:
                    self.fail("DISCOVERY_NOT_BETTER_THAN_TRAINING", key)
                if where == "test":
                    found_test.append(item["product"])
            if result.get("found_total", 0) <= 64:
                expected_best = min(found_test + [truth["train_min"]])
                if result["best_test_J"] != expected_best:
                    self.fail("ENDPOINT_MISMATCH", key)
            if result["best_test_J"] > truth["train_min"]:
                self.fail("ENDPOINT_ABOVE_TRAINING", key)
            if result.get("defect_count"):
                self.fail("FIXTURE_DEFECT", key)
            info = result.get("info") or {}
            if row["arm"] != "empirical_cover" and info.get("pool_sha256"):
                pools[row["fixture_id"]].add(info["pool_sha256"])
            if info.get("ordering_sha256"):
                orders[(row["fixture_id"], row["arm"])].add(info["ordering_sha256"])
            if row["arm"] == "shuffled_tree" and info.get("shuffled_labels_sha256"):
                shuffled[row["fixture_id"]].add(info["shuffled_labels_sha256"])
            if row["arm"] == "empirical_cover" and result.get("counts", {}).get("novel"):
                self.fail("NEGATIVE_CONTROL_PROPOSED_NOVEL", key)
            self.ok("fixture_row")
        for fixture, hashes in pools.items():
            if len(hashes) != 1:
                self.fail("POOL_HASH_DIFFERS_ACROSS_ARMS", f"{stage}: {fixture}")
        for key, hashes in orders.items():
            if len(hashes) != 1:
                self.fail("ORDER_NOT_DETERMINISTIC", f"{stage}: {key}")
        for fixture, hashes in shuffled.items():
            if len(hashes) != 1:
                self.fail("SHUFFLED_LABELS_DIFFER", f"{stage}: {fixture}")

    # -- claims ----------------------------------------------------------------

    def claims(self) -> None:
        learning = self.run / "LEARNING.json"
        if learning.exists():
            gate = json.loads(learning.read_text())["H_LEARN"]
            lows = [c.get("interval", [0])[0] for c in gate["contrasts"].values()]
            passed = (gate["complete_30_fixture_membership"] and gate["defects"] == 0
                      and gate["failed_rows"] == 0 and len(lows) == 3
                      and all(low > 0 for low in lows))
            if (gate["verdict"] == "PASS") != passed:
                self.fail("FALSE_H_LEARN_VERDICT", gate["verdict"])
            self.ok("claim")
        comparison = self.run / "COMPARISON.json"
        if comparison.exists():
            c = json.loads(comparison.read_text())
            primary = c["primary"]
            lows = [x["interval"][0] for x in primary["contrasts"].values()
                    if x.get("interval") is not None]
            best = (len(lows) == 3 and all(low > 0 for low in lows))
            if primary["claim_best_average_quality"] != best:
                self.fail("FALSE_PRIMARY_CLAIM", primary["claim_best_average_quality"])
            for name, contrast in primary["contrasts"].items():
                if contrast.get("percentiles") and \
                        abs(contrast["percentiles"][0] - 1 / 120) > 1e-15:
                    self.fail("PRIMARY_NOT_BONFERRONI", name)
            self.ok("claim")
        public = self.run / "PUBLIC_SCORE.json"
        if public.exists():
            p = json.loads(public.read_text())
            scores = p["score"]["scores"]
            if not scores["serial_matches_frozen"] or scores["serial_rows"] != 120:
                self.fail("SERIAL_DENOMINATOR_MISMATCH", scores["serial_rows"])
            serial = scores["serial"]
            for arm_key, arm in scores["arms"].items():
                cs = arm["per_program_distinct_CSJ"]
                if arm["scores"] and arm["scores"][0] is not None and \
                        all(len(v) == 1 for v in cs.values()) and len(cs) == 8:
                    speed = math.exp(sum(math.log(serial[n][0] / cs[n][0][0]) for n in cs) / 8)
                    scratch = math.exp(sum(math.log(serial[n][1] / cs[n][0][1]) for n in cs) / 8)
                    if abs(math.sqrt(speed * scratch) - arm["scores"][0]) > 1e-12:
                        self.fail("SCORE_DENOMINATOR", arm_key)
            for key, entry in p["score"]["ratios"].items():
                strict = (len(entry["ratios"]) == 15 and
                          all(r is not None and r > 1 + 1e-12 for r in entry["ratios"]))
                if entry["strict_improvement_every_repetition"] != strict:
                    self.fail("FALSE_PUBLIC_STRICT_GAIN", key)
            self.ok("claim")

    def run_all(self) -> dict:
        self.package()
        self.learner_isolation()
        frozen = self.freeze()
        self.stages(frozen)
        self.claims()
        codes = collections.Counter(f["code"] for f in self.findings)
        return {"checker": "research/objective_index_checker.py",
                "checker_sha256": oc.file_sha256(Path(__file__)),
                "run": str(self.run), "checks": dict(self.counts),
                "starting_changes": getattr(self, "starting_changes", None),
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
    print(json.dumps({"status": report["status"], "finding_codes": report["finding_codes"],
                      "checks": sum(report["checks"].values())}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
