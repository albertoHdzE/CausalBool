"""Preservation records and the implementation lock (PROTOCOL sections 2-3, ACCEPTANCE 3).

    (from index-deconvolution/) PYTHONPATH=experiments:.:../src ../venv/bin/python -B \
        -m hierarchy_dictionary.preserve {final|compare} [OUT_JSON]

``record`` produces the same fields as the pre-edit capture
(``preflight/capture_initial.py``, run before any new file existed) so the two compare
key by key. Hashing helpers, snapshot and environment are the multilevel-v1 owners;
``tree_hash`` is ``search_v3a.preserve.tree_hash``.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from hierarchy_multilevel.preserve import environment, git_head, git_status, sha, sha_file, snapshot_tar
from search_v3a.preserve import tree_hash

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
PACKET = ID_ROOT / "protocols" / "hierarchy_dictionary_v1"
RUN_DIR = ID_ROOT / "results" / "hierarchy_dictionary_v1" / "dictionary-feasibility-v1-r1"

__all__ = ["environment", "git_head", "sha", "sha_file", "snapshot_tar", "record", "compare",
           "lock_members", "import_probe"]

SHARED_OWNERS = ("index-deconvolution/experiments/search_v3a/preserve.py",
                 "index-deconvolution/results/hierarchy_search_v2/review_closure/scripts/"
                 "execute_notebook_artifact_only.py",
                 "index-deconvolution/notebooks/_nblib.py",
                 "src/description_lengths.py")


def _files(globs) -> list[str]:
    out = set()
    for g in globs:
        out.update(p.relative_to(REPO).as_posix() for p in REPO.glob(g)
                   if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    return sorted(out)


def _sha_or_none(p: Path):
    return sha_file(p) if p.is_file() else None


def record(stage: str) -> dict:
    st = json.loads((PACKET / "INITIAL_STATE.json").read_text())
    gs = git_status()
    rec = {"stage": stage, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "git_head": git_head(), "git_status": gs,
           "packet_git_status_equal": gs == st["git_status"],
           "protected_files": {p: {"packet": h, "now": _sha_or_none(REPO / p)}
                               for p, h in st["protected_files"].items()},
           "scientific_dependencies": {p: {"packet": h, "now": _sha_or_none(REPO / p)}
                                       for p, h in st["scientific_dependencies"].items()},
           "prior_result_trees": {t: tree_hash(REPO / t) for t in st["prior_result_roots"]},
           "hierarchy_sources": {f: _sha_or_none(REPO / f)
                                 for f in _files(["index-deconvolution/hierarchy/**/*"])},
           "multilevel_package": {f: _sha_or_none(REPO / f) for f in
                                  _files(["index-deconvolution/experiments/hierarchy_multilevel/**/*"])},
           "notebooks_and_builders": {f: _sha_or_none(REPO / f)
                                      for f in _files(["index-deconvolution/notebooks/*"])},
           "protocols_tree": tree_hash(ID_ROOT / "protocols"),
           "bitacora": tree_hash(ID_ROOT / "bitacora"),
           "destinations_absent": {p: not (REPO / p).exists()
                                   for p in st["destinations_absent_at_delegation"]}}
    rec["protected_changed"] = sorted(p for p, v in rec["protected_files"].items() if v["packet"] != v["now"])
    rec["scientific_changed"] = sorted(p for p, v in rec["scientific_dependencies"].items()
                                       if v["packet"] != v["now"])
    return rec


def compare(initial: dict, final: dict) -> dict:
    def diff(a, b):
        return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    new = ("index-deconvolution/experiments/hierarchy_dictionary/",
           "index-deconvolution/results/hierarchy_dictionary_v1/",
           "index-deconvolution/notebooks/build_22.py",
           "index-deconvolution/notebooks/22_hierarchy_dictionary.ipynb")
    added = sorted(set(final["git_status"]) - set(initial["git_status"]))
    return {
        "protected_changed_initial": initial["protected_changed"],
        "protected_changed_final": final["protected_changed"],
        "scientific_changed_final": final["scientific_changed"],
        "prior_trees_changed": diff(initial["prior_result_trees"], final["prior_result_trees"]),
        "hierarchy_sources_changed": diff(initial["hierarchy_sources"], final["hierarchy_sources"]),
        "multilevel_package_changed": diff(initial["multilevel_package"], final["multilevel_package"]),
        "notebooks_changed": diff(initial["notebooks_and_builders"], final["notebooks_and_builders"]),
        "protocols_changed": initial["protocols_tree"] != final["protocols_tree"],
        "bitacora_changed": initial["bitacora"] != final["bitacora"],
        "git_head_changed": initial["git_head"] != final["git_head"],
        "git_status_added": added,
        "git_status_added_outside_owned_paths": [x for x in added if not any(n in x for n in new)],
        "git_status_removed": sorted(set(initial["git_status"]) - set(final["git_status"])),
    }


# ---------------------------------------------------------------------------
# Implementation lock
# ---------------------------------------------------------------------------

LOCK_GLOBS = ("index-deconvolution/experiments/hierarchy_dictionary/*.py",
              "index-deconvolution/experiments/hierarchy_dictionary/tests/*.py",
              "index-deconvolution/experiments/hierarchy_multilevel/**/*.py",
              "index-deconvolution/hierarchy/**/*.py",
              "index-deconvolution/protocols/hierarchy_dictionary_v1/*",
              "index-deconvolution/protocols/hierarchy_multilevel_v1/CASES.json",
              "index-deconvolution/protocols/hierarchy_multilevel_v1/contract.json",
              "index-deconvolution/PROTOCOL_hierarchy_dictionary_v1.md",
              "index-deconvolution/KICKOFF_hierarchy_dictionary_v1.md",
              "index-deconvolution/results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1/"
              "fixtures/declared_inputs.json",
              "index-deconvolution/results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1/"
              "IMPLEMENTATION_MAP.md")
POST_LOCK_PRESENTATION = ("index-deconvolution/experiments/hierarchy_dictionary/notebook22.py",)


def lock_members() -> list[str]:
    return sorted((set(_files(LOCK_GLOBS)) | set(SHARED_OWNERS)) - set(POST_LOCK_PRESENTATION))


def import_probe() -> dict:
    """Where every reused owner resolves from, in a ``-S`` child with the worker path."""
    code = ("import json,sys;sys.path.insert(0,sys.argv[1]);"
            "import hierarchy_dictionary.search,hierarchy_dictionary.runner,"
            "hierarchy_dictionary.report,hierarchy_dictionary.audit,hierarchy.ledger,"
            "hierarchy.benchmark,hierarchy.wire,hierarchy.decode;"
            "print(json.dumps({m:getattr(sys.modules[m],'__file__',None) for m in sorted(sys.modules)"
            " if m.startswith(('hierarchy','search_v3a'))}))")
    env = {"PATH": "", "PYTHONHASHSEED": "0", "PYTHONPATH": f"{ID_ROOT}:{REPO / 'src'}"}
    out = subprocess.run([sys.executable, "-S", "-B", "-c", code, str(ID_ROOT / "experiments")],
                         capture_output=True, text=True, env=env, cwd=str(ID_ROOT))
    mods = json.loads(out.stdout) if out.returncode == 0 else {}
    ok = bool(mods) and all(str(Path(v).resolve()).startswith(str(ID_ROOT)) for v in mods.values() if v)
    return {"modules": mods, "all_inside_index_deconvolution": ok, "stderr": out.stderr[-2000:]}


if __name__ == "__main__":
    cmd = sys.argv[1]
    pres = RUN_DIR / "preservation"
    if cmd == "final":
        rec = record("final")
        (pres / "final.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        cmd = "compare"
    if cmd == "compare":
        cmp = compare(json.loads((pres / "initial.json").read_text()),
                      json.loads((pres / "final.json").read_text()))
        (pres / "initial_vs_final.json").write_text(json.dumps(cmp, indent=1, sort_keys=True) + "\n")
        print(json.dumps({k: v for k, v in cmp.items() if k != "git_status_added"}, indent=1))
