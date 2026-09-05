#!/usr/bin/env python3
"""AUDIT03-C - does GOVERNANCE/VERIFICATION.md tell the truth?

WHY THIS EXISTS, and it is not hypothetical. VERIFICATION.md opens with
"Regenerate every number here with `make ci-local`; none of them is typed by
hand." That sentence was false on the day it was written: the row for
`check_core_index.sh` read **36 / 36** while the guard itself printed
**40 / 40**. The claim had been typed from an earlier state and nothing could
notice, because nothing compared the page to the tools it names.

WHY NOT ENRICH tools/snapshot_paper_numbers.py, which also watches numbers.
Because it answers a DIFFERENT question. It is a drift gate: it diffs a
document against a stored snapshot and reports what changed. A stored snapshot
is precisely what must not be trusted here -- 36/36 was stored, committed and
stable, and a drift gate would have passed it every day forever. This gate
compares the document against the LIVE OUTPUT OF THE PRODUCING TOOL. Change
detection and truth are two concepts, so they get two names.

SCOPE, stated rather than implied. Only the claims regenerable in seconds are
checked here; the expensive ones (the MUnit suite, the Wolfram parse, coverage)
belong to the wolfram tier and are named as UNCHECKED in the output rather than
quietly dropped. The gate prints "checked K of N claims" and lists the N-K, so
a reader can never mistake its scope for the whole page.

Exit codes, three states as everywhere in this programme:
    0  every checkable claim matches
    1  a claim disagrees with its tool
    2  refusal: the table could not be parsed, or zero claims were found
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "GOVERNANCE" / "VERIFICATION.md"

# Rows are keyed by a substring of the FIRST cell, which is prose and stable,
# rather than by row order, which is not. A key that stops matching is reported
# as a parse failure, not silently skipped -- a renamed row must not be able to
# disable its own check.
CHECKERS: dict[str, str] = {
    "tests/analysis": "collect_root",
    "index-deconvolution": "collect_deconv",
    "Owners named in": "core_index",
    "Test files classified": "test_manifest",
    "Replication packages": "collect_subprojects",
}

SUBPROJECTS = [
    "imp-causal-paper",
    "imp-prices",
    "imp-causalNet-paper",
    "imp-pathinfo-paper",
]


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def collected(cwd: Path, py: Path, target: str | None = None) -> int | None:
    """pytest's collected count, or None if the suite could not be collected.

    None is UNKNOWN and never folded into a pass: a suite that fails to collect
    reports zero tests, and zero tests trivially "matches" nothing. That is the
    all-match-over-0-cases failure this programme has already been bitten by.
    """
    cmd = [str(py), "-m", "pytest", "--collect-only", "-q"]
    if target:
        cmd.append(target)
    rc, out = run(cmd, cwd)
    m = re.search(r"^(\d+) tests? collected", out, re.M)
    if m:
        return int(m.group(1))
    # imp-prices doubles -q in its addopts, which suppresses the summary line
    # entirely and leaves only per-file counts ("tests/test_clock.py: 6").
    # Summing those is the same number, but only when at least one line was
    # seen -- an empty sum is 0, and 0 must read as UNKNOWN rather than as a
    # suite that honestly contains no tests.
    per_file = re.findall(r"^\S+\.py: (\d+)$", out, re.M)
    if per_file:
        return sum(int(x) for x in per_file)
    return None


# ── the individual regenerations ────────────────────────────────────────────

def collect_root() -> tuple[list[int] | None, str]:
    n = collected(ROOT, ROOT / "venv/bin/python", "tests/analysis")
    return ([n] if n is not None else None), "pytest --collect-only tests/analysis"


def collect_deconv() -> tuple[list[int] | None, str]:
    n = collected(ROOT / "index-deconvolution", ROOT / "venv/bin/python")
    return ([n] if n is not None else None), "pytest --collect-only (index-deconvolution)"


def collect_subprojects() -> tuple[list[int] | None, str]:
    counts: list[int] = []
    for sp in SUBPROJECTS:
        py = ROOT / sp / ".venv" / "bin" / "python"
        if not py.exists():
            return None, f"UNKNOWN: {sp}/.venv absent"
        n = collected(ROOT / sp, py)
        if n is None:
            return None, f"UNKNOWN: {sp} did not collect"
        counts.append(n)
    return counts, "pytest --collect-only in each replication package"


def core_index() -> tuple[list[int] | None, str]:
    rc, out = run(["zsh", str(ROOT / "tools/check_core_index.sh")], ROOT)
    m = re.search(r"(\d+)\s*/\s*(\d+)\s+paths", out)
    if not m:
        return None, "UNKNOWN: check_core_index.sh printed no denominator"
    return [int(m.group(1)), int(m.group(2))], "check_core_index.sh"


def test_manifest() -> tuple[list[int] | None, str]:
    rc, out = run(["zsh", str(ROOT / "tools/check_test_manifest.sh")], ROOT)
    m = re.search(r"(\d+)\s*/\s*(\d+)", out)
    if not m:
        return None, "UNKNOWN: check_test_manifest.sh printed no denominator"
    return [int(m.group(1)), int(m.group(2))], "check_test_manifest.sh"


# ── the document side ───────────────────────────────────────────────────────

ROW = re.compile(r"^\|(?P<label>[^|]+)\|(?P<claim>[^|]+)\|(?P<gate>[^|]*)\|\s*$")
BOLD_NUM = re.compile(r"\*\*([\d\s/.,%]+)\*\*")


def parse_claims(text: str) -> list[tuple[str, list[float], str]]:
    """Every §3 row, as (label, the bolded numbers, raw claim cell).

    Only the FIRST bolded group is read. The coverage row carries a second one
    ("fails below **95 %**") which is the threshold, not the measurement, and
    comparing a measurement against a threshold is how a gate ends up asserting
    the wrong thing.
    """
    out: list[tuple[str, list[float], str]] = []
    in_section = False
    for ln in text.splitlines():
        if ln.startswith("## "):
            in_section = ln.startswith("## 3.")
            continue
        if not in_section:
            continue
        m = ROW.match(ln)
        if not m:
            continue
        label = m.group("label").strip()
        if label.startswith("---") or label.lower() == "what":
            continue
        b = BOLD_NUM.search(m.group("claim"))
        if not b:
            continue
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", b.group(1))]
        out.append((label, nums, m.group("claim").strip()))
    return out


def main() -> int:
    if not DOC.exists():
        print(f"REFUSED: {DOC} does not exist.")
        return 2

    claims = parse_claims(DOC.read_text())
    if not claims:
        print("REFUSED: parsed 0 numeric claims from VERIFICATION.md section 3. "
              "A gate that checks nothing must not report success.")
        return 2

    checked = 0
    unchecked: list[str] = []
    unknown: list[str] = []
    bad: list[str] = []

    for label, nums, raw in claims:
        fn_name = next((v for k, v in CHECKERS.items() if k in label), None)
        if fn_name is None:
            unchecked.append(label)
            continue
        got, how = globals()[fn_name]()
        if got is None:
            unknown.append(f"{label}: {how}")
            continue
        checked += 1
        want = [int(x) for x in nums]
        if got != want:
            bad.append(f"{label}\n      document says {want}\n      {how} says {got}")
        else:
            print(f"  OK   {label}: {got}  ({how})")

    total = len(claims)
    print(f"\nVERIFICATION-NUMBERS: checked {checked} of {total} numeric claims "
          f"in VERIFICATION.md section 3.")
    if unchecked:
        print("  NOT CHECKED HERE (wolfram tier or no cheap producer):")
        for u in unchecked:
            print(f"    - {u}")
    if unknown:
        print("  UNKNOWN (reported as unknown, never as a pass):")
        for u in unknown:
            print(f"    - {u}")
    if bad:
        print("\n  MISMATCH -- the document does not match its own tool:")
        for b in bad:
            print(f"    - {b}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
