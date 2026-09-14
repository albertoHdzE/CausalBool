"""Reproduce the resumption audit without changing implementation or pilot data.

Run from the repository root with venv/bin/python and optionally --wolfram.
The JSON reports defects as observations; exit zero does not certify the project.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "doppel-challenge"
sys.path.insert(0, str(PROJECT / "src"))

from doppel_challenge.adapters import Network
from doppel_challenge.compression import decode_repertoire, encode_repertoire, ncd
from doppel_challenge.full_behaviour import WL_SCRIPT, WOLFRAM_KERNEL
from doppel_challenge.perturbations import ball, indegrees, index, is_admissible_perturbation
from doppel_challenge.pilot_runner import make_network
from doppel_challenge.records import compute_sha256
from doppel_challenge.repertoire import compute_repertoire
from doppel_challenge.stats import expected_loss, kl


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_distribution(rep):
    return dict(zip(rep["support"], (Fraction(c, rep["probability_denominator"])
                                    for c in rep["counts"])))


def independent_next(cm, gates, state):
    result = 0
    for target, row in enumerate(cm):
        inputs = [(state >> source) & 1 for source, present in enumerate(row) if present]
        gate = gates[target]
        if gate == "AND":
            output = int(all(inputs))
        elif gate == "OR":
            output = int(any(inputs))
        elif gate == "XOR":
            output = sum(inputs) % 2
        elif gate == "MAJORITY":
            output = int(2 * sum(inputs) > len(inputs))
        else:
            raise ValueError(gate)
        result |= output << target
    return result


def independent_repertoire(cm, gates):
    mass = Counter()
    for start in range(1 << len(cm)):
        path = []
        current = start
        while current not in path:
            path.append(current)
            current = independent_next(cm, gates, current)
        cycle = path[path.index(current):]
        for state in cycle:
            mass[state] += Fraction(1, (1 << len(cm)) * len(cycle))
    return dict(mass)


def python_checks():
    p = {"rows": 2, "cols": 1, "support": [0, 1], "counts": [1, 99],
         "probability_denominator": 100, "probs": [0.01, 0.99]}
    q = {"rows": 2, "cols": 1, "support": [0], "counts": [1],
         "probability_denominator": 1, "probs": [1.0]}
    families = {}
    for family in ["ring", "sparse_random", "modular", "hub"]:
        cm, gates = make_network(family, 10)
        empty = [i for i, row in enumerate(cm) if not any(row)]
        families[family] = {
            "guard_indegrees": indegrees(cm), "engine_indegrees": list(map(sum, cm)),
            "empty_engine_nodes": empty, "empty_node_gates": [gates[i] for i in empty],
            "guard_admits": is_admissible_perturbation(cm),
        }
    rng = random.Random(20260909)
    oracle_matches = 0
    for n in [4, 5, 6]:
        for _ in range(12):
            cm = [[rng.randrange(2) for _ in range(n)] for _ in range(n)]
            for i, row in enumerate(cm):
                if not any(row):
                    row[(i + 1) % n] = 1
            gates = [rng.choice(["AND", "OR", "XOR", "MAJORITY"]) for _ in range(n)]
            actual = exact_distribution(compute_repertoire(Network(n, cm, gates)))
            oracle_matches += actual == independent_repertoire(cm, gates)
    cm = [[0, 1], [1, 1]]
    gates = ["AND", "AND"]
    stationary = compute_repertoire(Network(2, cm, gates))
    one_step = Counter(independent_next(cm, gates, s) for s in range(4))
    indistinguishable = compute_repertoire(Network(2, [[1, 1], [1, 1]], gates))
    adjacency = [[1, 0], [0, 1]]
    indices = [index(adjacency, a) for a in ball(adjacency, 2)]
    return {
        "families_n10_seed0": families,
        "KL_counterexample": {"current": kl(p, q), "standard_KL": "positive_infinity",
                              "total_variation": 0.99},
        "cross_entropy_counterexample": {"current": expected_loss(p, "L_ENTROPY", {}, q),
                                         "correct": "positive_infinity"},
        "NCD_counterexample": {"p_q": ncd(p, q), "q_p": ncd(q, p), "p_p": ncd(p, p)},
        "independent_attractor_oracle": {"cases": 36, "matches": oracle_matches,
                                        "sizes": [4, 5, 6], "seed": 20260909},
        "distinct_observables": {"one_step_probs": {s: c / 4 for s, c in one_step.items()},
                                 "stationary": stationary,
                                 "distinct_mechanisms_same_attractor_distribution":
                                     exact_distribution(stationary) == exact_distribution(indistinguishable)},
        "radius_2_indices": {"networks": len(indices), "unique_indices": len(set(indices)),
                             "indices": indices},
        "radius_3_N8_full_ball": sum(math.comb(64, i) for i in range(4)),
    }


def catalogue_checks():
    reports = []
    for path in sorted((PROJECT / "out").rglob("catalogue.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        identity = next(row for row in rows if row["graph_distance"] == 0)
        q = identity["repertoire"]
        base_support = set(q["support"])
        joint_path = path.with_name("joint.jsonl")
        joints = [json.loads(line) for line in joint_path.read_text().splitlines()]
        infinite_indices = []
        roundtrips = 0
        failure_empty_pairs = Counter()
        for row in rows:
            rep = row["repertoire"]
            if any(s not in base_support and c > 0 for s, c in zip(rep["support"], rep["counts"])):
                infinite_indices.append(row["perturbation_index"])
            encoded = encode_repertoire(rep)
            decoded = decode_repertoire(encoded["decimal_str"], encoded["summandos_str"], rep["cols"])
            roundtrips += exact_distribution(decoded) == exact_distribution(rep)
            empty = any(not any(r) for r in row["A"])
            failure = not row["owner_validation"]["exact_match"]
            failure_empty_pairs[f"owner_mismatch={failure},empty_engine_input={empty}"] += 1
        reports.append({
            "path": str(path.relative_to(ROOT)), "sha256": digest(path), "rows_including_base": len(rows),
            "owner_mismatches": sum(not r["owner_validation"]["exact_match"] for r in rows),
            "kernel_exit_codes": dict(Counter(str(r["owner_validation"]["kernel_exit_code"]) for r in rows)),
            "true_KL_infinite_rows": len(infinite_indices), "true_KL_infinite_indices": infinite_indices,
            "codec_distribution_roundtrips": roundtrips,
            "implementation_hash_matches": sum(r.get("sha256") == compute_sha256(r) for r in rows),
            "documented_hash_matches": sum(r.get("sha256") == hashlib.sha256(
                json.dumps({**r, "sha256": ""}, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest() for r in rows),
            "owner_mismatch_vs_empty_input": dict(failure_empty_pairs),
            "NCD_above_one": sum(r["NCD"] > 1 for r in joints),
            "NCD_max": max(r["NCD"] for r in joints),
        })
    return reports


def wolfram_checks():
    cm, gates = make_network("sparse_random", 10)
    repaired = [r[:] for r in cm]
    repaired[0][9] = 1
    cases = [("original", cm), ("row_input_repair", repaired),
             ("transpose", list(map(list, zip(*cm))))]
    reports = []
    for label, matrix in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            json.dump({"cm": matrix, "dyn": gates, "division_size": 2}, f)
            f.flush()
            env = {**os.environ, "CB_REPO": str(ROOT), "DOPPEL_INPUT_JSON": f.name}
            try:
                proc = subprocess.run([WOLFRAM_KERNEL, "-script", str(WL_SCRIPT)],
                                      env=env, cwd=ROOT, capture_output=True, text=True, timeout=40)
            except subprocess.TimeoutExpired:
                reports.append({"case": label, "status": "timeout"})
                continue
        result = {"case": label, "cm": matrix, "gates": gates, "kernel_exit_code": proc.returncode,
                  "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
                  "stderr": proc.stderr}
        for offset, char in enumerate(proc.stdout):
            if char != "{":
                continue
            try:
                obj, _ = json.JSONDecoder().raw_decode(proc.stdout[offset:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "network" in obj:
                result.update({k: obj[k] for k in ["exact_match", "dispatch_rows",
                              "unique_output_patterns_dispatch", "reconstructed_patterns"]})
                result["stdout_prefix"] = proc.stdout[:offset]
                break
        reports.append(result)
    return reports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wolfram", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"review_date": "2026-09-09", "python_checks": python_checks(),
              "catalogue_checks": catalogue_checks()}
    if args.wolfram:
        report["live_wolfram_checks"] = wolfram_checks()
    paths = list((PROJECT / "src").rglob("*.py")) + list((PROJECT / "src").rglob("*.wl"))
    paths += [PROJECT / "doc" / p for p in ["00-protocol.md", "01-record-schema.md",
                                          "02-plan.md", "03-continuation.txt"]]
    paths += [ROOT / "index-deconvolution/src/causalbool.py", ROOT / "src/integration/Alpha.m",
              ROOT / "src/Packages/Integration/Experiments.m", Path(__file__).resolve()]
    report["reviewed_source_hashes"] = {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output),
                      "independent_oracle": report["python_checks"]["independent_attractor_oracle"],
                      "catalogues_audited": len(report["catalogue_checks"]),
                      "rows_audited": sum(r["rows_including_base"] for r in report["catalogue_checks"])}))


if __name__ == "__main__":
    main()
