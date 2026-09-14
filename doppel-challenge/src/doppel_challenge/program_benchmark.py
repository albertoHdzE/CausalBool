"""Isolated, independently verified benchmarks of shared repertoire programs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time

from .adapters import Network, apply_gate
from .execution import source_provenance
from .full_behaviour import REPO_ROOT, WOLFRAM_KERNEL
from .full_behaviour_scaling import make_full_behaviour_benchmark_cases
from .io import atomic_write_json
from .records import make_envelope, seal
from .schema import validate_record
from .repertoire_program import (
    ProgramLimits, ResourceLimitError, compile_repertoire_program,
    deserialize_program, evaluate_program, iter_output_rows,
    program_metadata, serialize_program,
)


def bdm_output_matrix(outputs):
    """BDM on the original ordered matrix; no reshaping into an index stream."""
    provenance = {"implementation": "pybdm", "version": None,
                  "input_mode": "original_output_matrix", "dimensionality": 2,
                  "partition": "PartitionIgnore", "block_shape": [4, 4],
                  "padding_policy": "bottom_right_zero_pad_to_multiples_of_four"}
    try:
        import numpy as np
        import pybdm
        from pybdm import BDM
        from pybdm.partitions import PartitionIgnore
        provenance["version"] = pybdm.__version__
        if pybdm.__version__ != "0.1.0":
            raise ValueError("pybdm must be version 0.1.0")
        matrix = np.asarray(outputs, dtype=int)
        if matrix.ndim != 2 or not matrix.size or not np.isin(matrix, [0, 1]).all():
            raise ValueError("BDM requires a nonempty binary matrix")
        rows, columns = matrix.shape
        padded = np.pad(matrix, ((0, -rows % 4), (0, -columns % 4)))
        provenance.update({"original_shape": [rows, columns],
                           "padded_shape": list(padded.shape),
                           "padding_bits": int(padded.size-matrix.size),
                           "original_output_sha256": hashlib.sha256(matrix.astype('uint8').tobytes()).hexdigest()})
        value = float(BDM(ndim=2, shape=(4, 4), partition=PartitionIgnore).bdm(padded))
        return {"status": "completed", "value": value, "provenance": provenance}
    except ImportError as exc:
        return {"status": "missing_dependency", "value": None,
                "failure": str(exc), "provenance": provenance}
    except Exception as exc:
        return {"status": "bdm_failure", "value": None,
                "failure": str(exc), "provenance": provenance}


def _network(case):
    n = case["network_size"]
    return Network(n, case["cm"], case["dyn"], case.get("params") or [{} for _ in range(n)])


def _worker(case, timeout, max_nodes):
    started = time.perf_counter()
    net = _network(case)
    t = time.perf_counter()
    program = compile_repertoire_program(net, limits=ProgramLimits(max_nodes, timeout))
    compile_seconds = time.perf_counter()-t
    t = time.perf_counter()
    payload = serialize_program(program)
    restored = deserialize_program(payload, n=net.n)
    serialization_seconds = time.perf_counter()-t
    sampled = case.get("validation_scope") == "sampled"
    rng = random.Random(20260910)
    indices = [0, (1 << net.n)-1] + [rng.getrandbits(net.n) for _ in range(100)] if sampled else range(1 << net.n)
    connections = [[i for i, bit in enumerate(row) if bit] for row in net.C]
    outputs = []
    digest = hashlib.sha256()
    t = time.perf_counter()
    checked = 0
    for x in indices:
        expected = [apply_gate(gate, [(x >> i) & 1 for i in ic], p)
                    for gate, ic, p in zip(net.gates, connections, net.params)]
        actual = evaluate_program(restored, x)
        if expected != actual:
            return {"status": "reconstruction_mismatch", "accepted_validation": False,
                    "mismatch_row": x}
        digest.update(bytes(actual))
        checked += net.n
        if not sampled:
            outputs.append(actual)
    validation_seconds = time.perf_counter()-t
    bdm = ({"status": "not_run_sampled_validation", "value": None} if sampled
           else bdm_output_matrix(outputs))
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "status": "completed", "accepted_validation": True,
        **program_metadata(program), "payload_hex": payload.hex(),
        "compile_seconds": compile_seconds, "serialization_seconds": serialization_seconds,
        "decode_and_reference_validation_seconds": validation_seconds,
        "elapsed_seconds": time.perf_counter()-started,
        "peak_worker_rss_bytes": int(rss if sys.platform == "darwin" else rss*1024),
        "memory_scope": "whole_isolated_worker_including_reference_validation_and_BDM",
        "validation_scope": "sampled_102_rows" if sampled else "exhaustive_all_output_bits",
        "checked_output_bits": checked, "checked_output_sha256": digest.hexdigest(),
        "validation_materializes_output_matrix": not sampled,
        "bdm_original_output": bdm,
    }


def _run_isolated(case, *, timeout_seconds=300, max_nodes=1_000_000):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]) + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, "-m", "doppel_challenge.program_benchmark", "--worker"]
    try:
        proc = subprocess.run(command, input=json.dumps({"case": case, "timeout": timeout_seconds,
                              "max_nodes": max_nodes}), text=True, capture_output=True,
                              timeout=timeout_seconds, env=env)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "accepted_validation": False}
    except OSError as exc:
        return {"status": "compiler_failure", "accepted_validation": False, "failure": str(exc)}
    if proc.returncode:
        return {"status": "compiler_failure", "accepted_validation": False,
                "exit_code": proc.returncode, "failure": proc.stderr}
    try:
        result = json.loads(proc.stdout)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("missing worker status")
        if result["status"] == "completed":
            for key in ("payload_hex", "program_bit_length", "canonical_program_sha256", "validation_scope"):
                if key not in result:
                    raise ValueError(f"missing {key}")
            p = deserialize_program(bytes.fromhex(result["payload_hex"]), n=case["network_size"])
            metadata = program_metadata(p)
            if any(result[key] != metadata[key] for key in ("program_bit_length", "canonical_program_sha256")):
                raise ValueError("worker program metadata mismatch")
        return result
    except (ValueError, TypeError, KeyError) as exc:
        return {"status": "malformed_payload", "accepted_validation": False, "failure": str(exc)}


def wolfram_reference(case, *, timeout_seconds=300):
    """Independent whole-matrix reference; timing excludes program compilation."""
    params = [dict(p) for p in case.get("params", [{} for _ in case["dyn"]])]
    for p in params:
        if "canalisingIndex" in p:
            p["canalisingIndex"] += 1
    payload = json.dumps({"cm": case["cm"], "dyn": case["dyn"], "params": params})
    code = ('Get["src/Packages/Integration/Gates.m"]; Get["src/Packages/Integration/Experiments.m"];'
            'p=ImportString[' + json.dumps(payload) + ',"RawJSON"];'
            'pa=Association[Table[i->p["params"][[i]],{i,Length[p["dyn"]]}]];'
            'r=Integration`Experiments`CreateRepertoiresDispatch[p["cm"],p["dyn"],pa]["RepertoireOutputs"];'
            'WriteString["stdout",ExportString[r,"RawJSON"]];Exit[]')
    t = time.perf_counter()
    try:
        proc = subprocess.run([WOLFRAM_KERNEL, "-noprompt", "-run", code], cwd=REPO_ROOT,
                              text=True, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "owner": "Wolfram"}
    except OSError as exc:
        return {"status": "process_failure", "owner": "Wolfram", "failure": str(exc)}
    if proc.returncode:
        return {"status": "process_failure", "exit_code": proc.returncode, "failure": proc.stderr}
    try:
        rows = json.loads(proc.stdout)
        n = case["network_size"]
        if not isinstance(rows, list) or len(rows) != 1 << n or any(
                not isinstance(row, list) or len(row) != n or
                any(type(b) is not int or b not in (0, 1) for b in row) for row in rows):
            raise ValueError("invalid Wolfram output matrix")
        digest = hashlib.sha256(bytes(b for row in rows for b in row)).hexdigest()
        return {"status": "completed", "process_status": "normal_exit", "owner": "Wolfram",
                "output_sha256": digest, "elapsed_seconds": time.perf_counter()-t}
    except (ValueError, TypeError) as exc:
        return {"status": "malformed_payload", "owner": "Wolfram", "failure": str(exc)}


def mixed_cases():
    from .adapters import GATE_TYPES
    rng = random.Random(20260910)
    cases = []
    for n in (8, 10, 12):
        for trial in range(4):
            cm, dyn, params = [], [], []
            for j in range(n):
                gate = GATE_TYPES[(j+3*trial) % len(GATE_TYPES)]
                d = rng.randint(2, min(n, 6))
                ic = sorted(rng.sample(range(n), d))
                p = {}
                if gate == "KOFN":
                    p = {"k": rng.randint(0, d), "strict": bool(trial % 2)}
                if gate == "MAJORITY":
                    p = {"tiePolicy": "atOrAbove" if trial % 2 else "strict"}
                if gate == "CANALISING":
                    p = {"canalisingIndex": rng.randrange(d), "canalisingValue": trial % 2,
                         "canalisedOutput": (trial//2) % 2}
                cm.append([int(i in ic) for i in range(n)])
                dyn.append(gate)
                params.append(p)
            cases.append({"label": f"mixed_n{n}_{trial}", "network_size": n,
                          "topology": "seeded_mixed", "seed": 20260910,
                          "cm": cm, "dyn": dyn, "params": params})
    return cases


def large_cases():
    n = 100
    return [{"label": f"{name}_n100", "network_size": n, "topology": name,
             "cm": [[int(i == j) if name == "identity" else 1 for i in range(n)] for j in range(n)],
             "dyn": [gate]*n, "validation_scope": "sampled"}
            for name, gate in (("identity", "AND"), ("shared_parity", "XOR"), ("shared_majority", "MAJORITY"))]


def notebook_cases():
    from .pilot_runner import make_mixed_ring_network
    from .full_behaviour import chapter4_network_7
    a, gates = make_mixed_ring_network(8, seed=3)
    b, gates7 = chapter4_network_7()
    return [{"label": "worked_n8", "network_size": 8, "topology": "mixed_ring_seed3", "cm": a, "dyn": gates},
            {"label": "chapter4_n7", "network_size": 7, "topology": "chapter4", "cm": b, "dyn": gates7}]


def run_program_benchmark(cases=None, *, extra_cases=(), include_large=True, verify_wolfram=True,
                          timeout_seconds=300, max_nodes=1_000_000, out_dir=None, progress=False):
    cases = list(cases) if cases is not None else make_full_behaviour_benchmark_cases() + mixed_cases() + notebook_cases()
    cases += list(extra_cases)
    if include_large:
        cases += large_cases()
    if not cases or len({c["label"] for c in cases}) != len(cases):
        raise ValueError("benchmark needs nonempty, uniquely labelled cases")
    rows = []
    for case in cases:
        if progress:
            print(f"Compiling and verifying {case['label']}", file=sys.stderr, flush=True)
        result = _run_isolated(case, timeout_seconds=timeout_seconds, max_nodes=max_nodes)
        result = {"label": case["label"], "network_size": case["network_size"],
                  "network": case, **result}
        if result["status"] == "completed" and verify_wolfram and case.get("validation_scope") != "sampled":
            reference = wolfram_reference(case, timeout_seconds=timeout_seconds)
            result["wolfram_reference"] = reference
            if reference["status"] != "completed":
                result.update(status="reference_owner_failure", accepted_validation=False)
            elif reference["output_sha256"] != result["checked_output_sha256"]:
                result.update(status="reconstruction_mismatch", accepted_validation=False)
        rows.append(result)
    failures = sum(r["status"] != "completed" for r in rows)
    bdm_failures = sum(r.get("bdm_original_output", {}).get("status") != "completed"
                       for r in rows if r.get("validation_scope") == "exhaustive_all_output_bits")
    record = make_envelope("shared_program_benchmark", config_id="shared_program_v1", sweep_id=None)
    record.update({"observable": "whole_ordered_one_step_output_repertoire",
                   "approximation": "exact_program_with_explicit_validation_scope",
                   "estimator_parameters": {"timeout_seconds": timeout_seconds, "max_nodes": max_nodes},
                   "uncertainty": None, "process_status": "normal_exit" if not failures else "completed_with_failures",
                   "scientific_status": "complete" if not failures else "completed_with_failures",
                   "accepted_validation": not failures,
                   "release_ready": not failures and not bdm_failures and verify_wolfram,
                   "cases": rows, "n_cases": len(rows), "n_failures": failures,
                   "n_bdm_failures": bdm_failures,
                   "provenance": {**source_provenance(), "decoder_source_sha256": hashlib.sha256(
                       Path(__file__).with_name("repertoire_program.py").read_bytes()).hexdigest()}})
    record = seal(record)
    if out_dir is not None:
        atomic_write_json(Path(out_dir)/"shared_program_benchmark.json", record)
    return record


def validate_program_benchmark(record):
    errors = list(validate_record(record)["errors"])
    rows = record.get("cases", [])
    if record.get("n_cases") != len(rows):
        errors.append("case_count_mismatch")
    failures = sum(r.get("status") != "completed" for r in rows)
    if not rows or len({r.get("label") for r in rows}) != len(rows):
        errors.append("empty_or_duplicate_cases")
    if record.get("release_ready") and (failures or not record.get("accepted_validation")):
        errors.append("invalid_release_status")
    if failures != record.get("n_failures") or (failures and record.get("accepted_validation")):
        errors.append("inconsistent_failure_status")
    for row in rows:
        if row.get("accepted_validation") and row.get("status") != "completed":
            errors.append("accepted_failed_case")
        if row.get("status") != "completed":
            continue
        try:
            p = deserialize_program(bytes.fromhex(row["payload_hex"]), n=row["network_size"])
            m = program_metadata(p)
            for key in ("raw_bit_length", "program_bit_length", "canonical_program_sha256"):
                if row[key] != m[key]:
                    errors.append(f"metadata_mismatch:{row['label']}:{key}")
            if row["validation_scope"] == "exhaustive_all_output_bits" and row["checked_output_bits"] != m["raw_bit_length"]:
                errors.append("incomplete_exhaustive_validation")
            if row["validation_scope"] not in ("exhaustive_all_output_bits", "sampled_102_rows"):
                errors.append("unknown_validation_scope")
            if row["validation_scope"] == "sampled_102_rows" and row["checked_output_bits"] != 102*p.n:
                errors.append("sample_count_mismatch")
            if record.get("release_ready") and row["validation_scope"] == "exhaustive_all_output_bits":
                if row.get("bdm_original_output", {}).get("status") != "completed":
                    errors.append("release_missing_bdm")
                ref = row.get("wolfram_reference", {})
                if ref.get("status") != "completed" or ref.get("output_sha256") != row["checked_output_sha256"]:
                    errors.append("release_missing_independent_validation")
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"invalid_program:{exc}")
    return {"valid": not errors, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--out-dir", default="doppel-challenge/results/shared_program")
    parser.add_argument("--extra-cases", type=Path)
    args = parser.parse_args()
    if args.worker:
        try:
            request = json.load(sys.stdin)
            result = _worker(request["case"], request["timeout"], request["max_nodes"])
        except ResourceLimitError as exc:
            result = {"status": "resource_exhaustion", "accepted_validation": False, "failure": str(exc)}
        except TimeoutError as exc:
            result = {"status": "timeout", "accepted_validation": False, "failure": str(exc)}
        except (ValueError, AssertionError, TypeError, KeyError) as exc:
            result = {"status": "invalid_input", "accepted_validation": False, "failure": str(exc)}
        except Exception as exc:
            result = {"status": "compiler_failure", "accepted_validation": False, "failure": str(exc)}
        print(json.dumps(result))
    else:
        extra = json.loads(args.extra_cases.read_text()) if args.extra_cases else ()
        record = run_program_benchmark(extra_cases=extra, out_dir=args.out_dir, progress=True)
        result = validate_program_benchmark(record)
        print(json.dumps({"validation": result, "n_cases": record["n_cases"],
                          "n_failures": record["n_failures"], "release_ready": record["release_ready"]}))
        if not result["valid"] or not record["release_ready"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
