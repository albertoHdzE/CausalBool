"""Independent stdlib recount of source identity, replay and profile evidence."""
import collections
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = HERE.parent / "efficiency_20260925"
PREVIOUS = HERE.parent / "next_round_20260925"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


freeze = load(RUN / "R0_FREEZE.json")
drift = [p for p, digest in freeze["sources"].items() if sha(ROOT / p) != digest]
export = freeze["R0"]["export"]
assert not drift
assert sha(ROOT / export["path"]) == export["sha256"]

original = {r["key"]: r for r in rows(PREVIOUS / "stages/L_orderings/rows.jsonl")}
replay = rows(RUN / "ranker_replay/rows.jsonl")
assert len(replay) == len(original) == 420
assert sorted(r["key"] for r in replay) == sorted(original)
for r in replay:
    assert r["exit_code"] == 0 and r["status"] == "OK"
    assert r["ordered_identical"] and r["digest_identical"] and r["info_identical"]
    assert not r["refused_opens"] and not r["refused_imports"]
    assert set(r["loaded_non_stdlib"]) <= {"__main__", "schema_index", "efficiency_ranker"}
    ordered = [int(i) for i in original[r["key"]]["result"]["ordered"]]
    digest = hashlib.sha256(json.dumps(ordered, separators=(",", ":")).encode()).hexdigest()
    assert digest == r["original_ordering_sha256"] == r["replay_ordering_sha256"]
    assert r["ranker_input_opens"] == [str(RUN / "ranker_replay/workspace/inputs" /
                                           r["fixture_id"] / "RANKER_INPUT.json")]
manifest = load(RUN / "ranker_replay/WORKSPACE_MANIFEST.json")
for name, item in manifest["code"].items():
    assert sha(RUN / "ranker_replay/workspace" / name) == item.get("copy_sha256", item["sha256"])
for fixture, item in manifest["inputs"].items():
    assert sha(Path(item["source"])) == item["sha256"] == item["copy_sha256"]
    assert sha(RUN / "ranker_replay/workspace/inputs" / fixture / "RANKER_INPUT.json") == item["sha256"]

profile = rows(RUN / "profile/rows.jsonl")
by = collections.defaultdict(list)
for r in profile:
    assert not r.get("failed")
    by[(r["seed"], r["mode"])].append(r)
assert {r["seed"] for r in profile} == set(range(800000, 800010))
shares = collections.defaultdict(list)
nodes = 0
for seed in range(800000, 800010):
    timing = by[(seed, "time")]
    assert len(timing) == 3
    total = statistics.median(r["compile_call_seconds"] for r in timing)
    split = by[(seed, "timers_split")]
    assert len(split) == 1
    assert by[(seed, "parity")][0]["split_changes_no_decision"]
    for component, seconds in split[0]["exclusive_seconds"].items():
        shares[component].append((seed % 5, seconds / total))
    nodes += by[(seed, "count")][0]["nodes"]
ceilings = {}
for key, values in shares.items():
    family_logs = collections.defaultdict(list)
    for family, share in values:
        family_logs[family].append(math.log(1 - share))
    ceilings[key] = math.exp(statistics.mean(statistics.mean(v) for v in family_logs.values()))
reported = load(RUN / "profile/PROFILE.json")["summary"]["zero_cost_ceilings"]
for key, ratio in ceilings.items():
    assert abs(ratio - reported[key]["zero_cost_ceiling_equal_family"]) < 1e-12
proposal = load(RUN / "MECHANISM_PROPOSAL.json")
predicted = math.exp(statistics.mean(math.log(1 - s) for s in
    proposal["prediction"]["per_program_saving_fraction_predicted"].values()))
assert abs(predicted - proposal["prediction"]["fixed_work_compile_ratio_equal_family_predicted"]) < 1e-12
development = load(RUN / "DEVELOPMENT.json")
assert development["candidate_implemented"] is False
assert not (ROOT / "research/efficiency_candidate.py").exists()
assert development["confirmation"]["candidate_outcomes_observed"] is False
assert development["confirmation"]["programs_generated"] == 0
out = {"status": "PASS", "frozen_sources_checked": len(freeze["sources"]),
       "source_drift": drift, "export_sha256": export["sha256"],
       "replay_rows_checked": len(replay), "replay_note": "Checks retained fields and original digests; does not re-execute the 420 rankers.",
       "profile_rows": len(profile), "profile_modes": dict(collections.Counter(r["mode"] for r in profile)),
       "profile_programs": 10, "fixed_work_nodes": nodes,
       "zero_cost_ratios": ceilings, "predicted_M1_ratio": predicted,
       "prediction_note": "Reaggregated reported per-program predictions, not an independently validated cost model.",
       "candidate_implemented": False}
(HERE / "RECOUNT.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(json.dumps(out, sort_keys=True))
