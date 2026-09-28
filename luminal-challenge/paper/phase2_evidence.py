"""Owner of every Phase 2 and round 1-3 number cited by the manuscripts.

Two jobs, one owner:

* ``generate()`` derives the structural-encoding feasibility table (P0/P1),
  unchanged from the accepted 23 September revision.
* ``Ledger`` records every other cited value as (key, formatted value, raw value,
  source file, field path, derivation). ``build_programme_ledger`` fills it from
  the frozen evidence of rounds 1-3 and the Phase 2 comparison; the figure
  generator adds the Phase 1 and worked-example values. The ledger writes
  ``generated/values.tex`` (one ``\\V{key}`` macro per value; an undefined key
  is a LaTeX error, so the build fails) and ``generated/claim_ledger.json``.
  ``verify_ledger`` re-opens every source from disk, re-walks every field path or
  re-runs every named derivation, and fails on any difference.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN_REL = "results/phase2_structural_encoding/phase2_repair_20260923c"
RUN = ROOT / RUN_REL
OUT = HERE / "generated"
EXPECTED_PROGRAMS = [f"0{i}_{name}.json" for i, name in enumerate([
    "scalar_pipeline", "scalar_dual_chain", "vector_axpy", "vector_bitmix",
    "mixed_broadcast", "parallel_memory", "scalar_selects", "vector_reduction"], 1)]
EXPECTED_UNION = [0, 234, 194, 55, 135, 16, 168, 17]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(relative):
    path = ROOT / relative
    return json.loads(path.read_text()), path


def generate():
    p1_rel = RUN_REL + "/p1/summary.json"
    p0_rel = RUN_REL + "/p0/summary.json"
    paths = [
        RUN_REL + "/LEAD_ACCEPTANCE.md", RUN_REL + "/manifest.json",
        RUN_REL + "/gates.json", RUN_REL + "/hypotheses.json",
        RUN_REL + "/checker.json", p0_rel, p1_rel,
        "plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md",
        "plan/phase2/PROTOCOL.json",
    ]
    sources = {}
    docs = {}
    for rel in paths:
        docs[rel], path = read_json(rel) if rel.endswith(".json") else (None, ROOT / rel)
        sources[rel] = sha256(path)

    p1 = docs[p1_rel]
    gates = docs[RUN_REL + "/gates.json"]
    checker = docs[RUN_REL + "/checker.json"]
    p0 = docs[p0_rel]
    assert len(p1["fixtures"]) == 12 and len(p0["fixtures"]) == 12
    assert p1["exhausted_comparisons"] == 24
    assert all(set(fixture["codecs"]) == {"absolute", "static_rank", "structural_rank", "vector_block"}
               for fixture in p1["fixtures"])
    assert sum(codec["round_trips"] for fixture in p1["fixtures"]
               for codec in fixture["codecs"].values()) == 564
    assert p1["round_trip_failures"] == 0 and p1["defect_count"] == 0
    assert p1["sampling_raw_rows"] == p1["sampling_attempts_drawn"] == 160000
    assert p1["stream_count"] == 16 and p1["sampling_completions"] == 819
    assert p1["sampling_case_checks"] == 1356 and p1["sampling_discrepancy_count"] == 0
    assert p1["sampling_case_failures"] == 0
    assert p1["coverage_minimum"] == 100 and not p1["coverage_met"]
    assert p0["stage"] == "p0"
    assert gates["p0"]["status"] == "PASS"
    assert gates["p1"]["status"] == "INCONCLUSIVE"
    assert all(gates[f"p{i}"]["status"] == "BLOCKED_BY_GATE" for i in range(2, 6))
    assert checker["finding_count"] == 0 and checker["artifacts_internally_consistent"]
    assert checker["artifacts_complete"] is False and checker["scientific_success"] is False
    assert [r["program"] for r in p1["public_coverage"]] == EXPECTED_PROGRAMS
    assert [r["distinct_complete_union"] for r in p1["public_coverage"]] == EXPECTED_UNION
    assert all(r["raw_complete"] == 0 for r in p1["public_coverage"])
    assert all(r["meets_minimum"] == (r["distinct_complete_union"] >= p1["coverage_minimum"])
               for r in p1["public_coverage"])
    assert all(r["case_failures"] == 0 for r in p1["public_coverage"])

    raw_hashes = {}
    for name, expected in p1["raw_artifacts"].items():
        rel = RUN_REL + "/p1/" + name
        observed = sha256(ROOT / rel)
        assert observed == expected, f"raw artifact hash mismatch: {rel}"
        raw_hashes[rel] = observed

    rows = []
    for item in p1["public_coverage"]:
        status = "meets minimum" if item["meets_minimum"] else "below minimum"
        label = item["program"].split("_", 1)[1].removesuffix(".json").replace("_", " ")
        rows.append(
            f"{label} & {item['raw_complete']} & "
            f"{item['path_complete']} & {item['distinct_complete_union']} & {status} \\\\"
        )
    (OUT / "phase2_coverage_rows.tex").write_text("\n".join(rows) + "\n")
    metrics = {
        "run_id": "phase2_repair_20260923c",
        "run_date": "2026-09-23",
        "source_sha256": sources,
        "raw_artifact_sha256_verified_against_p1_summary": raw_hashes,
        "finite_checks": {"fixtures": 12, "codecs": 4, "exhausted_code_universes": 24,
                          "round_trips": 564, "round_trip_failures": 0},
        "sampling": {"attempts": 160000, "streams": 16, "completed_draws": 819,
                     "case_checks": 1356, "discrepancies": 0,
                     "raw_bit_completions": 0, "coverage_minimum_per_program": 100},
        "public_coverage": p1["public_coverage"],
        "stages": {"p0": "PASS", "p1": "INCONCLUSIVE",
                   "p2": "BLOCKED_BY_GATE", "p3": "BLOCKED_BY_GATE",
                   "p4": "BLOCKED_BY_GATE", "p5": "BLOCKED_BY_GATE"},
        "checker": {"findings": 0, "artifacts_internally_consistent": True,
                    "artifacts_complete": False, "scientific_success": False},
    }
    (OUT / "phase2_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics





# ---------------------------------------------------------------------------
# The value ledger
# ---------------------------------------------------------------------------

import math
import re
import statistics
from collections import Counter, defaultdict

PHASE2 = "results/phase2_structural_encoding/"
T3 = PHASE2 + "third_round_20260925_resume/"
REV = PHASE2 + "lead_resume_review_20260926/"
R1 = PHASE2 + "objective_index_20260924/"
R2 = PHASE2 + "next_round_20260925/"
EFF = PHASE2 + "efficiency_20260925/"
A0RUN = PHASE2 + "recovery_campaign_20260923_r3/"
P1 = "results/direct_index_v4_optimization_repair2/"

FORMATS = {
    "int": lambda v: f"{int(v):,}",
    "f1": lambda v: f"{v:.1f}", "f2": lambda v: f"{v:.2f}", "f3": lambda v: f"{v:.3f}",
    "f4": lambda v: f"{v:.4f}", "f6": lambda v: f"{v:.6f}",
    "pct1": lambda v: f"{100 * v:.1f}", "pct2": lambda v: f"{100 * v:.2f}",
    "str": lambda v: str(v),
    "sgn4": lambda v: f"{v:+.4f}".replace("-", "\N{MINUS SIGN}"),
    "neg4": lambda v: f"{v:.4f}".replace("-", "\N{MINUS SIGN}"),
    "neg3": lambda v: f"{v:.3f}".replace("-", "\N{MINUS SIGN}"),
}
TRANSFORMS = {
    None: lambda v: v,
    "pct_from_ratio": lambda v: 1 - 1 / v,          # J_control/J_candidate -> fractional J reduction
    "pct_from_log": lambda v: 1 - math.exp(-v),     # mean log(J_control/J_candidate) -> reduction
    "ratio_from_log": lambda v: math.exp(-v),       # mean log(J_control/J_candidate) -> J ratio
    "neg": lambda v: -v,
    "ms": lambda v: 1000 * v,
    "pct_points": lambda v: v / 100,
    "level": lambda v: 100 * (1 - 2 * v),           # lower percentile -> two-sided interval level (%)
}
_JSON_CACHE = {}


def _load(rel):
    if rel not in _JSON_CACHE:
        path = ROOT / rel
        if rel.endswith(".jsonl"):
            _JSON_CACHE[rel] = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        elif rel.endswith(".json") or rel.endswith(".ipynb"):
            _JSON_CACHE[rel] = json.loads(path.read_text())
        else:
            _JSON_CACHE[rel] = path.read_text()
    return _JSON_CACHE[rel]


def _walk(doc, path):
    for step in path:
        doc = doc[step]
    return doc


class Ledger:
    """Every cited number, with the file and field it comes from."""

    def __init__(self):
        self.entries = {}

    def _put(self, key, raw, fmt, entry):
        if key in self.entries:
            raise ValueError(f"duplicate ledger key {key}")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9.]*", key):
            raise ValueError(f"bad ledger key {key}")
        entry.update(key=key, raw=raw, fmt=fmt, value=FORMATS[fmt](raw))
        self.entries[key] = entry
        return raw

    def ptr(self, key, source, path, fmt, transform=None, claim=""):
        """A value read directly from a field of a frozen JSON file."""
        raw = TRANSFORMS[transform](_walk(_load(source), path))
        return self._put(key, raw, fmt, {"kind": "pointer", "source": source, "field": list(path),
                                         "transform": transform, "claim": claim})

    def derived(self, key, name, fmt, claim="", **kwargs):
        """A value computed from frozen rows by a named derivation in DERIVATIONS."""
        raw = DERIVATIONS[name](**kwargs)
        return self._put(key, raw, fmt, {"kind": "derived", "derivation": name, "arguments": kwargs,
                                         "source": DERIVATION_SOURCES.get(name, "see derivation"),
                                         "claim": claim})

    def computed(self, key, raw, fmt, source, field, claim=""):
        """A value produced by an executing generator (figure checks, worked example)."""
        return self._put(key, raw, fmt, {"kind": "computed", "source": source, "field": field,
                                         "claim": claim})

    def value(self, key):
        return self.entries[key]["value"]

    def write(self):
        lines = ["% Generated by phase2_evidence.Ledger. Do not edit.",
                 r"\makeatletter"]
        for key, entry in sorted(self.entries.items()):
            text = entry["value"].replace("\N{MINUS SIGN}", r"\ensuremath{-}").replace("×", r"\ensuremath{\times}")
            lines.append(r"\expandafter\def\csname lv@" + key + r"\endcsname{" + text + "}")
        lines += [r"\newcommand{\V}[1]{\ifcsname lv@#1\endcsname\csname lv@#1\endcsname"
                  r"\else\PackageError{ledger}{Undefined ledger value #1}{}\fi}",
                  r"\makeatother"]
        (OUT / "values.tex").write_text("\n".join(lines) + "\n")
        serial = {k: {x: v for x, v in e.items()} for k, e in sorted(self.entries.items())}
        (OUT / "claim_ledger.json").write_text(json.dumps(serial, indent=1, default=str) + "\n")


def verify_ledger(path=None):
    """Re-derive every ledger entry from the files on disk; return the check count."""
    ledger = json.loads((path or OUT / "claim_ledger.json").read_text())
    _JSON_CACHE.clear()
    checked = 0
    for key, entry in ledger.items():
        if entry["kind"] == "pointer":
            raw = TRANSFORMS[entry["transform"]](_walk(_load(entry["source"]), entry["field"]))
        elif entry["kind"] == "derived":
            raw = DERIVATIONS[entry["derivation"]](**entry["arguments"])
        elif entry["kind"] == "derived-ms":
            raw = 1000 * DERIVATIONS[entry["derivation"]](**entry["arguments"])
        else:
            continue  # computed entries are re-derived by rerunning the generator itself
        text = FORMATS[entry["fmt"]](raw)
        if text != entry["value"]:
            raise AssertionError(f"ledger drift for {key}: {text} != {entry['value']}")
        checked += 1
    if not checked:
        raise AssertionError("ledger verification checked zero entries")
    return checked, len(ledger)


# ---------------------------------------------------------------------------
# Named derivations over frozen rows (each re-run by verify_ledger)
# ---------------------------------------------------------------------------

def _rows(stage):
    return _load(T3 + f"stages/{stage}/rows.jsonl")


def _pairs(stage, mode):
    pairs = defaultdict(dict)
    for r in _rows(stage):
        if r["mode_key"] == mode:
            pairs[(r["seed"], r["repetition"])][r["arm_id"]] = r
    assert all(set(p) == {"R0", "C1"} for p in pairs.values())
    return pairs


def d_zero_node_programs():
    seeds = {r["seed"] for r in _rows("C_fixed_work") if r["nodes"] == 0}
    assert all(r["nodes"] == 0 for r in _rows("C_fixed_work") if r["seed"] in seeds)
    return len(seeds)


def d_substantive_pairs():
    rows = _rows("C_fixed_work")
    keyed = defaultdict(dict)
    for r in rows:
        keyed[(r["seed"], r["repetition"])][r["arm_id"]] = r
    assert len(keyed) == 1000
    return sum(1 for p in keyed.values() if p["R0"]["nodes"] > 0)


def d_reps_per_program():
    counts = Counter((r["seed"], r["arm_id"]) for r in _rows("C_fixed_work"))
    values = set(counts.values())
    assert len(values) == 1
    return values.pop()


def d_certificate_median():
    return statistics.median(r["certificates"] for r in _rows("C_fixed_work"))


def d_distinct_traces():
    return len({r["fingerprint"]["trace_sha256"] for r in _rows("C_fixed_work")})


def d_wall_losses(mode, what):
    pairs = _pairs("C_wall", mode)
    lost = [(k, p) for k, p in pairs.items() if p["C1"]["J"] > p["R0"]["J"]]
    if what == "runs":
        return len(lost)
    if what == "programs":
        return len({k[0] for k, _ in lost})
    if what == "no_unknown":
        return sum(1 for _, p in lost if p["C1"]["unknown_queries"] == 0 and p["R0"]["unknown_queries"] == 0)
    raise KeyError(what)


def d_wall_seed(seed, arm, field, mode="wall:1.0"):
    values = {r[field] for r in _rows("C_wall") if r["seed"] == seed and r["arm_id"] == arm
              and r["mode_key"] == mode}
    assert len(values) == 1, (seed, arm, values)
    return values.pop()


def d_acceptance(what):
    rows = _rows("C_acceptance")
    per_arm = defaultdict(list)
    for r in rows:
        per_arm[r["arm_id"]].append(r)
    assert set(per_arm) == {"R0", "C1"} and all(r["ok"] and r["input_unchanged"] for r in rows)
    sizes = {arm: len(v) for arm, v in per_arm.items()}
    cases = {arm: sum(r["cases"] for r in v) for arm, v in per_arm.items()}
    assert len(set(sizes.values())) == 1 and len(set(cases.values())) == 1
    return sizes["C1"] if what == "programs" else cases["C1"]


def d_public_row(program_sha, arm, mode, field):
    values = {r[field] for r in _rows("C_public") if r["program_sha256"] == program_sha
              and r["arm_id"] == arm and r["mode_key"] == mode}
    assert len(values) == 1, values
    return values.pop()


def d_public_median_seconds(program_sha, arm, mode):
    return statistics.median(r["compile_call_seconds"] for r in _rows("C_public")
                             if r["program_sha256"] == program_sha and r["arm_id"] == arm
                             and r["mode_key"] == mode)


def d_phase1_median_seconds(source, arm, program):
    rows = _load(source)["runs"]
    values = [r["compile_seconds"] for r in rows if r["arm"] == arm and r["program"] == program]
    assert values
    return statistics.median(values)


def d_log_count(source, pattern):
    match = re.search(pattern, _load(source), flags=re.MULTILINE)
    assert match, pattern
    return int(match.group(1))


def d_tercile(index, field):
    entry = _load(REV + "RECOMPUTE.json")["probes"]["cost_by_nodes_tercile"][index]
    return entry["nodes_range"][0] if field == "lo" else entry["nodes_range"][1] if field == "hi" else entry[field]


def d_d_memory_programs():
    return len({r["seed"] for r in _rows("D_memory")})


def d_classical_relative(mode):
    d = _load(P1 + "lead_review/final/runs.json")
    rows = d["runs"]
    programs = d["analysis"]["programs"]
    med = lambda arm, p: statistics.median(r["compile_seconds"] for r in rows if r["arm"] == arm and r["program"] == p)
    return math.exp(statistics.mean(math.log(med("candidate_" + mode, p) / med("classical", p)) for p in programs))


def d_tests_total(source):
    return sum(r.get("tests", 0) or 0 for r in _load(source)["records"])


def d_p1_round_trips():
    p1 = _load(RUN_REL + "/p1/summary.json")
    return sum(codec["round_trips"] for fixture in p1["fixtures"] for codec in fixture["codecs"].values())


def d_protocol_value(source, path):
    return _walk(_load(source), path)


DERIVATIONS = {
    "zero_node_programs": d_zero_node_programs, "substantive_pairs": d_substantive_pairs,
    "reps_per_program": d_reps_per_program, "certificate_median": d_certificate_median,
    "distinct_traces": d_distinct_traces, "wall_losses": d_wall_losses, "wall_seed": d_wall_seed,
    "acceptance": d_acceptance, "public_row": d_public_row,
    "public_median_seconds": d_public_median_seconds,
    "phase1_median_seconds": d_phase1_median_seconds, "log_count": d_log_count,
    "tercile": d_tercile, "d_memory_programs": d_d_memory_programs,
    "classical_relative": d_classical_relative, "tests_total": d_tests_total,
    "p1_round_trips": d_p1_round_trips,
}
DERIVATION_SOURCES = {
    "zero_node_programs": T3 + "stages/C_fixed_work/rows.jsonl",
    "substantive_pairs": T3 + "stages/C_fixed_work/rows.jsonl",
    "reps_per_program": T3 + "stages/C_fixed_work/rows.jsonl",
    "certificate_median": T3 + "stages/C_fixed_work/rows.jsonl",
    "distinct_traces": T3 + "stages/C_fixed_work/rows.jsonl",
    "wall_losses": T3 + "stages/C_wall/rows.jsonl", "wall_seed": T3 + "stages/C_wall/rows.jsonl",
    "acceptance": T3 + "stages/C_acceptance/rows.jsonl",
    "public_row": T3 + "stages/C_public/rows.jsonl",
    "public_median_seconds": T3 + "stages/C_public/rows.jsonl",
    "phase1_median_seconds": P1 + "lead_review/{final,comparison}/runs.json",
    "tercile": REV + "RECOMPUTE.json", "d_memory_programs": T3 + "stages/D_memory/rows.jsonl",
    "classical_relative": P1 + "lead_review/final/runs.json",
    "tests_total": P1 + "lead_review/verification/summary.json",
    "p1_round_trips": RUN_REL + "/p1/summary.json",
}


# ---------------------------------------------------------------------------
# Rounds 1-3 and the Phase 2 comparison
# ---------------------------------------------------------------------------

def build_programme_ledger(L):
    """Record the frozen programme evidence; assert its internal consistency first."""
    cmp3 = _load(T3 + "COMPARISON.json")
    rec = _load(REV + "RECOMPUTE.json")
    assert cmp3["verdict"] == "SUCCESS" and rec["verdict_reproduced"] and not rec["findings"]
    assert rec["endpoints"]["cost_ratio"] == cmp3["cost_ratio"]
    assert rec["endpoints"]["quality_ratio"] == cmp3["quality_ratio"]
    assert cmp3["fixed_work_parity"]["exact"] and cmp3["fixed_work_parity"]["mismatch_count"] == 0
    assert _load(T3 + "CONFIRMATION_FREEZE.json")["sources"]["research/third_round_candidate.py"] == \
        hashlib.sha256((ROOT / "research/third_round_candidate.py").read_bytes()).hexdigest()

    P3 = "plan/phase2_third_round/PROTOCOL.json"
    PR2 = "plan/phase2_next_round/PROTOCOL.json"
    for i, tag in enumerate("ABC"):
        L.ptr(f"b{tag}", P3, ["wall_budgets_seconds", i], "str", claim="wall-clock optimisation allowance (s)")
    L.ptr("sliceMs", P3, ["wall_limits", "slice_seconds"], "int", transform="ms")
    L.ptr("sliceNodes", P3, ["wall_limits", "slice_nodes"], "int")
    L.ptr("resident", P3, ["wall_limits", "resident_queries"], "int")
    L.ptr("lvThree", P3, ["statistics", "percentiles", 0], "f1", transform="level")
    L.ptr("lvTwo", PR2, ["statistics", "new_candidate_four_endpoints_percentiles", 0], "f2", transform="level")
    L.ptr("lvOne", PR2, ["statistics", "learning_three_contrasts_percentiles", 0], "f2", transform="level")
    L.ptr("lvStd", PR2, ["statistics", "primary_head_to_head_percentiles", 0], "int", transform="level")
    c = "C1/R0, 200 fresh programs"
    L.ptr("tCost", T3 + "COMPARISON.json", ["cost_ratio"], "f3", claim=c + ", fixed work, compile-call time")
    L.ptr("tCostLo", T3 + "COMPARISON.json", ["intervals_97_5", "cost", 0], "f3", claim="97.5% lower bound")
    L.ptr("tCostHi", T3 + "COMPARISON.json", ["intervals_97_5", "cost", 1], "f3", claim="97.5% upper bound")
    L.ptr("tQual", T3 + "COMPARISON.json", ["quality_ratio"], "f3", claim=c + ", J ratio at 0.1 s")
    L.ptr("tQualLo", T3 + "COMPARISON.json", ["intervals_97_5", "quality", 0], "f3")
    L.ptr("tQualHi", T3 + "COMPARISON.json", ["intervals_97_5", "quality", 1], "f3")
    L.ptr("tCostFour", T3 + "COMPARISON.json", ["cost_ratio"], "f4")
    L.ptr("tCostLoFour", T3 + "COMPARISON.json", ["intervals_97_5", "cost", 0], "f4")
    L.ptr("tCostHiFour", T3 + "COMPARISON.json", ["intervals_97_5", "cost", 1], "f4")
    L.ptr("tQualFour", T3 + "COMPARISON.json", ["quality_ratio"], "f4")
    L.ptr("tQualLoFour", T3 + "COMPARISON.json", ["intervals_97_5", "quality", 0], "f4")
    L.ptr("tQualHiFour", T3 + "COMPARISON.json", ["intervals_97_5", "quality", 1], "f4")
    L.ptr("tGateCost", T3 + "COMPARISON.json", ["gate", "fixed_work_compile_ratio_upper_max"], "f2")
    L.ptr("tGateQual", T3 + "COMPARISON.json", ["gate", "wall_primary_J_ratio_upper_max"], "f2")
    L.ptr("tResamples", T3 + "COMPARISON.json", ["intervals_97_5", "resamples"], "int")
    L.ptr("tSeed", T3 + "COMPARISON.json", ["intervals_97_5", "seed"], "str")
    L.ptr("tPctLo", T3 + "COMPARISON.json", ["intervals_97_5", "percentiles", 0], "pct2")
    L.ptr("tPctHi", T3 + "COMPARISON.json", ["intervals_97_5", "percentiles", 1], "pct2")
    L.ptr("tPrograms", T3 + "COMPARISON.json", ["programs"], "int")
    L.ptr("tPerFamily", REV + "RECOMPUTE.json", ["checks", "family_sizes", "vector"], "int")
    assert set(rec["checks"]["family_sizes"].values()) == {40} and len(rec["checks"]["family_sizes"]) == 5
    L.computed("tFamilies", len(rec["checks"]["family_sizes"]), "int", REV + "RECOMPUTE.json",
                   "len(checks.family_sizes)")
    L.ptr("tSeedLo", REV + "RECOMPUTE.json", ["checks", "cohort", "seeds", 0], "str")
    L.ptr("tSeedHi", REV + "RECOMPUTE.json", ["checks", "cohort", "seeds", 1], "str")
    L.ptr("tNodes", "plan/phase2_third_round/PROTOCOL.json", ["fixed_work", "aggregate_nodes"], "int",
          claim="fixed-work node limit")
    L.ptr("tParityPairs", T3 + "COMPARISON.json", ["fixed_work_parity", "pairs"], "int")
    L.ptr("tParityMismatch", T3 + "COMPARISON.json", ["fixed_work_parity", "mismatch_count"], "int")
    L.derived("tSubstantive", "substantive_pairs", "int", claim="fixed-work pairs with at least one search node")
    L.derived("tZeroNode", "zero_node_programs", "int", claim="fresh programs needing no search node")
    L.derived("tReps", "reps_per_program", "int")
    L.derived("tCertMedian", "certificate_median", "int", claim="median certificates per fixed-work run")
    L.derived("tTraces", "distinct_traces", "int", claim="distinct search traces over the fixed-work rows")
    for budget, tag in (("0.01", "A"), ("0.1", "B"), ("1.0", "C")):
        w, t, l = cmp3["descriptive"][f"wall:{budget}_W_T_L_C1"]
        assert w + t + l == 1000
        for i, name in enumerate(("W", "T", "L")):
            L.ptr(f"tWTL{tag}{name}", T3 + "COMPARISON.json", ["descriptive", f"wall:{budget}_W_T_L_C1", i], "int")
        L.ptr(f"tJr{tag}", T3 + "COMPARISON.json", ["descriptive", f"wall:{budget}_J_ratio_geo"], "f3")
        L.ptr(f"tWallTime{tag}", REV + "RECOMPUTE.json", ["probes", f"wall:{budget}_compile_call_time_geo_ratio"], "f3")
        L.ptr(f"tLossUnknown{tag}", REV + "RECOMPUTE.json", ["probes", f"wall:{budget}_losses_with_unknown_queries"], "int")
    for i, name in enumerate(("Better", "Equal", "Worse")):
        L.ptr(f"tProg{name}", REV + "RECOMPUTE.json", ["probes", "quality_programs_better_equal_worse", i], "int")
    L.derived("tLossRuns", "wall_losses", "int", mode="wall:1.0", what="runs")
    L.derived("tLossPrograms", "wall_losses", "int", mode="wall:1.0", what="programs")
    L.derived("tLossNoUnknown", "wall_losses", "int", mode="wall:1.0", what="no_unknown")
    assert L.entries["tLossRuns"]["raw"] == cmp3["descriptive"]["wall:1.0_W_T_L_C1"][2]
    assert L.entries["tLossRuns"]["raw"] - L.entries["tLossUnknownC"]["raw"] == L.entries["tLossNoUnknown"]["raw"]
    for seed in (980183, 980026):
        for arm in ("R0", "C1"):
            for field in ("J", "cycles", "scratch", "nodes"):
                if field == "nodes":
                    continue
                L.derived(f"tSeed{seed}{arm}{field}", "wall_seed", "int", seed=seed, arm=arm, field=field)
    L.ptr("tImport", REV + "RECOMPUTE.json", ["probes", "cost_including_import"], "f3")
    L.ptr("tProcess", REV + "RECOMPUTE.json", ["probes", "process_seconds_ratio"], "f3")
    for arm in ("R0", "C1"):
        L.ptr(f"tOrder{arm}", REV + "RECOMPUTE.json", ["probes", "arm_order", arm, "geo_ratio"], "f3")
        L.ptr(f"tOrder{arm}Pairs", REV + "RECOMPUTE.json", ["probes", "arm_order", arm, "pairs"], "int")
    for i in range(4):
        L.ptr(f"tDrift{'ABCD'[i]}", REV + "RECOMPUTE.json", ["probes", "drift_by_time_quartile", i], "f3")
    for key in ("min", "q10", "median", "q90", "max"):
        L.ptr(f"tPP{key}", REV + "RECOMPUTE.json", ["probes", "per_program_cost_ratio", key], "f3")
    L.ptr("tPPslower", REV + "RECOMPUTE.json", ["probes", "per_program_cost_ratio", "programs_C1_slower"], "int")
    for i, tag in enumerate("ABC"):
        L.ptr(f"tTer{tag}", REV + "RECOMPUTE.json", ["probes", "cost_by_nodes_tercile", i, "geo_ratio"], "f3")
        L.derived(f"tTer{tag}lo", "tercile", "int", index=i, field="lo")
        L.derived(f"tTer{tag}hi", "tercile", "int", index=i, field="hi")
    L.ptr("tTerAms", REV + "RECOMPUTE.json", ["probes", "cost_by_nodes_tercile", 0, "R0_median_s"], "f1", transform="ms")
    L.ptr("tTerBs", REV + "RECOMPUTE.json", ["probes", "cost_by_nodes_tercile", 1, "R0_median_s"], "f2")
    L.ptr("tTerCs", REV + "RECOMPUTE.json", ["probes", "cost_by_nodes_tercile", 2, "R0_median_s"], "f2")
    L.ptr("tSummed", REV + "RECOMPUTE.json", ["probes", "summed_median_seconds", "ratio"], "f3")
    for i, s in enumerate((1, 2, 3)):
        L.ptr(f"tAltSeed{'ABC'[i]}CostHi", REV + "RECOMPUTE.json",
              ["endpoints", "intervals_97_5_independent_draw_order", str(s), "cost", 1], "f3")
    for arm in ("C1", "R0"):
        for budget, tag in (("0.01", "A"), ("0.1", "B"), ("1.0", "C")):
            L.ptr(f"tPub{arm}{tag}", T3 + "COMPARISON.json", ["descriptive", "public_scores", f"{arm}@wall:{budget}", 0], "f3")
            L.ptr(f"tPubSix{arm}{tag}", T3 + "COMPARISON.json", ["descriptive", "public_scores", f"{arm}@wall:{budget}", 0], "f6")
    for arm in ("C1", "R0"):
        L.ptr(f"tFixedMed{arm}", T3 + "COMPARISON.json", ["descriptive", f"fixed_work_{arm}", "median"], "f3")
        L.ptr(f"tFixedPct{arm}", T3 + "COMPARISON.json", ["descriptive", f"fixed_work_{arm}", "p95"], "f2")

    dev = _load(T3 + "DEVELOPMENT.json")
    assert dev["verdict"] == "PASS" and dev["gate_met"] and dev["memory_fingerprints_equal"]
    L.ptr("tMemMed", T3 + "DEVELOPMENT.json", ["memory_peak_ratio_median"], "f3")
    L.ptr("tMemMax", T3 + "DEVELOPMENT.json", ["memory_peak_ratio_max"], "f3")
    L.derived("tMemPrograms", "d_memory_programs", "int")
    L.computed("tDevPrograms", len(dev["programs"]), "int", T3 + "DEVELOPMENT.json", "len(programs)")
    L.ptr("tDevParity", T3 + "DEVELOPMENT.json", ["fixed_work_parity", "pairs"], "int")
    L.ptr("tDevCost", T3 + "DEVELOPMENT.json", ["fixed_work_compile_ratio_equal_family"], "f3")
    L.ptr("tDevGate", T3 + "DEVELOPMENT.json", ["gate", "fixed_work_compile_ratio_max"], "f2")
    L.ptr("tDevLogJ", T3 + "DEVELOPMENT.json", ["wall_primary_mean_log_J_ratio_equal_family"], "neg4")
    for i, n in enumerate("WTL"):
        L.ptr(f"tDevWTL{n}", T3 + "DEVELOPMENT.json", ["wall_J_wins_ties_losses_C1", i], "int")
    L.ptr("tDevNodesC", T3 + "DEVELOPMENT.json", ["wall_nodes_median", "C1"], "int")
    L.ptr("tDevNodesR", T3 + "DEVELOPMENT.json", ["wall_nodes_median", "R0"], "f1")

    L.derived("tAccPrograms", "acceptance", "int", what="programs")
    L.derived("tAccCases", "acceptance", "int", what="cases")
    L.ptr("tExportRows", T3 + "COMPARISON.json", ["stages", "C_export", "observed"], "int")
    L.ptr("tExportValid", REV + "RECOMPUTE.json", ["checks", "export_revalidated", "valid"], "int")
    assert rec["checks"]["export_revalidated"]["bad"] == []
    L.ptr("tRawStdout", REV + "RECOMPUTE.json", ["checks", "raw_stdout", "checked"], "int")
    L.ptr("tAuditC", T3 + "checks/AUDIT_C.json", ["total_checks"], "int")
    L.ptr("tAuditM", T3 + "checks/AUDIT_M_final.json", ["total_checks"], "int")
    both = _load(REV + "D_AUDIT_BOTH.json")
    assert both["frozen"]["total_checks"] == both["current"]["total_checks"]
    assert both["frozen"]["findings"] == both["current"]["findings"] == [["D_FREEZE", "research/third_round_resume_audit.py"]]
    L.ptr("tAuditD", REV + "D_AUDIT_BOTH.json", ["frozen", "total_checks"], "int")
    L.derived("tPytest", "log_count", "int", source=REV + "PYTEST.log", pattern=r"^(\d+) passed")
    L.derived("tInherited", "log_count", "int", source=REV + "INHERITED.log", pattern=r"^Ran (\d+) tests")

    # Evidence classes (a)-(c): historical, forecast, kernel-only.
    md = _load(PHASE2 + "third_round_20260925/MECHANISM_DECISION.json")
    assert md["decision"] == "NO_JUSTIFIED_MECHANISM"
    L.ptr("tMReg", PHASE2 + "third_round_20260925/MECHANISM_DECISION.json", ["gate", "registered_conservative_ratio"], "f4",
          claim="historical registered M result (scope-defective)")
    L.ptr("tMGate", PHASE2 + "third_round_20260925/MECHANISM_DECISION.json", ["gate", "conservative_ratio_max"], "f2")
    rp = _load(T3 + "RECALIBRATED_PREDICTION.json")
    assert rp["gate_met"] and rp["original_registered_conservative"] == md["gate"]["registered_conservative_ratio"]
    assert rp["kernel_speedup_median"] == _load(T3 + "REPAIR_CLOSURE.json")["R3_speedup_median"]["corrected"]
    L.ptr("tMCons", T3 + "RECALIBRATED_PREDICTION.json", ["corrected_conservative"], "f4", claim="post-hoc forecast, not a measurement")
    L.ptr("tMPoint", T3 + "RECALIBRATED_PREDICTION.json", ["corrected_point"], "f4", claim="post-hoc forecast, not a measurement")
    L.ptr("tKernelMed", T3 + "RECALIBRATED_PREDICTION.json", ["kernel_speedup_median"], "f4", claim="kernel-only replay, not a compiler speed-up")
    L.ptr("tKernelMin", T3 + "RECALIBRATED_PREDICTION.json", ["kernel_speedup_range", 0], "f3")
    L.ptr("tKernelMax", T3 + "RECALIBRATED_PREDICTION.json", ["kernel_speedup_range", 1], "f3")
    for fam in ("scalar", "vector", "mixed", "dependency", "aliasing"):
        L.ptr(f"tMFam{fam}", T3 + "RECALIBRATED_PREDICTION.json", ["family_corrected_conservative", fam], "f3")
        L.ptr(f"tCFam{fam}", T3 + "COMPARISON.json", ["family", fam, "cost_ratio"], "f3")
        L.ptr(f"tQFam{fam}", T3 + "COMPARISON.json", ["family", fam, "quality_ratio"], "f3")
    L.ptr("tMOldAdapter", T3 + "RECALIBRATED_PREDICTION.json", ["corrected_scope_old_adapter_conservative"], "f4")
    L.ptr("tMReplayOnly", T3 + "RECALIBRATED_PREDICTION.json", ["replay_only_sensitivity_conservative"], "f4")
    L.ptr("tMWorkloads", REV + "RECOMPUTE_M.json", ["programs"], "int")
    L.ptr("tAdapterRows", REV + "RECOMPUTE_M.json", ["adapter_rows"], "int")

    # Round 1: the objective-index ladder.
    r1 = _load(R1 + "COMPARISON.json")
    assert r1["primary"]["claim_best_average_quality"]
    for ctrl, tag in (("A0_frozen_phase2", "Azero"), ("accepted_budgeted", "Acc"), ("classical", "Cl")):
        base = ["primary", "contrasts", ctrl]
        assert r1["primary"]["contrasts"][ctrl]["percentiles"][0] == 1 / 120
        L.ptr(f"rOne{tag}Red", R1 + "COMPARISON.json", base + ["geometric_J_ratio_control_over_candidate"], "pct2",
              transform="pct_from_ratio", claim=f"A4 vs {ctrl}: geometric J reduction, 200 fresh programs, 0.1 s")
        L.ptr(f"rOne{tag}Lo", R1 + "COMPARISON.json", base + ["interval", 0], "pct2", transform="pct_from_log")
        L.ptr(f"rOne{tag}Hi", R1 + "COMPARISON.json", base + ["interval", 1], "pct2", transform="pct_from_log")
        for n in ("wins", "ties", "losses"):
            L.ptr(f"rOne{tag}{n}", R1 + "COMPARISON.json", base + [n], "int")
        rt = ["runtime_primary_bonferroni", f"{ctrl}:compile_seconds"]
        L.ptr(f"rOne{tag}Time", R1 + "COMPARISON.json", rt + ["geometric_ratio_candidate_over_control"], "f2")
        L.ptr(f"rOne{tag}TimeLo", R1 + "COMPARISON.json", rt + ["interval_ratio", 0], "f2")
        L.ptr(f"rOne{tag}TimeHi", R1 + "COMPARISON.json", rt + ["interval_ratio", 1], "f2")
    L.ptr("rOneAccTimeThree", R1 + "COMPARISON.json", ["runtime_primary_bonferroni", "accepted_budgeted:compile_seconds", "geometric_ratio_candidate_over_control"], "f3")
    L.ptr("rOneBonf", R1 + "COMPARISON.json", ["primary", "contrasts", "classical", "percentiles", 1], "pct2")
    ladder = [s for s in r1["ladder_unadjusted_95"] if s["budget"] == 0.1]
    assert [s["step"] for s in ladder] == ["A0_frozen_phase2->A1_deadline_control", "A1_deadline_control->A2_product_search",
                                          "A2_product_search->A3_propagated_search", "A3_propagated_search->A4_multiscale_search"]
    for i, tag in enumerate(("One", "Two", "Three", "Four")):
        idx = r1["ladder_unadjusted_95"].index(ladder[i])
        base = ["ladder_unadjusted_95", idx]
        L.ptr(f"lad{tag}Q", R1 + "COMPARISON.json", base + ["quality", "point"], "sgn4")
        L.ptr(f"lad{tag}Lo", R1 + "COMPARISON.json", base + ["quality", "interval", 0], "sgn4")
        L.ptr(f"lad{tag}Hi", R1 + "COMPARISON.json", base + ["quality", "interval", 1], "sgn4")
        for n in ("wins", "ties", "losses"):
            L.ptr(f"lad{tag}{n}", R1 + "COMPARISON.json", base + ["quality", n], "int")
        L.ptr(f"lad{tag}T", R1 + "COMPARISON.json", base + ["compile", "geometric_ratio_candidate_over_control"], "f2")
    L.ptr("rOneDevEffect", R1 + "DEVELOPMENT.json", ["selection", "best_effect"], "sgn4")
    pub1 = ["score", "scores", "arms"]
    L.ptr("rOnePubAfour", R1 + "PUBLIC_SCORE.json", pub1 + ["A4_multiscale_search@0.1", "geometric_mean"], "f6")
    L.ptr("rOnePubAzero", R1 + "PUBLIC_SCORE.json", pub1 + ["A0_frozen_phase2@0.1", "geometric_mean"], "f6")
    learning = _load(R1 + "LEARNING.json")
    assert learning["H_LEARN"]["verdict"] == "FAIL" and learning["end_to_end_learning_hypothesis"] == "BLOCKED_BY_H_LEARN"
    L.ptr("rOneLearnZero", R1 + "LEARNING.json", ["design_diagnostic", "evaluation_fixtures_with_a_test_object_below_training_minimum"], "int")
    L.ptr("rOneLearnOf", R1 + "LEARNING.json", ["design_diagnostic", "of"], "int")

    # Round 2: repair, comparison with cap512_wider, factorial, learning gates.
    r2 = _load(R2 + "COMPARISON.json")
    assert r2["primary"]["verdict"] == "FAVOURS_A4" and r2["candidate_endpoints"]["verdict"] == "TARGET_NOT_REACHED"
    L.ptr("rTwoLog", R2 + "COMPARISON.json", ["primary", "estimate"], "sgn4")
    L.ptr("rTwoLo", R2 + "COMPARISON.json", ["primary", "interval_95", 0], "sgn4")
    L.ptr("rTwoHi", R2 + "COMPARISON.json", ["primary", "interval_95", 1], "sgn4")
    L.ptr("rTwoJ", R2 + "COMPARISON.json", ["primary", "estimate"], "f3", transform="ratio_from_log")
    for i, n in enumerate(("W", "T", "L")):
        L.ptr(f"rTwoWTL{n}", R2 + "COMPARISON.json", ["primary", "wins_ties_losses_for_A4", i], "int")
    L.ptr("rTwoTime", R2 + "COMPARISON.json", ["primary", "compile_ratio_A4_over_earlier_geometric"], "f3")
    for ctrl, tag in (("earlier_cap512_wider", "E"), ("cell_a4cat_heap", "H")):
        base = ["candidate_endpoints", ctrl]
        L.ptr(f"rTwoDfs{tag}J", R2 + "COMPARISON.json", base + ["J_ratio"], "f3")
        L.ptr(f"rTwoDfs{tag}Lo", R2 + "COMPARISON.json", base + ["J_ratio_interval_98_75", 0], "f3")
        L.ptr(f"rTwoDfs{tag}Hi", R2 + "COMPARISON.json", base + ["J_ratio_interval_98_75", 1], "f4")
        L.ptr(f"rTwoDfs{tag}T", R2 + "COMPARISON.json", base + ["compile_ratio"], "f3")
        for i, n in enumerate(("W", "T", "L")):
            L.ptr(f"rTwoDfs{tag}n{n}", R2 + "COMPARISON.json", base + ["wins_ties_losses", i], "int")
    proto2 = "plan/phase2_next_round/PROTOCOL.json"
    L.ptr("rTwoQRoute", proto2, ["practical_targets", "quality_route", "upper_J_ratio"], "f2")
    L.ptr("rTwoERoute", proto2, ["practical_targets", "efficiency_route", "upper_compile_ratio"], "f2")
    dcl = ["descriptive_unadjusted_95", "log(J_classical/J_cell_a4cat_dfs@0.1)"]
    L.ptr("rTwoDfsClLog", R2 + "COMPARISON.json", dcl + ["estimate"], "f3")
    L.ptr("rTwoDfsClRed", R2 + "COMPARISON.json", dcl + ["estimate"], "pct1", transform="pct_from_log")
    for i, n in enumerate(("W", "T", "L")):
        L.ptr(f"rTwoDfsCl{n}", R2 + "COMPARISON.json", dcl + ["wins_ties_losses_for_arm", i], "int")
    fac = ["budgets", "0.1", "factorial"]
    for key, tag in (("catalog_effect_a4_minus_a3", "Cat"), ("traversal_effect_heap_minus_dfs", "Trav"), ("interaction", "Int")):
        L.ptr(f"fac{tag}", R2 + "FACTORIAL.json", fac + [key, "estimate"], "sgn4")
        L.ptr(f"fac{tag}Lo", R2 + "FACTORIAL.json", fac + [key, "interval_95", 0], "sgn4")
        L.ptr(f"fac{tag}Hi", R2 + "FACTORIAL.json", fac + [key, "interval_95", 1], "sgn4")
    L.ptr("facPrograms", R2 + "FACTORIAL.json", fac + ["programs"], "int")
    eng = _load(R2 + "ENGINEERING_DECISION.json")
    assert "NOT frozen" in eng["reason"]
    L.ptr("rTwoWorklist", R2 + "ENGINEERING_DECISION.json", ["decision_by_budget", "0.1", "compile_time_reduction"], "pct1")
    L.computed("rTwoWorklistGate", float(re.search(r"< (0\.\d+)", eng["reason"]).group(1)), "pct1",
               R2 + "ENGINEERING_DECISION.json", "reason: gate threshold")
    lf = _load(R2 + "LEARNING_FEASIBILITY.json")
    assert lf["contrasts"]["mechanism_signal"] == "FAIL_OR_INCONCLUSIVE" and lf["economics"]["verdict"] == "ECONOMICALLY_UNAVAILABLE"
    L.ptr("lrnHamNeg", R2 + "LEARNING_FEASIBILITY.json", ["contrasts", "tree_minus_hamming", "negative"], "int")
    L.ptr("lrnFixtures", R2 + "LEARNING_FEASIBILITY.json", ["evaluation_design", "informative"], "int")
    L.ptr("lrnHam", R2 + "LEARNING_FEASIBILITY.json", ["contrasts", "tree_minus_hamming", "estimate"], "neg3")
    L.ptr("lrnShuf", R2 + "LEARNING_FEASIBILITY.json", ["contrasts", "tree_minus_shuffled_tree", "estimate"], "f3")
    L.ptr("lrnRand", R2 + "LEARNING_FEASIBILITY.json", ["contrasts", "tree_minus_random_mean", "estimate"], "f3")
    L.ptr("lrnEcoZero", R2 + "LEARNING_FEASIBILITY.json", ["economics", "programs_with_a_query_reaching_20_validated"], "int")
    L.ptr("lrnEcoPrograms", R2 + "LEARNING_FEASIBILITY.json", ["economics", "programs"], "int")
    L.ptr("lrnBoundary", R2 + "LEARNING_FEASIBILITY.json", ["economics", "queries_reaching_boundary"], "int")
    L.ptr("lrnQueries", R2 + "LEARNING_FEASIBILITY.json", ["economics", "queries_with_learner"], "int")
    pub2 = ["scores", "arms"]
    for arm, tag in (("cell_a4cat_dfs@0.1", "Dfs"), ("earlier_cap512_wider@0.1", "Cap"), ("cell_a4cat_heap@0.1", "Heap"),
                     ("classical@None", "Classical"), ("accepted_bootstrap@None", "Direct")):
        L.ptr(f"rTwoPub{tag}", R2 + "PUBLIC_SCORE.json", pub2 + [arm, "min"], "f6")
        assert _walk(_load(R2 + "PUBLIC_SCORE.json"), pub2 + [arm, "min"]) == _walk(_load(R2 + "PUBLIC_SCORE.json"), pub2 + [arm, "max"])

    # Efficiency round: Gate P.
    mp = _load(EFF + "MECHANISM_PROPOSAL.json")
    assert mp["gate"]["decision"] == "NO_JUSTIFIED_OPTIMIZATION"
    L.ptr("effPred", EFF + "MECHANISM_PROPOSAL.json", ["prediction", "fixed_work_compile_ratio_equal_family_predicted"], "f3")
    L.ptr("effCeil", EFF + "MECHANISM_PROPOSAL.json", ["prediction", "zero_cost_ceiling_if_the_scan_vanished"], "f3")

    # Phase 2 structural encoding (A0) against the accepted optimiser and classical.
    r3 = _load(A0RUN + "COMPARISON.json")
    entries = r3["entries"]
    for ctrl, tag in (("accepted_budgeted", "Acc"), ("classical", "Cl")):
        idx = next(i for i, e in enumerate(entries) if e["budget_seconds"] == 0.1 and e["corpus"] == "heldout" and e["control"] == ctrl)
        base = ["entries", idx]
        L.ptr(f"aZero{tag}Log", A0RUN + "COMPARISON.json", base + ["quality_log_control_over_candidate", "point_estimate"], "f4")
        L.ptr(f"aZero{tag}Lo", A0RUN + "COMPARISON.json", base + ["quality_log_control_over_candidate", "intervals", "0.025-0.975", 0], "f4")
        L.ptr(f"aZero{tag}Hi", A0RUN + "COMPARISON.json", base + ["quality_log_control_over_candidate", "intervals", "0.025-0.975", 1], "f4")
        L.ptr(f"aZero{tag}Red", A0RUN + "COMPARISON.json", base + ["quality_log_control_over_candidate", "point_estimate"], "pct1", transform="pct_from_log")
        for n in ("wins", "ties", "losses"):
            L.ptr(f"aZero{tag}{n}", A0RUN + "COMPARISON.json", base + [n], "int")
        L.ptr(f"aZero{tag}Time", A0RUN + "COMPARISON.json", base + ["compile_candidate_over_control_ratio"], "f3")
        L.ptr(f"aZero{tag}N", A0RUN + "COMPARISON.json", base + ["n_programs"], "int")
    P1S = RUN_REL + "/p1/summary.json"
    L.computed("feFixtures", len(_load(P1S)["fixtures"]), "int", P1S, "len(fixtures)")
    L.ptr("feExhausted", P1S, ["exhausted_comparisons"], "int")
    L.derived("feRoundTrips", "p1_round_trips", "int")
    L.ptr("feAttempts", P1S, ["sampling_attempts_drawn"], "int")
    L.ptr("feStreams", P1S, ["stream_count"], "int")
    L.ptr("feCompletions", P1S, ["sampling_completions"], "int")
    L.ptr("feCaseChecks", P1S, ["sampling_case_checks"], "int")
    L.ptr("feDiscrepancies", P1S, ["sampling_discrepancy_count"], "int")
    L.ptr("feMinimum", P1S, ["coverage_minimum"], "int")
    L.computed("feBelow", sum(1 for r in _load(P1S)["public_coverage"] if not r["meets_minimum"]), "int",
               P1S, "count(public_coverage[].meets_minimum == false)")
    L.ptr("aZeroPub", PHASE2 + "lead_release_review_20260924/PUBLIC_SCORE_RECOUNT.json", ["arms", "structural_bound", "scores", 0], "f6")
    return L
