"""Successor checker and numerical auditor of the third round (resume plan section 4).

Independent of the reporters (``third_round_analysis``, ``third_round_resume_analysis``):
own medians, own geometric means, expected membership derived from the protocol
and the program generator. File bytes are read directly; JSONL is parsed with a
strict parser of this module (every line one complete finite JSON object; a
trailing fragment, blank or malformed line fails).

Checks, each recorded with its denominator:

- STRICT: every rows / ATTEMPTS / ledger file of both runs.
- MEMBERSHIP: M_diagnosis (210), M_kernel (180), R_adapter (90) keys from
  protocol x generator; rows, frozen EXPECTED_KEYS, finished attempts (exit 0,
  no timeout, stdout hash reproduced) and ledger charges reconcile one-to-one.
- SOURCES: every hash recorded at a freeze equals the current bytes, except the
  single approved disposition (third_round_common.py, exact reconstruction);
  the spec-era kernel hash is the exact 17,377-byte prefix; transitive imports of
  every measured worker are unchanged since the parent's starting manifest.
- WORKLOADS: gz bytes vs WORKLOAD_MANIFEST vs M0 rows; event counts.
- M0/M2 PREREQUISITES: plain/timer/trace fingerprints equal per program; the
  instrumentation parity recomputed; kernel parity recomputed from its parts
  (0 output / emission mismatches, lengths equal, stream equal, event counts).
- REPLAY (optional, ``replay=True``): baseline replay of every workload
  reproduces outputs, emissions and certificate stream.
- STAGES: every protocol stage has an explicit state; NOT_RUN files exist and
  agree with decisions and with the stage directories present.
- NUMBERS: original / corrected / recalibrated M arithmetic recomputed and
  compared field by field with the reporter's file; every leaf of that file is
  either checked or declared unchecked (field map); unmapped leaves fail.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
PARENT_PROTOCOL = json.loads((ROOT / "plan/phase2_third_round/PROTOCOL.json").read_text())
RESUME_PROTOCOL = json.loads((ROOT / "plan/phase2_third_round_resume/PROTOCOL.json").read_text())
KEY = ("stage_id", "program_sha256", "repetition", "arm_id", "mode_key")
BASE_FIELDS = KEY + ("seed", "process_seconds", "exit_code", "timed_out")
REL = 1e-12


class Report:
    def __init__(self) -> None:
        self.checks: Dict[str, int] = {}
        self.findings: List[list] = []

    def check(self, area: str, ok: bool, *detail) -> bool:
        self.checks[area] = self.checks.get(area, 0) + 1
        if not ok:
            self.findings.append([area, *detail])
        return ok

    def result(self) -> dict:
        total = sum(self.checks.values())
        return {"checks": self.checks, "total_checks": total, "findings": self.findings,
                "status": "PASS" if total and not self.findings else "FAIL"}


# --------------------------------------------------------------------------
# Primitives (own implementations)
# --------------------------------------------------------------------------


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict(path: Path, rep: Report, area: str = "STRICT") -> List[dict]:
    path = Path(path)
    if not path.exists():
        rep.check(area, False, str(path), "missing file")
        return []
    data = path.read_bytes()
    rows: List[dict] = []
    if not rep.check(area, not data or data.endswith(b"\n"), str(path), "trailing fragment"):
        return rows
    for n, line in enumerate(data.decode("utf-8").split("\n")[:-1]):
        try:
            row = json.loads(line, parse_constant=lambda c: float("nan"))
        except json.JSONDecodeError:
            rep.check(area, False, str(path), n + 1, "malformed line")
            continue
        ok = isinstance(row, dict) and _finite(row)
        if rep.check(area, ok, str(path), n + 1, "not a finite object"):
            rows.append(row)
    return rows


def _finite(v) -> bool:
    if isinstance(v, float):
        return math.isfinite(v)
    if isinstance(v, dict):
        return all(_finite(x) for x in v.values())
    if isinstance(v, list):
        return all(_finite(x) for x in v)
    return True


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        raise ValueError("median of nothing")
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def family_geo(values: Dict[int, float], families) -> float:
    groups: Dict[int, List[float]] = {}
    for seed, v in values.items():
        groups.setdefault(seed % 5, []).append(math.log(v))
    if len(groups) != len(families):
        raise ValueError("families missing")
    return math.exp(sum(sum(g) / len(g) for g in groups.values()) / len(groups))


def close(a, b) -> bool:
    return abs(a - b) <= REL * max(1.0, abs(a), abs(b))


def key_of(r) -> str:
    return "|".join(str(r[k]) for k in KEY)


# --------------------------------------------------------------------------
# Expected membership from protocol and generator
# --------------------------------------------------------------------------


def expected_keys() -> Dict[str, List[tuple]]:
    sys.path[:0] = [str(ROOT / ".reference"), str(ROOT)]
    from tests_direct import generate_programs as gp
    d = PARENT_PROTOCOL["diagnostic"]
    seeds = range(d["first_seed"], d["last_seed"] + 1)
    digests = {s: gp.program_digest(gp.additional_program(s)) for s in seeds}
    m0, mk, ad = [], [], []
    for s in seeds:
        for rep in range(d["time_repetitions"]):
            m0.append(("M_diagnosis", digests[s], rep, "R0", "work:10000", s))
        for mode in d["other_modes"]:
            m0.append(("M_diagnosis", digests[s], 0, "R0", mode, s))
        for rep in range(d["kernel_repetitions"]):
            for v in d["kernel_versions"]:
                mk.append(("M_kernel", digests[s], rep, v, "kernel", s))
    a = RESUME_PROTOCOL["adapter"]
    for s in range(a["first_seed"], a["last_seed"] + 1):
        for rep in range(a["repetition_base"], a["repetition_base"] + a["repetitions"]):
            ad.append((a["stage"], digests[s], rep, a["arm_id"], a["mode_key"], s))
    return {"M_diagnosis": m0, "M_kernel": mk, a["stage"]: ad}


def check_stage_rows(rep: Report, run: Path, stage: str, expected: List[tuple],
                     ledger: List[dict], raw_streams: bool) -> List[dict]:
    area = f"MEMBERSHIP:{stage}"
    exp = ["|".join(str(x) for x in k[:5]) for k in expected]
    seed_of = {"|".join(str(x) for x in k[:5]): k[5] for k in expected}
    rows = strict(run / "stages" / stage / "rows.jsonl", rep)
    attempts = strict(run / "stages" / stage / "ATTEMPTS.jsonl", rep)
    frozen_path = run / "stages" / stage / "EXPECTED_KEYS.json"
    rep.check(area, frozen_path.exists(), "EXPECTED_KEYS.json missing")
    if frozen_path.exists():
        frozen = json.loads(frozen_path.read_text())["keys"]
        rep.check(area, sorted(frozen) == sorted(exp), "frozen keys differ from protocol")
    keys = [key_of(r) for r in rows]
    rep.check(area, len(exp) == len(set(exp)) and len(exp) > 0, "expected keys", len(exp))
    rep.check(area, sorted(keys) == sorted(exp), "rows not one-to-one with protocol keys",
              len(keys), len(exp))
    finished = [a for a in attempts if "finished_utc" in a]
    started = [a for a in attempts if "started_utc" in a]
    rep.check(area, sorted(a["key"] for a in finished) == sorted(exp),
              "finished attempts not one-to-one")
    rep.check(area, sorted(a["key"] for a in started) == sorted(exp),
              "started attempts not one-to-one (hidden retry?)")
    by_attempt = {a["key"]: a for a in finished}
    charged: Dict[str, List[float]] = {}
    for c in ledger:
        if c["stage"] == stage:
            charged.setdefault(c["key"], []).append(float(c["process_seconds"]))
    for r in rows:
        k = key_of(r)
        a = by_attempt.get(k)
        rep.check(area, r.get("seed") == seed_of.get(k), k, "seed does not match generator")
        rep.check(area, not r.get("failed") and not r.get("timed_out") and r.get("exit_code") == 0,
                  k, "failed / timed out / nonzero exit")
        if not rep.check(area, a is not None, k, "no finished attempt"):
            continue
        rep.check(area, a["exit_code"] == 0 and not a["timed_out"], k, "attempt failed")
        rep.check(area, close(a["process_seconds"], r["process_seconds"]), k, "seconds differ")
        rep.check(area, charged.get(k) == [a["process_seconds"]], k, "ledger charge mismatch")
        if raw_streams:
            index = r.get("raw_index")
            out = run / "stages" / stage / "raw" / f"{index:05d}.stdout"
            err = run / "stages" / stage / "raw" / f"{index:05d}.stderr"
            ok = out.exists() and err.exists()
            if rep.check(area, ok, k, "raw stream files missing"):
                data = out.read_bytes()
                rep.check(area, sha(data) == a["stdout_sha256"] == r["stdout_sha256"], k,
                          "raw stdout hash")
                rep.check(area, sha(err.read_bytes()) == a["stderr_sha256"], k,
                          "raw stderr hash")
                if raw_streams == "cli":
                    _cli_payload(rep, area, k, r, data)
                else:
                    payload = json.loads(data)
                    rep.check(area, all(r.get(f) == v for f, v in payload.items()), k,
                              "row payload differs from raw stdout")
        else:
            payload = {f: v for f, v in r.items() if f not in BASE_FIELDS}
            text = json.dumps(payload, sort_keys=True) + "\n"
            rep.check(area, sha(text.encode()) == a["stdout_sha256"], k,
                      "reconstructed stdout hash (parent: no raw files kept)")
    return rows


# --------------------------------------------------------------------------
# The audit
# --------------------------------------------------------------------------


def transitive_sources(module: str) -> List[str]:
    code = (f"import sys; sys.argv=['x']; import {module}; "
            f"print('\\n'.join(sorted(m.__file__ for m in list(sys.modules.values()) "
            f"if getattr(m, '__file__', None))))")
    proc = subprocess.run([sys.executable, "-s", "-c", code], cwd=str(ROOT), text=True,
                          capture_output=True,
                          env={"PYTHONPATH": f"{ROOT / '.reference'}:{ROOT}", "PATH": "/usr/bin:/bin"})
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])
    out = []
    for line in proc.stdout.splitlines():
        p = Path(line).resolve()
        if p.is_relative_to(ROOT) and p.suffix == ".py":
            out.append(str(p.relative_to(ROOT)))
    return out


def audit(parent: Path, resume: Path, prediction_file: Path = None, replay: bool = False
          ) -> dict:
    rep = Report()
    parent, resume = Path(parent), Path(resume)
    exp = expected_keys()
    p_ledger = strict(parent / "MEASUREMENT_WALL_LEDGER.jsonl", rep)
    r_ledger = strict(resume / "MEASUREMENT_WALL_LEDGER.jsonl", rep)
    m0 = check_stage_rows(rep, parent, "M_diagnosis", exp["M_diagnosis"], p_ledger, False)
    mk = check_stage_rows(rep, parent, "M_kernel", exp["M_kernel"], p_ledger, False)
    ad = check_stage_rows(rep, resume, "R_adapter", exp["R_adapter"], r_ledger, True)
    # ledger: nothing charged twice, nothing outside known stages except the preflight
    known = {"M_diagnosis", "M_kernel", "M_preflight"}
    rep.check("LEDGER", all(c["stage"] in known for c in p_ledger), "unknown parent stage")
    rep.check("LEDGER", sum(1 for c in p_ledger if c["stage"] == "M_preflight") == 1,
              "preflight charges")
    hours = (sum(float(c["process_seconds"]) for c in p_ledger + r_ledger)) / 3600
    rep.check("LEDGER", hours < PARENT_PROTOCOL["measurement_wall_cap_hours"], "cap", hours)

    # sources
    manifest = json.loads((parent / "WORKLOAD_MANIFEST.json").read_text())
    disp = RESUME_PROTOCOL["narrow_source_dispositions"]
    for name, recorded in manifest["kernel_stage_sources"].items():
        current = (ROOT / name).read_bytes()
        if sha(current) == recorded:
            rep.check("SOURCES", True)
            continue
        allowed = [d for d in disp if d["file"] == name and d["before"] == recorded
                   and d["after"] == sha(current)]
        rebuilt = current.decode().replace(
            "from typing import Dict, Optional, Sequence, Tuple",
            "from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple")
        rep.check("SOURCES", bool(allowed) and sha(rebuilt.encode()) == recorded, name,
                  "measured source differs (no exact disposition)", recorded, sha(current))
    kernel = (ROOT / RESUME_PROTOCOL["preserved_mechanism"]["source"]).read_bytes()
    rep.check("SOURCES", sha(kernel) == RESUME_PROTOCOL["preserved_mechanism"]["sha256"],
              "kernel hash")
    spec = json.loads((parent / "MECHANISM_SPEC.json").read_text())
    rep.check("SOURCES", sha(kernel[:17377]) == spec["kernel_source_at_spec"]["sha256"],
              "spec-era kernel prefix")
    freeze = json.loads((resume / "ADAPTER_FREEZE.json").read_text())
    for name, recorded in freeze["sources"].items():
        rep.check("SOURCES", sha((ROOT / name).read_bytes()) == recorded, name,
                  "adapter-freeze source changed")
    rep.check("SOURCES", sha((resume / "ADAPTER_SPEC.json").read_bytes())
              == freeze["adapter_spec_sha256"], "adapter spec changed")
    start = json.loads((parent / "SOURCE_MANIFESTS/starting.json").read_text())
    lock = json.loads((ROOT / "plan/phase2_third_round/LOCK.json").read_text())
    known_hashes = {**lock["protected_inputs"], **start["research_sources"],
                    **start["production_sources"]}
    measured_modules = ("research.third_round_diagnosis", "research.third_round_mkernel",
                        "research.third_round_resume_adapter")
    for module in measured_modules:
        for name in transitive_sources(module):
            if name.startswith("research/third_round"):
                continue            # own modules: checked against their freezes above
            if name.startswith(".reference/"):
                continue            # protected inputs: checked by verify_package
            if name in known_hashes:
                rep.check("SOURCES", sha((ROOT / name).read_bytes()) == known_hashes[name],
                          module, name, "transitive dependency changed since parent start")
            else:
                rep.check("SOURCES:undeclared", False, module, name,
                          "transitive dependency not in the parent's starting manifest")

    # workloads
    traced = {r["seed"]: r for r in m0 if r["mode_key"] == "workload_trace"}
    rep.check("WORKLOADS", len(manifest["workloads"]) == 30, "workload count")
    for seed_text, item in manifest["workloads"].items():
        raw = gzip.decompress(Path(item["path"]).read_bytes())
        rep.check("WORKLOADS", sha(raw) == item["sha256"], seed_text, "bytes")
        t = traced.get(int(seed_text))
        rep.check("WORKLOADS", t is not None and t["workload_sha256"] == item["sha256"]
                  and t["events"] == item["events"], seed_text, "M0 row")
        n_events = len(json.loads(raw)["events"])
        rep.check("WORKLOADS", n_events == item["events"], seed_text, "event count")

    # M0 prerequisites
    by = {}
    for r in m0:
        by.setdefault((r["seed"], r["mode_key"]), []).append(r)
    for seed in range(PARENT_PROTOCOL["diagnostic"]["first_seed"],
                      PARENT_PROTOCOL["diagnostic"]["last_seed"] + 1):
        par = (by.get((seed, "instrumentation_parity")) or [None])[0]
        tim = (by.get((seed, "exclusive_timers")) or [None])[0]
        tra = (by.get((seed, "workload_trace")) or [None])[0]
        if not rep.check("M0", None not in (par, tim, tra), seed, "missing prerequisite rows"):
            continue
        plain = par["plain"]
        rep.check("M0", par.get("parity") is True and par.get("timers_equal_plain") is True
                  and par.get("trace_equal_plain") is True, seed, "instrumentation parity")
        rep.check("M0", tim["fingerprint"] == plain, seed, "timer fingerprint != plain")
        rep.check("M0", tra["fingerprint"] == plain, seed, "trace fingerprint != plain")
        rep.check("M0", tra["fingerprint"]["certificates"] == plain["certificates"], seed)
    # M2 prerequisites, recomputed from parts
    events = {int(s): i["events"] for s, i in manifest["workloads"].items()}
    for r in mk:
        p = r["parity"]
        ok = (p["output_mismatches"] == 0 and p["emitted_mismatches"] == 0
              and p["length_equal"] is True and p["certificate_stream_equal"] is True
              and p["events"] == events[r["seed"]] == r["events"])
        rep.check("M2", ok and p["parity"] is True, key_of(r), "kernel parity parts")
    for r in ad:
        rep.check("R_adapter", r["events"] == events[r["seed"]] and r["adapter_seconds"] > 0,
                  key_of(r), "adapter row")
    if replay:
        _replay_check(rep, manifest)

    # stage states
    _stage_states(rep, parent, resume)

    # numbers
    if prediction_file is not None:
        try:
            _numbers(rep, m0, mk, ad, json.loads(Path(prediction_file).read_text()))
        except (KeyError, IndexError, ValueError, ZeroDivisionError) as exc:
            rep.check("NUMBERS", False, "cannot recompute from the evidence", repr(exc))
    return rep.result()


def _replay_check(rep: Report, manifest: dict) -> None:
    from research import efficiency_search as es
    from research import third_round_kernel as tk
    from research import third_round_workload as tw
    for seed_text, item in manifest["workloads"].items():
        prep = tw.prepare(tw.load(Path(item["path"])))
        for name, fn in (("baseline", tw.replay_baseline), ("shared", tk.replay_shared)):
            stats = es.PropagationStats()
            out = fn(prep, stats)
            n = len(prep["events"])
            ok = (len(out["outputs"]) == n == len(out["emitted"])
                  and out["outputs"] == prep["outputs"] and out["emitted"] == prep["emitted"]
                  and stats.digest() == prep["certificate_stream_sha256"]
                  and stats.stream_length == prep["certificate_stream_length"])
            rep.check("REPLAY", ok, seed_text, name)


def _stage_states(rep: Report, parent: Path, resume: Path) -> None:
    stages = list(PARENT_PROTOCOL["stages"])
    not_run = parent / "NOT_RUN.json"
    if rep.check("STAGES", not_run.exists(), "parent NOT_RUN.json missing"):
        recorded = json.loads(not_run.read_text())["stages"]
        decision = json.loads((parent / "MECHANISM_DECISION.json").read_text())
        for stage in stages:
            if stage.startswith("M_"):
                rep.check("STAGES", (parent / "stages" / stage).is_dir(), stage, "M stage absent")
                continue
            rep.check("STAGES", stage in recorded and stage in decision["dependents"], stage,
                      "parent stage without explicit state")
            rep.check("STAGES", not (parent / "stages" / stage).exists(), stage,
                      "dependent stage launched in parent under a failing gate")
    states_path = resume / "STAGE_STATES.json"
    if not rep.check("STAGES", states_path.exists(), "resume STAGE_STATES.json missing"):
        return
    states = json.loads(states_path.read_text())["stages"]
    required = [RESUME_PROTOCOL["adapter"]["stage"]] + [
        s for s in stages if not s.startswith("M_")]
    for stage in required:
        state = states.get(stage)
        exists = (resume / "stages" / stage).exists()
        if not rep.check("STAGES", state is not None, stage, "no explicit resume state"):
            continue
        if state.startswith("NOT_RUN"):
            rep.check("STAGES", not exists, stage, "NOT_RUN but directory exists")
        else:
            rep.check("STAGES", exists, stage, f"{state} but no directory")
    # dependency matrix: C requires D pass; D requires the repaired M gate
    order = ["R_adapter", "D_fixed_work", "D_wall", "D_memory"]
    gate = json.loads(states_path.read_text()).get("gates", {})
    if gate.get("M_repaired") != "PASS":
        for s in order[1:]:
            rep.check("STAGES", str(states.get(s, "")).startswith("NOT_RUN"), s,
                      "D launched without a repaired M PASS")
    if gate.get("D") != "PASS":
        for s in [x for x in stages if x.startswith("C_")]:
            rep.check("STAGES", str(states.get(s, "")).startswith("NOT_RUN"), s,
                      "C launched without a D PASS")


FIELD_MAP_UNCHECKED = {
    "label": "free text", "gate_max": "protocol constant (checked in MEMBERSHIP via protocol)",
    "programs.*.family": "generator label", "programs.*.timer_inflation": "intermediate",
    "programs.*.adapter_repaired_runs": "raw values (checked via the median)",
}


def _numbers(rep: Report, m0, mk, ad, pred: dict) -> None:
    gate = RESUME_PROTOCOL["accounting"]["conservative_ratio_max"]
    mult = RESUME_PROTOCOL["accounting"]["overhead_multiplier"]
    matched = set(RESUME_PROTOCOL["accounting"]["matched_timer_components"])
    old_scope = matched - {"certificates", "propagation_setup", "address_pairs"}
    families = PARENT_PROTOCOL["families"]
    g = {}
    for r in m0 + mk + ad:
        g.setdefault((r["seed"], r["mode_key"], r["arm_id"]), []).append(r)
    mine: Dict[str, Dict[int, float]] = {k: {} for k in (
        "old", "corr_old_n", "corr", "replay_only", "point", "speed")}
    checked = set()
    for seed in range(800000, 800030):
        t0 = median([r["compile_call_seconds"] for r in g[(seed, "work:10000", "R0")]])
        tm = g[(seed, "exclusive_timers", "R0")][0]
        infl = tm["timed_call_wall_seconds"] / t0
        ex = tm["exclusive_seconds"]
        o_rep = median([r["replay_seconds"] for r in g[(seed, "kernel", "baseline_kernel")]])
        shared = g[(seed, "kernel", "shared_state_kernel")]
        nk = median([r["replay_seconds"] for r in shared])
        a_old = median([r["integration_estimate_seconds"] for r in shared])
        a_new = median([r["adapter_seconds"] for r in g[(seed, "adapter", "adapter")]])
        o_old = min(o_rep, sum(v for c, v in ex.items() if c in old_scope) / infl)
        o_m = min(o_rep, sum(v for c, v in ex.items() if c in matched) / infl)
        n = nk + max(a_old, a_new)
        rep.check("NUMBERS", 0 <= o_m <= t0, seed, "O outside [0,T0]")
        mine["old"][seed] = (t0 - o_old + mult * (nk + a_old)) / t0
        mine["corr_old_n"][seed] = (t0 - o_m + mult * (nk + a_old)) / t0
        mine["corr"][seed] = (t0 - o_m + mult * n) / t0
        mine["replay_only"][seed] = (t0 - o_rep + mult * n) / t0
        mine["point"][seed] = (t0 - o_m + n) / t0
        mine["speed"][seed] = o_rep / nk
        p = pred["programs"].get(str(seed), {})
        for field, v in (("T0", t0), ("O_replay", o_rep), ("O_old_scope", o_old),
                         ("O_matched", o_m), ("N_kernel", nk), ("adapter_old_median", a_old),
                         ("adapter_repaired_median", a_new), ("unmeasured_upper", 0.0),
                         ("N", n), ("point_ratio", mine["point"][seed]),
                         ("conservative_ratio", mine["corr"][seed]),
                         ("kernel_speedup", mine["speed"][seed])):
            rep.check("NUMBERS", field in p and close(p[field], v), seed, field)
            checked.add(f"programs.*.{field}")
    agg = {"original_registered_conservative": family_geo(mine["old"], families),
           "corrected_scope_old_adapter_conservative": family_geo(mine["corr_old_n"], families),
           "corrected_conservative": family_geo(mine["corr"], families),
           "replay_only_sensitivity_conservative": family_geo(mine["replay_only"], families),
           "corrected_point": family_geo(mine["point"], families),
           "kernel_speedup_median": median(list(mine["speed"].values()))}
    for field, v in agg.items():
        rep.check("NUMBERS", close(pred[field], v), field, pred.get(field), v)
        checked.add(field)
    rep.check("NUMBERS", close(agg["original_registered_conservative"],
                               RESUME_PROTOCOL["accounting"]["old_conservative_ratio"]),
              "original result not reproduced")
    rep.check("NUMBERS", close(agg["corrected_scope_old_adapter_conservative"],
                               RESUME_PROTOCOL["accounting"]["matched_scope_ratio_with_old_adapter"]),
              "lead's corrected-scope value not reproduced")
    rep.check("NUMBERS", close(agg["kernel_speedup_median"],
                               RESUME_PROTOCOL["corrected_kernel_speedup_median"]),
              "speedup median")
    rng = [min(mine["speed"].values()), max(mine["speed"].values())]
    rep.check("NUMBERS", all(close(a, b) for a, b in zip(pred["kernel_speedup_range"], rng)),
              "speedup range")
    checked.add("kernel_speedup_range")
    fam = {}
    for seed, v in mine["corr"].items():
        fam.setdefault(families[seed % 5], []).append(math.log(v))
    for f, logs in fam.items():
        rep.check("NUMBERS", close(pred["family_corrected_conservative"][f],
                                   math.exp(sum(logs) / len(logs))), f)
    checked.add("family_corrected_conservative.*")
    amax = max(median([r["adapter_seconds"] for r in g[(s, "adapter", "adapter")]])
               / median([r["replay_seconds"] for r in g[(s, "kernel", "shared_state_kernel")]])
               for s in range(800000, 800030))
    rep.check("NUMBERS", close(pred["adapter_over_N_kernel_max"], amax), "adapter/N max")
    checked.add("adapter_over_N_kernel_max")
    met = agg["corrected_conservative"] <= gate
    rep.check("NUMBERS", pred["gate_met"] is met, "gate_met", pred["gate_met"], met)
    checked.add("gate_met")
    # field coverage
    for leaf in _leaves(pred):
        generic = ".".join("*" if part.isdigit() and len(part) == 6 else part
                           for part in leaf.split("."))
        family_generic = generic.split(".")[0] + ".*" if generic.startswith("family_") else generic
        ok = (generic in checked or family_generic in checked or generic in FIELD_MAP_UNCHECKED
              or generic.rsplit(".", 1)[0] in FIELD_MAP_UNCHECKED)
        rep.check("FIELD_MAP", ok, leaf, "unmapped field")


def _leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list) and obj and all(isinstance(x, (int, float)) for x in obj):
        yield prefix
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{prefix}.{i}")
    else:
        yield prefix


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", default=str(ROOT / PARENT_PROTOCOL["results_prefix"]))
    parser.add_argument("--resume", required=True)
    parser.add_argument("--prediction")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    report = audit(Path(args.parent), Path(args.resume),
                   Path(args.prediction) if args.prediction else None, args.replay)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "total_checks": report["total_checks"],
                      "checks": report["checks"], "findings": report["findings"][:10]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())


# --------------------------------------------------------------------------
# Stage D (after the repaired M gate): independent membership, parity, gate
# --------------------------------------------------------------------------

D_MODES = {"D_fixed_work": "work:10000", "D_wall": "wall:0.1", "D_memory": "peak_memory"}
D_UNCHECKED = {"programs.*.family": "generator label", "gate.*": "protocol constants (compared)",
               "verdict": "derived from gate_met (checked)", "reason": "free text",
               "stages.*.failed_keys": "empty lists when complete (checked via counts)",
               "stages.*.incorrect_keys": "empty lists when complete (checked via counts)",
               "absolute_fixed_work_seconds.*": "descriptive; median recomputed",
               "wall_compile_seconds_median.*": "descriptive",
               "wall_unknown_queries.*": "descriptive",
               "wall_nodes_median.*": "descriptive", "cost_regressions": "descriptive list",
               "memory_peak_ratio_max": "descriptive",
               "family.*": "family summaries (aggregate recomputed)"}


def expected_dev_keys() -> Dict[str, List[tuple]]:
    sys.path[:0] = [str(ROOT / ".reference"), str(ROOT)]
    from tests_direct import generate_programs as gp
    dev = PARENT_PROTOCOL["development"]
    diag = PARENT_PROTOCOL["diagnostic"]
    arms = PARENT_PROTOCOL["export"]["arms"]
    out = {}
    for stage, mode in D_MODES.items():
        if stage == "D_memory":
            seeds, reps = range(diag["first_seed"], diag["last_seed"] + 1), \
                dev["memory_repetitions"]
        else:
            seeds, reps = range(dev["first_seed"], dev["last_seed"] + 1), dev["repetitions"]
        keys = []
        for s in seeds:
            d = gp.program_digest(gp.additional_program(s))
            for rep in range(reps):
                for arm in arms:
                    keys.append((stage, d, rep, arm, mode, s))
        out[stage] = keys
    return out


def development_audit(resume: Path, report_file: Path) -> dict:
    rep = Report()
    resume = Path(resume)
    ledger = strict(resume / "MEASUREMENT_WALL_LEDGER.jsonl", rep)
    exp = expected_dev_keys()
    for stage, keys in exp.items():
        rep.check("D_EXPECTED", len(keys) == PARENT_PROTOCOL["expected_rows"][stage], stage)
    rows = {s: check_stage_rows(rep, resume, s, exp[s], ledger, True) for s in D_MODES}
    freeze_path = resume / "DEVELOPMENT_FREEZE.json"
    if rep.check("D_FREEZE", freeze_path.exists(), "DEVELOPMENT_FREEZE.json missing"):
        freeze = json.loads(freeze_path.read_text())
        for name, recorded in freeze["sources"].items():
            rep.check("D_FREEZE", sha((ROOT / name).read_bytes()) == recorded, name)
        for stage in D_MODES:
            k = json.loads((resume / "stages" / stage / "EXPECTED_KEYS.json").read_text())
            rep.check("D_FREEZE", k["sha256"] == freeze["expected_keys_sha256"][stage], stage)
    for stage, rs in rows.items():
        for r in rs:
            want = "third_round_candidate C1" if r["arm_id"] == "C1" else "efficiency_search R0"
            rep.check("D_ROWS", r.get("solver_version") == want, key_of(r), "solver")
            rep.check("D_ROWS", r.get("correctness") == "PASS" and r.get("discrepancy_count") == 0
                      and r.get("cases", 0) > 0, key_of(r), "correctness")
            loaded = r.get("loaded_solvers", [])
            rep.check("D_ROWS", ("research.third_round_candidate" in loaded) == (r["arm_id"] == "C1"),
                      key_of(r), "solver isolation")
    report = json.loads(Path(report_file).read_text())
    try:
        _dev_numbers(rep, rows, report)
    except (KeyError, ValueError, ZeroDivisionError, TypeError) as exc:
        rep.check("D_NUMBERS", False, "cannot recompute", repr(exc))
    return rep.result()


def _dev_numbers(rep: Report, rows, report) -> None:
    gate = PARENT_PROTOCOL["development_gate"]
    fams = PARENT_PROTOCOL["families"]
    checked = set()
    pairs: Dict[tuple, dict] = {}
    for r in rows["D_fixed_work"]:
        pairs.setdefault((r["seed"], r["repetition"]), {})[r["arm_id"]] = r
    mism = [[s, k] for (s, k), p in sorted(pairs.items())
            if set(p) != {"R0", "C1"} or p["R0"]["fingerprint"] != p["C1"]["fingerprint"]
            or p["R0"]["J"] != p["C1"]["J"]]
    rep.check("D_NUMBERS", report["fixed_work_parity"]["mismatches"] == mism, "parity list")
    rep.check("D_NUMBERS", report["fixed_work_parity"]["exact"] is (not mism), "parity flag")
    rep.check("D_NUMBERS", report["fixed_work_parity"]["pairs"] == len(pairs), "pairs")
    checked |= {"fixed_work_parity.mismatches", "fixed_work_parity.exact",
                "fixed_work_parity.pairs"}
    t: Dict[int, Dict[str, list]] = {}
    for r in rows["D_fixed_work"]:
        t.setdefault(r["seed"], {}).setdefault(r["arm_id"], []).append(r["compile_call_seconds"])
    logs = {}
    for seed, arms in t.items():
        a, b = median(arms["R0"]), median(arms["C1"])
        logs[seed] = math.log(b / a)
        p = report["programs"][str(seed)]
        for field, v in (("R0_median", a), ("C1_median", b), ("ratio", b / a)):
            rep.check("D_NUMBERS", close(p[field], v), seed, field)
            checked.add(f"programs.*.{field}")
    fam_logs: Dict[str, List[float]] = {}
    for seed, v in logs.items():
        fam_logs.setdefault(fams[seed % 5], []).append(v)
    cost = math.exp(sum(sum(v) / len(v) for v in fam_logs.values()) / len(fam_logs))
    rep.check("D_NUMBERS", len(fam_logs) == 5 and all(len(v) == 20 for v in fam_logs.values()),
              "family denominators")
    rep.check("D_NUMBERS", close(report["fixed_work_compile_ratio_equal_family"], cost), "cost")
    checked.add("fixed_work_compile_ratio_equal_family")
    w: Dict[tuple, dict] = {}
    for r in rows["D_wall"]:
        w.setdefault((r["seed"], r["repetition"]), {})[r["arm_id"]] = r["J"]
    per: Dict[int, List[float]] = {}
    for (seed, _), p in w.items():
        per.setdefault(seed, []).append(math.log(p["C1"] / p["R0"]))
    q: Dict[str, List[float]] = {}
    for seed, v in per.items():
        m = sum(v) / len(v)
        q.setdefault(fams[seed % 5], []).append(m)
        rep.check("D_NUMBERS", close(report["programs"][str(seed)]["wall_mean_log_J_ratio"], m),
                  seed, "wall log J")
    checked.add("programs.*.wall_mean_log_J_ratio")
    quality = sum(sum(v) / len(v) for v in q.values()) / len(q)
    rep.check("D_NUMBERS", close(report["wall_primary_mean_log_J_ratio_equal_family"], quality),
              "quality")
    checked.add("wall_primary_mean_log_J_ratio_equal_family")
    wtl = [sum(1 for p in w.values() if p["C1"] < p["R0"]),
           sum(1 for p in w.values() if p["C1"] == p["R0"]),
           sum(1 for p in w.values() if p["C1"] > p["R0"])]
    rep.check("D_NUMBERS", report["wall_J_wins_ties_losses_C1"] == wtl, "W/T/L")
    checked.add("wall_J_wins_ties_losses_C1")
    mem: Dict[int, dict] = {}
    for r in rows["D_memory"]:
        mem.setdefault(r["seed"], {})[r["arm_id"]] = r
    feq = all(p["R0"]["fingerprint"] == p["C1"]["fingerprint"] for p in mem.values())
    rep.check("D_NUMBERS", report["memory_fingerprints_equal"] is feq, "memory fingerprints")
    ratios = [p["C1"]["tracemalloc_peak_bytes"] / p["R0"]["tracemalloc_peak_bytes"]
              for p in mem.values()]
    rep.check("D_NUMBERS", close(report["memory_peak_ratio_median"], median(ratios)), "memory")
    checked |= {"memory_fingerprints_equal", "memory_peak_ratio_median"}
    for stage in D_MODES:
        s = report["stages"][stage]
        n = len(rows[stage])
        rep.check("D_NUMBERS", s["expected"] == PARENT_PROTOCOL["expected_rows"][stage]
                  and s["observed"] == n and s["complete"] is True, stage, "stage summary")
        checked.add(f"stages.{stage}.*")
    met = (not mism and feq and cost <= gate["fixed_work_compile_ratio_max"]
           and quality <= gate["wall_primary_mean_log_J_ratio_max"])
    rep.check("D_NUMBERS", report["gate_met"] is met, "gate_met", report["gate_met"], met)
    rep.check("D_NUMBERS", report["complete"] is True, "complete flag")
    rep.check("D_NUMBERS", report["verdict"] == ("PASS" if met else
                                                 "DEVELOPMENT_TARGET_NOT_REACHED"), "verdict")
    checked |= {"gate_met", "complete", "verdict"}
    for leaf in _leaves(report):
        parts = leaf.split(".")
        generic = ".".join("*" if p.isdigit() and len(p) == 6 else p for p in parts)
        stage_generic = ".".join(parts[:2]) + ".*" if parts[0] == "stages" else generic
        top = parts[0] + ".*"
        ok = (generic in checked or stage_generic in checked or generic in D_UNCHECKED
              or top in D_UNCHECKED or parts[0] in D_UNCHECKED)
        rep.check("D_FIELD_MAP", ok, leaf, "unmapped field")


# --------------------------------------------------------------------------
# Stage C (after a Stage D PASS)
# --------------------------------------------------------------------------

C_UNCHECKED = {"descriptive": "descriptive statistics (public scores recomputed separately)",
               "gate": "protocol constants", "family": "family summaries",
               "stages": "stage summaries (membership checked from protocol)",
               "intervals_97_5.resamples": "protocol constant", "intervals_97_5.percentiles":
               "protocol constant", "intervals_97_5.seed": "protocol constant"}


def _c_programs():
    sys.path[:0] = [str(ROOT / ".reference"), str(ROOT)]
    from tests_direct import generate_programs as gp
    import machine as _m
    conf = PARENT_PROTOCOL["confirmation"]
    fresh = {s: gp.program_digest(gp.additional_program(s))
             for s in range(conf["first_seed"], conf["last_seed"] + 1)}
    public = [gp.program_digest(_m.load_program(str(p)))
              for p in sorted((ROOT / ".reference/programs").glob("*.json"))]
    corpus = []
    for fn in (gp.public_programs, gp.regression_programs, gp.additional_programs,
               gp.stress_programs):
        corpus += [gp.program_digest(p) for p in fn()]
    return fresh, public, corpus


def expected_c_keys() -> Dict[str, List[tuple]]:
    fresh, public, corpus = _c_programs()
    arms = PARENT_PROTOCOL["export"]["arms"]
    reps = PARENT_PROTOCOL["confirmation"]["repetitions"]
    walls = [f"wall:{b if b != 1 else 1.0}" for b in PARENT_PROTOCOL["wall_budgets_seconds"]]
    out = {"C_fixed_work": [], "C_wall": [], "C_public": [], "C_export": [], "C_acceptance": []}
    for s, d in fresh.items():
        for rep in range(reps):
            out["C_fixed_work"] += [("C_fixed_work", d, rep, a, "work:10000", s) for a in arms]
            out["C_wall"] += [("C_wall", d, rep, a, m, s) for a in arms for m in walls]
    for d in public:
        for rep in range(reps):
            out["C_public"] += [("C_public", d, rep, a, m, None) for a in arms for m in walls]
            out["C_public"].append(("C_public", d, rep, "serial", "serial", None))
    for d in list(fresh.values()) + public:
        for rep in range(PARENT_PROTOCOL["export"]["repetitions"]):
            out["C_export"] += [("C_export", d, rep, a, "wall:0.1", None) for a in arms]
    for d in corpus:
        out["C_acceptance"] += [("C_acceptance", d, 0, a, "wall:0.1", None) for a in arms]
    seed_of = {d: s for s, d in fresh.items()}
    for stage in ("C_export",):
        out[stage] = [k[:5] + (seed_of.get(k[1]),) for k in out[stage]]
    return out


def confirmation_audit(resume: Path, comparison_file: Path) -> dict:
    rep = Report()
    resume = Path(resume)
    ledger = strict(resume / "MEASUREMENT_WALL_LEDGER.jsonl", rep)
    exp = expected_c_keys()
    for stage, keys in exp.items():
        rep.check("C_EXPECTED", len(keys) == PARENT_PROTOCOL["expected_rows"][stage], stage,
                  len(keys))
    rows = {s: check_stage_rows(rep, resume, s, exp[s], ledger,
                                "cli" if s in ("C_export", "C_acceptance") else True)
            for s in exp}
    freeze = json.loads((resume / "CONFIRMATION_FREEZE.json").read_text())
    for name, recorded in freeze["sources"].items():
        rep.check("C_FREEZE", sha((ROOT / name).read_bytes()) == recorded, name)
    for arm, info in freeze["exports"].items():
        rep.check("C_FREEZE", sha(Path(info["path"]).read_bytes()) == info["sha256"], arm)
    rep.check("C_FREEZE", freeze["exports"]["R0"]["sha256"]
              == PARENT_PROTOCOL["baseline"]["export_sha256"], "R0 export bytes")
    for stage in exp:
        k = json.loads((resume / "stages" / stage / "EXPECTED_KEYS.json").read_text())
        rep.check("C_FREEZE", k["sha256"] == freeze["expected_keys_sha256"][stage], stage)
    for stage in ("C_export", "C_acceptance"):
        for r in rows[stage]:
            rep.check("C_EXPORT", r.get("ok") is True and r.get("input_unchanged") is True
                      and r.get("export_sha256") == freeze["exports"][r["arm_id"]]["sha256"],
                      key_of(r))
    acc_cases = {a: sum(r.get("cases", 0) for r in rows["C_acceptance"] if r["arm_id"] == a)
                 for a in ("R0", "C1")}
    rep.check("C_EXPORT", acc_cases == {"R0": 277, "C1": 277}, "acceptance cases", acc_cases)
    comp = json.loads(Path(comparison_file).read_text())
    try:
        _c_numbers(rep, rows, comp)
    except (KeyError, ValueError, ZeroDivisionError, TypeError) as exc:
        rep.check("C_NUMBERS", False, "cannot recompute", repr(exc))
    return rep.result()


def _pctl(xs, p):
    k = (len(xs) - 1) * p
    f = int(math.floor(k))
    c = min(f + 1, len(xs) - 1)
    return xs[f] * (1 - (k - f)) + xs[c] * (k - f)


def _c_numbers(rep: Report, rows, comp) -> None:
    fams = PARENT_PROTOCOL["families"]
    gate = PARENT_PROTOCOL["confirmation_gate"]
    checked = set()
    fixed = rows["C_fixed_work"]
    fam_of = {r["program_sha256"]: fams[r["seed"] % 5] for r in fixed}
    per: Dict[str, Dict[str, list]] = {}
    fps: Dict[tuple, dict] = {}
    for r in fixed:
        per.setdefault(r["program_sha256"], {}).setdefault(r["arm_id"], []).append(
            r["compile_call_seconds"])
        fps.setdefault((r["program_sha256"], r["repetition"]), {})[r["arm_id"]] = (
            r["fingerprint"], r["J"])
    mism = sum(1 for v in fps.values() if v["R0"] != v["C1"])
    rep.check("C_NUMBERS", comp["fixed_work_parity"]["mismatch_count"] == mism
              and comp["fixed_work_parity"]["exact"] is (mism == 0), "parity")
    checked |= {"fixed_work_parity"}
    cost = {p: math.log(median(a["C1"]) / median(a["R0"])) for p, a in per.items()}
    q: Dict[str, List[float]] = {}
    wall: Dict[tuple, dict] = {}
    for r in rows["C_wall"]:
        if r["mode_key"] == "wall:0.1":
            wall.setdefault((r["program_sha256"], r["repetition"]), {})[r["arm_id"]] = r["J"]
    for (p, _), v in wall.items():
        q.setdefault(p, []).append(math.log(v["C1"] / v["R0"]))
    quality = {p: sum(v) / len(v) for p, v in q.items()}
    order = {f: sorted(p for p in cost if fam_of[p] == f) for f in fams}
    rep.check("C_NUMBERS", all(len(v) == 40 for v in order.values()), "40 per family")

    def eq(d):
        return sum(sum(d[p] for p in order[f]) / len(order[f]) for f in fams) / len(fams)

    rep.check("C_NUMBERS", close(comp["cost_ratio"], math.exp(eq(cost))), "cost point")
    rep.check("C_NUMBERS", close(comp["quality_ratio"], math.exp(eq(quality))), "quality point")
    checked |= {"cost_ratio", "quality_ratio"}
    import random as _r
    rng = _r.Random(PARENT_PROTOCOL["seeds"]["bootstrap"])
    dc, dq = [], []
    for _ in range(PARENT_PROTOCOL["statistics"]["resamples"]):
        sc = sq = 0.0
        for f in fams:
            g = order[f]
            n = len(g)
            tc_ = tq = 0.0
            for _i in range(n):
                p = g[rng.randrange(n)]
                tc_ += cost[p]
                tq += quality[p]
            sc += tc_ / n
            sq += tq / n
        dc.append(sc / len(fams))
        dq.append(sq / len(fams))
    dc.sort()
    dq.sort()
    lo, hi = PARENT_PROTOCOL["statistics"]["percentiles"]
    mine = {"cost": [math.exp(_pctl(dc, lo)), math.exp(_pctl(dc, hi))],
            "quality": [math.exp(_pctl(dq, lo)), math.exp(_pctl(dq, hi))]}
    for k in ("cost", "quality"):
        for i in (0, 1):
            rep.check("C_NUMBERS", abs(comp["intervals_97_5"][k][i] - mine[k][i]) <= 1e-9,
                      k, i, comp["intervals_97_5"][k][i], mine[k][i])
    checked |= {"intervals_97_5.cost", "intervals_97_5.quality"}
    success = (mism == 0 and mine["cost"][1] <= gate["fixed_work_compile_ratio_upper_max"]
               and mine["quality"][1] <= gate["wall_primary_J_ratio_upper_max"])
    rep.check("C_NUMBERS", comp["success"] is success, "joint success")
    rep.check("C_NUMBERS", comp["verdict"] == ("SUCCESS" if success else "TARGET_NOT_REACHED"),
              "verdict")
    rep.check("C_NUMBERS", comp["complete"] is True and comp["programs"] == 200, "complete")
    checked |= {"success", "verdict", "complete", "programs"}
    pub = rows["C_public"]
    for arm in ("R0", "C1"):
        for mode in ("wall:0.01", "wall:0.1", "wall:1.0"):
            for k in range(PARENT_PROTOCOL["confirmation"]["repetitions"]):
                n = sum(1 for r in pub if r["arm_id"] == arm and r["mode_key"] == mode
                        and r["repetition"] == k)
                rep.check("C_PUBLIC", n == 8, arm, mode, k, "public denominator")
    rep.check("C_PUBLIC", sum(1 for r in pub if r["arm_id"] == "serial") == 40, "serial rows")
    for leaf in _leaves(comp):
        parts = leaf.split(".")
        ok = (leaf in checked or ".".join(parts[:2]) in checked or parts[0] in checked
              or parts[0] in C_UNCHECKED or ".".join(parts[:2]) in C_UNCHECKED)
        rep.check("C_FIELD_MAP", ok, leaf, "unmapped field")



_PROGRAMS: Dict[str, Path] = {}


def _program_paths() -> Dict[str, Path]:
    if not _PROGRAMS:
        sys.path[:0] = [str(ROOT / ".reference"), str(ROOT)]
        import machine as _m
        from tests_direct import generate_programs as gp
        prefix = ROOT / RESUME_PROTOCOL["results_prefix"]
        for folder in (prefix / "cohort" / "programs", prefix / "cohort" / "corpus",
                       ROOT / ".reference" / "programs"):
            for path in folder.glob("*.json"):
                _PROGRAMS[gp.program_digest(_m.load_program(str(path)))] = path
    return _PROGRAMS


def _cli_payload(rep: Report, area: str, k: str, r: dict, data: bytes) -> None:
    """CLI stdout is a compiled schedule: one JSON line, re-validated here."""

    import machine as _m
    text = data.decode("utf-8", errors="replace")
    ok_line = text.count("\n") == 1 and text.endswith("\n")
    if not rep.check(area, ok_line, k, "CLI stdout is not exactly one JSON line"):
        return
    path = _program_paths().get(r["program_sha256"])
    if not rep.check(area, path is not None, k, "program not found by digest"):
        return
    program = _m.load_program(str(path))
    compiled = json.loads(text)
    cycles = _m.check_compilation(program, compiled)
    for case in program["cases"]:
        _m.check_case(program, compiled, case)
    scratch = _m.scratch_footprint(program, compiled)
    rep.check(area, (cycles, scratch, cycles * scratch) == (r.get("cycles"), r.get("scratch"),
                                                             r.get("J")), k, "CLI J differs")
