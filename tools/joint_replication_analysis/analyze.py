"""Fresh audit, analysis and release gate for the completed final replication."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from doppel_challenge.io import atomic_write_json, read_json
from doppel_challenge.records import compute_sha256, seal, scientific_digest
from doppel_challenge import joint_study as joint

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "doppel-challenge/results/joint_degree5_final_replication_v1"
OUTPUT = ROOT / "doppel-challenge/results/joint_degree5_final_replication_analysis_v1"
HERE = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "joint_finalization_base", ROOT / "tools/joint_finalization/finalize.py"
)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
_controller_spec = importlib.util.spec_from_file_location(
    "joint_final_phase_controller", ROOT / "tools/joint_final_phase/run.py"
)
controller = importlib.util.module_from_spec(_controller_spec)
_controller_spec.loader.exec_module(controller)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_read(path):
    value = read_json(path)
    require(value["sha256"] == compute_sha256(value), f"canonical seal: {path}")
    require(value["scientific_digest"] == scientific_digest(value), f"scientific seal: {path}")
    return value


def source_audit(source):
    protocol = strict_read(source / "protocol.json")
    main_manifest = strict_read(source / "main_manifest.json")
    pilot_manifest = strict_read(source / "pilot_manifest.json")
    require(protocol["manifests"] == {"main": main_manifest["sha256"], "pilot": pilot_manifest["sha256"]},
            "protocol manifest links")
    require(protocol["study_provenance"] == joint.study_provenance(), "study source provenance")
    require(protocol["controller_sources"] == __import_controller_sources(), "controller provenance")
    previous = controller.previous_release()
    require(protocol["previous_final_release_sha256"] == previous["sha256"], "previous release link")
    for stage, manifest in (("pilot", pilot_manifest), ("main", main_manifest)):
        audit = strict_read(source / stage / "audit.json")
        summary = strict_read(source / stage / "summary.json")
        require(audit["release_ready"] and not audit["errors"], f"{stage} audit")
        require(audit["manifest_sha256"] == manifest["sha256"], f"{stage} audit manifest")
        require(summary["release_ready"] and summary["manifest_sha256"] == manifest["sha256"], f"{stage} summary")
        require(len(summary["catalogues"]) == 2 * len(manifest["bases"]), f"{stage} catalogue count")
    amendment = strict_read(source / "reference_recovery/amendment.json")
    require(amendment["protocol_sha256"] == protocol["sha256"], "recovery protocol link")
    recovery_reports = sorted((source / "reference_recovery").glob("batch_*/report.json"))
    require(len(recovery_reports) == 1, "recovery batch count")
    recovery = strict_read(recovery_reports[0])
    require(recovery["passed"] and recovery["n_recovered"] == 48, "recovery report")
    plan = strict_read(recovery_reports[0].parent / "plan.json")
    require(recovery["plan_sha256"] == plan["sha256"], "recovery plan link")
    base.check_artifacts(recovery_reports[0].parent / "original", plan["archive_hashes"])
    for key, digest in recovery["replacements"].items():
        row = strict_read(source / "main/networks" / f"{key}.json")
        require(row["sha256"] == digest and row["accepted_validation"], "recovered record")
        require(row["reference_recovery"]["amendment_sha256"] == amendment["sha256"], "recovery amendment link")
    return {
        "protocol_sha256": protocol["sha256"],
        "main_manifest_sha256": main_manifest["sha256"],
        "pilot_manifest_sha256": pilot_manifest["sha256"],
        "main_audit_sha256": strict_read(source / "main/audit.json")["sha256"],
        "main_summary_sha256": strict_read(source / "main/summary.json")["sha256"],
        "pilot_audit_sha256": strict_read(source / "pilot/audit.json")["sha256"],
        "pilot_summary_sha256": strict_read(source / "pilot/summary.json")["sha256"],
        "recovery_amendment_sha256": amendment["sha256"],
        "recovery_report_sha256": recovery["sha256"],
        "previous_final_release_sha256": previous["sha256"],
    }


def __import_controller_sources():
    controller = ROOT / "tools/joint_final_phase"
    return {str(p.relative_to(ROOT)): raw_hash(p) for p in
            (controller / "run.py", controller / "test_run.py", controller / "PROTOCOL.md")}


def worker_init(source):
    base._SOURCE = Path(source)
    base._MANIFESTS = {s: strict_read(base._SOURCE / f"{s}_manifest.json") for s in ("main", "pilot")}
    bases = {b["base_id"]: b for b in base._MANIFESTS["main"]["bases"]}
    summary = strict_read(base._SOURCE / "main/summary.json")
    base._EFFECTS = {}
    for catalogue in summary["catalogues"]:
        for effect in catalogue["effects"]:
            base._EFFECTS.setdefault(effect["network_sha256"], []).append(
                (effect, bases[catalogue["base_id"]]["network_sha256"], catalogue["target_state"])
            )


def replay_job(job):
    """Module-local wrapper so ProcessPool pickling does not expose the dynamic import."""
    return base.replay_one(job)


def run_replay(source, output, workers=8):
    started = time.monotonic()
    jobs = []
    for stage in ("pilot", "main"):
        manifest = strict_read(source / f"{stage}_manifest.json")
        planned = list(joint.tasks(manifest))
        actual = {p.stem for p in (source / stage / "networks").glob("*.json")}
        require(actual == {key for key, _, _ in planned}, f"{stage} network namespace")
        jobs.extend((stage, key, case) for key, case, _ in planned)
    rows = []
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[name] = "1"
    with ProcessPoolExecutor(max_workers=workers, initializer=worker_init, initargs=(str(source),)) as pool:
        for index, row in enumerate(pool.map(replay_job, jobs, chunksize=8), 1):
            rows.append(row)
            if index % 1000 == 0 or index == len(jobs):
                progress = seal({"record_kind": "replication_replay_progress", "completed": index,
                                 "expected": len(jobs), "failures": sum(not item["valid"] for item in rows),
                                 "elapsed_seconds": time.monotonic() - started})
                atomic_write_json(output / "progress.json", progress)
                print(json.dumps({k: progress[k] for k in ("completed", "expected", "failures", "elapsed_seconds")}), flush=True)
    failures = [row for row in rows if not row["valid"]]
    replay = seal({"record_kind": "final_replication_network_replay", "rows": rows,
                   "n_replayed": len(rows), "n_failures": len(failures), "scope": "fresh compilation, exact decoder, dynamics, BDM and historical Wolfram digest"})
    atomic_write_json(output / "network_replay.json", replay)
    return replay


def catalogue_audit(source, facts):
    summary = strict_read(source / "main/summary.json")
    manifests = {s: strict_read(source / f"{s}_manifest.json") for s in ("main", "pilot")}
    catalogues = {(cat["base_id"], cat["kind"]): cat for cat in summary["catalogues"]}
    require(len(catalogues) == len(summary["catalogues"]), "duplicate catalogue keys")
    frontiers = 0
    from doppel_challenge.perturbations import ball, changed_edges, perturbation_id
    from doppel_challenge.stats import kl_ball_upper_bound
    for base_row in manifests["main"]["bases"]:
        for kind, entries in base_row["catalogues"].items():
            cat = catalogues.pop((base_row["base_id"], kind))
            matrices = ball(base_row["network"]["cm"], 1, kind)
            require(len(entries) == len(matrices), "catalogue matrix count")
            for entry, matrix in zip(entries, matrices):
                require(entry["perturbation_id"] == perturbation_id(base_row["network"]["cm"], matrix, kind), "catalogue ID")
                require(entry["changed_edges"] == changed_edges(base_row["network"]["cm"], matrix), "catalogue edges")
                require(entry["network_sha256"] == joint.network_hash({**base_row["network"], "cm": matrix}), "catalogue network hash")
                reasons = joint.exclusion_reasons(matrix, base_row["network"]["dyn"], manifests["main"]["policy"])
                require(entry["exclusion_reasons"] == reasons and entry["admissible"] == (not reasons), "catalogue exclusion")
            admissible = [entry for entry in entries if entry["admissible"]]
            effects = [entry for entry in admissible if entry["changed_edges"]]
            require(cat["n_admissible"] == len(admissible) and cat["n_excluded"] == len(entries) - len(admissible), "catalogue denominator")
            require(cat["n_nonidentity"] == len(effects) == len(cat["effects"]), "effect denominator")
            require([(x["perturbation_id"], x["network_sha256"]) for x in effects] ==
                    [(x["perturbation_id"], x["network_sha256"]) for x in cat["effects"]], "effect membership")
            baseline = strict_read(source / "main/networks" / f"{base_row['network_sha256']}.json")
            repertoire = baseline["dynamics"]["repertoire"]
            target = repertoire["support"][base_row["seed"] % len(repertoire["support"])]
            require(cat["target_state"] == target, "target selection")
            for loss, frontiers_list in cat["sensitivity"].items():
                params = {"targets": [target]} if loss == "L_SINGLE_TARGET" else {"weights": [1 / cat["n"]] * cat["n"]}
                for frontier in frontiers_list:
                    feasible = [e for e in cat["effects"] if not e["infinite_kl"] and e["D_KL_nats"] <= frontier["C"] + 1e-12]
                    score = lambda e: e["loss"] if loss == "L_SINGLE_TARGET" else facts[e["network_sha256"]]["linear_loss"]
                    best = max(feasible, key=lambda e: (score(e), -e["D_KL_nats"]), default=None)
                    require(frontier["n_candidates"] == len(admissible) and frontier["n_feasible"] == len(feasible), "frontier counts")
                    require(frontier["best_perturbation_id"] == (best["perturbation_id"] if best else None), "frontier selection")
                    require(base.close(frontier["V_k_C"], score(best) if best else None), "frontier value")
                    require(base.close(frontier["best_D_KL_nats"], best["D_KL_nats"] if best else None), "frontier KL")
                    upper = kl_ball_upper_bound(repertoire, frontier["C"], loss, params)["upper_bound"]
                    require(base.close(frontier["upper_bound"], upper), "frontier bound")
                    require(best is None or upper is None or score(best) <= upper + 1e-9, "frontier exceeds bound")
                    frontiers += 1
    require(not catalogues, "unvisited catalogue summaries")
    return {"catalogues": len(summary["catalogues"]), "frontiers": frontiers}


METRICS = base.METRICS


def make_analysis(source, output, audit, replay):
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    summary = strict_read(source / "main/summary.json")
    rows, empty = [], []
    for cat in summary["catalogues"]:
        if not cat["effects"]:
            empty.append({k: cat[k] for k in ("base_id", "family", "n", "kind", "n_admissible", "n_excluded")})
        for effect in cat["effects"]:
            rows.append({**{k: cat[k] for k in ("base_id", "family", "n", "kind")}, **effect,
                         "program_ratio": effect["program_bits"] / effect["raw_bits"],
                         "finite_kl": not effect["infinite_kl"]})
    effects = pd.DataFrame(rows)
    bases = base.base_statistics(effects)
    groups = []
    correlations = []
    for index, ((family, n, kind), group) in enumerate(bases.groupby(["family", "n", "kind"], sort=True)):
        row = {"family": family, "n": int(n), "kind": kind, "n_bases": len(group),
               "n_effects": int(((effects.family == family) & (effects.n == n) & (effects.kind == kind)).sum())}
        rng = np.random.default_rng(20260911 + index)
        sample_indices = rng.integers(0, len(group), size=(5000, len(group)))
        for metric in METRICS:
            values = group[metric].to_numpy(float)
            lo, hi = np.quantile(values[sample_indices].mean(axis=1), [.025, .975])
            row.update({f"mean_{metric}": float(values.mean()), f"{metric}_lo95": float(lo), f"{metric}_hi95": float(hi)})
        groups.append(row)
        for x, y in (("delta_program_bits", "delta_bdm"), ("delta_program_bits", "total_variation"), ("delta_bdm", "total_variation")):
            rho = group[x].rank().corr(group[y].rank()) if group[x].nunique() > 1 and group[y].nunique() > 1 else None
            correlations.append({"family": family, "n": int(n), "kind": kind, "n_bases": len(group), "x": x, "y": y,
                                 "spearman_base_means": None if rho is None or not math.isfinite(rho) else float(rho)})
    bases.to_csv(output / "base_means.csv", index=False)
    effects.to_csv(output / "effect_rows.csv", index=False)
    pd.DataFrame(groups).to_csv(output / "group_summary.csv", index=False)
    pd.DataFrame(correlations).to_csv(output / "base_correlations.csv", index=False)
    network_rows = [r for r in replay["rows"] if r["stage"] == "main"]
    networks = pd.DataFrame(network_rows)
    networks["program_ratio"] = networks["program_bits"] / networks["raw_bits"]
    networks.to_csv(output / "network_metrics.csv", index=False)
    old_groups = pd.read_csv(ROOT / "doppel-challenge/results/joint_degree5_final_analysis_v1/group_summary.csv")
    new_groups = pd.DataFrame(groups)
    compare = new_groups.merge(old_groups, on=["family", "n", "kind"], suffixes=("_replication", "_previous"))
    for field in ("mean_program_ratio", "mean_delta_program_bits", "mean_delta_bdm", "mean_total_variation", "mean_jensen_shannon", "mean_finite_kl"):
        compare[f"change_{field}"] = compare[f"{field}_replication"] - compare[f"{field}_previous"]
    compare.to_csv(output / "comparison_with_previous.csv", index=False)
    sizes = sorted(networks.n.unique())
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), constrained_layout=True)
    for ax, metric, title in zip(axes, ["program_bits", "bdm", "bdm_padding_bits"],
                                ["Shared program and raw output (bits)", "BDM on original output matrix (BDM units)", "Zero padding for BDM (bits)"]):
        ax.boxplot([networks.loc[networks.n == n, metric] for n in sizes], tick_labels=[str(n) for n in sizes], showfliers=False)
        ax.set(xlabel="Network size N", title=title)
    axes[0].plot(range(1, len(sizes) + 1), [int(n) * 2**int(n) for n in sizes], "o--", color="black", label="Raw N × 2^N")
    axes[0].set_yscale("log")
    axes[0].legend()
    fig.savefig(output / "lengths_and_bdm.png", dpi=180)
    fig.savefig(output / "lengths_and_bdm.svg")
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    for kind, color in (("EDGE_ADD", "#2864ad"), ("EDGE_REMOVE", "#bd572c")):
        subset = bases[bases.kind == kind]
        for ax, x, y in zip(axes, ["delta_program_bits", "delta_program_bits", "delta_bdm"],
                            ["delta_bdm", "total_variation", "total_variation"]):
            ax.scatter(subset[x], subset[y], label=kind, color=color, alpha=.55, s=16)
            ax.set(xlabel=x.replace("_", " "), ylabel=y.replace("_", " "))
    axes[0].legend()
    fig.suptitle("Replication base means; descriptive comparison")
    fig.savefig(output / "base_associations.png", dpi=180)
    fig.savefig(output / "base_associations.svg")
    plt.close(fig)
    result = seal({"record_kind": "final_replication_descriptive_analysis", "audit_sha256": audit["sha256"],
                   "source_main_summary_sha256": strict_read(source / "main/summary.json")["sha256"],
                   "n_networks": len(networks), "n_bases": int(len(strict_read(source / "main_manifest.json")["bases"])),
                   "n_catalogues": len(summary["catalogues"]), "n_nonempty_catalogues": len(bases), "n_effects": len(effects),
                   "empty_catalogues": empty, "group_summary": groups, "correlations": correlations,
                   "weighting": "equal base means within family/N/kind; additions and removals separate",
                   "bootstrap": {"resamples": 5000, "seed": "20260911 + sorted stratum index", "interval": "percentile 95%",
                                 "scope": "descriptive stability across new base draws"},
                   "previous_comparison": {"previous_release": "joint_degree5_final_analysis_v1", "file": "comparison_with_previous.csv"},
                   "all_main_programs_shorter_than_raw": bool((networks.program_bits < networks.raw_bits).all()),
                   "bdm": {"version": "0.1.0", "block_shape": [4, 4], "partition": "PartitionIgnore", "N10_padding_bits": 2048},
                   "tool_sha256": raw_hash(__file__)})
    atomic_write_json(output / "analysis.json", result)
    lines = ["# Final independent replication analysis", "",
             "The computation and fresh network replay passed before this descriptive analysis was generated.", "",
             f"Main sample: {len(networks):,} accepted unique networks from 1,200 base draws; {len(summary['catalogues']):,} catalogue definitions; {len(bases):,} nonempty catalogues; {len(effects):,} paired effects.", "",
             "One shared program per network reconstructs the complete ordered one-step output matrix. Raw length is already binary: N × 2^N bits. Program length is the logical length of the declared executable codec with implicit ordered input addresses, shared N and fixed decoder conventions. It is an algorithmic description length for this method, not universal Kolmogorov complexity.", "",
             "BDM is computed on the original output matrix with pybdm 0.1.0, non-overlapping 4×4 blocks and PartitionIgnore. Bottom/right zero padding is explicit; N=10 adds 2,048 padding bits, while N=8 and N=12 require none. BDM units are not program bits.", "",
             "Effects are averaged within each base and then equally across bases within each family, size and perturbation kind. The 5,000-resample intervals describe stability over the generated base draws. Perturbations are not independent replicates and this is not a confirmatory hypothesis test.", "",
             "The previous released study is compared stratum by stratum in comparison_with_previous.csv. These comparisons are descriptive replication checks; the two studies are not pooled into one estimate.", "",
             "| Family | N | Kind | Bases | Program/raw mean [95% interval] | Program change (bits) | BDM change | TV |", "|---|---:|---|---:|---:|---:|---:|---:|"]
    for row in groups:
        lines.append(f"| {row['family']} | {row['n']} | {row['kind']} | {row['n_bases']} | {100*row['mean_program_ratio']:.2f}% [{100*row['program_ratio_lo95']:.2f}, {100*row['program_ratio_hi95']:.2f}] | {row['mean_delta_program_bits']:.2f} | {row['mean_delta_bdm']:.2f} | {row['mean_total_variation']:.3f} |")
    lines += ["", "![Lengths and BDM](lengths_and_bdm.png)", "", "![Base associations](base_associations.png)", "",
              "The final release requires the executed replication notebook, tests, artifact hashes and this replay evidence. No universal scaling or universal Kolmogorov claim follows."]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    return result


def notebook_complete(path):
    book = json.loads(Path(path).read_text())
    cells = [c for c in book["cells"] if c["cell_type"] == "code" and "".join(c["source"]).strip()]
    return bool(cells) and all(c.get("execution_count") is not None for c in cells) and not any(
        o.get("output_type") == "error" for c in cells for o in c.get("outputs", []))


def verify(source, output):
    audit = strict_read(output / "audit.json")
    analysis = strict_read(output / "analysis.json")
    require(audit["passed"] and analysis["audit_sha256"] == audit["sha256"], "stale final analysis")
    require(audit["replay_sha256"] == raw_hash(output / "network_replay.json"), "replay hash")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "doppel-challenge/src"), MPLBACKEND="Agg")
    commands = [[sys.executable, "-m", "pytest", "doppel-challenge/tests",
                 "tests/analysis/test_description_length_is_algorithmic.py",
                 "tests/analysis/test_description_lengths_values.py",
                 "tools/joint_final_phase/test_run.py", "tools/joint_reference_recovery/test_recover.py", "-q",
                 f"--junitxml={output/'pytest.xml'}"]]
    notebook = ROOT / "doppel-challenge/notebooks/04-final-replication-analysis.ipynb"
    commands.append([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                     "--ExecutePreprocessor.timeout=300", "--output", str(output / "04-final-replication-analysis.executed.ipynb"), str(notebook)])
    errors = []
    for index, command in enumerate(commands):
        try:
            process = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=1800)
            record = {"record_kind": "replication_verification_command", "command": command,
                      "returncode": process.returncode, "stdout": process.stdout, "stderr": process.stderr}
            if process.returncode:
                errors.append(f"command_{index}_failed")
        except (OSError, subprocess.TimeoutExpired) as exc:
            record = {"record_kind": "replication_verification_command", "command": command, "error": str(exc)}
            errors.append(f"command_{index}_error")
        atomic_write_json(output / f"verification_{index}.json", seal(record))
    counts = {}
    try:
        suites = list(ET.parse(output / "pytest.xml").getroot().iter("testsuite"))
        counts = {key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")}
        require(counts["tests"] and not any(counts[key] for key in ("failures", "errors", "skipped")), "tests failed")
        require(notebook_complete(output / "04-final-replication-analysis.executed.ipynb"), "notebook incomplete")
        require(source_audit(source) == audit["source"], "source changed during verification")
    except (OSError, ValueError, ET.ParseError) as exc:
        errors.append(str(exc))
    release_artifacts = {path.name: raw_hash(path) for path in sorted(output.iterdir())
                         if path.is_file() and path.name not in {"release.json", "progress.json"}}
    release = seal({"record_kind": "final_replication_analysis_release", "release_ready": not errors,
                    "errors": errors, "tests": counts, "source": audit["source"],
                    "audit_sha256": audit["sha256"], "analysis_sha256": analysis["sha256"],
                    "artifact_hashes": release_artifacts,
                    "source_hashes": {str(path.relative_to(ROOT)): raw_hash(path) for path in
                                      (Path(__file__), HERE / "README.md", notebook)},
                    "claim_scope": "independent descriptive replication of frozen N8/10/12 degree-five study; no universal complexity or unrestricted scaling claim"})
    atomic_write_json(output / "release.json", release)
    for name, digest in release_artifacts.items():
        require(raw_hash(output / name) == digest, f"release artifact changed: {name}")
    print(json.dumps({key: release[key] for key in ("release_ready", "errors", "tests")}, indent=2))
    require(release["release_ready"], "replication release failed")
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("audit", "analyze", "verify"), required=True)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out-dir", type=Path, default=OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.action == "audit":
        source = source_audit(args.source)
        replay = run_replay(args.source, args.out_dir, args.workers)
        require(replay["n_failures"] == 0, "fresh replay failures")
        facts = {row["network_sha256"]: row for row in replay["rows"] if row["stage"] == "main"}
        cats = catalogue_audit(args.source, facts)
        audit = seal({"record_kind": "final_replication_audit", "source": source,
                      "n_replayed": replay["n_replayed"], "n_failures": replay["n_failures"],
                      "replay_sha256": raw_hash(args.out_dir / "network_replay.json"), "catalogues": cats,
                      "passed": True, "scope": "fresh compilation, decoder, dynamics, BDM, Wolfram digests and catalogue frontiers",
                      "workers": args.workers})
        atomic_write_json(args.out_dir / "audit.json", audit)
        print(json.dumps({key: audit[key] for key in ("passed", "n_replayed", "n_failures", "catalogues")}, indent=2))
    elif args.action == "analyze":
        source = source_audit(args.source)
        audit = strict_read(args.out_dir / "audit.json")
        replay = strict_read(args.out_dir / "network_replay.json")
        require(audit["passed"] and audit["source"] == source, "audit is stale")
        require(audit["replay_sha256"] == raw_hash(args.out_dir / "network_replay.json"), "replay is stale")
        analysis = make_analysis(args.source, args.out_dir, audit, replay)
        print(json.dumps({key: analysis[key] for key in ("n_networks", "n_bases", "n_catalogues", "n_effects")}, indent=2))
    else:
        verify(args.source, args.out_dir)


if __name__ == "__main__":
    main()
