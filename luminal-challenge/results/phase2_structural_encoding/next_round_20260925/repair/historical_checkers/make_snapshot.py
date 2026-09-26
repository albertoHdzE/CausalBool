"""Build and verify an original-source snapshot (every research file except next_round_*).

Every copied research/research_tests file must hash exactly as recorded in
SOURCE_MANIFESTS/starting/SOURCES.json (captured before any next-round source
existed apart from next_round_common.py, which is excluded like every
next_round_* file). Everything else is a read-only symlink to the live tree.
Usage: python make_snapshot.py SNAPSHOT_PARENT
"""
import hashlib, json, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUN = Path(__file__).resolve().parents[2]
parent = Path(sys.argv[1])
tree = parent / "CausalBool" / "luminal-challenge"
if tree.exists():
    raise SystemExit(f"{tree} exists")
tree.mkdir(parents=True)
(parent / "CausalBool" / ".git").mkdir()          # repository-shaped
os.symlink(ROOT.parent / "venv", parent / "CausalBool" / "venv")
os.symlink(ROOT.parent / "GOVERNANCE", parent / "CausalBool" / "GOVERNANCE")
expected = json.loads((RUN / "SOURCE_MANIFESTS/starting/SOURCES.json").read_text())[
    "research_excluding_next_round"]
copied, mismatched = 0, []
for folder in ("research", "research_tests"):
    (tree / folder).mkdir()
    for path in sorted((ROOT / folder).glob("*.py")):
        rel = f"{folder}/{path.name}"
        if path.name.startswith(("next_round_", "test_next_round_")):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected.get(rel) != digest:
            mismatched.append(rel)
        shutil.copy2(path, tree / rel)
        copied += 1
missing = sorted(set(expected) - {f"{f}/{p.name}" for f in ("research", "research_tests")
                                  for p in (tree / f).glob("*.py")})
for entry in ROOT.iterdir():
    if entry.name in ("research", "research_tests", "__pycache__"):
        continue
    os.symlink(entry, tree / entry.name)
report = {"snapshot": str(tree), "copied": copied, "expected": len(expected),
          "mismatched": mismatched, "missing": missing,
          "status": "PASS" if copied == len(expected) and not mismatched and not missing else "FAIL"}
print(json.dumps(report))
(RUN / "repair/historical_checkers/SNAPSHOT_VERIFICATION.json").write_text(json.dumps(report, indent=2) + "\n")
