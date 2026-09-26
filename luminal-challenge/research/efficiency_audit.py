"""Successor numerical auditor of the next-round release (efficiency phase, R2).

Standard library ONLY. It imports nothing from ``research``, the production
tree or the reporter; every estimator below is written here from the plan's
definitions. The historical auditor ``research/next_round_audit.py`` is
unchanged; this successor writes to a NEW directory.

What it adds to the historical auditor (lead review F2):

- BOTH endpoints of every declared interval, every per-contrast flag, the
  joint mechanism verdict, the practical routes, the economics verdict and
  every other decision label are recomputed and compared;
- a FIELD-TO-CHECK MAP. Every leaf of every audited report is either compared
  by a named check (the leaf path is recorded when it is compared) or listed
  in ``DECLARED_UNCHECKED`` with a reason (timestamps, free text, paths, and
  quantities only the codec or a profiler can produce). A leaf in neither
  class is an ``UNMAPPED_FIELD`` finding. ``AUDIT_COVERAGE.json`` lists both;
  "nothing unaudited" is therefore never claimed;
- raw evidence is read strictly: a malformed line anywhere, including the
  final line of a completed stage, is a ``MALFORMED_ROW`` finding; duplicate,
  missing, unexpected, failed and timed-out rows are findings;
- a missing REQUIRED report or stage is a ``MISSING_REQUIRED`` finding, never
  a silent "not audited";
- learning evidence is recomputed from the fixture oracles and the returned
  orderings alone: the seeded training draw and its code-to-J alignment, the
  elite threshold, the common pool (Hamming 1-then-2 neighbours plus seeded
  draws), every ordering that has a closed-form definition (ascending,
  Hamming, the ten random permutations, the shuffled labels and both trees,
  with an independently written depth-3 Gini tree), the novel yields, the
  secondary endpoint, the sensitivity diagnostics, the design gates, the three
  contrasts and the mechanism verdict;
- export evidence: membership of all 624 rows, correctness, J = C*S, the
  compiler hash against its manifest, and the export public scores.

Usage::

    python research/efficiency_audit.py --run SOURCE_RUN --output OUT_DIR
"""

from __future__ import annotations

import argparse
import collections
import fnmatch
import hashlib
import itertools
import json
import math
import random
from fractions import Fraction
from pathlib import Path

TOL = 1e-9
TIE = 1e-12
ORDER_SEED = 2026092601
BOOT_SEED = 2026092602
TRAINING_SEED = 2026092603
POOL_SEED = 2026092604
SHUFFLED_SEED = 2026092605
RANDOM_SEEDS = tuple(range(2026092610, 2026092620))
RESAMPLES = 10000
PRIMARY = (0.025, 0.975)
CANDIDATE = (0.00625, 0.99375)
LEARNING = (0.008333333333333333, 0.9916666666666667)
BUDGETS = (0.01, 0.1, 1.0)
FAMILIES = ("scalar", "vector", "mixed", "dependency", "aliasing")
CELLS = ("cell_a3cat_dfs", "cell_a3cat_heap", "cell_a4cat_dfs", "cell_a4cat_heap")
EARLIER = "earlier_cap512_wider"
A4 = "cell_a4cat_heap"
DEV_ARMS = CELLS + (EARLIER,)
ORDERINGS = ("tree", "hamming", "shuffled_tree", "ascending") + tuple(
    f"random_{s}" for s in RANDOM_SEEDS)
PREFIX = 32
TRAINING = 20
MIN_YIELD_GAIN = 0.05
ECON_THRESHOLD = 0.1
ROUTES = {"quality_route": {"upper_J_ratio": 0.98, "upper_compile_ratio": 1.1},
          "efficiency_route": {"upper_compile_ratio": 0.8, "upper_J_ratio": 1.01}}
COST_FIELDS = ("compile_seconds", "bootstrap_seconds", "optimisation_seconds",
               "validate_seconds", "import_seconds", "process_seconds")
TARGET_RATES = (0.01, 0.05)
HAMMING_MAX = RANDOM_MAX = 256
RANDOM_DRAWS_MAX = 8192
MAX_DEPTH, MIN_CHILD = 3, 4

REQUIRED_REPORTS = ("SELECTION.json", "FACTORIAL.json", "BOTTLENECKS.json",
                    "ENGINEERING_DECISION.json", "FROZEN_SELECTION.json",
                    "CONFIRMATION_COHORT.json", "COMPARISON.json", "PUBLIC_SCORE.json",
                    "LEARNING_FREEZE.json", "LEARNING_FEASIBILITY.json",
                    "learning/DESIGN_DEVELOPMENT.json", "learning/DESIGN_EVALUATION.json",
                    "export/candidate/EXPORT_VALIDATION.json",
                    "export/candidate/compiler_MANIFEST.json")
REQUIRED_STAGES = ("D_factorial", "D_fixed_work", "D_profile", "E_engineering",
                   "C_confirmation", "C_public", "L_acquisition", "L_orderings")

# Leaves not compared numerically, each with its reason. Patterns are
# fnmatch patterns over "file::dotted.path" (list positions are numbers).
DECLARED_UNCHECKED = {
    "*::decided_utc": "timestamp",
    "*::frozen_utc": "timestamp",
    "*::protocol_id": "checked as a constant by check_constants, not per report",
    "SELECTION.json::population": "free text",
    "SELECTION.json::stage": "free text",
    "SELECTION.json::selection.rule": "free text restating the rule that is recomputed",
    "FACTORIAL.json::budgets.*.factorial.sign": "free text",
    "FACTORIAL.json::fixed_work.note": "free text",
    "FACTORIAL.json::targets.*.*.*.note": "free text",
    "COMPARISON.json::targets.*.*.*.note": "free text",
    "COMPARISON.json::primary.endpoint": "free text",
    "COMPARISON.json::bootstrap_consistency.note": "free text",
    "ENGINEERING_DECISION.json::claim_limit": "free text",
    "ENGINEERING_DECISION.json::parity_evidence": "free text naming a test file",
    "ENGINEERING_DECISION.json::prediction_vs_outcome": "free text",
    "ENGINEERING_DECISION.json::reason": "free text restating the recomputed decision",
    "ENGINEERING_DECISION.json::stage": "free text",
    "LEARNING_FEASIBILITY.json::economics.note": "free text",
    "LEARNING_FEASIBILITY.json::evaluation_sensitivity.*.decode_mismatches":
        "needs the codec (structural_encoding.decode); the auditor imports no codec",
    "learning/DESIGN_*.json::designs.*.sensitivity.decode_mismatches":
        "needs the codec (structural_encoding.decode); the auditor imports no codec",
    "learning/DESIGN_*.json::designs.*.ranker_input": "absolute path; its hash is checked",
    "learning/DESIGN_*.json::manifest": "path; the manifest it names is read and checked",
    "learning/DESIGN_*.json::cohort": "label",
    "FROZEN_SELECTION.json::inference.*": "free text and the route constants (compared "
                                          "with ROUTES by check_constants)",
    "FROZEN_SELECTION.json::learning_track.*": "source hashes of the learning track; the "
                                               "successor checker owns source identity",
    "FROZEN_SELECTION.json::reporting.*": "source hash; the successor checker owns it",
    "FROZEN_SELECTION.json::references.*": "worker/solver labels",
    "FROZEN_SELECTION.json::confirmation.measured_sources.*": "source list; checker",
    "FROZEN_SELECTION.json::package_lock_sha256": "package lock; checker",
    "FROZEN_SELECTION.json::sources.*": "source hashes at the freeze; the successor checker "
                                        "owns source identity",
    "learning/DESIGN_*.json::utc": "timestamp",
    "FROZEN_SELECTION.json::exposure.*": "declaration, not a number",
    "CONFIRMATION_COHORT.json::*": "cohort legality metadata; the program digests are "
                                   "recomputed from the pinned inputs by programs()",
    "LEARNING_FREEZE.json::ranker_sources.*": "source hashes; checker",
    "LEARNING_FREEZE.json::evaluation_outcomes_observed": "declaration",
    "export/candidate/EXPORT_VALIDATION.json::pinned.*": "pinned-workspace evidence; "
        "exit codes are compared, identity strings are labels",
    "export/candidate/EXPORT_VALIDATION.json::build.path": "absolute path",
    "export/candidate/EXPORT_VALIDATION.json::outputs_outside_research_J_set.note":
        "free text",
    "export/candidate/EXPORT_VALIDATION.json::label": "label",
    "export/candidate/compiler_MANIFEST.json::owner_generator_sha256":
        "hash of the frozen owner generator; checker",
    "export/candidate/compiler_MANIFEST.json::generator_sha256": "checker",
    "export/candidate/*::build.components.*": "component hashes; checker",
    "export/candidate/compiler_MANIFEST.json::components.*": "component hashes; checker",
}


# --------------------------------------------------------------------------
# Independent estimators
# --------------------------------------------------------------------------


def stable(parts) -> int:
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def mean(values):
    values = list(values)
    return sum(values) / len(values)


