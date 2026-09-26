"""Independent raw-row numerical auditor for the objective-index protocol 1.0.

Standard library only. It imports NOTHING from ``research`` -- not the runner,
not the analysis, not the report, not the bootstrap owner -- and re-derives from
raw rows, the frozen ledgers and the locked package text:

- every stage's expected keys, re-implementing the written cell-order rule
  (sha256 of compact sorted-key JSON of [2026092505, program digest,
  repetition, arm, budget], first 16 hex digits, lexicographic tie-break);
- row integrity (membership, duplicates, J = C*S, family = FAMILIES[seed % 5]);
- the development selection (arm, every effect, the tie-break);
- the primary fresh-cohort contrasts, their Bonferroni intervals and the claim;
- H_LEARN's three contrasts, intervals and verdict;
- the exact public scores and paired ratios; the conditional learned pair if run.

Any recomputed number differing from the release's artifact by more than 1e-9
is a finding.

Usage::

    python research/objective_index_audit.py --run DIR [--output PATH]
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
from pathlib import Path

TOL = 1e-9
TIE = 1e-12
ORDER_SEED = 2026092505
BOOT_SEED = 2026092504
RESAMPLES = 10000
BONFERRONI = (1 / 120, 119 / 120)
CONDITIONAL = (0.0125, 0.9875)
BUDGETS = (0.01, 0.1, 1.0)
FAMILIES = ("scalar", "vector", "mixed", "dependency", "aliasing")
ARMS = ("A0_frozen_phase2", "A1_deadline_control", "A2_product_search",
        "A3_propagated_search", "A4_multiscale_search")
RANDOM = tuple(f"random_{t}" for t in range(2026092510, 2026092520))
RANKER = ("tree", "ascending", "hamming", "shuffled_tree", "empirical_cover") + RANDOM


def _cells(unbudgeted, budgeted, budgets=BUDGETS):
    return {(a, None) for a in unbudgeted} | {(a, b) for a in budgeted for b in budgets}


# Stage specifications transcribed from the protocol text (sections 3, 8, 9).
STAGE_SPECS = {
    "DEV_compiler": (_cells(["classical"], list(ARMS) + ["accepted_budgeted"]), 3),
    "DEV_model": (_cells([], RANKER), 3),
    "EVAL_model_wall": (_cells([], RANKER), 15),
    "EVAL_model_work": (_cells([], RANKER, ["fixed_work"]), 1),
    "EVAL_compiler": (_cells(["accepted_bootstrap", "accepted_default", "classical"],
                             ["accepted_budgeted"] + list(ARMS)), 15),
    "EVAL_public": (_cells(["accepted_bootstrap", "accepted_default", "classical"],
                           ["accepted_budgeted"] + list(ARMS)), 15),
    "EVAL_public_serial": (_cells(["serial"], []), 15),
    "EVAL_learned_tree": (_cells([], ["learned_tree"]), 15),
    "EVAL_learned_shuffled_tree": (_cells([], ["learned_shuffled_tree"]), 15),
}
PROGRAM_COUNTS = {"DEV_compiler": 100, "DEV_model": 15, "EVAL_model_wall": 30,
                  "EVAL_model_work": 30, "EVAL_compiler": 200, "EVAL_public": 8,
                  "EVAL_public_serial": 8, "EVAL_learned_tree": 208,
                  "EVAL_learned_shuffled_tree": 208}
SERIAL_RUNS = (Path(__file__).resolve().parents[1] / "results" / "phase2_structural_encoding" /
               "claude_release_20260923" / "production" / "production_comparison" / "runs.json")


def load(path):
    return json.loads(Path(path).read_text())


def rows_of(path):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    lines = p.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                if i != len(lines) - 1:
                    raise
    return out


def stable(parts):
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def fam_mean(per, fam):
    g = collections.defaultdict(list)
    for k, v in per.items():
        g[fam[k]].append(v)
    return mean(mean(v) for _, v in sorted(g.items()))


def pct(values, q):
    pos = (len(values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return values[lo]
    return values[lo] * (1 - (pos - lo)) + values[hi] * (pos - lo)


def boot(per, fam, qs):
    g = collections.defaultdict(list)
    for k, v in sorted(per.items()):
        g[fam[k]].append(v)
    rng = random.Random(BOOT_SEED)
    draws = []
    for _ in range(RESAMPLES):
        fm = []
        for f in sorted(g):
            vals = g[f]
            fm.append(mean(vals[rng.randrange(len(vals))] for _ in range(len(vals))))
        draws.append(mean(fm))
    draws.sort()
    return [pct(draws, q) for q in qs]


def ident(row):
    return row.get("fixture_id") or row["program_sha256"]


class Audit:
    def __init__(self, run):
        self.run = Path(run)
        self.findings = []
        self.checks = collections.Counter()

    def check(self, label, ok, detail=""):
        self.checks[label] += 1
        if not ok:
            self.findings.append({"check": label, "detail": str(detail)[:500]})

    def close(self, label, a, b):
        ok = (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= TOL)
        self.check(label, ok, f"recomputed {a!r} vs reported {b!r}")

    # -- ledgers ---------------------------------------------------------------

    def schedule(self, programs, cells, reps):
        keys = []
        for p in programs:
            pid = p.get("fixture_id") or p["program_sha256"]
            for r in range(reps):
                ordered = sorted(((stable([ORDER_SEED, pid, r, arm, budget]), arm,
                                   "" if budget is None else str(budget)), arm, budget)
                                 for arm, budget in cells)
                keys.extend(f"{pid}|{arm}|{budget}|{r}" for _, arm, budget in ordered)
        return keys

    def ledgers(self):
        fresh = load(self.run / "FRESH_COHORT.json") if (self.run / "FRESH_COHORT.json").exists() \
            else None
        if fresh:
            seeds = [p["seed"] for p in fresh["programs"]]
            self.check("fresh_seeds", sorted(seeds) == list(range(910000, 910200)), seeds[:3])
            self.check("fresh_families", all(p["family"] == FAMILIES[p["seed"] % 5]
                                             for p in fresh["programs"]))
        stages = {}
        for directory in sorted((self.run / "stages").iterdir()):
            manifest = load(directory / "STAGE_MANIFEST.json")["extra"]
            spec = STAGE_SPECS.get(directory.name)
            self.check(f"stage_known:{directory.name}", spec is not None)
            if spec is None:
                continue
            cells, reps = spec
            self.check(f"cells:{directory.name}",
                       {tuple(c) for c in manifest["cells"]} == cells and
                       manifest["repetitions"] == reps)
            self.check(f"program_count:{directory.name}",
                       len(manifest["programs"]) == PROGRAM_COUNTS[directory.name],
                       len(manifest["programs"]))
            keys = self.schedule(manifest["programs"], sorted(cells, key=str), reps)
            expected = load(directory / "EXPECTED_KEYS.json")["keys"]
            self.check(f"ledger:{directory.name}", keys == expected,
                       f"{len(keys)} recomputed vs {len(expected)}")
            frozen = self.run / "frozen_expected" / f"{directory.name}.json"
            if frozen.exists():
                self.check(f"frozen_ledger:{directory.name}", load(frozen)["keys"] == keys)
            if directory.name == "DEV_compiler":
                self.check("dev_seeds", sorted(p["seed"] for p in manifest["programs"]) ==
                           list(range(800000, 800100)))
            if directory.name == "EVAL_compiler" and fresh:
                self.check("eval_programs_are_fresh_cohort",
                           [p["program_sha256"] for p in manifest["programs"]] ==
                           [p["program_sha256"] for p in fresh["programs"]])
            rows = rows_of(directory / "rows.jsonl")
            counts = collections.Counter(r["key"] for r in rows)
            self.check(f"membership:{directory.name}", set(counts) == set(expected) and
                       all(n == 1 for n in counts.values()),
                       f"missing {len(set(expected) - set(counts))} extra "
                       f"{len(set(counts) - set(expected))}")
            for row in rows:
                if row.get("cycles") is not None and row.get("scratch") is not None:
                    self.check("J=C*S", row["product"] == row["cycles"] * row["scratch"], row["key"])
                if row.get("seed") is not None:
                    self.check("family", row["family"] == FAMILIES[row["seed"] % 5], row["key"])
            stages[directory.name] = rows
        return stages

    # -- quality ---------------------------------------------------------------

    def paired(self, rows, control, candidate, cb, kb, reps):
        index = {(ident(r), r["arm"], r["budget_seconds"], r["repetition"]): r for r in rows}
        fam = {ident(r): r["family"] for r in rows}
        per = {}
        for p in sorted(fam):
            logs = []
            for r in range(reps):
                a, b = index.get((p, control, cb, r)), index.get((p, candidate, kb, r))
                if a is None or b is None or a["failed_row"] or b["failed_row"]:
                    break
                logs.append(math.log(a["product"] / b["product"]))
            if len(logs) == reps:
                per[p] = mean(logs)
        return per, fam

    def compile_log_ratio(self, rows, control, candidate, budget):
        times = collections.defaultdict(list)
        fam = {}
        for r in rows:
            if r["failed_row"] or r["budget_seconds"] != budget:
                continue
            if r["arm"] in (control, candidate):
                times[(r["program_sha256"], r["arm"])].append(r["result"]["compile_seconds"])
                fam[r["program_sha256"]] = r["family"]
        per = {}
        for p in fam:
            a, b = times.get((p, control)), times.get((p, candidate))
            if a and b:
                per[p] = math.log(sorted(b)[len(b) // 2] if len(b) % 2 else
                                  (sorted(b)[len(b) // 2 - 1] + sorted(b)[len(b) // 2]) / 2) - \
                    math.log(sorted(a)[len(a) // 2] if len(a) % 2 else
                             (sorted(a)[len(a) // 2 - 1] + sorted(a)[len(a) // 2]) / 2)
        return fam_mean(per, fam)

    def development(self, rows):
        path = self.run / "DEVELOPMENT.json"
        if not path.exists():
            return
        dev = load(path)["selection"]
        effects = {"A0_frozen_phase2": 0.0}
        compile_ratio = {"A0_frozen_phase2": 0.0}
        for arm in ARMS[1:]:
            per, fam = self.paired(rows, "A0_frozen_phase2", arm, 0.1, 0.1, 3)
            self.check(f"dev_complete:{arm}", len(per) == 100, len(per))
            effects[arm] = fam_mean(per, fam)
            compile_ratio[arm] = self.compile_log_ratio(rows, "A0_frozen_phase2", arm, 0.1)
        reported = {e["arm"]: e.get("effect") for e in dev["table"]}
        for arm, value in effects.items():
            self.close(f"dev_effect:{arm}", value, reported.get(arm))
        best = max(effects.values())
        tied = [a for a in ARMS if effects[a] >= best - TIE]
        tied.sort(key=lambda a: (compile_ratio[a], ARMS.index(a)))
        self.check("dev_selected_arm", tied[0] == dev["selected_arm"],
                   f"recomputed {tied[0]} vs reported {dev['selected_arm']}")

    def comparison(self, rows):
        path = self.run / "COMPARISON.json"
        if not path.exists():
            return
        rep = load(path)
        selected = rep["selected_arm"]
        lows = []
        for control, budget in (("A0_frozen_phase2", 0.1), ("accepted_budgeted", 0.1),
                                ("classical", None)):
            reported = rep["primary"]["contrasts"][control]
            if control == selected:
                lows.append(0.0)
                continue
            per, fam = self.paired(rows, control, selected, budget, 0.1, 15)
            self.check(f"primary_complete:{control}", len(per) == 200, len(per))
            point = fam_mean(per, fam)
            low, high = boot(per, fam, BONFERRONI)
            self.close(f"primary_point:{control}", point, reported["point"])
            self.close(f"primary_low:{control}", low, reported["interval"][0])
            self.close(f"primary_high:{control}", high, reported["interval"][1])
            lows.append(low)
        self.check("primary_claim", rep["primary"]["claim_best_average_quality"] ==
                   all(low > 0 for low in lows), rep["primary"]["claim_best_average_quality"])

    def learning(self, rows):
        path = self.run / "LEARNING.json"
        if not path.exists():
            return
        rep = load(path)["H_LEARN"]
        index = {(r["fixture_id"], r["arm"], r["budget_seconds"], r["repetition"]): r
                 for r in rows}
        fam = {r["fixture_id"]: r["family"] for r in rows}
        lows = []
        for name, labels in (("hamming", ["hamming"]), ("random", list(RANDOM)),
                             ("shuffled_tree", ["shuffled_tree"])):
            per = {}
            for fx in sorted(fam):
                means = []
                for label in labels:
                    logs = []
                    for r in range(15):
                        a = index.get((fx, label, 0.1, r))
                        b = index.get((fx, "tree", 0.1, r))
                        if a is None or b is None or a["failed_row"] or b["failed_row"]:
                            break
                        logs.append(math.log(a["result"]["best_test_J"] /
                                             b["result"]["best_test_J"]))
                    if len(logs) != 15:
                        break
                    means.append(mean(logs))
                if len(means) == len(labels):
                    per[fx] = mean(means)
            self.check(f"learn_complete:{name}", len(per) == 30, len(per))
            point = fam_mean(per, fam)
            low, high = boot(per, fam, BONFERRONI)
            reported = rep["contrasts"][name]
            self.close(f"learn_point:{name}", point, reported["point"])
            self.close(f"learn_low:{name}", low, reported["interval"][0])
            self.close(f"learn_high:{name}", high, reported["interval"][1])
            lows.append(low)
        defects = sum((r.get("result") or {}).get("defect_count", 0) for r in rows)
        passed = all(low > 0 for low in lows) and defects == 0 and \
            not any(r["failed_row"] for r in rows)
        self.check("h_learn_verdict", (rep["verdict"] == "PASS") == passed, rep["verdict"])

    def public(self, rows):
        path = self.run / "PUBLIC_SCORE.json"
        if not path.exists():
            return
        rep = load(path)["score"]["scores"]
        frozen = {}
        for row in load(SERIAL_RUNS)["runs"]:
            if row.get("arm") == "serial":
                frozen[row["program"]] = (row["cycles"], row["scratch"])
        serial = {}
        for r in rows:
            if r["arm"] == "serial":
                name = r["result"]["program_name"]
                serial.setdefault(name, (r["cycles"], r["scratch"]))
                self.check("serial_stable", serial[name] == (r["cycles"], r["scratch"]) ==
                           frozen[name], name)
        self.check("serial_rows", sum(r["arm"] == "serial" for r in rows) == 120)
        index = {(r["result"]["program_name"], r["arm"], r["budget_seconds"], r["repetition"]): r
                 for r in rows if r.get("result")}
        names = sorted(serial)
        for key, arm in rep["arms"].items():
            name, budget = key.split("@")
            budget = None if budget == "None" else float(budget)
            recomputed = []
            for r in range(15):
                chosen = [index.get((n, name, budget, r)) for n in names]
                if any(c is None or c["failed_row"] for c in chosen):
                    recomputed.append(None)
                    continue
                sp = math.exp(sum(math.log(serial[n][0] / c["cycles"])
                                  for n, c in zip(names, chosen)) / len(names))
                sc = math.exp(sum(math.log(serial[n][1] / c["scratch"])
                                  for n, c in zip(names, chosen)) / len(names))
                recomputed.append(math.sqrt(sp * sc))
            for a, b in zip(recomputed, arm["scores"]):
                self.close(f"public_score:{key}", a, b)

    def learned(self, stages):
        path = self.run / "COMPARISON.json"
        if not path.exists() or "conditional_learned" not in load(path):
            return
        rep = load(path)
        fresh = {p["program_sha256"] for p in load(self.run / "FRESH_COHORT.json")["programs"]}
        rows = [r for s in ("EVAL_compiler", "EVAL_learned_tree", "EVAL_learned_shuffled_tree")
                for r in stages.get(s, []) if r["program_sha256"] in fresh]
        for name, control in (("tree_vs_selected", rep["selected_arm"]),
                              ("tree_vs_shuffled", "learned_shuffled_tree")):
            per, fam = self.paired(rows, control, "learned_tree", 0.1, 0.1, 15)
            low, high = boot(per, fam, CONDITIONAL)
            reported = rep["conditional_learned"][name]
            self.close(f"learned_point:{name}", fam_mean(per, fam), reported["point"])
            self.close(f"learned_low:{name}", low, reported["interval"][0])

    def run_all(self):
        stages = self.ledgers()
        self.development(stages.get("DEV_compiler", []))
        self.comparison(stages.get("EVAL_compiler", []))
        self.learning(stages.get("EVAL_model_wall", []))
        self.public(stages.get("EVAL_public", []) + stages.get("EVAL_public_serial", []))
        self.learned(stages)
        return {"auditor": "research/objective_index_audit.py",
                "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "imports_research": False, "run": str(self.run),
                "checks": dict(self.checks), "check_total": sum(self.checks.values()),
                "findings": self.findings[:300], "finding_count": len(self.findings),
                "status": "PASS" if not self.findings and sum(self.checks.values()) else "FAIL"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = Audit(Path(args.run).resolve()).run_all()
    out = Path(args.output) if args.output else Path(args.run) / "INDEPENDENT_AUDIT.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "findings": report["finding_count"],
                      "checks": report["check_total"]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
