"""Reproducible downstream finalization; frozen experiment inputs are read-only."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from doppel_challenge.io import atomic_write_json, read_json
from doppel_challenge.records import compute_sha256, scientific_digest, seal
from doppel_challenge import joint_study as joint

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "doppel-challenge/results/joint_degree5_v2"
OUTPUT = ROOT / "doppel-challenge/results/joint_degree5_final_analysis_v1"
HERE = Path(__file__).resolve().parent


def raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_read(path):
    value = read_json(path)
    require(value["sha256"] == compute_sha256(value), f"canonical seal: {path}")
    require(value["scientific_digest"] == scientific_digest(value), f"scientific seal: {path}")
    return value


def check_artifacts(root, hashes):
    require(bool(hashes), "empty artifact manifest")
    for name, expected in hashes.items():
        path = (Path(root) / name).resolve()
        require(path.is_relative_to(Path(root).resolve()), f"artifact outside root: {name}")
        require(raw_hash(path) == expected, f"raw artifact hash: {name}")


def check_parent_link(analysis, parent, summary):
    # These references name canonical JSON records, not their formatted files.
    require(analysis["release_sha256"] == parent["sha256"], "canonical parent reference")
    require(analysis["main_summary_sha256"] == summary["sha256"], "canonical summary reference")


def input_audit(source):
    parent = strict_read(source / "scientific_release.json")
    require(parent["release_ready"] and not parent["errors"], "parent not ready")
    check_artifacts(source, parent["artifact_hashes"])
    require(parent["provenance"] == joint.study_provenance(), "frozen source/environment mismatch")
    summary = strict_read(source / "main/summary.json")
    require(summary["release_ready"], "summary not ready")
    old = strict_read(source / "analysis_scientific_release.json")
    check_artifacts(source / "analysis", old["artifact_hashes"])
    analysis = strict_read(source / "analysis/analysis.json")
    check_parent_link(analysis, parent, summary)
    require(old["analysis_sha256"] == analysis["sha256"], "old analysis reference")
    require(old["parent_scientific_release_sha256"] == raw_hash(source / "scientific_release.json"),
            "old release raw parent reference")
    preflight = strict_read(source / "preflight/report.json")
    check_artifacts(source / "preflight", preflight["artifact_hashes"])
    require(preflight["passed"] and not preflight["errors"], "historical preflight failed")
    recovery = strict_read(source / "main/reference_recovery.json")
    require(len(recovery["attempts"]) == recovery["n_attempts"] == recovery["n_recovered"], "recovery count")
    for item in recovery["attempts"]:
        current = strict_read(source / "main/networks" / (item["network_sha256"] + ".json"))
        require(item["reference"] == current["wolfram_reference"], "recovery reference mismatch")
        require(item["reference"]["process_status"] == "normal_exit", "recovery did not exit normally")
    return {"parent_record_sha256": parent["sha256"],
            "parent_file_sha256": raw_hash(source / "scientific_release.json"),
            "summary_record_sha256": summary["sha256"],
            "old_analysis_release_file_sha256": raw_hash(source / "analysis_scientific_release.json"),
            "old_analysis_errors": old["errors"], "frozen_provenance_matches": True,
            "recovery_attempts_verified": len(recovery["attempts"])}


def close(a, b):
    if a is None or b is None:
        return a is b
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    return math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-10)


def worker_init(source):
    global _SOURCE, _MANIFESTS, _EFFECTS
    _SOURCE = Path(source)
    _MANIFESTS = {s: strict_read(_SOURCE / f"{s}_manifest.json") for s in ("main", "pilot")}
    bases = {b["base_id"]: b for b in _MANIFESTS["main"]["bases"]}
    _EFFECTS = {}
    for cat in strict_read(_SOURCE / "main/summary.json")["catalogues"]:
        for effect in cat["effects"]:
            _EFFECTS.setdefault(effect["network_sha256"], []).append(
                (effect, bases[cat["base_id"]]["network_sha256"], cat["target_state"]))


@lru_cache(maxsize=256)
def baseline(key):
    return strict_read(_SOURCE / "main/networks" / f"{key}.json")


def replay_one(job):
    from doppel_challenge.adapters import Network
    from doppel_challenge.program_benchmark import bdm_output_matrix
    from doppel_challenge.repertoire_program import compile_repertoire_program, serialize_program, iter_output_rows
    from doppel_challenge.validation import validate_codec, validate_ncd
    from doppel_challenge.stats import kl, total_variation, jensen_shannon, expected_loss
    stage, key, case = job
    try:
        row = strict_read(_SOURCE / stage / "networks" / f"{key}.json")
        check = joint.validate_joint_record(row, case, _MANIFESTS[stage], replay=True)
        require(check["valid"], f"record replay: {check['errors']}")
        c, rep = row["compression"], row["dynamics"]["repertoire"]
        require(row["wolfram_reference"].get("process_status") == "normal_exit", "Wolfram normal exit")
        net = Network(case["network_size"], case["cm"], case["dyn"], case["params"])
        program = compile_repertoire_program(net)
        require(serialize_program(program).hex() == c["payload_hex"], "fresh program differs")
        require(serialize_program(compile_repertoire_program(net, division_size=net.n)).hex() == c["payload_hex"],
                "division changes program")
        require(len(program.outputs) == net.n, "one ordered output reference per node")
        require(not c["compiler_enumerates_states"] and not c["compiler_materializes_positions"], "compiler scope")
        require(c["raw_bit_length"] == net.n * 2**net.n, "raw bit count")
        require(validate_codec(rep)["valid"], "distribution round trip")
        bdm = bdm_output_matrix(list(iter_output_rows(program)))
        require(bdm["status"] == "completed", f"BDM {bdm['status']}")
        require(bdm["provenance"] == c["bdm_original_output"]["provenance"], "BDM configuration")
        require(close(bdm["value"], c["bdm_original_output"]["value"]), "BDM value")
        if stage == "main":
            for expected, base_key, target in _EFFECTS.get(key, []):
                base = baseline(base_key)
                base_rep, bc = base["dynamics"]["repertoire"], base["compression"]
                k = kl(rep, base_rep)
                actual = {"program_bits": c["program_bit_length"], "raw_bits": c["raw_bit_length"],
                          "bdm": bdm["value"], "delta_program_bits": c["program_bit_length"]-bc["program_bit_length"],
                          "delta_bdm": bdm["value"]-bc["bdm_original_output"]["value"],
                          "total_variation": total_variation(rep, base_rep),
                          "jensen_shannon": jensen_shannon(rep, base_rep), "infinite_kl": k["infinite_kl"],
                          "D_KL_nats": None if k["infinite_kl"] else k["D_KL_nats"],
                          "loss": expected_loss(rep, "L_SINGLE_TARGET", {"targets": [target]})}
                for name, value in actual.items():
                    require(close(value, expected[name]), f"paired metric {name}")
                require(validate_ncd(rep, base_rep)["valid"], "NCD symmetry")
        return {"stage": stage, "network_sha256": key, "valid": True, "record_sha256": row["sha256"],
                "n": net.n, "program_bits": c["program_bit_length"], "raw_bits": c["raw_bit_length"],
                "bdm": bdm["value"], "bdm_padding_bits": bdm["provenance"]["padding_bits"],
                "linear_loss": expected_loss(rep, "L_LINEAR", {"weights": [1/net.n]*net.n})}
    except Exception as exc:
        return {"stage": stage, "network_sha256": key, "valid": False,
                "error": f"{type(exc).__name__}: {exc}"}


def catalogue_audit(source, facts):
    from doppel_challenge.perturbations import ball, perturbation_id, changed_edges
    from doppel_challenge.stats import kl_ball_upper_bound
    summary = strict_read(source / "main/summary.json")
    cats = {(c["base_id"], c["kind"]): c for c in summary["catalogues"]}
    require(len(cats) == len(summary["catalogues"]), "duplicate catalogue summaries")
    frontier_count = 0
    for stage in ("pilot", "main"):
        manifest = strict_read(source / f"{stage}_manifest.json")
        for base in manifest["bases"]:
            for kind, entries in base["catalogues"].items():
                matrices = ball(base["network"]["cm"], 1, kind)
                require(len(entries) == len(matrices), "catalogue count")
                for entry, matrix in zip(entries, matrices):
                    require(entry["perturbation_id"] == perturbation_id(base["network"]["cm"], matrix, kind), "catalogue ID")
                    require(entry["changed_edges"] == changed_edges(base["network"]["cm"], matrix), "changed edges")
                    require(entry["network_sha256"] == joint.network_hash({**base["network"], "cm": matrix}), "candidate network hash")
                    reasons = joint.exclusion_reasons(matrix, base["network"]["dyn"], manifest["policy"])
                    require(entry["exclusion_reasons"] == reasons and entry["admissible"] == (not reasons), "exclusions")
                if stage != "main":
                    continue
                cat = cats.pop((base["base_id"], kind))
                admitted = [e for e in entries if e["admissible"]]
                effects = [e for e in admitted if e["changed_edges"]]
                require(cat["n_admissible"] == len(admitted) and cat["n_excluded"] == len(entries)-len(admitted), "summary denominator")
                require(cat["n_nonidentity"] == len(effects) == len(cat["effects"]), "effect denominator")
                require([(e["perturbation_id"], e["network_sha256"]) for e in effects] ==
                        [(e["perturbation_id"], e["network_sha256"]) for e in cat["effects"]], "effect membership")
                rep = strict_read(source / "main/networks" / f"{base['network_sha256']}.json")["dynamics"]["repertoire"]
                target = rep["support"][base["seed"] % len(rep["support"])]
                require(cat["target_state"] == target, "baseline target")
                for loss, frontiers in cat["sensitivity"].items():
                    params = {"targets": [target]} if loss == "L_SINGLE_TARGET" else {"weights": [1/cat["n"]]*cat["n"]}
                    require([f["C"] for f in frontiers] == manifest["KL_budgets"], "frontier budgets")
                    for f in frontiers:
                        feasible = [e for e in cat["effects"] if not e["infinite_kl"] and e["D_KL_nats"] <= f["C"]+1e-12]
                        score = lambda e: e["loss"] if loss == "L_SINGLE_TARGET" else facts[e["network_sha256"]]["linear_loss"]
                        best = max(feasible, key=lambda e: (score(e), -e["D_KL_nats"]), default=None)
                        require(f["n_candidates"] == len(admitted) and f["n_feasible"] == len(feasible), "frontier denominator")
                        require(f["best_perturbation_id"] == (best["perturbation_id"] if best else None), "frontier argmax")
                        require(close(f["V_k_C"], score(best) if best else None), "frontier value")
                        require(close(f["best_D_KL_nats"], best["D_KL_nats"] if best else None), "frontier KL")
                        upper = kl_ball_upper_bound(rep, f["C"], loss, params)["upper_bound"]
                        require(close(f["upper_bound"], upper), "frontier relaxation")
                        require(best is None or upper is None or score(best) <= upper+1e-9, "relaxation violation")
                        frontier_count += 1
    require(not cats, "unexpected catalogue summary")
    return {"main_catalogues": len(summary["catalogues"]), "frontiers_verified": frontier_count}


def run_audit(source, output, workers):
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    inputs = input_audit(source)
    jobs = []
    for stage in ("pilot", "main"):
        manifest = strict_read(source / f"{stage}_manifest.json")
        planned = list(joint.tasks(manifest))
        require({p.stem for p in (source/stage/"networks").glob("*.json")} == {k for k, _, _ in planned}, "network namespace coverage")
        jobs.extend((stage, key, case) for key, case, _ in planned)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[name] = "1"
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=worker_init, initargs=(str(source),)) as pool:
        for index, row in enumerate(pool.map(replay_one, jobs, chunksize=8), 1):
            rows.append(row)
            if index % 200 == 0 or index == len(jobs):
                progress = {"completed": index, "expected": len(jobs), "failures": sum(not r["valid"] for r in rows),
                            "elapsed_seconds": time.monotonic()-started}
                atomic_write_json(output / "progress.json", seal(progress))
                print(json.dumps(progress), flush=True)
    failures = [r for r in rows if not r["valid"]]
    atomic_write_json(output / "network_replay.json", seal({"record_kind": "final_network_replay", "rows": rows}))
    catalogues = catalogue_audit(source, {r["network_sha256"]: r for r in rows if r["stage"] == "main"}) if not failures else {}
    require(input_audit(source) == inputs, "inputs changed during audit")
    result = seal({"record_kind": "final_exact_audit", "inputs": inputs, "n_replayed": len(rows),
                   "stage_counts": {s: sum(r["stage"] == s for r in rows) for s in ("pilot", "main")},
                   "errors": failures, "passed": not failures, "catalogues": catalogues,
                   "scope": "all output bits, fresh symbolic compilation, independent trajectories, exact codec, BDM recomputation",
                   "wolfram_scope": "historical normal-exit evidence rechecked; no fresh full Wolfram run",
                   "workers": workers, "elapsed_seconds": time.monotonic()-started,
                   "tool_sha256": raw_hash(__file__), "network_replay_file_sha256": raw_hash(output/"network_replay.json")})
    atomic_write_json(output / "audit.json", result)
    require(result["passed"], f"{len(failures)} replay failures")
    return result


METRICS = ["program_bits", "raw_bits", "program_ratio", "bdm", "delta_program_bits", "delta_bdm",
           "total_variation", "jensen_shannon", "finite_kl"]


def base_statistics(effects):
    keys = ["family", "n", "kind", "base_id"]
    return effects.groupby(keys, sort=True)[METRICS].mean().reset_index()


def run_analysis(source, output):
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    audit = strict_read(output / "audit.json")
    require(audit["passed"] and audit["inputs"] == input_audit(source), "audit is not current")
    require(audit["tool_sha256"] == raw_hash(__file__), "audit tool changed; rerun audit")
    require(audit["network_replay_file_sha256"] == raw_hash(output/"network_replay.json"), "replay artifact changed")
    summary = strict_read(source / "main/summary.json")
    rows, empty = [], []
    for cat in summary["catalogues"]:
        if not cat["effects"]:
            empty.append({k: cat[k] for k in ("base_id", "family", "n", "kind", "n_admissible", "n_excluded")})
        for e in cat["effects"]:
            rows.append({**{k: cat[k] for k in ("base_id", "family", "n", "kind")}, **e,
                         "program_ratio": e["program_bits"]/e["raw_bits"], "finite_kl": not e["infinite_kl"]})
    effects = pd.DataFrame(rows)
    old = pd.read_csv(source / "analysis/effect_rows.csv")
    identity = ["base_id", "kind", "perturbation_id"]
    require(not effects.duplicated(identity).any() and not old.duplicated(identity).any(), "duplicate effect CSV rows")
    a, b = effects.set_index(identity).sort_index(), old.set_index(identity).sort_index()
    require(a.index.equals(b.index), "historical CSV membership mismatch")
    for col in set(a.columns) & set(b.columns):
        if pd.api.types.is_numeric_dtype(a[col]) and pd.api.types.is_numeric_dtype(b[col]):
            require(np.allclose(a[col], b[col], rtol=1e-11, atol=1e-10, equal_nan=True), f"historical CSV metric: {col}")
        else:
            require(a[col].equals(b[col]), f"historical CSV field: {col}")
    bases = base_statistics(effects)
    group_rows, correlations = [], []
    for index, ((family, n, kind), group) in enumerate(bases.groupby(["family", "n", "kind"], sort=True)):
        row = {"family": family, "n": int(n), "kind": kind, "n_bases": len(group),
               "n_effects": int(((effects.family == family) & (effects.n == n) & (effects.kind == kind)).sum())}
        rng = np.random.default_rng(20260911+index)
        samples = rng.integers(0, len(group), size=(5000, len(group)))
        for metric in METRICS:
            values = group[metric].to_numpy(float)
            lo, hi = np.quantile(values[samples].mean(axis=1), [.025, .975])
            row.update({f"mean_{metric}": float(values.mean()), f"{metric}_lo95": float(lo), f"{metric}_hi95": float(hi)})
        group_rows.append(row)
        for x, y in (("delta_program_bits", "delta_bdm"), ("delta_program_bits", "total_variation"), ("delta_bdm", "total_variation")):
            rho = group[x].rank().corr(group[y].rank()) if group[x].nunique() > 1 and group[y].nunique() > 1 else None
            correlations.append({"family": family, "n": int(n), "kind": kind, "n_bases": len(group),
                                 "x": x, "y": y, "spearman_base_means": rho})
    groups = pd.DataFrame(group_rows)
    effects.to_csv(output / "effect_rows.csv", index=False)
    bases.to_csv(output / "base_means.csv", index=False)
    groups.to_csv(output / "group_summary.csv", index=False)
    pd.DataFrame(correlations).to_csv(output / "base_correlations.csv", index=False)
    replay = strict_read(output / "network_replay.json")
    networks = pd.DataFrame([r for r in replay["rows"] if r["stage"] == "main"])
    networks.to_csv(output / "network_metrics.csv", index=False)
    # Panel units are explicit; BDM is never plotted as program bytes or bits.
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), constrained_layout=True)
    sizes = sorted(networks.n.unique())
    for ax, metric, title in zip(axes, ["program_bits", "bdm", "bdm_padding_bits"],
                                ["Shared program and raw output (bits)", "BDM on original output matrix (BDM units)", "Zero padding for BDM (bits)"]):
        ax.boxplot([networks.loc[networks.n == n, metric] for n in sizes], tick_labels=[str(n) for n in sizes], showfliers=False)
        ax.set(xlabel="Network size N", title=title)
    axes[0].plot(range(1, len(sizes)+1), [int(n)*2**int(n) for n in sizes], "o--", color="black", label="Raw N × 2^N")
    axes[0].set_yscale("log"); axes[0].legend()
    fig.savefig(output / "lengths_and_bdm.png", dpi=180); fig.savefig(output / "lengths_and_bdm.svg"); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    for kind, color in (("EDGE_ADD", "#2864ad"), ("EDGE_REMOVE", "#bd572c")):
        subset = bases[bases.kind == kind]
        for ax, x, y in zip(axes, ["delta_program_bits", "delta_program_bits", "delta_bdm"],
                            ["delta_bdm", "total_variation", "total_variation"]):
            ax.scatter(subset[x], subset[y], label=kind, color=color, alpha=.55, s=16)
            ax.set(xlabel=x.replace("_", " "), ylabel=y.replace("_", " "))
    axes[0].legend(); fig.suptitle("Each point is one base mean within one perturbation kind; descriptive only")
    fig.savefig(output / "base_associations.png", dpi=180); fig.savefig(output / "base_associations.svg"); plt.close(fig)
    result = seal({"record_kind": "final_descriptive_analysis", "audit_sha256": audit["sha256"],
                   "parent_record_sha256": audit["inputs"]["parent_record_sha256"],
                   "n_networks": len(networks), "n_bases": int(effects.base_id.nunique()),
                   "n_catalogues": len(summary["catalogues"]), "n_nonempty_catalogues": len(bases), "n_effects": len(effects),
                   "empty_catalogues": empty, "group_summary": group_rows, "correlations": correlations,
                   "weighting": "equal base means within each family/N/kind; no pooled primary estimate",
                   "bootstrap": {"resamples": 5000, "seed": "20260911 + sorted stratum index", "interval": "percentile 95%", "scope": "descriptive base sampling stability"},
                   "historical_pooled_effect_mean_ratio": float(effects.program_ratio.mean()),
                   "all_main_programs_shorter_than_raw": bool((networks.program_bits < networks.raw_bits).all()),
                   "bdm": {"version": "0.1.0", "block_shape": [4, 4], "partition": "PartitionIgnore", "N10_padding_bits": 2048},
                   "tool_sha256": raw_hash(__file__)})
    atomic_write_json(output / "analysis.json", result)
    lines = ["# Final descriptive analysis of the degree-five study", "",
             "Release status is determined by release.json after fresh tests and executed notebooks; this report alone does not certify readiness.", "",
             f"Verified main sample: {len(networks):,} unique networks from 240 bases; 480 catalogue definitions, {len(bases)} nonempty catalogues, and {len(effects):,} paired effects.", "",
             "Every input row is implicit and ordered LSB-first. One shared executable program per network reconstructs all output rows. Raw is already binary: N × 2^N bits. Program length includes the declared decoding structure; N and the fixed decoder are shared conventions. This is a code length for the declared method and variable order, not universal Kolmogorov complexity or a guaranteed shortest program.", "",
             "Fresh verification recompiled every pilot/main program, replayed independent trajectories, reconstructed all output bits, and recomputed BDM. Historical Wolfram normal-exit evidence was checked against those outputs; the full Wolfram experiment was not rerun.", "",
             "BDM uses pybdm 0.1.0, non-overlapping 4×4 blocks and PartitionIgnore after explicit bottom/right zero padding. N=10 uses a 1024×12 padded matrix (2,048 extra zeros); N=8 and N=12 need no padding. This convention is part of the BDM comparison and limits cross-size interpretation. BDM units are displayed separately from program bits.", "",
             "All main-sample programs are shorter than their raw output matrices. This is evidence for this bounded-degree sample; the fixed indegree of five strongly limits local Boolean function size and the result does not establish unrestricted large-network scaling.", "",
             "The old headline ratio of %.4f%% is a pooled perturbation-row average. It gives more weight to bases with more admissible perturbations. Primary results below instead average within each base and then equally across bases within each family, N and perturbation kind. Additions and removals stay separate." % (100*effects.program_ratio.mean()), "",
             "The intervals use 5,000 deterministic base resamples within each stratum. They describe stability across the sampled bases; the analysis was developed after inspecting results and is not a preregistered confirmatory inference. No perturbation-level p-values are reported. Cross-kind points from the same base are dependent.", "",
             "modular_n8_s15 has no admissible nonidentity removal. It remains a declared catalogue and has no defined mean removal effect; that stratum has 19 contributing bases.", "",
             "| Family | N | Kind | Bases | Program/raw mean [95% interval] | Mean program change (bits) | Mean BDM change | Mean TV |", "|---|---:|---|---:|---:|---:|---:|---:|"]
    for r in group_rows:
        lines.append(f"| {r['family']} | {r['n']} | {r['kind']} | {r['n_bases']} | {100*r['mean_program_ratio']:.2f}% [{100*r['program_ratio_lo95']:.2f}, {100*r['program_ratio_hi95']:.2f}] | {r['mean_delta_program_bits']:.2f} | {r['mean_delta_bdm']:.2f} | {r['mean_total_variation']:.3f} |")
    lines += ["", "![Lengths and BDM](lengths_and_bdm.png)", "", "![Base mean associations](base_associations.png)", "",
              "Base-level Spearman associations are tabulated separately within each family/N/kind in base_correlations.csv. The scatter plots pool strata for visualization only. Compression, BDM and long-run dynamics measure different properties; no equivalence, mechanism identification, or detector performance follows from these associations.", "",
              "The canonical-parent-reference correction is documented in audit.json. Original analysis and failed release artifacts are retained in the parent directory. New release.json seals this analysis and its verification evidence."]
    (output / "report.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({k:result[k] for k in ("n_networks", "n_bases", "n_catalogues", "n_effects")}), flush=True)
    return result


def notebook_complete(path):
    book = json.loads(Path(path).read_text())
    cells = [c for c in book["cells"] if c["cell_type"] == "code" and "".join(c["source"]).strip()]
    return bool(cells) and all(c.get("execution_count") is not None for c in cells) and not any(
        o.get("output_type") == "error" for c in cells for o in c.get("outputs", []))


def run_verification(source, output):
    audit = strict_read(output / "audit.json")
    analysis = strict_read(output / "analysis.json")
    require(audit["passed"] and audit["inputs"] == input_audit(source), "stale audit")
    require(analysis["audit_sha256"] == audit["sha256"], "analysis audit link")
    require(analysis["tool_sha256"] == audit["tool_sha256"] == raw_hash(__file__), "changed audit tool")
    require(audit["network_replay_file_sha256"] == raw_hash(output/"network_replay.json"), "changed replay artifact")
    env = dict(os.environ, PYTHONPATH=str(ROOT/"doppel-challenge/src"), MPLBACKEND="Agg")
    commands = [[sys.executable, "-m", "pytest", "doppel-challenge/tests", "tests/analysis/test_description_length_is_algorithmic.py",
                 "tests/analysis/test_description_lengths_values.py", "tools/joint_finalization/test_finalize.py", "-q", f"--junitxml={output/'pytest.xml'}"]]
    books = [ROOT/"doppel-challenge/notebooks"/name for name in ("01_exact_n8_walkthrough.ipynb", "02-pre-analysis.ipynb", "03-final-analysis.ipynb")]
    for book in books:
        commands.append([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--ExecutePreprocessor.timeout=300",
                         "--output", str(output/(book.stem+".executed.ipynb")), str(book)])
    errors = []
    for i, command in enumerate(commands):
        print(f"Verification {i+1}/{len(commands)}: {' '.join(command)}", flush=True)
        try:
            proc = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=1800)
            log = {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
            if proc.returncode:
                errors.append(f"command_{i}_failed")
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"command_{i}_error")
            log = {"command": command, "error": str(exc)}
        atomic_write_json(output/f"verification_{i}.json", seal(log))
    counts = {}
    try:
        suites = list(ET.parse(output/"pytest.xml").getroot().iter("testsuite"))
        counts = {k: sum(int(s.get(k, "0")) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
        require(counts["tests"] > 0 and all(counts[k] == 0 for k in ("failures", "errors", "skipped")), "tests failed/skipped")
        for book in books:
            require(notebook_complete(output/(book.stem+".executed.ipynb")), f"incomplete notebook: {book.name}")
        require(input_audit(source) == audit["inputs"], "inputs changed during verification")
    except (OSError, ValueError, ET.ParseError) as exc:
        errors.append(str(exc))
    from doppel_challenge.program_benchmark import validate_program_benchmark
    from doppel_challenge.release import run_release_gate
    benchmark = strict_read(ROOT/"doppel-challenge/results/shared_program/shared_program_benchmark.json")
    if not validate_program_benchmark(benchmark)["valid"] or not benchmark["release_ready"]:
        errors.append("shared_program_benchmark_failed")
    if run_release_gate(ROOT/"doppel-challenge/results/exact_small")["status"] != "passed":
        errors.append("historical_exact_release_failed")
    artifact_hashes = {p.name: raw_hash(p) for p in sorted(output.iterdir()) if p.is_file() and p.name not in ("release.json", "progress.json")}
    release = seal({"record_kind": "final_analysis_release", "release_ready": not errors, "errors": errors, "tests": counts,
                    "audit_sha256": audit["sha256"], "analysis_sha256": analysis["sha256"],
                    "parent_record_sha256": audit["inputs"]["parent_record_sha256"],
                    "parent_file_sha256": audit["inputs"]["parent_file_sha256"],
                    "artifact_hashes": artifact_hashes,
                    "source_hashes": {str(p.relative_to(ROOT)): raw_hash(p) for p in [Path(__file__), HERE/"README.md", HERE/"test_finalize.py", *books]},
                    "claim_scope": "completed frozen N8/10/12 degree-five study; descriptive base-weighted analysis; no additional experiment or unrestricted scaling claim"})
    atomic_write_json(output/"release.json", release)
    check_artifacts(output, release["artifact_hashes"])
    print(json.dumps({k: release[k] for k in ("release_ready", "errors", "tests")}, indent=2), flush=True)
    require(release["release_ready"], "final verification failed")
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("audit", "analyze", "verify"), required=True)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out-dir", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    require(args.source.resolve() != args.out_dir.resolve(), "output cannot be the parent experiment")
    if args.action == "audit":
        run_audit(args.source, args.out_dir, args.workers)
    elif args.action == "analyze":
        run_analysis(args.source, args.out_dir)
    else:
        run_verification(args.source, args.out_dir)


if __name__ == "__main__":
    main()
