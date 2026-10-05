"""Preservation records and the implementation lock (PROTOCOL sections 2-3, ACCEPTANCE 4).

    (from index-deconvolution/) PYTHONPATH=experiments:.:../src ../venv/bin/python -B \
        -m hierarchy_multilevel.preserve {initial|final} OUT_JSON

``tree_hash`` is reused from ``search_v3a.preserve`` (sorted relative path, NUL, file
sha256, newline; bytecode excluded) so old-tree aggregates stay comparable across runs.
"""
from __future__ import annotations

import hashlib
import io
import json
import platform
import subprocess
import sys
import tarfile
from pathlib import Path

from search_v3a.preserve import tree_hash

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
PACKET = ID_ROOT / "protocols" / "hierarchy_multilevel_v1"
PKG = Path(__file__).resolve().parent
OLD_TREES = ("index-deconvolution/results/hierarchy_v1",
             "index-deconvolution/results/hierarchy_search_v2",
             "index-deconvolution/results/hierarchy_search_diagnosis",
             "index-deconvolution/results/hierarchy_search_v3a")
# Shared owners imported by the new package or by its reused adapters (outside hierarchy/).
SHARED_OWNERS = ("index-deconvolution/experiments/search_v3a/preserve.py",
                 "index-deconvolution/results/hierarchy_search_v2/review_closure/scripts/"
                 "execute_notebook_artifact_only.py",
                 "index-deconvolution/notebooks/_nblib.py",
                 "src/description_lengths.py")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(p: Path) -> str:
    return sha(p.read_bytes())


def _files(globs) -> list[str]:
    out = set()
    for g in globs:
        out.update(p.relative_to(REPO).as_posix() for p in REPO.glob(g)
                   if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    return sorted(out)


def hierarchy_sources() -> dict:
    return {f: sha_file(REPO / f) for f in _files(["index-deconvolution/hierarchy/**/*"])}


def notebooks() -> dict:
    return {f: sha_file(REPO / f) for f in _files(["index-deconvolution/notebooks/*.ipynb",
                                                   "index-deconvolution/notebooks/*.py"])}


def git_status() -> list[str]:
    out = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                         cwd=REPO, capture_output=True, text=True).stdout
    return out.splitlines()


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()


def record(stage: str) -> dict:
    state = json.loads((PACKET / "INITIAL_STATE.json").read_text())
    crit = {p: {"packet": h, "now": sha_file(REPO / p) if (REPO / p).is_file() else None}
            for p, h in state["critical_files"].items()}
    prot = {p: {"packet": h, "now": sha_file(REPO / p) if (REPO / p).is_file() else None}
            for p, h in state["protected_notebooks"].items()}
    return {
        "stage": stage, "git_head": git_head(), "git_status": git_status(),
        "packet_git_head": state["git_head"],
        "critical_files": crit,
        "critical_changed": sorted(p for p, v in crit.items() if v["packet"] != v["now"]),
        "protected_notebooks": prot,
        "protected_changed": sorted(p for p, v in prot.items() if v["packet"] != v["now"]),
        "external_drift_warning_only": state["external_drift_warning_only"],
        "hierarchy_sources": hierarchy_sources(),
        "shared_owners": {p: sha_file(REPO / p) for p in SHARED_OWNERS},
        "notebooks_and_builders": notebooks(),
        "old_result_trees": {t: tree_hash(REPO / t) for t in OLD_TREES},
        "bitacora": tree_hash(ID_ROOT / "bitacora"),
        "notebook_readme_sha256": sha_file(ID_ROOT / "notebooks" / "README.md"),
    }


def compare(initial: dict, final: dict) -> dict:
    def diff(a, b):
        return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return {
        "hierarchy_sources_changed": diff(initial["hierarchy_sources"], final["hierarchy_sources"]),
        "shared_owners_changed": diff(initial["shared_owners"], final["shared_owners"]),
        "notebooks_changed": diff(initial["notebooks_and_builders"], final["notebooks_and_builders"]),
        "old_trees_changed": diff(initial["old_result_trees"], final["old_result_trees"]),
        "bitacora_changed": initial["bitacora"] != final["bitacora"],
        "notebook_readme_changed": initial["notebook_readme_sha256"] != final["notebook_readme_sha256"],
        "git_status_added": sorted(set(final["git_status"]) - set(initial["git_status"])),
        "git_status_removed": sorted(set(initial["git_status"]) - set(final["git_status"])),
    }


# ---------------------------------------------------------------------------
# Implementation lock
# ---------------------------------------------------------------------------

LOCK_GLOBS = ("index-deconvolution/experiments/hierarchy_multilevel/**/*.py",
              "index-deconvolution/hierarchy/**/*.py",
              "index-deconvolution/protocols/hierarchy_multilevel_v1/*",
              "index-deconvolution/PROTOCOL_hierarchy_multilevel_v1.md",
              "index-deconvolution/KICKOFF_hierarchy_multilevel_v1.md",
              "index-deconvolution/protocols/hierarchy_multilevel/CONCEPT_REVIEW.md")


def lock_members() -> list[str]:
    return sorted(set(_files(LOCK_GLOBS)) | set(SHARED_OWNERS))


def snapshot_tar(members) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for m in members:
            data = (REPO / m).read_bytes()
            ti = tarfile.TarInfo(m)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid = len(data), 0, 0o644, 0, 0
            ti.uname = ti.gname = ""
            tf.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def environment() -> dict:
    import lzma
    import zlib
    import numpy
    return {"python": sys.version, "executable": sys.executable,
            "platform": platform.platform(), "machine": platform.machine(),
            "zlib": zlib.ZLIB_RUNTIME_VERSION, "liblzma": lzma.LZMA_VERSION if hasattr(lzma, "LZMA_VERSION") else None,
            "numpy": numpy.__version__}


def import_probe() -> dict:
    """Where every reused owner resolves from, in a ``-S`` child with the worker path."""
    code = ("import json,sys;import hierarchy,hierarchy.model,hierarchy.wire,hierarchy.decode,"
            "hierarchy.candidates,hierarchy.ledger,hierarchy.search_v2,hierarchy.benchmark,"
            "hierarchy.segmentation,hierarchy.consensus,hierarchy.infer;"
            "sys.path.insert(0,sys.argv[1]);import hierarchy_multilevel.search as s;"
            "print(json.dumps({m:getattr(sys.modules[m],'__file__',None) for m in sorted(sys.modules)"
            " if m.startswith(('hierarchy','hierarchy_multilevel'))}))")
    env = {"PATH": "", "PYTHONHASHSEED": "0",
           "PYTHONPATH": f"{ID_ROOT}:{REPO / 'src'}"}
    out = subprocess.run([sys.executable, "-S", "-B", "-c", code, str(ID_ROOT / "experiments")],
                         capture_output=True, text=True, env=env, cwd=str(ID_ROOT))
    mods = json.loads(out.stdout) if out.returncode == 0 else {}
    ok = bool(mods) and all(str(Path(v).resolve()).startswith(str(ID_ROOT)) for v in mods.values() if v)
    return {"modules": mods, "all_inside_index_deconvolution": ok, "stderr": out.stderr[-2000:]}


if __name__ == "__main__":
    stage, out = sys.argv[1], Path(sys.argv[2])
    rec = record(stage)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"critical_changed": rec["critical_changed"],
                      "protected_changed": rec["protected_changed"],
                      "hierarchy_sources": len(rec["hierarchy_sources"]),
                      "old_trees": {k: v["files"] for k, v in rec["old_result_trees"].items()}}))
