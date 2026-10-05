"""Execute notebook 22 under the reviewed artifact-only guard and save its checks.

    (from index-deconvolution/) ../venv/bin/python -B experiments/hierarchy_dictionary/notebook22.py TAG

Reuses ``run``/``texts``/``sha_file`` from the reviewed harness
results/hierarchy_search_v2/review_closure/scripts/execute_notebook_artifact_only.py
(import gate: only hierarchy.{decode,ledger,codes,model}; no src imports; no writes below
results/; no subprocess) and ``coalesced`` (adjacent same-name stream messages joined)
from the multilevel-v1 driver. Executes from the notebook directory and from the
repository root, compares the two, checks that saved values are displayed, and writes the
deliverable notebook (the notebook-directory execution) plus records under the run's
``notebook/`` directory. A post-lock presentation adapter; it reads saved artifacts only.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import nbformat

sys.dont_write_bytecode = True
ID = Path(__file__).resolve().parents[2]
REPO = ID.parent
sys.path.insert(0, str(ID / "experiments"))
from hierarchy_multilevel.notebook21 import coalesced  # noqa: E402

HARNESS = ID / "results/hierarchy_search_v2/review_closure/scripts/execute_notebook_artifact_only.py"
spec = importlib.util.spec_from_file_location("reviewed_notebook_guard", HARNESS)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

NB = ID / "notebooks" / "22_hierarchy_dictionary.ipynb"
BUILDER = ID / "notebooks" / "build_22.py"
RUN = ID / "results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1"
ALLOWED = {"hierarchy", "hierarchy.decode", "hierarchy.ledger", "hierarchy.codes", "hierarchy.model"}


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    tmp = Path(tempfile.mkdtemp(prefix="nb22_guard_"))
    results, src = ID / "results", ID / "src"
    unexecuted_sha = guard.sha_file(NB)
    nb_a, rec_a = guard.run(NB, NB.parent, "notebook_dir", tmp, results, src)
    nb_b, rec_b = guard.run(NB, REPO, "repository_root", tmp, results, src)
    ca = [c for c in nb_a.cells if c.cell_type == "code"]
    cb = [c for c in nb_b.cells if c.cell_type == "code"]
    diffs = [i for i, (x, y) in enumerate(zip(ca, cb)) if coalesced(x) != coalesced(y)]
    alltext = "\n".join(t for c in ca for t in guard.texts(c))
    dec = json.loads((RUN / "DECISION.json").read_text())
    summ = json.loads((RUN / "summary.json").read_text())
    lock = (RUN / "implementation_lock.sha256").read_text().strip()
    con = summ["contrasts"]
    shown = {"lock": lock[:16] in alltext,
             "verdict": f"engineering verdict: {dec['engineering_verdict']}" in alltext,
             "label": f"label: {dec['recommendation']}" in alltext,
             "d2_vs_a0_aggregate": f"{con['D2_vs_A0']['aggregate']:16.6f}" in alltext,
             "d2_vs_d1_aggregate": f"{con['D2_vs_D1']['aggregate']:16.6f}" in alltext,
             "portfolio_aggregate": f"{con['D2_vs_portfolio']['aggregate']:16.6f}" in alltext,
             "new_jobs": f"{'new_encoder_jobs_with_rows':34s} {summ['counts']['new_encoder_jobs_with_rows']}" in alltext,
             "nesting_violations": f"violations: {len(summ['nesting']['violations'])}" in alltext,
             "failed_attempts_listed": "tests-01" in alltext and "mutations-01" in alltext}
    forbidden = [t for t in ("infer_v2", "augment(", "hierarchy.search", "hierarchy.segmentation",
                             "study_corpus", "hierarchy.corpus", "hierarchy.benchmark", "import random",
                             "subprocess", "hierarchy.wire", "import hierarchy_multilevel", "from hierarchy_multilevel",
                             "import hierarchy_dictionary", "from hierarchy_dictionary",
                             "pybdm", "write_text", "write_bytes")
                 if any(t in c.source for c in ca)]
    checks = {
        "both_executions_exit_0": rec_a["exit_status"] == 0 and rec_b["exit_status"] == 0,
        "zero_error_outputs": rec_a["error_outputs"] == 0 and rec_b["error_outputs"] == 0,
        "zero_unexecuted": rec_a["unexecuted"] == 0 and rec_b["unexecuted"] == 0,
        "guard_active_and_no_refusals": all(r["guard_log_present"] and not r["guard"]["refused"]
                                            for r in (rec_a, rec_b)),
        "only_allowlisted_hierarchy_modules": all(
            set(r["guard"]["allowed_hierarchy_imports"]) <= ALLOWED for r in (rec_a, rec_b)),
        "no_inference_generation_job_or_write_tokens_in_code": not forbidden,
        "cwd_outputs_identical_after_bootstrap_banner": len(ca) == len(cb) and not [i for i in diffs if i != 0],
        "saved_values_displayed": all(shown.values()),
    }
    ver = RUN / "notebook"
    ver.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb_a, ver / f"{tag}.notebook_dir.ipynb")
    nbformat.write(nb_b, ver / f"{tag}.repository_root.ipynb")
    report = {"harness": {"path": str(HARNESS.relative_to(REPO)), "sha256": guard.sha_file(HARNESS)},
              "driver_sha256": guard.sha_file(Path(__file__)), "builder_sha256": guard.sha_file(BUILDER),
              "unexecuted_notebook_sha256": unexecuted_sha, "lock_sha256": lock,
              "executions": {"notebook_dir": rec_a, "repository_root": rec_b},
              "cwd_text_output_differences": diffs,
              "cwd_difference_detail": {i: {"notebook_dir": guard.texts(ca[i]),
                                            "repository_root": guard.texts(cb[i])} for i in diffs},
              "forbidden_tokens_in_code": forbidden, "displayed_value_checks": shown,
              "checks": checks, "all_checks_pass": all(checks.values())}
    (ver / f"{tag}.checks.json").write_text(json.dumps(report, indent=1) + "\n")
    if report["all_checks_pass"]:
        nbformat.write(nb_a, NB)            # deliverable: the notebook-directory execution
    print(json.dumps({"checks": checks, "shown": shown, "diffs": diffs,
                      "elapsed_s": [rec_a["elapsed_s"], rec_b["elapsed_s"]],
                      "exception": [rec_a["exception"], rec_b["exception"]]}, indent=1))
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
