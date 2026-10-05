"""Preservation records for HID-search-v3a: git status, file hashes, protected trees,
and an executable snapshot of the hierarchy package plus shared owners.

    (from index-deconvolution/) PYTHONPATH=experiments:.:../src ../venv/bin/python -B \
        -m search_v3a.preserve \
        {initial|final|integration} OUT_DIR

The tree aggregate is the format of ``experiments/preserve_confirm_v1_r1_sources.tree_hash``
(sorted relative path, NUL, file sha256, newline) with bytecode excluded, as recorded in
``protocols/hierarchy_search_v3a/INITIAL_SOURCE_STATE.json``.
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
PACKET = ID_ROOT / "protocols" / "hierarchy_search_v3a"
SNAPSHOT_GLOBS = ("index-deconvolution/hierarchy/**/*.py", "index-deconvolution/hierarchy/*.md",
                  "index-deconvolution/experiments/search_diagnosis/**/*.py",
                  "index-deconvolution/src/deconvolution.py", "index-deconvolution/src/causalbool.py",
                  "src/description_lengths.py")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bytecode(p: Path) -> bool:
    return "__pycache__" in p.parts or p.suffix in (".pyc", ".pyo")


def tree_hash(root: Path) -> dict:
    files = sorted(p for p in root.rglob("*") if (p.is_file() or p.is_symlink()) and not _bytecode(p))
    h = hashlib.sha256()
    total = 0
    for p in files:
        data = p.read_bytes()
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + sha(data).encode() + b"\n")
        total += len(data)
    return {"files": len(files), "bytes": total, "aggregate_sha256": h.hexdigest(),
            "bytecode_excluded": True}


def snapshot_members() -> list[str]:
    out = set()
    for g in SNAPSHOT_GLOBS:
        out.update(p.relative_to(REPO).as_posix() for p in REPO.glob(g)
                   if p.is_file() and not _bytecode(p))
    return sorted(out)


def snapshot_tar(members) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for m in members:
            data = (REPO / m).read_bytes()
            ti = tarfile.TarInfo(m)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid = len(data), 0, 0o644, 0, 0
            tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def record(kind: str) -> dict:
    init = json.loads((PACKET / "INITIAL_SOURCE_STATE.json").read_text())
    git = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout  # noqa: E731
    status = git("status", "--porcelain=v1", "--untracked-files=all", "--", "index-deconvolution")
    files = {}
    for group in ("source_hashes", "protected_file_hashes"):
        cur = {}
        for p, h in init[group].items():
            q = REPO / p
            cur[p] = {"initial": h, "current": sha(q.read_bytes()) if q.is_file() else None}
            cur[p]["equal"] = cur[p]["initial"] == cur[p]["current"]
        files[group] = cur
    trees = {}
    for p, v in init["protected_trees"].items():
        now = tree_hash(REPO / p)
        trees[p] = {"initial": v, "current": now,
                    "equal": now["aggregate_sha256"] == v["aggregate_sha256"]
                    and now["files"] == v["files"]}
    return {"kind": kind, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_head": git("rev-parse", "HEAD").strip(),
            "git_status_index_deconvolution": status.splitlines(),
            "files": files, "trees": trees,
            "summary": {g: {"equal": sum(v["equal"] for v in d.values()), "total": len(d),
                            "differ": sorted(k for k, v in d.items() if not v["equal"])}
                        for g, d in files.items()}
            | {"trees": {k: v["equal"] for k, v in trees.items()}}}


def integration_equalities() -> dict:
    """The ten report-r3 source/notebook equalities, read from the integration owner's
    own EQUAL table (loaded without running its writer)."""
    import importlib.util
    path = ID_ROOT / ("results/hierarchy_search_diagnosis/integration/search-diagnosis-v1-r1/"
                      "integration_check.py")
    spec = importlib.util.spec_from_file_location("_integration_check_v3a", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    eq = {str(a.relative_to(REPO)): {"accepted": str(b.relative_to(REPO)),
                                     "equal": a.read_bytes() == b.read_bytes()}
          for a, b in mod.EQUAL.items()}
    return {"equalities": eq, "denominator": len(eq),
            "passed": sum(v["equal"] for v in eq.values()),
            "all_equal": len(eq) == 10 and all(v["equal"] for v in eq.values())}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    kind, out = argv[0], Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    if kind == "integration":
        rec = integration_equalities()
        (out / "integration_equalities.json").write_text(json.dumps(rec, indent=1) + "\n")
        print(json.dumps({k: rec[k] for k in ("denominator", "passed", "all_equal")}))
        return 0 if rec["all_equal"] else 1
    rec = record(kind)
    if kind == "initial":
        members = snapshot_members()
        tar = snapshot_tar(members)
        (out / "preedit_executable_snapshot.tar").write_bytes(tar)
        rec["snapshot"] = {"path": "preedit_executable_snapshot.tar", "sha256": sha(tar),
                           "members": {m: sha((REPO / m).read_bytes()) for m in members}}
    (out / f"{kind}_preservation.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps(rec["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
