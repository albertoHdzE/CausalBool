"""Execute the report-r2 notebook 18 under the reviewed artifact-only guard; save its checks.

Reuses ``run``/``texts``/``sha_file`` from the reviewed harness
results/hierarchy_search_v2/review_closure/scripts/execute_notebook_artifact_only.py
(import gate: only hierarchy.{decode,ledger,codes,model}; no src imports; no writes below
results/; no subprocess). Executes from the notebook's own directory (this closure's
``corrected/``) and from the repository root; saves BOTH executed notebooks separately,
then checks the displayed values against the report-r2 outputs. Writes only into this
closure (``corrected/``, ``verification/``) and a temporary directory.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import nbformat

sys.dont_write_bytecode = True       # loading the harness must not add __pycache__ to the accepted tree
HERE = Path(__file__).resolve().parent
CLOSURE = HERE.parent
ID = CLOSURE.parents[3]
REPO = ID.parent
HARNESS = ID / "results/hierarchy_search_v2/review_closure/scripts/execute_notebook_artifact_only.py"
spec = importlib.util.spec_from_file_location("reviewed_notebook_guard", HARNESS)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

NB = CLOSURE / "corrected" / "18_hierarchy_search_diagnosis.report-r2.ipynb"
R2 = CLOSURE / "report-r2"
ALLOWED = {"hierarchy", "hierarchy.decode", "hierarchy.ledger", "hierarchy.codes", "hierarchy.model"}


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    tmp = Path(tempfile.mkdtemp(prefix="nb18r2_guard_"))
    results, src = ID / "results", ID / "src"
    nb_a, rec_a = guard.run(NB, NB.parent, "notebook_dir", tmp, results, src)
    nb_b, rec_b = guard.run(NB, REPO, "repository_root", tmp, results, src)
    ca = [c for c in nb_a.cells if c.cell_type == "code"]
    cb = [c for c in nb_b.cells if c.cell_type == "code"]
    diffs = [i for i, (x, y) in enumerate(zip(ca, cb)) if guard.texts(x) != guard.texts(y)]
    alltext = "\n".join(t for c in ca for t in guard.texts(c))
    out = R2 / "outputs"
    dec = json.loads((out / "DECISION.json").read_text())
    kn = json.loads((out / "key_numbers.json").read_text())
    ident = json.loads((R2 / "identity.json").read_text())
    px = kn["d3_returned_B0_cut_proximity"]
    shown = {
        "reporting_revision": f"reporting revision: report-r2 | identity: {ident['identity_sha256'][:16]}" in alltext,
        "accepted_primary": str(kn["d1_accepted_primary_estimate"]) in alltext,
        "recommendation": f"recommendation: {dec['recommendation']}" in alltext,
        "d4_length_vs_bytes": (f"equal length H == T: {kn['d4_hid_loses_H_eq_T']} | byte-identical: "
                               f"{kn['d4_hid_loses_H_eq_T_identical_bytes']} | same length, different bytes: "
                               f"{kn['d4_hid_loses_H_eq_T_different_bytes']}") in alltext,
        "d3_returned_cut_proximity": (f"strings: {px['strings']} | supplied cuts with a returned B0 cut within 8 bits: "
                                      f"{px['supplied_cut_with_returned_B0_cut_within_8_bits']} | without: "
                                      f"{px['supplied_cut_without_returned_B0_cut_within_8_bits']}") in alltext,
        "d2_witness": kn["d2_B8_witnesses"][0]["case_id"] in alltext,
        "evidence_gate": f"evidence: complete {dec['complete']} | valid {dec['valid']}" in alltext,
    }
    forbidden = [t for t in ("infer_v2", "hierarchy.search_v2", "hierarchy.segmentation", "BoundarySearch", "study_corpus",
                             "hierarchy.corpus", "import search_diagnosis", "from search_diagnosis", "import random",
                             "subprocess", "hierarchy.wire")
                 if any(t in c.source for c in ca)]
    checks = {
        "both_executions_exit_0": rec_a["exit_status"] == 0 and rec_b["exit_status"] == 0,
        "zero_error_outputs": rec_a["error_outputs"] == 0 and rec_b["error_outputs"] == 0,
        "zero_unexecuted": rec_a["unexecuted"] == 0 and rec_b["unexecuted"] == 0,
        "guard_active_and_no_refusals": all(r["guard_log_present"] and not r["guard"]["refused"]
                                            for r in (rec_a, rec_b)),
        "only_allowlisted_hierarchy_modules": all(
            set(r["guard"]["allowed_hierarchy_imports"]) <= ALLOWED for r in (rec_a, rec_b)),
        "no_inference_generation_or_job_tokens_in_code": not forbidden,
        "cwd_outputs_identical_after_bootstrap_banner": len(ca) == len(cb) and not [i for i in diffs if i != 0],
        "saved_values_displayed": all(shown.values()),
    }
    ver = CLOSURE / "verification" / "notebook"
    ver.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb_a, ver / f"{tag}.notebook_dir.ipynb")         # both executions kept
    nbformat.write(nb_b, ver / f"{tag}.repository_root.ipynb")
    report = {"harness": {"path": str(HARNESS.relative_to(REPO)), "sha256": guard.sha_file(HARNESS)},
              "driver_sha256": guard.sha_file(Path(__file__)),
              "builder_sha256": guard.sha_file(R2 / "source" / "build_18.py"),
              "unexecuted_notebook_sha256": guard.sha_file(NB),
              "report_r2_identity": ident["identity_sha256"],
              "executions": {"notebook_dir": rec_a, "repository_root": rec_b},
              "cwd_text_output_differences": diffs,
              "cwd_difference_detail": {i: {"notebook_dir": guard.texts(ca[i]), "repository_root": guard.texts(cb[i])}
                                        for i in diffs},
              "forbidden_tokens_in_code": forbidden,
              "displayed_value_checks": shown, "checks": checks,
              "all_checks_pass": all(checks.values())}
    (ver / f"{tag}.checks.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"checks": checks, "diffs": diffs, "elapsed_s": [rec_a["elapsed_s"], rec_b["elapsed_s"]],
                      "exception": [rec_a["exception"], rec_b["exception"]]}, indent=1))
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
