"""Independent raw-row numerical auditor of the Phase 2 next round (protocol 1.0).

Standard library only. It imports NOTHING from ``research`` or the production
tree -- not the runner, the analysis, the report, the bootstrap owner nor the
ranker -- and re-derives from raw rows, pinned inputs, oracle files and the
locked package text:

- every stage's expected keys, from the plan's stage specifications transcribed
  below and the cell-order rule of PROTOCOL.json (sha256 of compact sorted-key
  JSON of [2026092601, program_sha256, repetition, arm, budget_or_null], first
  16 hex digits as an unsigned integer; ties by arm then budget text);
- row integrity: membership, duplicates, J = C * S, family = FAMILIES[seed % 5],
  equal family counts, program digest of every pinned input;
- the development selection, the 2x2 factorial point estimates, the Stage E
  decision;
- the primary head-to-head and its 95% interval, the frozen candidate's four
  endpoints and 98.75% intervals and the practical routes, with a bootstrap
  written here from the plan's definition (program-within-family resampling,
  equal family weights, linear-interpolation percentiles);
- the exact public scores and their reconciliation;
- the learning design (training draw, elite threshold, useful pool entries,
  sensitivity range) from oracle files, the yields of every ordering row, the
  three contrasts and their 98.333% intervals; the economics fraction.

Any recomputed number differing from the release's artifact by more than 1e-9
is a finding. An artifact that is absent is reported as not audited, never as
passing.

Usage::

    python research/next_round_audit.py --run DIR [--output PATH]
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
ORDER_SEED = 2026092601
BOOT_SEED = 2026092602
TRAINING_SEED = 2026092603
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
    f"random_{s}" for s in range(2026092610, 2026092620))


def stable(parts) -> int:
    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)


def cells(unbudgeted, budgeted, budgets=BUDGETS):
    return [(a, None) for a in unbudgeted] + [(a, b) for a in budgeted for b in budgets]


def keys_for(programs, cell_list, repetitions):
    out = []
    for digest in programs:
        for rep in range(repetitions):
            ordered = sorted(cell_list, key=lambda c: (
                stable([ORDER_SEED, digest, rep, c[0], c[1]]), c[0],
                "" if c[1] is None else str(c[1])))
            out.extend(f"{digest}|{a}|{b}|{rep}" for a, b in ordered)
    return out


def rows_of(path: Path):
    out = []
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                if i != len(lines) - 1:
                    raise
    return out


def mean(values):
    values = list(values)
    return sum(values) / len(values)


def median(values):
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def pct(sorted_values, p):
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    pos = (len(sorted_values) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(sorted_values[lo])
    w = pos - lo
    return float(sorted_values[lo] * (1 - w) + sorted_values[hi] * w)


def family_mean(per_program, families):
    grouped = collections.defaultdict(list)
    for p, v in per_program.items():
        grouped[families[p]].append(v)
    return mean(mean(v) for _, v in sorted(grouped.items()))


def boot(per_program, families, percentiles, seed=BOOT_SEED):
    grouped = {}
    for p, v in sorted(per_program.items()):
        grouped.setdefault(families[p], []).append(v)
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
    return point, [pct(draws, percentiles[0]), pct(draws, percentiles[1])]


class Audit:
    def __init__(self, run: Path) -> None:
        self.run = Path(run).resolve()
        self.root = self.run.parents[2]
        self.checks = 0
        self.findings = []
        self.not_audited = []

    def ok(self, cond, code, detail=""):
        self.checks += 1
        if not cond:
            self.findings.append({"code": code, "detail": str(detail)[:300]})

    def close(self, a, b, code, detail=""):
        self.ok(a is not None and b is not None and abs(a - b) <= TOL, code,
                f"{detail}: {a} vs {b}")

    def load(self, relative):
        path = self.run / relative
        if not path.exists():
            self.not_audited.append(relative)
            return None
        return json.loads(path.read_text())

    # -- rows ----------------------------------------------------------------

    def stage(self, stage, programs, cell_list, repetitions):
        directory = self.run / "stages" / stage
        if not (directory / "rows.jsonl").exists():
            self.not_audited.append(f"stages/{stage}")
            return None
        rows = rows_of(directory / "rows.jsonl")
        expected = keys_for(programs, cell_list, repetitions)
        ledger = json.loads((directory / "EXPECTED_KEYS.json").read_text())["keys"]
        self.ok(ledger == expected, "LEDGER_DIFFERS_FROM_PLAN", stage)
        frozen = self.run / "frozen_expected" / f"{stage}.json"
        if frozen.exists():
            self.ok(json.loads(frozen.read_text())["keys"] == expected, "FROZEN_LEDGER", stage)
        counts = collections.Counter(r["key"] for r in rows)
        self.ok(set(counts) == set(expected), "ROW_SET", stage)
        self.ok(all(n == 1 for n in counts.values()), "DUPLICATES", stage)
        for r in rows:
            self.ok(not r["failed_row"], "FAILED", r["key"])
            if r.get("cycles") is not None:
                self.ok(r["product"] == r["cycles"] * r["scratch"], "PRODUCT", r["key"])
            if r.get("seed") is not None:
                self.ok(r["family"] == FAMILIES[r["seed"] % 5], "FAMILY", r["key"])
        return rows

    def programs(self, cohort, first, last):
        out, fam = [], {}
        for seed in range(first, last + 1):
            path = self.run / "inputs" / cohort / f"seed_{seed}.json"
            program = json.loads(path.read_text())
            digest = hashlib.sha256(json.dumps(program, sort_keys=True, separators=(
                ",", ":")).encode("utf-8")).hexdigest()
            out.append((FAMILIES.index(FAMILIES[seed % 5]), seed, digest))
            fam[digest] = FAMILIES[seed % 5]
        out.sort()
        counts = collections.Counter(fam.values())
        self.ok(len(counts) == 5 and len(set(counts.values())) == 1, "FAMILY_BALANCE", cohort)
        return [d for _, _, d in out], fam

    # -- estimators ------------------------------------------------------------

    @staticmethod
    def logj(rows, arm, budget, reps):
        by = collections.defaultdict(list)
        for r in rows:
            if r["arm"] == arm and r["budget_seconds"] == budget:
                by[r["program_sha256"]].append(math.log(r["product"]))
        return {p: mean(v) for p, v in by.items() if len(v) == reps}

    @staticmethod
    def paired(rows, control, candidate, cb, db, reps):
        idx = {(r["program_sha256"], r["arm"], r["budget_seconds"], r["repetition"]): r
               for r in rows}
        programs = sorted({r["program_sha256"] for r in rows})
        out = {}
        for p in programs:
            logs = []
            for rep in range(reps):
                a, b = idx.get((p, control, cb, rep)), idx.get((p, candidate, db, rep))
                if a and b:
                    logs.append(math.log(a["product"] / b["product"]))
            if len(logs) == reps:
                out[p] = mean(logs)
        return out

    @staticmethod
    def med_time(rows, arm, budget):
        by = collections.defaultdict(list)
        for r in rows:
            if r["arm"] == arm and r["budget_seconds"] == budget:
                by[r["program_sha256"]].append(r["result"]["compile_seconds"])
        return {p: median(v) for p, v in by.items()}

    def geo_compile(self, rows, arm, budget, fam):
        m = self.med_time(rows, arm, budget)
        return math.exp(family_mean({p: math.log(v) for p, v in m.items()}, fam))

    # -- parts -----------------------------------------------------------------

    def development(self):
        programs, fam = self.programs("development", 800000, 800099)
        rows = self.stage("D_factorial", programs, cells([], list(DEV_ARMS)), 3)
        if rows is None:
            return None, fam
        table = {a: family_mean(self.logj(rows, a, 0.1, 3), fam) for a in DEV_ARMS}
        best = min(table.values())
        tied = sorted(a for a, v in table.items() if v - best <= TIE)
        chosen = sorted(tied, key=lambda a: (self.geo_compile(rows, a, 0.1, fam), a))[0]
        selection = self.load("SELECTION.json")
        if selection:
            self.ok(selection["selection"]["selected_arm"] == chosen, "SELECTION", chosen)
            for arm, v in table.items():
                self.close(selection["selection"]["table"][arm]["family_mean_log_J"], v,
                           "SELECTION_TABLE", arm)
        factorial = self.load("FACTORIAL.json")
        if factorial:
            for b in BUDGETS:
                y = {c: self.logj(rows, c, b, 3) for c in CELLS}
                common = set.intersection(*(set(v) for v in y.values()))
                cat = {p: 0.5 * ((y["cell_a4cat_heap"][p] - y["cell_a3cat_heap"][p])
                                 + (y["cell_a4cat_dfs"][p] - y["cell_a3cat_dfs"][p]))
                       for p in common}
                trav = {p: 0.5 * ((y["cell_a4cat_heap"][p] - y["cell_a4cat_dfs"][p])
                                  + (y["cell_a3cat_heap"][p] - y["cell_a3cat_dfs"][p]))
                        for p in common}
                inter = {p: (y["cell_a4cat_heap"][p] - y["cell_a4cat_dfs"][p])
                         - (y["cell_a3cat_heap"][p] - y["cell_a3cat_dfs"][p]) for p in common}
                f = factorial["budgets"][str(b)]["factorial"]
                self.close(f["catalog_effect_a4_minus_a3"]["estimate"], family_mean(cat, fam),
                           "FACTORIAL_CATALOG", b)
                self.close(f["traversal_effect_heap_minus_dfs"]["estimate"],
                           family_mean(trav, fam), "FACTORIAL_TRAVERSAL", b)
                self.close(f["interaction"]["estimate"], family_mean(inter, fam),
                           "FACTORIAL_INTERACTION", b)
        profile_programs = []
        seen = collections.Counter()
        for digest in programs:
            if seen[fam[digest]] < 2:
                profile_programs.append(digest)
                seen[fam[digest]] += 1
        self.stage("D_fixed_work", profile_programs,
                   cells([], list(CELLS), [f"work:{n}" for n in (1000, 10000, 50000)]), 1)
        self.stage("D_profile", profile_programs, cells([], list(DEV_ARMS)), 1)
        engineered = self.stage("E_engineering", programs,
                                cells([], [f"{chosen}+engineered"]), 3)
        decision = self.load("ENGINEERING_DECISION.json")
        if engineered is not None and decision:
            both = rows + engineered
            parent, variant = chosen, f"{chosen}+engineered"
            quality = (family_mean(self.logj(both, variant, 0.1, 3), fam)
                       - family_mean(self.logj(both, parent, 0.1, 3), fam))
            reduction = 1 - self.geo_compile(both, variant, 0.1, fam) / self.geo_compile(
                both, parent, 0.1, fam)
            d = decision["decision_by_budget"]["0.1"]
            self.close(d["delta_family_mean_log_J_variant_minus_parent"], quality,
                       "E_QUALITY")
            self.close(d["compile_time_reduction"], reduction, "E_REDUCTION")
            frozen = variant if (quality <= TIE and reduction >= 0.10) else parent
            self.ok(decision["frozen_candidate"] == frozen, "E_DECISION", frozen)
        return chosen, fam

    def confirmation(self):
        frozen = self.load("FROZEN_SELECTION.json")
        if not frozen:
            return
        arms = frozen["confirmation"]["budgeted_arms"]
        candidate = frozen["candidate"]["frozen_candidate"]
        decision = self.load("ENGINEERING_DECISION.json")
        self.ok(decision and decision["frozen_candidate"] == candidate, "FREEZE_CANDIDATE")
        expected_arms = []
        for a in (EARLIER, A4, candidate):
            if a not in expected_arms:
                expected_arms.append(a)
        self.ok(arms == expected_arms, "FREEZE_ARMS", arms)
        programs, fam = self.programs("confirmation", 960000, 960199)
        rows = self.stage("C_confirmation", programs,
                          cells(["classical", "accepted_bootstrap"], arms), 5)
        public_programs = sorted(
            hashlib.sha256(json.dumps(json.loads(p.read_text()), sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
            for p in (self.run / "inputs" / "public").glob("*.json"))
        cohort = json.loads((self.run / "CONFIRMATION_COHORT.json").read_text())
        order = [e["program_sha256"] for e in cohort["public_programs"]]
        self.ok(sorted(order) == public_programs, "PUBLIC_SET")
        public_rows = self.stage("C_public", order,
                                 cells(["classical", "accepted_bootstrap", "serial"], arms), 5)
        comparison = self.load("COMPARISON.json")
        if rows is not None and comparison:
            per = self.paired(rows, EARLIER, A4, 0.1, 0.1, 5)
            point, interval = boot(per, fam, PRIMARY)
            p = comparison["primary"]
            self.close(p["estimate"], point, "PRIMARY_POINT")
            self.close(p["interval_95"][0], interval[0], "PRIMARY_LOW")
            self.close(p["interval_95"][1], interval[1], "PRIMARY_HIGH")
            verdict = ("FAVOURS_A4" if interval[0] > 0 else "FAVOURS_EARLIER"
                       if interval[1] < 0 else "INCONCLUSIVE")
            self.ok(p["verdict"] == verdict, "PRIMARY_VERDICT", verdict)
            if frozen["candidate"]["candidate_is_distinct_new"]:
                routes = {"quality_route": True, "efficiency_route": True}
                for ref in (EARLIER, A4):
                    q = {k: -v for k, v in self.paired(rows, ref, candidate, 0.1, 0.1, 5).items()}
                    qp, qi = boot(q, fam, CANDIDATE)
                    a, b = self.med_time(rows, ref, 0.1), self.med_time(rows, candidate, 0.1)
                    c = {k: math.log(b[k] / a[k]) for k in a}
                    cp, ci = boot(c, fam, CANDIDATE)
                    e = comparison["candidate_endpoints"][ref]
                    self.close(e["J_ratio"], math.exp(qp), "CAND_J", ref)
                    self.close(e["J_ratio_interval_98_75"][1], math.exp(qi[1]), "CAND_J_HI", ref)
                    self.close(e["compile_ratio"], math.exp(cp), "CAND_C", ref)
                    self.close(e["compile_ratio_interval_98_75"][1], math.exp(ci[1]),
                               "CAND_C_HI", ref)
                    routes["quality_route"] &= math.exp(qi[1]) <= 0.98 and math.exp(ci[1]) <= 1.10
                    routes["efficiency_route"] &= (math.exp(ci[1]) <= 0.80
                                                   and math.exp(qi[1]) <= 1.01)
                self.ok(comparison["candidate_endpoints"]["routes_passed"] == routes, "ROUTES",
                        routes)
        public = self.load("PUBLIC_SCORE.json")
        if public_rows is not None and public:
            serial = {r["program_sha256"]: (r["cycles"], r["scratch"]) for r in public_rows
                      if r["arm"] == "serial"}
            idx = {(r["program_sha256"], r["arm"], r["budget_seconds"], r["repetition"]): r
                   for r in public_rows}
            for arm in arms:
                for b in BUDGETS:
                    got = public["scores"]["arms"][f"{arm}@{b}"]["scores"]
                    for rep in range(5):
                        chosen = [idx[(p, arm, b, rep)] for p in order]
                        s = math.sqrt(
                            math.exp(mean(math.log(serial[c["program_sha256"]][0] / c["cycles"])
                                          for c in chosen))
                            * math.exp(mean(math.log(serial[c["program_sha256"]][1]
                                                     / c["scratch"]) for c in chosen)))
                        self.close(got[rep], s, "PUBLIC_SCORE", f"{arm}@{b}#{rep}")

    def learning(self):
        design = self.load("learning/DESIGN_DEVELOPMENT.json")
        report = self.load("LEARNING_FEASIBILITY.json")
        for cohort in ("development", "evaluation"):
            data = self.load(f"learning/DESIGN_{cohort.upper()}.json")
            if not data:
                continue
            manifest_path = self.root / data["manifest"]
            manifest = json.loads(manifest_path.read_text())
            informative = 0
            for fixture in manifest["fixtures"]:
                fdir = manifest_path.parent / fixture["fixture_id"]
                oracle = json.loads((fdir / "oracle.json").read_text())
                ids = sorted(item["identity"] for item in oracle["feasible"])
                rng = random.Random(stable([TRAINING_SEED, fixture["record_sha256"]]))
                drawn = set(rng.sample(ids, 20))
                prod = {i["identity"]: i["product"] for i in oracle["feasible"]}
                index = {int(i["structural_rank_index"]): i["identity"]
                         for i in oracle["feasible"]}
                train = sorted(prod[i] for i in drawn)
                threshold = train[max(1, math.ceil(0.1 * 20)) - 1]
                ranker = json.loads((self.run / "learning" / "design" / cohort
                                     / fixture["fixture_id"] / "RANKER_INPUT.json").read_text())
                self.ok(sorted(int(i) for i in ranker["training_indices"]) == sorted(
                    int(i["structural_rank_index"]) for i in oracle["feasible"]
                    if i["identity"] in drawn), "TRAINING_DRAW", fixture["fixture_id"])
                pool = [int(i) for i in ranker["pool"]]
                useful = {index[i] for i in pool if i in index and index[i] not in drawn
                          and prod[index[i]] <= threshold}
                n, m = len(pool), len(useful)
                k = min(32, n)
                rng_ = min(k, m) - max(0, k - (n - m))
                d = [x for x in data["designs"] if x["fixture_id"] == fixture["fixture_id"]][0]
                self.ok(d["sensitivity"]["M_useful"] == m and d["sensitivity"]["range"] == rng_,
                        "SENSITIVITY", fixture["fixture_id"])
                informative += rng_ > 0
            self.ok(data["gate"]["informative"] == informative, "GATE_COUNT", cohort)
        if design is None:
            return
        order_path = self.run / "stages" / "L_orderings" / "rows.jsonl"
        if order_path.exists() and report and isinstance(report.get("contrasts"), dict):
            evaluation = json.loads((self.run / "learning" / "DESIGN_EVALUATION.json").read_text())
            fam = {d["fixture_id"]: d["family"] for d in evaluation["designs"]}
            rows = self.stage("L_orderings", [d["program_sha256"] for d in evaluation["designs"]],
                              cells(list(ORDERINGS), []), 1)
            manifest = json.loads((self.root / evaluation["manifest"]).read_text())
            yields = collections.defaultdict(dict)
            for r in rows:
                res = r["result"]
                fid = res["fixture_id"]
                fdir = (self.root / evaluation["manifest"]).parent / fid
                oracle = json.loads((fdir / "oracle.json").read_text())
                fixture = [f for f in manifest["fixtures"] if f["fixture_id"] == fid][0]
                ids = sorted(i["identity"] for i in oracle["feasible"])
                drawn = set(random.Random(stable([TRAINING_SEED, fixture["record_sha256"]]))
                            .sample(ids, 20))
                prod = {i["identity"]: i["product"] for i in oracle["feasible"]}
                index = {int(i["structural_rank_index"]): i["identity"]
                         for i in oracle["feasible"]}
                threshold = sorted(prod[i] for i in drawn)[1]
                useful = {index[int(i)] for i in res["ordered"][:32]
                          if int(i) in index and index[int(i)] not in drawn
                          and prod[index[int(i)]] <= threshold}
                yields[fid][res["ordering"]] = len(useful) / 32
            randoms = [o for o in ORDERINGS if o.startswith("random_")]
            for name, control in (("tree_minus_hamming", lambda s: s["hamming"]),
                                  ("tree_minus_random_mean", lambda s: mean(s[o] for o in randoms)),
                                  ("tree_minus_shuffled_tree", lambda s: s["shuffled_tree"])):
                per = {f: s["tree"] - control(s) for f, s in yields.items()}
                point, interval = boot(per, fam, LEARNING)
                c = report["contrasts"][name]
                self.close(c["estimate"], point, "LEARN_POINT", name)
                self.close(c["interval_98_333"][0], interval[0], "LEARN_LOW", name)
        acq = self.run / "stages" / "L_acquisition" / "rows.jsonl"
        if acq.exists() and report and isinstance(report.get("economics"), dict):
            rows = rows_of(acq)
            frac = sum(1 for r in rows if r["result"]["queries_reaching_20_validated"] > 0) / len(rows)
            self.close(report["economics"]["fraction"], frac, "ECON_FRACTION")

    def run_all(self):
        self.development()
        self.confirmation()
        self.learning()
        codes = collections.Counter(f["code"] for f in self.findings)
        return {"status": "PASS" if self.checks and not self.findings else "FAIL",
                "checks": self.checks, "finding_codes": dict(codes),
                "findings": self.findings[:100], "not_audited": self.not_audited,
                "imports": "standard library only"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = Audit(Path(args.run)).run_all()
    out = Path(args.output) if args.output else Path(args.run) / "INDEPENDENT_AUDIT.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "checks", "finding_codes",
                                             "not_audited")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
