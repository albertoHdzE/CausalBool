"""Original-source view for the inherited suites (efficiency phase, R exit).

The frozen evidence checkers deliberately reject research modules added after
their freeze, so their tests must run in the source view they were written
for, not in a tree that holds this phase's ``efficiency_*`` files. This builds
that view: a repository-shaped temporary tree whose ``research/`` and
``research_tests/`` are byte copies of every file in this phase's STARTING
manifest (each verified by hash; an ``efficiency_*`` file is never copied) and
whose other entries are symlinks to the live tree. The inherited suite is then
run there, and the new ``test_efficiency_*`` suite in the live tree.

Usage::

    PYTHONPATH=.reference:. python -m research.efficiency_snapshot --run RUN --parent DIR
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from research import efficiency_common as ec
from research import optimization_common as oc


def build(run: Path, parent: Path) -> dict:
    manifest = {}
    for line in (Path(run) / "SOURCE_MANIFESTS/starting/source_sha256.txt").read_text() \
            .splitlines():
        digest, name = line.split(None, 1)
        if name.startswith(("research/", "research_tests/")):
            manifest[name.strip()] = digest
    tree = Path(parent) / "CausalBool" / "luminal-challenge"
    if tree.exists():
        raise FileExistsError(tree)
    tree.mkdir(parents=True)
    (Path(parent) / "CausalBool" / ".git").mkdir()
    for name in ("venv", "GOVERNANCE"):
        os.symlink(ec.ROOT.parent / name, Path(parent) / "CausalBool" / name)
    copied, mismatched = 0, []
    for folder in ("research", "research_tests"):
        (tree / folder).mkdir()
    for name, digest in sorted(manifest.items()):
        if Path(name).name.startswith(("efficiency_", "test_efficiency_")):
            continue
        if oc.file_sha256(ec.ROOT / name) != digest:
            mismatched.append(name)
        shutil.copy2(ec.ROOT / name, tree / name)
        copied += 1
    for entry in ec.ROOT.iterdir():
        if entry.name not in ("research", "research_tests", "__pycache__"):
            os.symlink(entry, tree / entry.name)
    present = sorted(f"{f}/{p.name}" for f in ("research", "research_tests")
                     for p in (tree / f).glob("*.py"))
    report = {"snapshot": str(tree), "copied": copied, "manifest_entries": len(manifest),
              "mismatched": mismatched,
              "efficiency_files_present": [p for p in present if "efficiency_" in p],
              "status": ("PASS" if copied == len(manifest) and copied > 0 and not mismatched
                         and not any("efficiency_" in p for p in present) else "FAIL")}
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--parent", required=True)
    args = parser.parse_args(argv)
    report = build(Path(args.run), Path(args.parent))
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
