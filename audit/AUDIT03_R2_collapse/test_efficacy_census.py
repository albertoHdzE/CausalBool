"""AUDIT03 — can our tests fail?

The duplication census raised "23 of 78 MUnit files never run". Inspecting them
surgically showed the glob is the smaller half of the problem.

`tests/MUnit` is NOT an MUnit suite despite the name: no file in the tree uses
`VerificationTest` or `Test[`. The runner executes each `.m` as a script and
reads a `Status.txt` the script exports; `OK`/`PASS` is green, anything else is
red. That design is fine — but it means a script can be green by *writing the
word OK*, with nothing checked.

So the question worth asking is not "which files run" but "which files could
ever go red". This measures both, over all 78 files:

  RUNS       collected by the runner's `*Tests.m` glob
  CONDITIONAL the exported status depends on a computed predicate
  FIXED      the status is a literal "OK" — the file cannot fail

A file that is FIXED and RUNS is worse than one that never runs, because it is
counted in the green total.

Usage:  venv/bin/python audit/AUDIT03_R2_collapse/test_efficacy_census.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MUNIT = ROOT / "tests" / "MUnit"

# The runner's own discovery rule, transcribed from tests/MUnit/run-tests.sh:46.
GLOB = "*Tests.m"

# An Export whose payload is a bare string literal cannot depend on anything.
# Matches both the plain form and the {status, DateString[]} list form.
EXPORT_STATUS = re.compile(
    r'Export\[\s*(?:FileNameJoin\[[^\]]*\]|"[^"]*")\s*,\s*(.*?)\s*(?:,\s*"[A-Za-z]+"\s*)?\]\s*;',
    re.DOTALL)
LITERAL_OK = re.compile(r'^\{?\s*"(OK|PASS)"\s*(?:,\s*DateString\[\])?\s*\}?$')


def status_exports(text: str) -> list[str]:
    """Payload expressions of every Export that writes a status artefact."""
    out = []
    for m in EXPORT_STATUS.finditer(text):
        whole = m.group(0)
        if not re.search(r'[Ss]tatus|Acceptance', whole):
            continue
        out.append(" ".join(m.group(1).split()))
    return out


def classify(path: Path) -> dict:
    text = path.read_text(errors="replace")
    exports = status_exports(text)
    runs = path.match(GLOB)
    if not exports:
        kind = "NO-STATUS"
    elif all(LITERAL_OK.match(e) for e in exports):
        kind = "FIXED"
    else:
        kind = "CONDITIONAL"
    return {"file": str(path.relative_to(ROOT)), "runs": bool(runs),
            "kind": kind, "exports": exports}


def main() -> int:
    files = sorted(p for p in MUNIT.rglob("*.m") if p.name != "RunTests.m")
    if not files:
        print("REFUSED: found no .m files under tests/MUnit. "
              "A census over zero files is not a result.")
        return 2

    rows = [classify(p) for p in files]
    n = len(rows)

    def count(**kw):
        return sum(1 for r in rows if all(r[k] == v for k, v in kw.items()))

    print(f"tests/MUnit: {n} files (excluding RunTests.m)\n")
    print(f"{'':14}{'RUNS':>8}{'SKIPPED':>10}{'total':>8}")
    print("-" * 40)
    for kind in ("CONDITIONAL", "FIXED", "NO-STATUS"):
        r = count(kind=kind, runs=True)
        s = count(kind=kind, runs=False)
        print(f"{kind:14}{r:>8}{s:>10}{r + s:>8}")
    print("-" * 40)
    print(f"{'total':14}{count(runs=True):>8}{count(runs=False):>10}{n:>8}\n")

    fixed_running = [r for r in rows if r["kind"] == "FIXED" and r["runs"]]
    print(f"CANNOT FAIL BUT COUNTED GREEN: {len(fixed_running)} file(s)")
    for r in fixed_running:
        print(f"    {r['file']}")

    fixed_skipped = [r for r in rows if r["kind"] == "FIXED" and not r["runs"]]
    print(f"\nCANNOT FAIL, currently not collected: {len(fixed_skipped)} file(s)")
    for r in fixed_skipped:
        print(f"    {r['file']}")

    cond_skipped = [r for r in rows if r["kind"] == "CONDITIONAL" and not r["runs"]]
    print(f"\nREAL COVERAGE BEING LOST TO THE GLOB: {len(cond_skipped)} file(s)")
    for r in cond_skipped:
        print(f"    {r['file']}")
        for e in r["exports"]:
            print(f"        status <- {e[:88]}")

    nostatus = [r for r in rows if r["kind"] == "NO-STATUS"]
    print(f"\nNO STATUS EXPORT AT ALL (producers, not tests): {len(nostatus)} file(s)")
    for r in nostatus:
        print(f"    {r['file']}{'   [COLLECTED — scored as FAIL]' if r['runs'] else ''}")

    out = ROOT / "audit" / "AUDIT03_R2_collapse" / "test_efficacy_census.json"
    out.write_text(json.dumps({"n": n, "rows": rows}, indent=2))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
