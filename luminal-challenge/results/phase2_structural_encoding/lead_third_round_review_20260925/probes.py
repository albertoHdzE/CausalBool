"""Lead mutations and independent arithmetic. Never writes the worker's evidence."""
import collections
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import tempfile

from research import third_round_audit as audit

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
RUN = ROOT / "results/phase2_structural_encoding/third_round_20260925"


def load(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


m0 = rows(RUN / "stages/M_diagnosis/rows.jsonl")
mk = rows(RUN / "stages/M_kernel/rows.jsonl")
by = collections.defaultdict(list)
for r in m0 + mk:
    assert r["exit_code"] == 0 and not r.get("timed_out") and not r.get("failed")
    by[(r["seed"], r["mode_key"], r["arm_id"])].append(r)
old_scope = {"tfix_shell", "tfix_copy", "precedence", "issue_capacity", "bounds_live",
             "bounds_product", "address_support", "child_domain_copy"}
matched_scope = old_scope | {"certificates", "propagation_setup", "address_pairs"}
per = {}
for seed in range(800000, 800030):
    time = by[(seed, "work:10000", "R0")]
    b = by[(seed, "kernel", "baseline_kernel")]
    k = by[(seed, "kernel", "shared_state_kernel")]
    assert len(time) == len(b) == len(k) == 3
    t0 = statistics.median(r["compile_call_seconds"] for r in time)
    timer = by[(seed, "exclusive_timers", "R0")][0]
    inflation = timer["timed_call_wall_seconds"] / t0
    o_replay = statistics.median(r["replay_seconds"] for r in b)
    o_old = sum(timer["exclusive_seconds"].get(c, 0) for c in old_scope) / inflation
    o_matched = sum(timer["exclusive_seconds"].get(c, 0) for c in matched_scope) / inflation
    n = statistics.median(r["replay_seconds"] for r in k)
    extra = statistics.median(r["integration_estimate_seconds"] for r in k)
    assert 0 <= min(o_replay, o_matched) <= t0
    assert all(r["parity"]["parity"] for r in b + k)
    per[str(seed)] = {"T0": t0, "O_old": min(o_replay, o_old),
                     "O_matched": min(o_replay, o_matched), "O_replay": o_replay,
                     "N_kernel": n, "N_adapter_recorded": extra,
                     "old_ratio": (t0 - min(o_replay, o_old) + 1.5*(n+extra))/t0,
                     "matched_ratio": (t0 - min(o_replay, o_matched) + 1.5*(n+extra))/t0,
                     "replay_ratio": (t0 - o_replay + 1.5*(n+extra))/t0,
                     "replay_over_matched_timer": o_replay/o_matched,
                     "kernel_speedup": o_replay/n}


def geom(key):
    groups = collections.defaultdict(list)
    for seed, p in per.items():
        groups[int(seed) % 5].append(math.log(p[key]))
    return math.exp(statistics.mean(statistics.mean(v) for v in groups.values()))


mutations = {}
for kind in ("extra_torn_row", "changed_kernel_freeze_hash", "false_M0_parity", "missing_NOT_RUN"):
    with tempfile.TemporaryDirectory(prefix="lead_third_mutation_") as tmp:
        overlay = Path(tmp) / "run"
        shutil.copytree(RUN, overlay, ignore=shutil.ignore_patterns("workloads"))
        if kind == "extra_torn_row":
            with (overlay / "stages/M_kernel/rows.jsonl").open("a") as f:
                f.write('{"stage_id": "unfinished"')
        elif kind == "changed_kernel_freeze_hash":
            p = overlay / "WORKLOAD_MANIFEST.json"
            payload = load(p)
            payload["kernel_stage_sources"]["research/third_round_kernel.py"] = "0" * 64
            p.write_text(json.dumps(payload))
        elif kind == "false_M0_parity":
            p = overlay / "stages/M_diagnosis/rows.jsonl"
            payload = rows(p)
            for r in payload:
                if r["mode_key"] == "instrumentation_parity":
                    r["parity"] = False
                    break
            p.write_text("".join(json.dumps(r) + "\n" for r in payload))
        else:
            (overlay / "NOT_RUN.json").unlink()
        result = audit.audit(overlay)
        mutations[kind] = {"status": result["status"],
                           "numerical_findings": result["numerical"]["findings"],
                           "identity_findings": result["identity"]["findings"]}

manifest = load(RUN / "WORKLOAD_MANIFEST.json")
changed = {}
for name, expected in manifest["kernel_stage_sources"].items():
    actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    if expected != actual:
        changed[name] = {"frozen": expected, "current": actual}
common = (ROOT / "research/third_round_common.py").read_text()
before = common.replace("from typing import Dict, Optional, Sequence, Tuple",
                       "from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple")
common_reconstructed = hashlib.sha256(before.encode()).hexdigest()
assert common_reconstructed == manifest["kernel_stage_sources"]["research/third_round_common.py"]

spec = load(RUN / "MECHANISM_SPEC.json")
kernel = (ROOT / "research/third_round_kernel.py").read_bytes()
prefix, prefix_length = b"", None
for line in kernel.splitlines(keepends=True):
    prefix += line
    if hashlib.sha256(prefix).hexdigest() == spec["kernel_source_at_spec"]["sha256"]:
        prefix_length = len(prefix)
        break

out = {"registered_conservative_ratio": geom("old_ratio"),
       "scope_matched_conservative_ratio": geom("matched_ratio"),
       "replay_only_conservative_ratio": geom("replay_ratio"),
       "median_kernel_speedup": statistics.median(p["kernel_speedup"] for p in per.values()),
       "programs": per, "audit_mutations": mutations,
       "measured_source_drift": changed,
       "common_old_bytes_reconstructed_sha256": common_reconstructed,
       "kernel_spec_hash_is_prefix_of_current": prefix_length,
       "note": "Corrected scope is exploratory development accounting. Adapter estimate still needs validation; no compiler gain measured."}
(HERE / "PROBES.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(json.dumps({k: v for k, v in out.items() if k != "programs"}, indent=2))