def median(values):
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def percentile(sorted_values, p):
    pos = (len(sorted_values) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(sorted_values[lo])
    w = pos - lo
    return float(sorted_values[lo] * (1 - w) + sorted_values[hi] * w)


def by_family(per_program, families):
    grouped = collections.defaultdict(list)
    for p, v in per_program.items():
        grouped[families[p]].append(v)
    return grouped


def family_mean(per_program, families):
    grouped = by_family(per_program, families)
    return mean(mean(v) for _, v in sorted(grouped.items()))


def family_breakdown(per_program, families):
    return {f: {"n": len(v), "mean": mean(v)}
            for f, v in sorted(by_family(per_program, families).items())}


_BOOT_CACHE: dict = {}


def bootstrap(per_program, families, percentiles, seed=BOOT_SEED):
    """Program-within-family resampling, equal family weights, linear percentiles."""

    grouped = {}
    for p, v in sorted(per_program.items()):
        grouped.setdefault(families[p], []).append(v)
    key = (tuple((f, tuple(v)) for f, v in sorted(grouped.items())), tuple(percentiles), seed)
    if key in _BOOT_CACHE:
        return _BOOT_CACHE[key]
    rng = random.Random(seed)
    draws = []
    for _ in range(RESAMPLES):
        means = []
        for family in sorted(grouped):
            vals = grouped[family]
            means.append(mean(vals[rng.randrange(len(vals))] for _ in range(len(vals))))
        draws.append(mean(means))
    draws.sort()
    point = mean(mean(grouped[f]) for f in sorted(grouped))
    out = (point, [percentile(draws, percentiles[0]), percentile(draws, percentiles[1])])
    _BOOT_CACHE[key] = out
    return out


def quantiles_index(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return {str(q): values[int(q * (len(values) - 1))] for q in (0.0, 0.25, 0.5, 0.75, 1.0)}


# --------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------


def keys_for(programs, cell_list, repetitions):
    out = []
    for digest in programs:
        for rep in range(repetitions):
            ordered = sorted(cell_list, key=lambda c: (
                stable([ORDER_SEED, digest, rep, c[0], c[1]]), c[0],
                "" if c[1] is None else str(c[1])))
            out.extend(f"{digest}|{a}|{b}|{rep}" for a, b in ordered)
    return out


def cells(unbudgeted, budgeted, budgets=BUDGETS):
    return [(a, None) for a in unbudgeted] + [(a, b) for a in budgeted for b in budgets]


def program_digest(path: Path) -> str:
    program = json.loads(path.read_text())
    return hashlib.sha256(json.dumps(program, sort_keys=True, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def file_sha(path: Path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def index_rows(rows):
    return {(r["program_sha256"], r["arm"], r["budget_seconds"], r["repetition"]): r
            for r in rows}


def logj(rows, arm, budget, reps):
    by = collections.defaultdict(list)
    for r in rows:
        if r["arm"] == arm and r["budget_seconds"] == budget:
            by[r["program_sha256"]].append(None if r["failed_row"] else math.log(r["product"]))
    out, incomplete = {}, []
    for p, v in by.items():
        if len(v) == reps and all(x is not None for x in v):
            out[p] = mean(v)
        else:
            incomplete.append(p)
    return out, sorted(incomplete)


def medians(rows, arm, budget, field):
    values = collections.defaultdict(list)
    for r in rows:
        if r["arm"] == arm and r["budget_seconds"] == budget and not r["failed_row"]:
            value = r["process_seconds"] if field == "process_seconds" else r["result"][field]
            if value is None:
                continue
            values[r["program_sha256"]].append(value)
    return {p: median(v) for p, v in values.items()}


def geometric(rows, arm, budget, field, families):
    try:
        m = medians(rows, arm, budget, field)
    except KeyError:
        return None
    if not m or min(m.values()) <= 0:
        return None
    return math.exp(family_mean({p: math.log(v) for p, v in m.items()}, families))


def paired(rows, control, candidate, cb, db, reps):
    idx = index_rows(rows)
    programs = sorted({r["program_sha256"] for r in rows})
    out, missing, failed = {}, 0, 0
    for p in programs:
        logs = []
        for rep in range(reps):
            a, b = idx.get((p, control, cb, rep)), idx.get((p, candidate, db, rep))
            if a is None or b is None:
                missing += 1
                continue
            if a["failed_row"] or b["failed_row"]:
                failed += 1
                continue
            logs.append(math.log(a["product"] / b["product"]))
        if len(logs) == reps:
            out[p] = mean(logs)
    wins = sum(v > TIE for v in out.values())
    losses = sum(v < -TIE for v in out.values())
    return {"per_program": out, "missing": missing, "failed": failed,
            "wtl": [wins, len(out) - wins - losses, losses]}


def cost_logs(rows, control, candidate, cb, db, families):
    a = medians(rows, control, cb, "compile_seconds")
    b = medians(rows, candidate, db, "compile_seconds")
    return {p: math.log(b[p] / a[p]) for p in sorted(set(a) & set(b)) if a[p] > 0 and b[p] > 0}


# --------------------------------------------------------------------------
# Learning primitives (independent re-implementations)
# --------------------------------------------------------------------------


def elite_threshold(products):
    ordered = sorted(products)
    return ordered[max(1, math.ceil(0.1 * len(ordered))) - 1]


def gini(pos, count):
    if count == 0:
        return Fraction(0)
    p = Fraction(pos, count)
    return 1 - p * p - (1 - p) * (1 - p)


def fit_tree(bits, indices, labels):
    """Independent depth-3 exact-Gini tree: list of (fixed {coord: bit}, count, pos, depth)."""

    leaves = []

    def grow(fixed, rows, depth):
        pos, count = sum(l for _, l in rows), len(rows)
        if depth >= MAX_DEPTH or pos in (0, count):
            leaves.append((dict(fixed), count, pos, depth))
            return
        parent = gini(pos, count)
        best = None
        for c in range(bits):
            if c in fixed:
                continue
            left = [r for r in rows if not (r[0] >> c) & 1]
            right = [r for r in rows if (r[0] >> c) & 1]
            if len(left) < MIN_CHILD or len(right) < MIN_CHILD:
                continue
            gain = parent - (Fraction(len(left), count) * gini(sum(l for _, l in left), len(left))
                             + Fraction(len(right), count)
                             * gini(sum(l for _, l in right), len(right)))
            if best is None or gain > best[0]:
                best = (gain, c, left, right)
        if best is None or best[0] <= 0:
            leaves.append((dict(fixed), count, pos, depth))
            return
        _, c, left, right = best
        grow({**fixed, c: 0}, left, depth + 1)
        grow({**fixed, c: 1}, right, depth + 1)

    grow({}, list(zip(indices, labels)), 0)
    return leaves


def tree_order(pool, leaves):
    def score(index):
        for fixed, count, pos, _ in leaves:
            if all((index >> c) & 1 == b for c, b in fixed.items()):
                return Fraction(pos + 1, count + 2)
        raise ValueError("index outside the universe")
    return sorted(pool, key=lambda i: (-score(i), i))


def common_pool(bits, training, elite, seed):
    training_set = set(training)
    chosen, seen = [], set()
    for distance in (1, 2):
        if len(chosen) >= HAMMING_MAX:
            break
        for anchor in sorted(set(elite)):
            if len(chosen) >= HAMMING_MAX:
                break
            for coords in itertools.combinations(range(bits), distance):
                candidate = anchor
                for c in coords:
                    candidate ^= 1 << c
                if candidate in training_set or candidate in seen:
                    continue
                seen.add(candidate)
                chosen.append(candidate)
                if len(chosen) >= HAMMING_MAX:
                    break
    hamming = len(chosen)
    rng = random.Random(seed)
    draws = added = 0
    exhausted = False
    while added < RANDOM_MAX and draws < RANDOM_DRAWS_MAX:
        if len(training_set | seen) >= (1 << bits):
            exhausted = True
            break
        draws += 1
        candidate = rng.getrandbits(bits) if bits else 0
        if candidate in training_set or candidate in seen:
            continue
        seen.add(candidate)
        added += 1
    pool = sorted(seen)
    return {"pool": pool, "hamming": hamming, "random": added, "draws": draws,
            "universe_exhausted": exhausted, "size": len(pool),
            "pool_sha256": hashlib.sha256(json.dumps(pool, separators=(",", ":")).encode())
            .hexdigest()}


# --------------------------------------------------------------------------
# The audit
# --------------------------------------------------------------------------


class Audit:
    def __init__(self, run: Path, root: Path = None) -> None:
        self.run = Path(run).resolve()
        self.root = Path(root) if root is not None else self.run.parents[2]
        self.checks = 0
        self.findings = []
        self.checked = {}          # "file::path" -> check code
        self.reports = {}
        self.stage_rows = {}
        self.notes = []
        self.loader = self._read_report
        self.raw_codes = set()

    # -- bookkeeping -------------------------------------------------------

    def ok(self, cond, code, detail=""):
        self.checks += 1
        self.raw_codes.add(code)
        if not cond:
            self.findings.append({"code": code, "detail": str(detail)[:400]})
        return cond

    def _read_report(self, name):
        path = self.run / name
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def report(self, name):
        if name not in self.reports:
            value = self.loader(name)
            self.ok(value is not None, "MISSING_REQUIRED", name)
            self.reports[name] = value
        return self.reports[name]

    def get(self, name, path):
        node = self.report(name)
        for part in path:
            if node is None:
                return _MISSING
            if isinstance(node, dict):
                if part not in node:
                    return _MISSING
                node = node[part]
            elif isinstance(node, list):
                if not isinstance(part, int) or part >= len(node):
                    return _MISSING
                node = node[part]
            else:
                return _MISSING
        return node

    def expect(self, name, path, expected, code, tol=TOL):
        """Compare a report subtree with an expected object; mark every leaf checked."""

        path = tuple(path)
        actual = self.get(name, path)
        self._compare(name, path, actual, expected, code, tol)

    def _compare(self, name, path, actual, expected, code, tol):
        label = f"{name}::{'.'.join(str(p) for p in path)}"
        if isinstance(expected, dict):
            if not self.ok(isinstance(actual, dict), code, f"{label}: not an object"):
                return
            self.ok(set(actual) == set(expected), code,
                    f"{label}: keys {sorted(set(actual) ^ set(expected))[:6]}")
            for k in expected:
                if k in actual:
                    self._compare(name, path + (k,), actual[k], expected[k], code, tol)
            return
        if isinstance(expected, (list, tuple)):
            if not self.ok(isinstance(actual, list) and len(actual) == len(expected), code,
                           f"{label}: list length"):
                return
            for i, (a, e) in enumerate(zip(actual, expected)):
                self._compare(name, path + (i,), a, e, code, tol)
            if not expected:
                self.checked[label] = code
            return
        self.checked[label] = code
        detail = f"{label}: {actual!r} vs {expected!r}"
        if actual is _MISSING:
            self.ok(False, code, f"{label}: missing")
        elif expected is None or isinstance(expected, bool):
            self.ok(actual is expected, code, detail)
        elif isinstance(expected, (int, float)):
            number = isinstance(actual, (int, float)) and not isinstance(actual, bool)
            self.ok(number and abs(actual - expected) <= tol * max(1.0, abs(expected)), code,
                    detail)
        else:
            self.ok(actual == expected, code, detail)

    # -- raw evidence --------------------------------------------------------

    def strict_rows(self, path: Path, label: str):
        rows = []
        text = path.read_text()
        for number, line in enumerate(text.splitlines()):
            if not line.strip():
                self.ok(False, "MALFORMED_ROW", f"{label}: blank line {number + 1}")
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                self.ok(False, "MALFORMED_ROW", f"{label}: line {number + 1}")
                continue
            self.ok(isinstance(row, dict) and "key" in row, "MALFORMED_ROW",
                    f"{label}: line {number + 1} has no key")
            rows.append(row)
        self.ok(text.endswith("\n") or not text, "MALFORMED_ROW", f"{label}: torn final line")
        return rows

    def stage(self, stage, programs, cell_list, repetitions, frozen=False):
        directory = self.run / "stages" / stage
        if not self.ok((directory / "rows.jsonl").exists(), "MISSING_REQUIRED",
                       f"stages/{stage}"):
            return None
        rows = self.strict_rows(directory / "rows.jsonl", stage)
        expected = keys_for(programs, cell_list, repetitions)
        ledger = json.loads((directory / "EXPECTED_KEYS.json").read_text())
        self.ok(ledger["keys"] == expected, "LEDGER_DIFFERS_FROM_PLAN", stage)
        self.ok(ledger.get("count") == len(expected), "LEDGER_COUNT", stage)
        if frozen:
            path = self.run / "frozen_expected" / f"{stage}.json"
            self.ok(path.exists() and json.loads(path.read_text())["keys"] == expected,
                    "FROZEN_LEDGER", stage)
        self._rows_integrity(stage, rows, expected)
        self.stage_rows[stage] = rows
        return rows

    def _rows_integrity(self, stage, rows, expected):
        counts = collections.Counter(r.get("key") for r in rows)
        self.ok(set(counts) == set(expected), "ROW_SET",
                f"{stage}: missing {len(set(expected) - set(counts))}, "
                f"unexpected {len(set(counts) - set(expected))}")
        self.ok(all(n == 1 for n in counts.values()), "DUPLICATES", stage)
        for r in rows:
            key = r.get("key")
            self.ok(not r.get("failed_row", True), "FAILED_ROW", key)
            self.ok(r.get("timed_out") is False, "TIMED_OUT", key)
            self.ok(r.get("exit_code") == 0, "EXIT_CODE", key)
            if r.get("cycles") is not None:
                self.ok(r["product"] == r["cycles"] * r["scratch"], "PRODUCT", key)
                result = r.get("result") or {}
                if "product" in result:
                    self.ok(result["product"] == r["product"], "RESULT_PRODUCT", key)
            if r.get("seed") is not None:
                self.ok(r["family"] == FAMILIES[r["seed"] % 5], "FAMILY", key)
            if key:
                p, arm, budget, rep = key.split("|")
                self.ok((r["program_sha256"], r["arm"], str(r["budget_seconds"]),
                         str(r["repetition"])) == (p, arm, budget, rep), "KEY_FIELDS", key)

    def programs(self, cohort, first, last):
        out, fam = [], {}
        for seed in range(first, last + 1):
            digest = program_digest(self.run / "inputs" / cohort / f"seed_{seed}.json")
            out.append((FAMILIES.index(FAMILIES[seed % 5]), seed, digest))
            fam[digest] = FAMILIES[seed % 5]
        out.sort()
        counts = collections.Counter(fam.values())
        self.ok(len(fam) == last - first + 1, "PROGRAM_COUNT", cohort)
        self.ok(len(counts) == 5 and len(set(counts.values())) == 1, "FAMILY_BALANCE", cohort)
        return [d for _, _, d in out], fam

    def completeness(self, rows, expected_keys):
        counts = collections.Counter(r["key"] for r in rows)
        expected = set(expected_keys)
        return {"expected": len(expected_keys), "observed": len(counts),
                "missing": sorted(expected - set(counts))[:20],
                "missing_count": len(expected - set(counts)),
                "unexpected_count": len(set(counts) - expected),
                "duplicates": sorted(k for k, n in counts.items() if n > 1)[:20],
                "failed": sum(1 for r in rows if r["failed_row"]),
                "timed_out": sum(1 for r in rows if r["timed_out"]),
                "complete": expected == set(counts) and all(n == 1 for n in counts.values())}

    # -- summaries -------------------------------------------------------------

    def arm_summary(self, rows, arm, budget, reps, families):
        values, incomplete = logj(rows, arm, budget, reps)
        return {"arm": arm, "budget_seconds": budget, "programs": len(values),
                "incomplete_programs": incomplete,
                "family_mean_log_J": family_mean(values, families) if values else None,
                "family_breakdown_log_J": family_breakdown(values, families) if values else None,
                "costs_geometric_median": {f: geometric(rows, arm, budget, f, families)
                                           for f in COST_FIELDS}}

    def targets(self, rows, arms):
        base = {}
        for r in rows:
            value = (r.get("result") or {}).get("bootstrap_product")
            if value is not None:
                previous = base.setdefault(r["program_sha256"], value)
                self.ok(previous == value, "BOOTSTRAP_J_CONSISTENT", r["key"])
        out = {"bootstrap_programs": len(base), "rates": list(TARGET_RATES), "arms": {}}
        for arm in arms:
            per_arm = {}
            for rate in TARGET_RATES:
                for budget in BUDGETS:
                    selected = [r for r in rows if r["arm"] == arm
                                and r["budget_seconds"] == budget]
                    reached = censored = failed = 0
                    times = []
                    for r in selected:
                        if r["failed_row"]:
                            failed += 1
                            times.append(math.inf)
                            continue
                        target = math.floor((1 - rate) * base[r["program_sha256"]])
                        reached += r["product"] <= target
                        trajectory = (r.get("result") or {}).get("trajectory")
                        if trajectory is None:
                            times.append(None)
                            continue
                        first = next((t for t, j in trajectory if j <= target), None)
                        if first is None:
                            censored += 1
                            times.append(math.inf)
                        else:
                            times.append(first)
                    entry = {"rows": len(selected), "failed_rows_counted_unreached": failed,
                             "reached": reached,
                             "attainment": reached / len(selected) if selected else None}
                    known = [t for t in times if t is not None]
                    if known and len(known) == len(selected):
                        ordered = sorted(known)
                        entry["hitting_time_quantiles_capped"] = {
                            str(q): (None if ordered[int(q * (len(ordered) - 1))] == math.inf
                                     else ordered[int(q * (len(ordered) - 1))])
                            for q in (0.1, 0.25, 0.5, 0.75, 0.9)}
                        entry["censored_at_budget"] = censored + failed
                        entry["note"] = _SKIP
                    else:
                        entry["hitting_time_quantiles_capped"] = (
                            "unavailable: no trajectory recorded")
                    per_arm[f"r{rate}@{budget}"] = entry
            out["arms"][arm] = per_arm
        return out

    def interruption_sums(self, rows, arm, with_rows=False, with_successor=False):
        def total(field):
            return sum((r.get("result") or {}).get("optimisation", {}).get(field, 0)
                       for r in rows if r["arm"] == arm)
        out = {"interrupted_validation_total": total("interrupted_validation_total"),
               "affected_queries": total("interrupted_validation_queries"),
               "construction_interruptions": total("construction_interruption_count")}
        if with_rows:
            out["rows"] = sum(1 for r in rows if r["arm"] == arm)
        if with_successor:
            out["rows_with_successor_accounting"] = sum(
                1 for r in rows if r["arm"] == arm and "interrupted_validation_total" in
                ((r.get("result") or {}).get("optimisation") or {}))
        return out

    # -- parts -----------------------------------------------------------------

    def development(self):
        programs, fam = self.programs("development", 800000, 800099)
        self.dev_families = fam
        rows = self.stage("D_factorial", programs, cells([], list(DEV_ARMS)), 3)
        if rows is None:
            return None
        name = "SELECTION.json"
        table = {}
        for arm in DEV_ARMS:
            values, incomplete = logj(rows, arm, 0.1, 3)
            table[arm] = {"family_mean_log_J": family_mean(values, fam) if values else math.inf,
                          "programs": len(values), "incomplete": incomplete,
                          "geometric_median_compile_seconds": geometric(rows, arm, 0.1,
                                                                        "compile_seconds", fam)}
        best = min(e["family_mean_log_J"] for e in table.values())
        tied = sorted(a for a, e in table.items() if e["family_mean_log_J"] - best <= TIE)
        chosen = sorted(tied, key=lambda a: (table[a]["geometric_median_compile_seconds"], a))[0]
        expected_keys = json.loads((self.run / "stages/D_factorial/EXPECTED_KEYS.json")
                                   .read_text())["keys"]
        self.expect(name, ("completeness",), self.completeness(rows, expected_keys),
                    "SELECTION_COMPLETENESS")
        self.expect(name, ("selection", "table"), table, "SELECTION_TABLE")
        self.expect(name, ("selection", "selected_arm"), chosen, "SELECTION")
        self.expect(name, ("selection", "tie_group"), tied, "SELECTION_TIES")
        self.expect(name, ("selection", "status"), "SELECTED", "SELECTION_STATUS")
        self.expect(name, ("rows_sha256",), file_sha(self.run / "stages/D_factorial/rows.jsonl"),
                    "SELECTION_ROWS_HASH")
        self.expect(name, ("selected_is_distinct_from_references",),
                    chosen not in (A4, EARLIER), "SELECTION_DISTINCT")
        self.factorial(rows, fam, expected_keys)
        engineered = self.engineering(rows, programs, fam, chosen)
        return chosen

    def factorial(self, rows, fam, expected_keys):
        name = "FACTORIAL.json"
        self.expect(name, ("completeness",), self.completeness(rows, expected_keys),
                    "FACTORIAL_COMPLETENESS")
        for budget in BUDGETS:
            b = str(budget)
            y = {c: logj(rows, c, budget, 3)[0] for c in CELLS}
            common = sorted(set.intersection(*(set(v) for v in y.values())))
            yy = {("a4", "heap"): y["cell_a4cat_heap"], ("a4", "dfs"): y["cell_a4cat_dfs"],
                  ("a3", "heap"): y["cell_a3cat_heap"], ("a3", "dfs"): y["cell_a3cat_dfs"]}
            contrasts = {
                "catalog_effect_a4_minus_a3": lambda p: 0.5 * (
                    (yy["a4", "heap"][p] - yy["a3", "heap"][p])
                    + (yy["a4", "dfs"][p] - yy["a3", "dfs"][p])),
                "traversal_effect_heap_minus_dfs": lambda p: 0.5 * (
                    (yy["a4", "heap"][p] - yy["a4", "dfs"][p])
                    + (yy["a3", "heap"][p] - yy["a3", "dfs"][p])),
                "interaction": lambda p: ((yy["a4", "heap"][p] - yy["a4", "dfs"][p])
                                          - (yy["a3", "heap"][p] - yy["a3", "dfs"][p])),
                "catalog_effect_under_heap": lambda p: yy["a4", "heap"][p] - yy["a3", "heap"][p],
                "catalog_effect_under_dfs": lambda p: yy["a4", "dfs"][p] - yy["a3", "dfs"][p],
                "traversal_effect_under_a4": lambda p: yy["a4", "heap"][p] - yy["a4", "dfs"][p],
                "traversal_effect_under_a3": lambda p: yy["a3", "heap"][p] - yy["a3", "dfs"][p],
            }
            expected = {"budget_seconds": budget, "programs": len(common),
                        "cell_family_mean_log_J": {c: family_mean({p: y[c][p] for p in common},
                                                                  fam) for c in CELLS},
                        "sign": _SKIP}
            for label, fn in contrasts.items():
                per = {p: fn(p) for p in common}
                point, interval = bootstrap(per, fam, PRIMARY)
                expected[label] = {"estimate": point, "interval_95": interval,
                                   "family_breakdown": family_breakdown(per, fam),
                                   "programs": len(per)}
            self.expect(name, ("budgets", b, "factorial"), expected, "FACTORIAL_CONTRAST")
            self.expect(name, ("budgets", b, "arms"),
                        {a: self.arm_summary(rows, a, budget, 3, fam) for a in DEV_ARMS},
                        "FACTORIAL_ARM")
            versus = {}
            for arm in DEV_ARMS:
                if arm == A4:
                    continue
                result = paired(rows, arm, A4, budget, budget, 3)
                point, interval = bootstrap(result["per_program"], fam, PRIMARY)
                versus[f"log(J_{arm}/J_{A4})"] = {
                    "estimate": point, "interval_95": interval,
                    "wins_ties_losses_for_repaired_A4": result["wtl"]}
            self.expect(name, ("budgets", b, "versus_repaired_A4_descriptive"), versus,
                        "FACTORIAL_VERSUS_A4")
        self.expect(name, ("targets",), self.targets(rows, DEV_ARMS), "FACTORIAL_TARGETS")
        self.expect(name, ("interruption_accounting",),
                    {a: self.interruption_sums(rows, a, with_rows=True) for a in CELLS},
                    "FACTORIAL_INTERRUPTIONS")
        profile_programs, seen = [], collections.Counter()
        for digest in self._dev_order:
            if seen[fam[digest]] < 2:
                profile_programs.append(digest)
                seen[fam[digest]] += 1
        fixed = self.stage("D_fixed_work", profile_programs,
                           cells([], list(CELLS), [f"work:{n}" for n in (1000, 10000, 50000)]), 1)
        if fixed is not None:
            fixed_keys = json.loads((self.run / "stages/D_fixed_work/EXPECTED_KEYS.json")
                                    .read_text())["keys"]
            cells_out = {}
            for label in sorted(CELLS):
                for limit in (1000, 10000, 50000):
                    budget = f"work:{limit}"
                    selected = [r for r in fixed if r["arm"] == label
                                and r["budget_seconds"] == budget]
                    ok = [r for r in selected if not r["failed_row"]]
                    values = {r["program_sha256"]: math.log(r["product"]) for r in ok}
                    work = [r["result"]["work"] for r in ok]
                    cells_out[f"{label}@{limit}"] = {
                        "rows": len(selected), "failed": len(selected) - len(ok),
                        "timed_out": sum(r["timed_out"] for r in selected),
                        "family_mean_log_J": family_mean(values, fam) if values else None,
                        "charged_nodes_total": sum(w["charged_nodes"] for w in work),
                        "charged_nodes_max": max((w["charged_nodes"] for w in work),
                                                 default=None),
                        "propagation_certificates_total": sum(
                            w["propagation_certificates"] for w in work),
                        "validations_total": sum(w["validations"] for w in work),
                        "compile_seconds_geometric": (math.exp(mean(
                            math.log(r["result"]["compile_seconds"]) for r in ok))
                            if ok else None),
                        "stopped_because": dict(collections.Counter(
                            r["result"]["optimisation"]["stopped_because"] for r in ok))}
            self.expect(name, ("fixed_work",),
                        {"completeness": self.completeness(fixed, fixed_keys),
                         "cells": cells_out, "note": _SKIP}, "FACTORIAL_FIXED_WORK")
        profile = self.stage("D_profile", profile_programs, cells([], list(DEV_ARMS)), 1)
        if profile is not None:
            out = {}
            for arm in DEV_ARMS:
                for budget in BUDGETS:
                    selected = [r for r in profile if r["arm"] == arm
                                and r["budget_seconds"] == budget and not r["failed_row"]]
                    if not selected:
                        continue
                    seconds = collections.Counter()
                    total = wall = 0.0
                    for r in selected:
                        for k, v in r["result"]["category_seconds"].items():
                            seconds[k] += v
                        total += r["result"]["profiled_tottime_total"]
                        wall += r["result"]["profiled_call_wall_seconds"]
                    out[f"{arm}@{budget}"] = {
                        "programs": len(selected), "profiled_tottime_total": total,
                        "profiled_call_wall_total": wall, "reconciliation_ratio": total / wall,
                        "shares": {k: v / total for k, v in sorted(seconds.items())},
                        "largest": max(seconds, key=seconds.get)}
            self.expect("BOTTLENECKS.json", (), out, "BOTTLENECKS")

    def engineering(self, rows, programs, fam, chosen):
        variant = f"{chosen}+engineered"
        engineered = self.stage("E_engineering", programs, cells([], [variant]), 3)
        if engineered is None:
            return None
        name = "ENGINEERING_DECISION.json"
        both = rows + engineered
        keys = json.loads((self.run / "stages/E_engineering/EXPECTED_KEYS.json")
                          .read_text())["keys"]
        self.expect(name, ("completeness",), self.completeness(engineered, keys), "E_COMPLETE")
        by_budget = {}
        for budget in BUDGETS:
            p_values, pi = logj(both, chosen, budget, 3)
            v_values, vi = logj(both, variant, budget, 3)
            quality = family_mean(v_values, fam) - family_mean(p_values, fam)
            tp = geometric(both, chosen, budget, "compile_seconds", fam)
            tv = geometric(both, variant, budget, "compile_seconds", fam)
            reduction = 1 - tv / tp
            by_budget[str(budget)] = {
                "parent": chosen, "variant": variant,
                "delta_family_mean_log_J_variant_minus_parent": quality,
                "geometric_median_compile_parent": tp, "geometric_median_compile_variant": tv,
                "compile_time_reduction": reduction, "quality_not_worse": quality <= TIE,
                "reduction_at_least_10pct": reduction >= 0.10}
        self.expect(name, ("decision_by_budget",), by_budget, "E_DECISION_TABLE")
        d = by_budget["0.1"]
        frozen = variant if (d["quality_not_worse"] and d["reduction_at_least_10pct"]) else chosen
        self.expect(name, ("frozen_candidate",), frozen, "E_DECISION")
        self.expect(name, ("eligible",), not any(r["failed_row"] for r in engineered)
                    and self.completeness(engineered, keys)["complete"], "E_ELIGIBLE")
        quality = paired(both, chosen, variant, 0.1, 0.1, 3)
        qp, qi = bootstrap(quality["per_program"], fam, PRIMARY)
        costs = cost_logs(both, chosen, variant, 0.1, 0.1, fam)
        cp, ci = bootstrap(costs, fam, PRIMARY)
        self.expect(name, ("development_uncertainty_at_0.1",), {
            "paired_log_J_parent_over_variant": {"estimate": qp, "interval_95": qi,
                                                 "wins_ties_losses_for_variant": quality["wtl"]},
            "log_compile_ratio_variant_over_parent": {"estimate": cp, "interval_95": ci}},
            "E_UNCERTAINTY")
        return frozen

    def confirmation(self, chosen):
        frozen = self.report("FROZEN_SELECTION.json")
        decision = self.report("ENGINEERING_DECISION.json")
        if not frozen or not decision:
            return
        name = "FROZEN_SELECTION.json"
        candidate = decision["frozen_candidate"]
        arms = [EARLIER, A4] + ([candidate] if candidate not in (EARLIER, A4) else [])
        self.expect(name, ("candidate",), {
            "candidate_is_distinct_new": candidate not in (EARLIER, A4),
            "engineering_variant_frozen": candidate.endswith("+engineered"),
            "frozen_candidate": candidate, "selected_development_arm": chosen}, "FREEZE")
        self.expect(name, ("confirmation", "budgeted_arms"), arms, "FREEZE_ARMS")
        self.expect(name, ("confirmation", "unbudgeted_controls"),
                    ["classical", "accepted_bootstrap"], "FREEZE_CONTROLS")
        self.expect(name, ("confirmation", "repetitions"), 5, "FREEZE_REPS")
        self.expect(name, ("confirmation", "K"), len(arms), "FREEZE_K")
        self.expect(name, ("confirmation", "public_extra_control"), "serial", "FREEZE_SERIAL")
        for key, entry in (frozen.get("inputs") or {}).items():
            self.expect(name, ("inputs", key), {"path": entry["path"],
                                                "sha256": file_sha(self.run / entry["path"])},
                        "FREEZE_INPUT_HASH")
        for stage in ("C_confirmation", "C_public"):
            path = self.run / "frozen_expected" / f"{stage}.json"
            self.expect(name, ("expected_matrices", stage),
                        {"count": len(json.loads(path.read_text())["keys"]),
                         "sha256": file_sha(path)}, "FREEZE_MATRIX")
        self.expect(name, ("expected_matrices", "export_candidate", "count"), 624,
                    "FREEZE_MATRIX")
        self.expect(name, ("inference", "practical_routes"), ROUTES, "ROUTE_CONSTANTS")
        self.expect(name, ("seeds",), {"arm_order": ORDER_SEED, "bootstrap": BOOT_SEED,
                                       "pool": POOL_SEED, "random_order": list(RANDOM_SEEDS),
                                       "shuffled_labels": SHUFFLED_SEED,
                                       "training_draw": TRAINING_SEED}, "FREEZE_SEEDS")
        programs, fam = self.programs("confirmation", 960000, 960199)
        self.conf_families = fam
        rows = self.stage("C_confirmation", programs,
                          cells(["classical", "accepted_bootstrap"], arms), 5, frozen=True)
        cohort = self.report("CONFIRMATION_COHORT.json")
        order = [e["program_sha256"] for e in cohort["public_programs"]]
        public_set = sorted(program_digest(p) for p in (self.run / "inputs/public").glob("*.json"))
        self.ok(sorted(order) == public_set and len(order) == 8, "PUBLIC_SET")
        self.ok(sorted(e["program_sha256"] for e in cohort["programs"]) == sorted(programs),
                "COHORT_PROGRAMS")
        public_rows = self.stage("C_public", order,
                                 cells(["classical", "accepted_bootstrap", "serial"], arms), 5,
                                 frozen=True)
        if rows is not None:
            self.comparison(rows, fam, arms, candidate)
        if public_rows is not None:
            self.public(public_rows, arms, order)
        self.export(rows, public_rows, order, programs, candidate)

    def comparison(self, rows, fam, arms, candidate):
        name = "COMPARISON.json"
        keys = json.loads((self.run / "frozen_expected/C_confirmation.json").read_text())["keys"]
        self.expect(name, ("completeness",), self.completeness(rows, keys), "C_COMPLETENESS")
        self.expect(name, ("candidate",), candidate, "C_CANDIDATE")
        result = paired(rows, EARLIER, A4, 0.1, 0.1, 5)
        point, interval = bootstrap(result["per_program"], fam, PRIMARY)
        verdict = ("FAVOURS_A4" if interval[0] > 0 else "FAVOURS_EARLIER" if interval[1] < 0
                   else "INCONCLUSIVE")
        costs = cost_logs(rows, EARLIER, A4, 0.1, 0.1, fam)
        self.expect(name, ("primary",), {
            "endpoint": _SKIP, "programs": len(result["per_program"]), "estimate": point,
            "interval_95": interval, "verdict": verdict,
            "wins_ties_losses_for_A4": result["wtl"], "missing_pairs": result["missing"],
            "failed_pairs": result["failed"],
            "family_breakdown": family_breakdown(result["per_program"], fam),
            "per_program_losses_for_A4": {p: v for p, v in result["per_program"].items()
                                          if v < -TIE},
            "compile_ratio_A4_over_earlier_geometric": (
                math.exp(family_mean(costs, fam)) if costs else None)}, "PRIMARY")
        if candidate not in (EARLIER, A4):
            endpoints = {}
            routes = {"quality_route": True, "efficiency_route": True}
            for ref in (EARLIER, A4):
                q = paired(rows, ref, candidate, 0.1, 0.1, 5)
                qp, qi = bootstrap({k: -v for k, v in q["per_program"].items()}, fam, CANDIDATE)
                c = cost_logs(rows, ref, candidate, 0.1, 0.1, fam)
                cp, ci = bootstrap(c, fam, CANDIDATE)
                endpoints[ref] = {
                    "J_ratio": math.exp(qp), "J_ratio_interval_98_75": [math.exp(x) for x in qi],
                    "compile_ratio": math.exp(cp),
                    "compile_ratio_interval_98_75": [math.exp(x) for x in ci],
                    "programs_quality": len(q["per_program"]), "programs_cost": len(c),
                    "wins_ties_losses": q["wtl"]}
                ju, cu = math.exp(qi[1]), math.exp(ci[1])
                routes["quality_route"] &= (ju <= ROUTES["quality_route"]["upper_J_ratio"]
                                            and cu <= ROUTES["quality_route"]["upper_compile_ratio"])
                routes["efficiency_route"] &= (
                    cu <= ROUTES["efficiency_route"]["upper_compile_ratio"]
                    and ju <= ROUTES["efficiency_route"]["upper_J_ratio"])
            endpoints["routes_passed"] = routes
            endpoints["verdict"] = ("QUALITY_ROUTE" if routes["quality_route"] else
                                    "EFFICIENCY_ROUTE" if routes["efficiency_route"]
                                    else "TARGET_NOT_REACHED")
            self.expect(name, ("candidate_endpoints",), endpoints, "CANDIDATE_ENDPOINTS")
        descriptive = {}
        for budget in BUDGETS:
            for i, first in enumerate(arms):
                for second in arms[i + 1:]:
                    r = paired(rows, first, second, budget, budget, 5)
                    p, iv = bootstrap(r["per_program"], fam, PRIMARY)
                    descriptive[f"log(J_{first}/J_{second})@{budget}"] = {
                        "estimate": p, "interval_95": iv, "wins_ties_losses_for_second": r["wtl"]}
            for control in ("classical", "accepted_bootstrap"):
                for arm in arms:
                    r = paired(rows, control, arm, None, budget, 5)
                    p, iv = bootstrap(r["per_program"], fam, PRIMARY)
                    descriptive[f"log(J_{control}/J_{arm}@{budget})"] = {
                        "estimate": p, "interval_95": iv, "wins_ties_losses_for_arm": r["wtl"]}
        self.expect(name, ("descriptive_unadjusted_95",), descriptive, "C_DESCRIPTIVE")
        costs_out = {f"{a}@{b}": self.arm_summary(rows, a, b, 5, fam)["costs_geometric_median"]
                     for a in arms for b in BUDGETS}
        costs_out.update({f"{c}@None": self.arm_summary(rows, c, None, 5, fam)[
            "costs_geometric_median"] for c in ("classical", "accepted_bootstrap")})
        self.expect(name, ("costs",), costs_out, "C_COSTS")
        self.expect(name, ("quality",), {f"{a}@{b}": self.arm_summary(rows, a, b, 5, fam)[
            "family_mean_log_J"] for a in arms for b in BUDGETS}, "C_QUALITY")
        self.expect(name, ("targets",), self.targets(rows, arms), "C_TARGETS")
        self.expect(name, ("interruption_accounting",),
                    {a: self.interruption_sums(rows, a, with_successor=True) for a in arms},
                    "C_INTERRUPTIONS")
        boots = {r["program_sha256"]: r["product"] for r in rows
                 if r["arm"] == "accepted_bootstrap" and not r["failed_row"]}
        pairs = {(r["program_sha256"], (r.get("result") or {})["bootstrap_product"])
                 for r in rows if "bootstrap_product" in (r.get("result") or {})}
        self.expect(name, ("bootstrap_consistency",), {
            "programs": len(boots), "note": _SKIP,
            "successor_bootstrap_equals_accepted_bootstrap": all(boots.get(p) == j
                                                                 for p, j in pairs)},
            "C_BOOTSTRAP_CONSISTENCY")

    def public(self, rows, arms, order):
        name = "PUBLIC_SCORE.json"
        keys = json.loads((self.run / "frozen_expected/C_public.json").read_text())["keys"]
        self.expect(name, ("completeness",), self.completeness(rows, keys), "PUBLIC_COMPLETE")
        serial = {}
        for r in rows:
            if r["arm"] == "serial":
                self.ok(serial.setdefault(r["program_sha256"], (r["cycles"], r["scratch"]))
                        == (r["cycles"], r["scratch"]), "SERIAL_STABLE", r["key"])
        self.ok(sorted(serial) == sorted(order), "PUBLIC_DENOMINATOR", len(serial))
        idx = index_rows(rows)
        names = {r["program_sha256"]: (r.get("result") or {}).get("program_name") for r in rows}
        combos = sorted({(r["arm"], r["budget_seconds"]) for r in rows if r["arm"] != "serial"},
                        key=lambda x: (x[0], -1 if x[1] is None else x[1]))
        out = {}
        for arm, budget in combos:
            scores, reconciled, per = [], [], collections.defaultdict(list)
            for rep in range(5):
                chosen = [idx.get((p, arm, budget, rep)) for p in sorted(serial)]
                if any(c is None or c["failed_row"] for c in chosen):
                    scores.append(None)
                    reconciled.append(None)
                    continue
                self.ok(len(chosen) == 8, "PUBLIC_DENOMINATOR", f"{arm}@{budget}#{rep}")
                speed = math.exp(mean(math.log(serial[c["program_sha256"]][0] / c["cycles"])
                                      for c in chosen))
                space = math.exp(mean(math.log(serial[c["program_sha256"]][1] / c["scratch"])
                                      for c in chosen))
                scores.append(math.sqrt(speed * space))
                reconciled.append(math.exp(mean(math.log(
                    serial[c["program_sha256"]][0] * serial[c["program_sha256"]][1]
                    / c["product"]) for c in chosen) / 2))
                for c in chosen:
                    per[names.get(c["program_sha256"]) or c["program_sha256"]].append(
                        [c["cycles"], c["scratch"], c["product"]])
            valid = [s for s in scores if s is not None]
            out[f"{arm}@{budget}"] = {
                "arm": arm, "budget_seconds": budget, "scores": scores,
                "reconciled_exp_half_mean_log": reconciled,
                "max_reconciliation_gap": max((abs(a - b) for a, b in zip(scores, reconciled)
                                               if a is not None), default=None),
                "min": min(valid) if valid else None, "max": max(valid) if valid else None,
                "complete": len(valid) == 5,
                "per_program_CSJ_by_repetition": dict(sorted(per.items()))}
        self.expect(name, ("scores",), {"serial": {names.get(k) or k: list(v)
                                                   for k, v in serial.items()},
                                        "arms": out}, "PUBLIC_SCORE", tol=1e-12)
        ratios = {}
        for arm in arms:
            for other in arms:
                if arm != other:
                    x, y = out[f"{arm}@0.1"]["scores"], out[f"{other}@0.1"]["scores"]
                    ratios[f"{arm}/{other}@0.1"] = [None if u is None or v is None else u / v
                                                   for u, v in zip(x, y)]
        self.expect(name, ("paired_score_ratios_at_0.1",), ratios, "PUBLIC_RATIOS")
        self.public_scores = out

    def export(self, rows, public_rows, order, programs, candidate):
        name = "export/candidate/EXPORT_VALIDATION.json"
        directory = self.run / "export" / "candidate"
        if not self.ok((directory / "rows.jsonl").exists(), "MISSING_REQUIRED", "export rows"):
            return
        export_rows = self.strict_rows(directory / "rows.jsonl", "export")
        expected = [f"{p}|export_candidate|0.1|{rep}" for p in list(order) + list(programs)
                    for rep in range(3)]
        counts = collections.Counter(r.get("key") for r in export_rows)
        self.ok(set(counts) == set(expected) and len(expected) == 624, "EXPORT_MEMBERSHIP",
                f"missing {len(set(expected) - set(counts))} unexpected "
                f"{len(set(counts) - set(expected))}")
        self.ok(all(n == 1 for n in counts.values()), "EXPORT_DUPLICATES")
        for r in export_rows:
            self.ok(r.get("correctness") == "PASS" and r.get("exit_code") == 0
                    and not r.get("failed_row") and not r.get("timed_out"), "EXPORT_ROW", r["key"])
            self.ok(r["product"] == r["cycles"] * r["scratch"], "EXPORT_PRODUCT", r["key"])
        manifest = self.report("export/candidate/compiler_MANIFEST.json")
        compiler_sha = file_sha(directory / "compiler.py")
        self.expect("export/candidate/compiler_MANIFEST.json", ("export_sha256",), compiler_sha,
                    "EXPORT_HASH")
        self.expect(name, ("build", "sha256"), compiler_sha, "EXPORT_HASH")
        self.expect("export/candidate/compiler_MANIFEST.json", ("arm",), candidate, "EXPORT_ARM")
        self.expect(name, ("arm",), candidate, "EXPORT_ARM")
        self.expect("export/candidate/compiler_MANIFEST.json", ("catalog",), "a4", "EXPORT_CELL")
        self.expect("export/candidate/compiler_MANIFEST.json", ("traversal",), "dfs",
                    "EXPORT_CELL")
        self.expect("export/candidate/compiler_MANIFEST.json", ("variant",), None, "EXPORT_CELL")
        self.expect("export/candidate/compiler_MANIFEST.json", ("optimisation_seconds",), 0.1,
                    "EXPORT_CELL")
        self.expect("export/candidate/compiler_MANIFEST.json", ("audit_problems",), [],
                    "EXPORT_AUDIT")
        self.expect(name, ("audit_problems",), [], "EXPORT_AUDIT")
        self.expect(name, ("expected_rows",), 624, "EXPORT_MEMBERSHIP")
        self.expect(name, ("failed_rows",), sum(1 for r in export_rows if r.get("failed_row")),
                    "EXPORT_FAILED")
        self.expect(name, ("rows",), len(export_rows), "EXPORT_MEMBERSHIP")
        times = sorted(r["process_seconds"] for r in export_rows if not r.get("failed_row"))
        self.expect(name, ("process_seconds",), {
            "median": times[len(times) // 2], "p95": times[int(0.95 * (len(times) - 1))],
            "max": times[-1]}, "EXPORT_PROCESS_SECONDS")
        clean = (len(export_rows) == 624 and not any(r.get("failed_row") for r in export_rows)
                 and set(counts) == set(expected))
        self.expect(name, ("status",), "PASS" if clean else "FAIL", "EXPORT_STATUS")
        for field in ("deterministic_regeneration",):
            self.expect(name, (field,), True, "EXPORT_REGENERATION")
        self.expect(name, ("build", "generator_matches_freeze"), True, "EXPORT_GENERATOR")
        self.expect(name, ("build", "component_file_mismatches_vs_freeze"), [], "EXPORT_GENERATOR")
        for field in ("pinned_tests_exit", "score_exit"):
            self.expect(name, ("pinned", field), 0, "EXPORT_PINNED")
        for field in ("compiler_is_export", "embedded_modules_only", "machine_is_pinned_copy"):
            self.expect(name, ("pinned", field), True, "EXPORT_PINNED")
        self.expect(name, ("pinned", "machine_sha256"),
                    file_sha(self.root / ".reference" / "machine.py"), "EXPORT_PINNED")
        if public_rows is not None:
            serial = {r["program_sha256"]: (r["cycles"], r["scratch"]) for r in public_rows
                      if r["arm"] == "serial"}
            by = {(r["program_sha256"], r["repetition"]): r for r in export_rows}
            scores = []
            for rep in range(3):
                chosen = [by.get((p, rep)) for p in sorted(serial)]
                if any(c is None for c in chosen):
                    scores.append(None)
                    continue
                speed = math.exp(mean(math.log(serial[c["program_sha256"]][0] / c["cycles"])
                                      for c in chosen))
                space = math.exp(mean(math.log(serial[c["program_sha256"]][1] / c["scratch"])
                                      for c in chosen))
                scores.append(math.sqrt(speed * space))
            self.expect(name, ("export_public_scores",), scores, "EXPORT_PUBLIC_SCORE",
                        tol=1e-12)
        if rows is not None:
            boots = {r["program_sha256"]: r["product"] for r in rows
                     if r["arm"] == "accepted_bootstrap"}
            research = collections.defaultdict(set)
            for r in rows:
                if r["arm"] == candidate and r["budget_seconds"] == 0.1:
                    research[r["program_sha256"]].add(r["product"])
            above = sorted(r["key"] for r in export_rows if r["program_sha256"] in boots
                           and r["product"] > boots[r["program_sha256"]])
            outside = sorted(r["key"] for r in export_rows if r["program_sha256"] in research
                             and r["product"] not in research[r["program_sha256"]])
            self.expect(name, ("outputs_above_bootstrap",), above, "EXPORT_ABOVE_BOOTSTRAP")
            self.expect(name, ("outputs_outside_research_J_set", "count"), len(outside),
                        "EXPORT_OUTSIDE_SET")
            shown = self.get(name, ("outputs_outside_research_J_set", "first"))
            self.expect(name, ("outputs_outside_research_J_set", "first"),
                        outside[:len(shown) if isinstance(shown, list) else 1],
                        "EXPORT_OUTSIDE_SET")

    # -- learning ----------------------------------------------------------------

    def learning(self):
        report_name = "LEARNING_FEASIBILITY.json"
        freeze = self.report("LEARNING_FREEZE.json")
        yields_by = {}
        for cohort, minimum, per_family in (("development", 10, 1), ("evaluation", 20, 3)):
            name = f"learning/DESIGN_{cohort.upper()}.json"
            data = self.report(name)
            if not data:
                continue
            manifest_path = self.root / data["manifest"]
            manifest = json.loads(manifest_path.read_text())
            fixtures = {f["fixture_id"]: f for f in manifest["fixtures"]}
            designs = []
            for i, design in enumerate(data["designs"]):
                fixture = fixtures[design["fixture_id"]]
                fdir = manifest_path.parent / fixture["fixture_id"]
                ddir = self.run / "learning" / "design" / cohort / fixture["fixture_id"]
                derived = self.fixture_design(fdir, fixture, ddir)
                self.expect(name, ("designs", i), {
                    "evaluator_sha256": file_sha(ddir / "EVALUATOR.json"),
                    "family": fixture["family"], "fixture_id": fixture["fixture_id"],
                    "program_sha256": fixture["program_sha256"], "seed": fixture["seed"],
                    "ranker_input": _SKIP, "ranker_input_sha256": file_sha(ddir / "RANKER_INPUT.json"),
                    "sensitivity": derived["sensitivity"]}, "DESIGN")
                designs.append({"fixture_id": fixture["fixture_id"], "family": fixture["family"],
                                "sensitivity": derived["sensitivity"]})
                yields_by[fixture["fixture_id"]] = derived
            informative = [d for d in designs if d["sensitivity"]["informative"]]
            fam_counts = collections.Counter(d["family"] for d in informative)
            gate = {"fixtures": len(designs), "informative": len(informative),
                    "informative_by_family": dict(sorted(fam_counts.items())),
                    "minimum": minimum, "per_family_minimum": per_family,
                    "status": "PASS" if (len(informative) >= minimum and all(
                        fam_counts.get(f, 0) >= per_family for f in FAMILIES))
                    else "DESIGN_INSUFFICIENT",
                    "uninformative": [{"fixture_id": d["fixture_id"], **{
                        k: d["sensitivity"][k] for k in ("N_pool", "M_useful", "range",
                                                         "constant_labels",
                                                         "no_useful_pool_objects",
                                                         "short_pool")}}
                                      for d in designs if not d["sensitivity"]["informative"]]}
            self.expect(name, ("gate",), gate, "DESIGN_GATE")
            self.expect(name, ("manifest_sha256",), file_sha(manifest_path), "DESIGN_MANIFEST")
            self.expect(name, ("orderings_evaluated_before_this_file",), False,
                        "DESIGN_BEFORE_OUTCOMES")
            self.expect(report_name, (f"{cohort}_design",), gate, "DESIGN_GATE")
            if cohort == "evaluation":
                self.expect(report_name, ("evaluation_sensitivity",),
                            {d["fixture_id"]: dict(d["sensitivity"], decode_mismatches=_SKIP)
                             for d in designs}, "SENSITIVITY")
                self.expect(report_name, ("evaluation_qualification",),
                            {k: manifest[k] for k in ("status", "filled", "collisions", "pool",
                                                      "quota_per_family")}, "QUALIFICATION")
                if freeze:
                    self.expect("LEARNING_FREEZE.json", ("fixtures",), [
                        {"evaluator_sha256": file_sha(self.run / "learning/design/evaluation"
                                                      / d["fixture_id"] / "EVALUATOR.json"),
                         "family": d["family"], "fixture_id": d["fixture_id"],
                         "program_sha256": fixtures[d["fixture_id"]]["program_sha256"],
                         "ranker_input_sha256": file_sha(self.run / "learning/design/evaluation"
                                                         / d["fixture_id"] / "RANKER_INPUT.json")}
                        for d in data["designs"]], "LEARNING_FREEZE")
                    self.expect("LEARNING_FREEZE.json", ("design_evaluation_sha256",),
                                file_sha(self.run / name), "LEARNING_FREEZE")
                    self.expect("LEARNING_FREEZE.json", ("design_development_sha256",),
                                file_sha(self.run / "learning/DESIGN_DEVELOPMENT.json"),
                                "LEARNING_FREEZE")
                    self.expect("LEARNING_FREEZE.json", ("fixture_manifest_sha256",),
                                file_sha(manifest_path), "LEARNING_FREEZE")
                    self.expect("LEARNING_FREEZE.json", ("orderings",), list(ORDERINGS),
                                "LEARNING_FREEZE")
                    self.expect("LEARNING_FREEZE.json", ("compiler_freeze_sha256",),
                                file_sha(self.run / "FROZEN_SELECTION.json"), "LEARNING_FREEZE")
                self.orderings(data, yields_by, report_name)
        self.economics(report_name)

    def fixture_design(self, fdir: Path, fixture: dict, ddir: Path) -> dict:
        record_sha = file_sha(fdir / "record.json")
        self.ok(record_sha == fixture["record_sha256"], "FIXTURE_RECORD_HASH", fixture["fixture_id"])
        self.ok(file_sha(fdir / "oracle.json") == fixture["oracle_sha256"], "FIXTURE_ORACLE_HASH",
                fixture["fixture_id"])
        oracle = json.loads((fdir / "oracle.json").read_text())
        ranker = json.loads((ddir / "RANKER_INPUT.json").read_text())
        feasible = oracle["feasible"]
        product = {i["identity"]: i["product"] for i in feasible}
        by_index = {int(i["structural_rank_index"]): i for i in feasible}
        code = {i["identity"]: int(i["structural_rank_index"]) for i in feasible}
        drawn = random.Random(stable([TRAINING_SEED, fixture["record_sha256"]])).sample(
            sorted(product), TRAINING)
        training = sorted((code[d], product[d]) for d in drawn)
        indices = [i for i, _ in training]
        products = [p for _, p in training]
        fid = fixture["fixture_id"]
        # Seeded training draw and code-to-J alignment, pair by pair.
        self.ok([int(i) for i in ranker["training_indices"]] == indices, "TRAINING_CODES", fid)
        self.ok(ranker["training_products"] == products, "TRAINING_J_ALIGNMENT", fid)
        for code, j in zip(ranker["training_indices"], ranker["training_products"]):
            item = by_index.get(int(code))
            self.ok(item is not None and item["product"] == j, "TRAINING_J_ALIGNMENT",
                    f"{fid}:{code}")
        self.ok(ranker["domain_sha256"] == oracle["domain_sha256"], "DOMAIN_DIGEST", fid)
        threshold = elite_threshold(products)
        labels = [1 if p <= threshold else 0 for p in products]
        elite = sorted({i for i, y in zip(indices, labels) if y})
        pool = common_pool(ranker["bits"], indices, elite,
                           stable([POOL_SEED, oracle["domain_sha256"]]))
        self.ok([int(i) for i in ranker["pool"]] == pool["pool"], "POOL_MEMBERSHIP", fid)
        self.ok(ranker["pool_sha256"] == pool["pool_sha256"], "POOL_HASH", fid)
        evaluator = json.loads((ddir / "EVALUATOR.json").read_text())
        self.ok(evaluator["pool"] == {k: pool[k] for k in ("hamming", "random", "draws",
                                                           "universe_exhausted", "size",
                                                           "pool_sha256")}, "POOL_STATS", fid)
        self.ok(evaluator["elite_threshold"] == threshold, "ELITE_THRESHOLD", fid)
        training_set = set(drawn)
        useful = {by_index[i]["identity"] for i in pool["pool"] if i in by_index
                  and by_index[i]["identity"] not in training_set
                  and by_index[i]["product"] <= threshold}
        heldout_products = [p for ident, p in product.items() if ident not in training_set]
        n, m = len(pool["pool"]), len(useful)
        k = min(PREFIX, n)
        sensitivity = {
            "N_pool": n, "M_useful": m, "k": k, "max_count": min(k, m),
            "min_count": max(0, k - (n - m)), "range": min(k, m) - max(0, k - (n - m)),
            "informative": min(k, m) - max(0, k - (n - m)) > 0,
            "constant_labels": len(set(labels)) == 1, "no_useful_pool_objects": m == 0,
            "short_pool": n < PREFIX, "training_positives": sum(labels),
            "heldout_below_training_minimum": sum(p < min(products) for p in heldout_products),
            "pool_feasible_heldout": sum(1 for i in pool["pool"] if i in by_index
                                         and by_index[i]["identity"] not in training_set),
            "pool_not_feasible": sum(1 for i in pool["pool"] if i not in by_index),
            "decode_mismatches": _SKIP}
        return {"sensitivity": sensitivity, "pool": pool["pool"], "indices": indices,
                "products": products, "labels": labels, "elite": elite, "threshold": threshold,
                "useful": useful, "by_index": by_index, "training_set": training_set,
                "min_train": min(products), "domain": oracle["domain_sha256"],
                "bits": ranker["bits"],
                "min_heldout": min(heldout_products) if heldout_products else None}

    def orderings(self, evaluation, derived_by, report_name):
        rows = self.stage("L_orderings", [d["program_sha256"] for d in evaluation["designs"]],
                          cells(list(ORDERINGS), []), 1)
        if rows is None:
            return
        families = {d["fixture_id"]: d["family"] for d in evaluation["designs"]}
        yields = collections.defaultdict(dict)
        secondary = collections.defaultdict(dict)
        leaks, constant = [], []
        for r in rows:
            res = r["result"]
            fid, ordering = res["fixture_id"], res["ordering"]
            d = derived_by[fid]
            ordered = [int(i) for i in res["ordered"]]
            self.ok(sorted(ordered) == d["pool"] and len(set(ordered)) == len(ordered),
                    "ORDERING_PERMUTATION", r["key"])
            self.ok(res["ordering_sha256"] == hashlib.sha256(json.dumps(
                ordered, separators=(",", ":")).encode()).hexdigest(), "ORDERING_DIGEST", r["key"])
            expected = self.expected_ordering(ordering, d)
            self.ok(expected is None or expected == ordered, "ORDERING_DEFINITION",
                    f"{r['key']}")
            if ordering == "tree":
                leaves = fit_tree(d["bits"], d["indices"], d["labels"])
                if len({Fraction(p + 1, c + 2) for _, c, p, _ in leaves}) <= 1:
                    constant.append(fid)     # row order, as the release lists them
            if res.get("loaded_modules_with_oracle_access"):
                leaks.append(r["key"])
            prefix = ordered[:PREFIX]
            useful = {d["by_index"][i]["identity"] for i in prefix if i in d["by_index"]
                      and d["by_index"][i]["identity"] in d["useful"]}
            heldout = [d["by_index"][i]["product"] for i in prefix if i in d["by_index"]
                       and d["by_index"][i]["identity"] not in d["training_set"]]
            yields[fid][ordering] = len(useful) / PREFIX
            best = min(heldout) if heldout else None
            secondary[fid][ordering] = best / d["min_train"] if best is not None else None
            secondary[fid]["saturated"] = (d["min_heldout"] is None
                                           or d["min_heldout"] >= d["min_train"])
        complete = {f: s for f, s in yields.items() if len(s) == len(ORDERINGS)}
        keys = json.loads((self.run / "stages/L_orderings/EXPECTED_KEYS.json").read_text())["keys"]
        self.expect(report_name, ("orderings",), {
            "completeness": self.completeness(rows, keys), "fixtures_scored": len(complete),
            "oracle_leaks_in_ranker_processes": leaks,
            "mean_yield_by_ordering": {o: mean(s[o] for s in complete.values())
                                       for o in ORDERINGS},
            "per_fixture_yield": complete,
            "secondary_best_J_over_training_minimum": dict(secondary),
            "saturated_fixtures": sum(1 for v in secondary.values() if v.get("saturated")),
            "constant_trees": constant}, "ORDERINGS")
        randoms = [o for o in ORDERINGS if o.startswith("random_")]
        out, passed = {}, True
        for name, control in (("tree_minus_hamming", lambda s: s["hamming"]),
                              ("tree_minus_random_mean", lambda s: mean(s[o] for o in randoms)),
                              ("tree_minus_shuffled_tree", lambda s: s["shuffled_tree"])):
            per = {f: s["tree"] - control(s) for f, s in complete.items()}
            point, (low, high) = bootstrap(per, families, LEARNING)
            ok = low > 0 and point >= MIN_YIELD_GAIN
            passed &= ok
            out[name] = {"estimate": point, "interval_98_333": [low, high], "fixtures": len(per),
                         "positive": sum(v > 0 for v in per.values()),
                         "zero": sum(v == 0 for v in per.values()),
                         "negative": sum(v < 0 for v in per.values()), "passes": ok}
        out["mechanism_signal"] = "PASS" if passed else "FAIL_OR_INCONCLUSIVE"
        self.expect(report_name, ("contrasts",), out, "LEARNING_CONTRASTS")

    @staticmethod
    def expected_ordering(ordering, d):
        pool = list(d["pool"])
        if ordering == "ascending":
            return sorted(pool)
        if ordering == "hamming":
            anchors = sorted(set(d["elite"]))
            return sorted(pool, key=lambda i: (min(((i ^ e).bit_count() for e in anchors),
                                                   default=0), i))
        if ordering.startswith("random_"):
            tag = int(ordering.split("_", 1)[1])
            shuffled = list(pool)
            random.Random(stable([tag, d["domain"]])).shuffle(shuffled)
            return shuffled
        labels = list(d["labels"])
        if ordering == "shuffled_tree":
            random.Random(stable([SHUFFLED_SEED, d["domain"]])).shuffle(labels)
        return tree_order(pool, fit_tree(d["bits"], d["indices"], labels))

    def economics(self, report_name):
        design = self.report("learning/DESIGN_DEVELOPMENT.json")
        if not design:
            return
        programs, _ = self.programs("development", 800000, 800099)
        rows = self.stage("L_acquisition", programs, cells([], ["acquisition_tree"], [0.1]), 1)
        if rows is None:
            return
        ok = [r for r in rows if not r["failed_row"]]
        reaching = [r for r in ok if r["result"]["queries_reaching_20_validated"] > 0]
        costs = collections.Counter()
        for r in ok:
            for k, v in r["result"]["cost_totals_seconds"].items():
                costs[k] += v
        boundary = [q for r in ok for q in r["result"]["queries"] if q["reached_boundary"]]
        fraction = len(reaching) / len(rows)
        keys = json.loads((self.run / "stages/L_acquisition/EXPECTED_KEYS.json")
                          .read_text())["keys"]
        self.expect(report_name, ("economics",), {
            "completeness": self.completeness(rows, keys), "programs": len(rows),
            "programs_with_a_query_reaching_20_validated": len(reaching), "fraction": fraction,
            "threshold": ECON_THRESHOLD,
            "verdict": ("ECONOMICALLY_UNAVAILABLE" if fraction < ECON_THRESHOLD else "AVAILABLE"),
            "queries_with_learner": sum(r["result"]["queries_with_learner"] for r in ok),
            "queries_reaching_boundary": len(boundary),
            "queries_observing_20_at_boundary": sum(
                r["result"]["queries_observing_20_at_boundary"] for r in ok),
            "boundary_observed_distinct_quantiles": quantiles_index(
                [q["observed_distinct_at_boundary"] or 0 for q in boundary]),
            "boundary_query_remaining_seconds_quantiles": quantiles_index(
                [q["query_remaining_seconds"] for q in boundary]),
            "boundary_global_remaining_seconds_quantiles": quantiles_index(
                [q["global_remaining_seconds"] for q in boundary]),
            "cost_totals_seconds": dict(costs),
            "model_improvements": sum(r["result"]["model_improvements"] for r in ok),
            "note": _SKIP}, "ECONOMICS")

    # -- constants, coverage, run -----------------------------------------------------

    def check_constants(self):
        protocol = json.loads((self.root / "plan/phase2_next_round/PROTOCOL.json").read_text())
        s = protocol["statistics"]
        self.ok(s["resamples"] == RESAMPLES, "CONSTANT_RESAMPLES")
        self.ok(tuple(s["primary_head_to_head_percentiles"]) == PRIMARY, "CONSTANT_PERCENTILES")
        self.ok(tuple(s["new_candidate_four_endpoints_percentiles"]) == CANDIDATE,
                "CONSTANT_PERCENTILES")
        self.ok(tuple(s["learning_three_contrasts_percentiles"]) == LEARNING,
                "CONSTANT_PERCENTILES")
        seeds = protocol["seeds"]
        self.ok((seeds["arm_order"], seeds["bootstrap"], seeds["training_draw"], seeds["pool"],
                 seeds["shuffled_labels"], tuple(seeds["random_order"]))
                == (ORDER_SEED, BOOT_SEED, TRAINING_SEED, POOL_SEED, SHUFFLED_SEED,
                    RANDOM_SEEDS), "CONSTANT_SEEDS")
        targets = dict(protocol["practical_targets"])
        self.ok(targets.pop("must_hold_against_both_references", None) is True
                and targets == ROUTES, "CONSTANT_ROUTES", protocol["practical_targets"])
        learning = protocol["learning"]
        self.ok((learning["training_count"], learning["primary_prefix"],
                 learning["minimum_yield_difference"],
                 learning["minimum_acquisition_program_fraction"])
                == (TRAINING, PREFIX, MIN_YIELD_GAIN, ECON_THRESHOLD), "CONSTANT_LEARNING")
        for name in REQUIRED_REPORTS:
            value = self.report(name)
            if isinstance(value, dict) and "protocol_id" in value:
                self.expect(name, ("protocol_id",), protocol["protocol_id"], "PROTOCOL_ID")

    def field_map(self):
        """Generalised leaf path -> the check that compares it, or the declared reason."""

        import re
        out = {}
        for name, value in self.reports.items():
            if value is None:
                continue
            leaves = []
            _leaves(value, (), leaves)
            entries = {}
            for path in leaves:
                label = f"{name}::{'.'.join(str(p) for p in path)}"
                code = self.checked.get(label)
                reason = next((r for pattern, r in DECLARED_UNCHECKED.items()
                               if fnmatch.fnmatchcase(label, pattern)), None)
                general = re.sub(r"[0-9a-f]{64}", "<sha256>",
                                 re.sub(r"(^|\.)\d+(?=\.|$)", r"\1<i>",
                                        ".".join(str(p) for p in path)))
                kind = (f"check:{code}" if code and code != "SKIP" else
                        f"declared:{reason or 'placeholder in an expected object'}"
                        if (reason or code == "SKIP") else "UNMAPPED")
                slot = entries.setdefault(general, {})
                slot[kind] = slot.get(kind, 0) + 1
            out[name] = entries
        return out

    def coverage(self):
        table, unmapped = {}, []
        for name, value in self.reports.items():
            if value is None:
                continue
            leaves = []
            _leaves(value, (), leaves)
            counts = collections.Counter()
            for path in leaves:
                label = f"{name}::{'.'.join(str(p) for p in path)}"
                if label in self.checked and self.checked[label] != "SKIP":
                    counts["checked"] += 1
                    continue
                reason = next((r for pattern, r in DECLARED_UNCHECKED.items()
                               if fnmatch.fnmatchcase(label, pattern)), None)
                if reason is not None:
                    counts["declared_unchecked"] += 1
                    continue
                if label in self.checked:
                    counts["declared_unchecked"] += 1
                    continue
                counts["unmapped"] += 1
                unmapped.append(label)
            table[name] = dict(counts, leaves=len(leaves))
        for label in unmapped[:200]:
            self.ok(False, "UNMAPPED_FIELD", label)
        if len(unmapped) > 200:
            self.ok(False, "UNMAPPED_FIELD", f"... and {len(unmapped) - 200} more")
        return table, unmapped

    def run_all(self):
        self.check_constants()
        dev_programs, _ = self.programs("development", 800000, 800099)
        self._dev_order = dev_programs
        chosen = self.development()
        self.confirmation(chosen)
        self.learning()
        for stage in REQUIRED_STAGES:
            self.ok(stage in self.stage_rows, "MISSING_REQUIRED", f"stage {stage} not audited")
        coverage, unmapped = self.coverage()
        codes = collections.Counter(f["code"] for f in self.findings)
        declared = sorted({f"{pattern}: {reason}" for pattern, reason in
                           DECLARED_UNCHECKED.items()})
        return {"status": "PASS" if self.checks and not self.findings else "FAIL",
                "checks": self.checks, "finding_codes": dict(codes),
                "findings": self.findings[:200], "coverage": coverage,
                "unmapped_fields": len(unmapped),
                "declared_unchecked": declared,
                "complete_coverage_claimed": False,
                "imports": "standard library only"}


class _Missing:
    def __repr__(self):
        return "<missing>"


_MISSING = _Missing()


class _Skip:
    """An expected-object placeholder: the leaf is declared, not compared."""


_SKIP = _Skip()


def _leaves(value, path, out):
    if isinstance(value, dict):
        if not value:
            out.append(path)
        for k, v in value.items():
            _leaves(v, path + (k,), out)
    elif isinstance(value, list):
        if not value:
            out.append(path)
        for i, v in enumerate(value):
            _leaves(v, path + (i,), out)
    else:
        out.append(path)


# ``_SKIP`` leaves inside expected objects are recorded as declared, not checked.
_original_compare = Audit._compare


def _compare_with_skip(self, name, path, actual, expected, code, tol):
    if isinstance(expected, _Skip):
        label = f"{name}::{'.'.join(str(p) for p in path)}"
        leaves = []
        _leaves(actual, (), leaves)
        for sub in leaves or [()]:
            full = label + ("." + ".".join(str(p) for p in sub) if sub else "")
            self.checked.setdefault(full, "SKIP")
        return
    _original_compare(self, name, path, actual, expected, code, tol)


Audit._compare = _compare_with_skip


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", required=True, help="a NEW directory")
    args = parser.parse_args(argv)
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to write into occupied {out}")
    out.mkdir(parents=True, exist_ok=True)
    audit = Audit(Path(args.run))
    report = audit.run_all()
    (out / "SUCCESSOR_AUDIT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (out / "AUDIT_COVERAGE.json").write_text(json.dumps(
        {"source_run": str(audit.run), "coverage_by_report": report["coverage"],
         "declared_unchecked_patterns": DECLARED_UNCHECKED,
         "field_to_check_map": audit.field_map(),
         "raw_evidence_checks": sorted({f"{c}" for c in audit.raw_codes}),
         "complete_coverage_claimed": False}, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "checks", "finding_codes",
                                             "unmapped_fields")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
