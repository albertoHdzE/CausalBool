"""Execute the revised notebook 17 under an artifact-only guard and check its outputs.

  execute_notebook_artifact_only.py <isolated-repo-root> [--negative-control]

``--negative-control`` runs the same guard on a copy holding the ORIGINAL builder's
notebook; it must be refused (exit 1) and writes ``*.negative_control.*`` outputs only.

Test harness only; no production module is modified or monkeypatched. An IPython
startup file in a private IPYTHONDIR installs, inside the kernel before any cell runs:

* an import gate: any ``hierarchy.*`` module outside the read-only allowlist (package
  ``__init__``, ``decode``, ``ledger``, ``codes``, ``model``) and any module loaded from
  ``index-deconvolution/src`` raises ImportError. The search/inference owners
  (``search_v2``, ``infer``, ``candidates``, ``consensus``, ``segmentation``), the
  serializer (``wire``), the corpus generators (``corpus``, ``study_corpus``), the
  runner and the baselines are therefore unreachable;
* an audit hook that raises on any file opened for writing below the isolated copy's
  ``results/`` or the repository's ``index-deconvolution/results/`` (symlinks resolved;
  the isolated copy reaches the saved artefacts through read-only-by-use symlinks) and
  on any subprocess or ``os.system`` call.

Every allowed and refused import and every refused event is logged. The notebook is
executed twice, from the notebook directory (saved as the deliverable) and from the
repository root, and the two text outputs are compared. Writes only into the
correction package and the harness's temporary directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve()
REPO = HERE.parents[5]
PKG = REPO / "index-deconvolution/results/hierarchy_search_v2/review_closure"
ORIGINAL = REPO / "index-deconvolution/notebooks/17_hierarchy_search_v2.ipynb"

STARTUP = r'''
import atexit, importlib.abc, json, os, sys
_LOG = os.environ["NB_GUARD_LOG"]
_RESULTS = [os.path.realpath(x) for x in os.environ["NB_GUARD_RESULTS"].split(os.pathsep)]
_SRC = os.path.realpath(os.environ["NB_GUARD_SRC"])
_ALLOWED = {"hierarchy", "hierarchy.decode", "hierarchy.ledger", "hierarchy.codes", "hierarchy.model"}
_events = {"allowed_hierarchy_imports": [], "refused": [], "hierarchy_origin": None}

def _dump():
    with open(_LOG, "w") as f:
        json.dump(_events, f, indent=1)

class _Gate(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "hierarchy" or name.startswith("hierarchy."):
            if name not in _ALLOWED:
                _events["refused"].append({"kind": "import", "name": name}); _dump()
                raise ImportError(f"artifact-only harness: import of {name} refused")
            if name not in _events["allowed_hierarchy_imports"]:
                _events["allowed_hierarchy_imports"].append(name)
                if name == "hierarchy":
                    import importlib.machinery as _m
                    _sp = _m.PathFinder.find_spec(name, sys.path)
                    _events["hierarchy_origin"] = os.path.realpath(_sp.origin) if _sp else None
                _dump()
        if path:
            for p in path:
                if os.path.realpath(str(p)).startswith(_SRC):
                    _events["refused"].append({"kind": "import", "name": name}); _dump()
                    raise ImportError(f"artifact-only harness: index-deconvolution/src module {name} refused")
        return None

sys.meta_path.insert(0, _Gate())
# top-level modules found on sys.path entries inside index-deconvolution/src
class _SrcGate(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if path is None and "." not in name:
            import importlib.machinery as _m
            spec = _m.PathFinder.find_spec(name, [p for p in sys.path if os.path.realpath(p) == _SRC])
            if spec is not None:
                _events["refused"].append({"kind": "import", "name": name}); _dump()
                raise ImportError(f"artifact-only harness: index-deconvolution/src module {name} refused")
        return None
sys.meta_path.insert(0, _SrcGate())

def _hook(event, args):
    if event == "open":
        path, mode = args[0], args[1]
        if isinstance(path, (str, bytes, os.PathLike)) and isinstance(mode, str) and any(c in mode for c in "wax+"):
            rp = os.path.realpath(os.fsdecode(path))
            if any(rp.startswith(r + os.sep) for r in _RESULTS):
                _events["refused"].append({"kind": "write", "path": rp}); _dump()
                raise PermissionError(f"artifact-only harness: write to {rp} refused")
    elif event in ("subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork"):
        _events["refused"].append({"kind": event, "args": repr(args)[:200]}); _dump()
        raise PermissionError(f"artifact-only harness: {event} refused")

sys.addaudithook(_hook)
_dump()
atexit.register(_dump)
'''


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def texts(cell) -> list[str]:
    out = []
    for o in cell.get("outputs", []):
        if o.get("output_type") == "stream":
            out.append(o["text"] if isinstance(o["text"], str) else "".join(o["text"]))
        elif "data" in o and "text/plain" in o["data"]:
            t = o["data"]["text/plain"]
            out.append(t if isinstance(t, str) else "".join(t))
        elif o.get("output_type") == "error":
            out.append(f"ERROR {o.get('ename')}: {o.get('evalue')}")
    return out


def run(nb_path: Path, cwd: Path, tag: str, tmp: Path, results: Path, src: Path):
    ipy = tmp / f"ipython_{tag}"
    (ipy / "profile_default/startup").mkdir(parents=True)
    (ipy / "profile_default/startup/00_artifact_only_guard.py").write_text(STARTUP)
    log = tmp / f"guard_{tag}.json"
    os.environ.update(IPYTHONDIR=str(ipy), NB_GUARD_LOG=str(log), NB_GUARD_RESULTS=os.pathsep.join([str(results), str(REPO / "index-deconvolution/results")]),
                      NB_GUARD_SRC=str(src), PYTHONDONTWRITEBYTECODE="1")
    nb = nbformat.read(nb_path, as_version=4)
    t0 = time.time()
    status, err = 0, None
    try:
        NotebookClient(nb, timeout=900, kernel_name="causalbool",
                       resources={"metadata": {"path": str(cwd)}}).execute()
    except Exception as e:  # noqa: BLE001  -- recorded, harness exits non-zero
        status, err = 1, f"{type(e).__name__}: {str(e)[:2000]}"
    guard = json.loads(log.read_text()) if log.exists() else None
    code = [c for c in nb.cells if c.cell_type == "code"]
    return nb, {"cwd": str(cwd), "exit_status": status, "exception": err,
                "elapsed_s": round(time.time() - t0, 3), "code_cells": len(code),
                "error_outputs": sum(o.get("output_type") == "error" for c in code for o in c.outputs),
                "unexecuted": sum(c.get("execution_count") is None for c in code),
                "guard_log_present": guard is not None, "guard": guard}


def main() -> int:
    iso = Path(sys.argv[1]).resolve()
    neg = "--negative-control" in sys.argv[2:]
    sfx = ".negative_control" if neg else ""
    nbdir = iso / "index-deconvolution/notebooks"
    nb_path = nbdir / "17_hierarchy_search_v2.ipynb"
    results = iso / "index-deconvolution/results"
    src = iso / "index-deconvolution/src"
    tmp = Path(tempfile.mkdtemp(prefix="nb17_guard_"))
    nb_a, rec_a = run(nb_path, nbdir, "notebook_dir", tmp, results, src)
    nb_b, rec_b = run(nb_path, iso, "repository_root", tmp, results, src)
    out_nb = PKG / f"17_hierarchy_search_v2.corrected{sfx}.ipynb"
    nbformat.write(nb_a, out_nb)

    # text outputs: both working directories, and unchanged cells against the original
    ca = [c for c in nb_a.cells if c.cell_type == "code"]
    cb = [c for c in nb_b.cells if c.cell_type == "code"]
    # cell 0 is the shared _nblib BOOTSTRAP: its banner prints the root it found (from the
    # repository root it falls back to the installed checkout); SETUP then re-roots explicitly.
    cwd_diffs = [i for i, (x, y) in enumerate(zip(ca, cb)) if texts(x) != texts(y)]
    bootstrap_banner = {"notebook_dir": texts(ca[0]), "repository_root": texts(cb[0])}
    orig = nbformat.read(ORIGINAL, as_version=4)
    co = {c.source: c for c in orig.cells if c.cell_type == "code"}
    same_source = [(i, co[c.source]) for i, c in enumerate(ca) if c.source in co]
    unchanged_cells = {"cells_with_identical_source": len(same_source),
                       "identical_text_outputs": [i for i, o in same_source if texts(ca[i]) == texts(o)],
                       "differing_text_outputs": {i: {"original": texts(o), "corrected": texts(ca[i])}
                                                  for i, o in same_source if texts(ca[i]) != texts(o)}}

    # displayed medians come from the erratum; saved scientific numbers keep their values
    err = json.loads((REPO / "index-deconvolution/results/hierarchy_search_v2/review_closure/"
                      "diagnostic_median_erratum.json").read_text())
    summ = json.loads((REPO / "index-deconvolution/results/hierarchy_search_v2/search-confirm-v2-r1/"
                       "summary.json").read_text())
    alltext = "\n".join(t for c in ca for t in texts(c))
    sec10 = next(("\n".join(texts(c)) for c in ca if "ERRATUM.read_text()" in c.source), "")
    median_checks = {}
    for k, c in err["cells"].items():
        line = next((ln for ln in sec10.splitlines() if ln.startswith(k + " ")), "")
        median_checks[k] = {
            "line_found": bool(line),
            "corrected_displayed": f"median {c['corrected_gap_median']} " in line,
            "label": "CORRECTED" if "CORRECTED (stored" in line else ("unchanged" if "[unchanged]" in line else None),
            "label_matches_erratum": ("CORRECTED (stored" in line) == c["changed"]}
    p = summ["primary"]
    scientific = {
        "primary_estimate_printed": f"estimate (bits per input bit): {p['estimate_mean_saving_per_input_bit']}" in alltext,
        "primary_ci_printed": f"95% percentile interval: {p['ci95']}" in alltext,
        "primary_verdict_printed": f"VERDICT: {p['verdict']}" in alltext,
        "contrasts_printed": all(f"{k:<12} {c['family']}  estimate {c.get('estimate_per_input_bit')}" in alltext
                                 for k, c in summ["contrasts"].items())}
    forbidden_tokens = [t for t in ("infer_v2", "hierarchy.search_v2", "import search_v2", "study_corpus",
                                    "hierarchy.corpus", "import corpus", "import random")
                        if any(t in c.source for c in ca)]
    checks = {
        "both_executions_exit_0": rec_a["exit_status"] == 0 and rec_b["exit_status"] == 0,
        "zero_error_outputs": rec_a["error_outputs"] == 0 and rec_b["error_outputs"] == 0,
        "zero_unexecuted": rec_a["unexecuted"] == 0 and rec_b["unexecuted"] == 0,
        "guard_active_and_no_refusals": all(r["guard_log_present"] and not r["guard"]["refused"]
                                            for r in (rec_a, rec_b)),
        "only_allowlisted_hierarchy_modules": all(
            set(r["guard"]["allowed_hierarchy_imports"]) <= {"hierarchy", "hierarchy.decode", "hierarchy.ledger",
                                                            "hierarchy.codes", "hierarchy.model"}
            for r in (rec_a, rec_b)),
        "no_inference_or_generation_tokens_in_code": not forbidden_tokens,
        "cwd_outputs_identical_after_bootstrap_banner": len(ca) == len(cb) and not [i for i in cwd_diffs if i != 0],
        "hierarchy_imported_from_isolated_copy": all(
            (r["guard"] or {}).get("hierarchy_origin") == str((iso / "index-deconvolution/hierarchy/__init__.py").resolve())
            for r in (rec_a, rec_b)),
        "medians_from_erratum": all(v["line_found"] and v["corrected_displayed"] and v["label_matches_erratum"]
                                    for v in median_checks.values()) and len(median_checks) == err["cells_total"] > 0,
        "scientific_values_displayed_unchanged": all(scientific.values())}
    report = {"harness": {"path": str(HERE.relative_to(REPO)), "sha256": sha_file(HERE)},
              "isolated_copy": str(iso), "notebook_built_sha256": sha_file(nb_path),
              "builder_sha256": sha_file(nbdir / "build_17.py"),
              "corrected_notebook": str(out_nb.relative_to(REPO)), "corrected_notebook_sha256": sha_file(out_nb),
              "original_notebook_sha256": sha_file(ORIGINAL),
              "executions": {"notebook_dir": rec_a, "repository_root": rec_b},
              "cwd_text_output_differences": cwd_diffs, "bootstrap_banner": bootstrap_banner, "forbidden_tokens_in_code": forbidden_tokens,
              "unchanged_source_cells_vs_original": unchanged_cells,
              "median_display_checks": median_checks, "scientific_display_checks": scientific,
              "checks": checks, "all_checks_pass": all(checks.values())}
    (PKG / f"notebook_execution_checks{sfx}.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"checks": checks, "elapsed_s": [rec_a["elapsed_s"], rec_b["elapsed_s"]],
                      "allowed_imports": rec_a["guard"] and rec_a["guard"]["allowed_hierarchy_imports"],
                      "unchanged_cells": {k: (v if not isinstance(v, dict) else sorted(v))
                                          for k, v in unchanged_cells.items()}}))
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
