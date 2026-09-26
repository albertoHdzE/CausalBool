"""Independent raw-row numerical auditor for optimization protocol 1.0.

Standard library only. It imports NOTHING from ``research`` -- not the runner,
not the analysis, not the report -- and re-derives from raw rows and the locked
package: expected key membership (re-implementing the arm-order schedule from
its written specification), row integrity, every development decision, the
primary comparison and its bootstrap interval, the descriptive contrasts, the
exact public scores and the H4_NEW gate. Each recomputed number is compared
with the artifact the release wrote; any disagreement above 1e-9 is a finding.

Usage::

    python research/optimization_audit.py --run DIR [--output PATH]
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
from pathlib import Path
import sys

TOL = 1e-9
TIE = 1e-12
ORDER_SEED = 2026092401
BOOT_SEED = 2026092403
RESAMPLES = 10000
BUDGETS = (0.01, 0.1, 1.0)
UNIFORM = tuple(range(2026092410, 2026092420))
# The frozen serial records of the accepted release, located from this file so
# that an audited copy of a run directory still reads the pinned denominator.
SERIAL_RUNS = (Path(__file__).resolve().parents[1] / "results" / "phase2_structural_encoding" /
               "claude_release_20260923" / "production" / "production_comparison" / "runs.json")


def load(path):
    return json.loads(Path(path).read_text())


def rows_of(path):
    out = []
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
        ok = (a is None and b is None) or (a is not None and b is not None and
                                           abs(a - b) <= TOL)
        self.check(label, ok, f"recomputed {a!r} vs reported {b!r}")


# -- the written arm-order specification, re-implemented -----------------------

def schedule_keys(entries, unbudgeted, budgeted, budgets, reps):
    rng = random.Random(ORDER_SEED)
    keys = []
    for e in entries:
        ident = e.get("fixture_id") or e["program_sha256"]
        for budget in [None] + sorted(budgets):
            arms = sorted(unbudgeted) if budget is None else sorted(budgeted)
            if not arms:
                continue
            for r in range(reps):
                order = list(arms)
                rng.shuffle(order)
                for arm in order:
                    keys.append(f"{ident}|{arm}|{budget}|{r}")
    return keys


# -- statistics, re-implemented from the protocol text --------------------------

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def fam_mean(per, fam):
    g = collections.defaultdict(list)
    for k, v in per.items():
        g[fam[k]].append(v)
    return mean(mean(v) for _, v in sorted(g.items()))


def pct(sorted_values, q):
    # Linear interpolation between closest ranks, the accepted owner's rule.
    if not sorted_values:
        return None
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


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


def paired(rows, a, b, ba, bb, reps):
    idx = {(ident(r), r["arm"], r["budget_seconds"], r["repetition"]): r for r in rows}
    per = {}
    for p in sorted({ident(r) for r in rows}):
        logs = []
        for k in range(reps):
            x, y = idx.get((p, a, ba, k)), idx.get((p, b, bb, k))
            if x is None or y is None or x["failed_row"] or y["failed_row"]:
                break
            logs.append(math.log(x["product"] / y["product"]))
        if len(logs) == reps:
            per[p] = mean(logs)
    return per


def families(rows):
    return {ident(r): r["family"] for r in rows}


# -- audits ---------------------------------------------------------------------

def audit_rows(a, stage, frozen_keys=None):
    d = a.run / "stages" / stage
    rows = rows_of(d / "rows.jsonl")
    expected = load(d / "EXPECTED_KEYS.json")["keys"] if (d / "EXPECTED_KEYS.json").exists() else []
    counts = collections.Counter(r["key"] for r in rows)
    a.check(f"{stage}:expected_nonempty", len(expected) > 0, len(expected))
    a.check(f"{stage}:no_missing", set(expected) <= set(counts),
            len(set(expected) - set(counts)))
    a.check(f"{stage}:no_duplicates", all(n == 1 for n in counts.values()),
            [k for k, n in counts.items() if n > 1][:3])
    a.check(f"{stage}:no_unexpected", set(counts) <= set(expected),
            len(set(counts) - set(expected)))
    if frozen_keys is not None:
        a.check(f"{stage}:ledger_equals_frozen", frozen_keys == expected,
                f"{len(frozen_keys)} vs {len(expected)}")
    for r in rows:
        key = f"{ident(r)}|{r['arm']}|{r['budget_seconds']}|{r['repetition']}"
        a.check(f"{stage}:key_fields", key == r["key"], r["key"])
        ok_exit = r["exit_code"] == 0 and not r["timed_out"]
        if r.get("result") and "cycles" in r["result"] and r["result"].get("cycles") is not None:
            a.check(f"{stage}:product", r["product"] == r["cycles"] * r["scratch"], r["key"])
        should_fail = (not ok_exit) or r.get("correctness") != "PASS" or bool(r.get("failure"))
        a.check(f"{stage}:failed_flag", r["failed_row"] == should_fail, r["key"])
        res = r.get("result") or {}
        if res.get("discrepancy_count"):
            a.check(f"{stage}:discrepancy_marks_failure", r["failed_row"], r["key"])
    failed = sum(r["failed_row"] for r in rows)
    return rows, {"rows": len(rows), "expected": len(expected), "failed": failed}


def audit_search_selection(a, rows):
    sel = load(a.run / "selection" / "search.json")
    fam = families(rows)
    configs = [f"cap{c}_{p}" for c in ("32", "128", "512", "null") for p in ("matched", "wider")]
    table = {}
    for c in configs:
        per = paired(rows, "frozen_phase2", f"new_{c}", 0.1, 0.1, 3)
        eff = fam_mean(per, fam) if len(per) == 100 else None
        comp = collections.defaultdict(list)
        for r in rows:
            if r["arm"] == f"new_{c}" and r["budget_seconds"] == 0.1 and not r["failed_row"]:
                comp[r["program_sha256"]].append(r["result"]["compile_seconds"])
        gm = math.exp(mean(math.log(sorted(v)[len(v) // 2] if len(v) % 2 else
                                    (sorted(v)[len(v) // 2 - 1] + sorted(v)[len(v) // 2]) / 2)
                           for v in comp.values()))
        cap = None if c.startswith("capnull") else int(c.split("_")[0][3:])
        table[c] = (eff, gm, cap, c.endswith("wider"))
        reported = next(e for e in sel["table"] if e["config"] == c)
        a.close(f"search:effect:{c}", eff, reported["effect_vs_frozen_0.1"])
        a.close(f"search:gm_compile:{c}", gm, reported["geometric_compile_seconds_0.1"])
    best = max(v[0] for v in table.values())
    tied = [c for c, v in table.items() if best - v[0] <= TIE]
    chosen = sorted(tied, key=lambda c: (table[c][1], math.inf if table[c][2] is None
                                         else table[c][2], table[c][3]))[0]
    expect = chosen if best > TIE else None
    a.check("search:selected_config", expect == sel["selected_config"],
            f"{expect} vs {sel['selected_config']}")


def audit_engineering(a):
    rows = rows_of(a.run / "stages" / "B_engineering_pair" / "rows.jsonl")
    sel = load(a.run / "selection" / "engineering.json")
    fam = families(rows)
    per = paired(rows, "selected_reference", "selected_cached", 0.1, 0.1, 3)
    q = fam_mean(per, fam)
    a.close("engineering:quality", q, sel["budgets"]["0.1"]["quality_effect_cached_vs_reference"])

    def ratio(field):
        t = collections.defaultdict(list)
        for r in rows:
            if r["budget_seconds"] == 0.1 and not r["failed_row"]:
                v = r["process_seconds"] if field == "process_seconds" else r["result"][field]
                t[(r["program_sha256"], r["arm"])].append(v)

        def med(v):
            v = sorted(v)
            n = len(v)
            return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
        per_p = {p: math.log(med(t[(p, "selected_cached")]) / med(t[(p, "selected_reference")]))
                 for p in fam}
        return fam_mean(per_p, fam)
    c, p = ratio("compile_seconds"), ratio("process_seconds")
    a.close("engineering:compile_log_ratio", c,
            sel["budgets"]["0.1"]["compile_ratio"]["mean_log_ratio"])
    adopt = "cached" if (q >= -TIE and (c < 0 or p < 0)) else "reference"
    a.check("engineering:adopted", adopt == sel["adopted_build"], f"{adopt} vs {sel['adopted_build']}")


def audit_depth(a):
    rows = rows_of(a.run / "stages" / "C_model_development" / "rows.jsonl")
    sel = load(a.run / "selection" / "model.json")
    fam = families(rows)
    vals = {}
    for d in (1, 2):
        per = collections.defaultdict(list)
        for r in rows:
            if r["arm"] == f"model_depth{d}" and r["budget_seconds"] == 0.1 and not r["failed_row"]:
                per[r["fixture_id"]].append(math.log(r["result"]["min_training_J"] /
                                                     r["result"]["best_validation_J"]))
                a.close("depth:row_log", per[r["fixture_id"]][-1],
                        r["result"]["log_train_over_best_validation"])
        vals[d] = fam_mean({k: mean(v) for k, v in per.items()}, fam)
    expect = 2 if vals[2] - vals[1] > TIE else 1
    a.check("depth:selected", expect == sel["selected_depth"], f"{expect} vs {sel['selected_depth']}")


def audit_comparison(a, rows):
    comp = load(a.run / "COMPARISON.json")
    fam = families(rows)
    per = paired(rows, "frozen_phase2", "selected_nonmodel", 0.1, 0.1, 15)
    a.check("primary:programs", len(per) == 200, len(per))
    eff = fam_mean(per, fam)
    lo, hi = boot(per, fam, (0.025, 0.975))
    a.close("primary:effect", eff, comp["primary"]["effect"])
    a.close("primary:low", lo, comp["primary"]["interval_95"][0])
    a.close("primary:high", hi, comp["primary"]["interval_95"][1])
    v = "SUPPORTS_IMPROVEMENT" if lo > 0 else "SUPPORTS_DEGRADATION" if hi < 0 else "INCONCLUSIVE"
    a.check("primary:verdict", v == comp["primary"]["verdict"], f"{v} vs {comp['primary']['verdict']}")
    wins = sum(x > TIE for x in per.values())
    losses = sum(x < -TIE for x in per.values())
    a.check("primary:wins_losses", (wins, losses) == (comp["primary"]["wins"],
                                                       comp["primary"]["losses"]),
            f"{wins},{losses}")
    for key, entry in comp["contrasts"].items():
        cand, ctrl = key.split("_vs_")
        cand_arm, cand_b = cand.rsplit("@", 1)
        ctrl_arm, ctrl_b = ctrl.rsplit("@", 1)
        per_c = paired(rows, ctrl_arm, cand_arm, None if ctrl_b == "None" else float(ctrl_b),
                       float(cand_b), 15)
        a.close(f"contrast:{key}", fam_mean(per_c, fam), entry["effect"])
    return per


def audit_public(a):
    rows = rows_of(a.run / "stages" / "D_public" / "rows.jsonl")
    pub = load(a.run / "PUBLIC_SCORE.json")
    serial_runs = load(SERIAL_RUNS)
    frozen = {}
    for r in serial_runs["runs"]:
        if r.get("arm") == "serial":
            frozen[r["program"]] = (r["cycles"], r["scratch"])
    serial_rows = [r for r in rows if r["arm"] == "serial"]
    a.check("public:serial_rows", len(serial_rows) == 120, len(serial_rows))
    for r in serial_rows:
        a.check("public:serial_matches_frozen",
                (r["cycles"], r["scratch"]) == frozen[r["result"]["program_name"]], r["key"])
    names = {r["program_sha256"]: r["result"]["program_name"] for r in rows if r.get("result")}
    by = collections.defaultdict(dict)
    for r in rows:
        if r["arm"] != "serial":
            by[(r["arm"], r["budget_seconds"], r["repetition"])][names[r["program_sha256"]]] = r
    for (arm, budget, rep), progs in by.items():
        if len(progs) != 8 or any(x["failed_row"] for x in progs.values()):
            continue
        sp = math.exp(mean(math.log(frozen[n][0] / x["cycles"]) for n, x in progs.items()))
        sc = math.exp(mean(math.log(frozen[n][1] / x["scratch"]) for n, x in progs.items()))
        s = math.sqrt(sp * sc)
        a.close(f"public:score:{arm}@{budget}",
                s, pub["scores"]["arms"][f"{arm}@{budget}"]["scores"][rep])
    for key, entry in pub["paired_score_ratios"].items():
        cand, ctrl = key.split("_vs_")
        a_s = pub["scores"]["arms"][cand]["scores"]
        c_s = pub["scores"]["arms"][ctrl]["scores"]
        strict = all(x / y > 1 + TIE for x, y in zip(a_s, c_s))
        a.check(f"public:strict:{key}", strict == entry["strict_improvement_every_repetition"],
                key)


def audit_h4(a):
    path = a.run / "stages" / "C_model_evaluation" / "rows.jsonl"
    if not path.exists():
        return
    rows = rows_of(path)
    report = load(a.run / "MODEL_EVALUATION.json")
    manifest = load(a.run / "fixtures" / "evaluation" / "MANIFEST.json")
    fam = {f["fixture_id"]: f["family"] for f in manifest["fixtures"]}
    idx = {(r["fixture_id"], r["arm"], r["budget_seconds"], r["repetition"]): r for r in rows}
    for r in rows:
        if r["failed_row"]:
            continue
        res = r["result"]
        a.check("h4:best_test_not_above_train", res["best_test_J"] <= res["min_training_J"],
                r["key"])
    defects = sum(r["failed_row"] for r in rows)
    lows = []
    for control in ("one_bit", "uniform_bits"):
        per = {}
        for f in sorted(fam):
            m = [idx.get((f, "selected_model", 0.1, k)) for k in range(15)]
            if any(x is None or x["failed_row"] for x in m):
                continue
            if control == "one_bit":
                c = [idx.get((f, "one_bit", 0.1, k)) for k in range(15)]
                if any(x is None or x["failed_row"] for x in c):
                    continue
                per[f] = mean(math.log(x["result"]["best_test_J"] / y["result"]["best_test_J"])
                              for x, y in zip(c, m))
            else:
                seeds = []
                for s in UNIFORM:
                    c = [idx.get((f, f"uniform_bits_{s}", 0.1, k)) for k in range(15)]
                    if any(x is None or x["failed_row"] for x in c):
                        seeds = None
                        break
                    seeds.append(mean(math.log(x["result"]["best_test_J"] /
                                               y["result"]["best_test_J"]) for x, y in zip(c, m)))
                if seeds:
                    per[f] = mean(seeds)
        eff = fam_mean(per, fam)
        lo, hi = boot(per, fam, (0.0125, 0.9875))
        entry = report["budgets"]["0.1"][control]
        a.close(f"h4:{control}:effect", eff, entry["effect"])
        a.close(f"h4:{control}:low", lo, entry["interval_97_5"][0])
        a.close(f"h4:{control}:high", hi, entry["interval_97_5"][1])
        a.check(f"h4:{control}:fixtures", len(per) == 30, len(per))
        lows.append(lo)
    passed = (len(set(fam.values())) >= 3 and defects == 0 and len(lows) == 2 and
              all(x > 0 for x in lows) and len(rows) == 17550)
    a.check("h4:no_false_pass", (report["H4_NEW"] == "PASS") == passed,
            f"reported {report['H4_NEW']} recomputed pass={passed}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    a = Audit(args.run)
    frozen = load(a.run / "FROZEN_SELECTION.json")
    # Ledgers re-derived from the written schedule specification.
    fresh = load(a.run / "FRESH_COHORT.json")["programs"]
    budgeted = sorted(["accepted_budgeted", "frozen_phase2", "selected_nonmodel"])
    unb = sorted(["accepted_bootstrap", "accepted_default", "classical"])
    derived = schedule_keys(fresh, unb, budgeted, BUDGETS, 15)
    a.check("ledger:D_fresh_derived", derived == load(a.run / "frozen_expected" /
                                                      "D_fresh_compiler.json")["keys"])
    a.check("ledger:D_fresh_count", len(derived) == 36000, len(derived))
    evalm = load(a.run / "fixtures" / "evaluation" / "MANIFEST.json")["fixtures"]
    labels = sorted(["empirical_cover", "selected_model", "one_bit"] +
                    [f"uniform_bits_{s}" for s in UNIFORM])
    derived_c = schedule_keys(evalm, [], labels, BUDGETS, 15)
    a.check("ledger:C_eval_derived", derived_c == load(a.run / "frozen_expected" /
                                                       "C_model_evaluation.json")["keys"])
    a.check("ledger:C_eval_count", len(derived_c) == 17550, len(derived_c))
    summary = {}
    for stage in ("B_search_development", "B_engineering_pair", "B_bound_ablation",
                  "C_model_development", "D_fresh_compiler", "D_public", "C_model_evaluation"):
        frozen_keys = None
        if (a.run / "frozen_expected" / f"{stage}.json").exists():
            frozen_keys = load(a.run / "frozen_expected" / f"{stage}.json")["keys"]
        if (a.run / "stages" / stage / "rows.jsonl").exists():
            rows, info = audit_rows(a, stage, frozen_keys)
            summary[stage] = info
            if stage == "B_search_development":
                audit_search_selection(a, rows)
            if stage == "D_fresh_compiler" and (a.run / "COMPARISON.json").exists():
                audit_comparison(a, rows)
                for r in rows:
                    if r["freeze_sha256"] != sha(a.run / "FROZEN_SELECTION.json"):
                        a.check("freeze:row_hash", False, r["key"])
                        break
    audit_engineering(a)
    audit_depth(a)
    if (a.run / "PUBLIC_SCORE.json").exists():
        audit_public(a)
    if (a.run / "MODEL_EVALUATION.json").exists():
        audit_h4(a)
    report = {"auditor": "research/optimization_audit.py (stdlib only; imports no research module)",
              "auditor_sha256": sha(Path(__file__)), "run": str(a.run),
              "checks": dict(a.checks), "total_checks": sum(a.checks.values()),
              "findings": a.findings, "stages": summary,
              "status": "PASS" if not a.findings and sum(a.checks.values()) > 0 else "FAIL",
              "imported_research_modules": sorted(m for m in sys.modules if m.startswith("research"))}
    out = Path(args.output) if args.output else a.run / "INDEPENDENT_AUDIT.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "total_checks": report["total_checks"],
                      "findings": len(a.findings)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
