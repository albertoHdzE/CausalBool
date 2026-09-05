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
    # Section 4 rows. The lint debt was recorded as 176/47/47 and had drifted to
    # 213/67/40 unnoticed, because the first version of this gate parsed only
    # section 3 -- the page's own "where verification is thin" table was the
    # part with no verification on it.
    "Lint hygiene debt": "lint_debt",
    "Manuscript tables with a producer wired": "table_coverage",
    "Coverage of `src/` as a whole": "src_coverage",
}

# Rows carrying SEVERAL bold figures rather than one. Everywhere else only the
# first bold group is read, because the coverage row's second group is a
# threshold ("fails below **95 %**") and asserting a measurement against a
# threshold is how a gate ends up checking the wrong thing.
MULTI_BOLD = {"Lint hygiene debt", "Coverage of `src/` as a whole"}

# A checker may return this prefix in its `how` string to mean "the measurement
# itself is invalid", which is a FAILURE and not an UNKNOWN. UNKNOWN is for a
# thing this repository cannot know -- an absent sibling repository, an absent
# WolframKernel. A coverage percentage computed over a partial denominator is
# not unknown, it is wrong, and it must go red.
FATAL = "REFUSED:"

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


def _ruff_f_counts(extra: list[str]) -> tuple[dict[str, int] | None, str]:
    """Pyflakes counts, or None if ruff did not actually run.

    "Zero findings" and "ruff never ran" both produce no finding lines, and they
    are opposite facts. Distinguished by ruff's own summary line: a real clean
    run says "All checks passed!". Without this the gate reported UNKNOWN the
    moment the debt was genuinely cleared.
    """
    rc, out = run([str(ROOT / "venv/bin/ruff"), "check", "--select", "F",
                   "--output-format", "concise", *extra, "."], ROOT)
    counts = {"F401": 0, "F541": 0, "F841": 0}
    for ln in out.splitlines():
        m = re.search(r"\s(F\d+)\s", ln)
        if m and m.group(1) in counts:
            counts[m.group(1)] += 1
    if sum(counts.values()) == 0 and "All checks passed" not in out:
        return None, "UNKNOWN: ruff produced neither findings nor a clean verdict"
    return counts, "ruff check --select F"


def lint_debt() -> tuple[list[int] | None, str]:
    """[enforced total, F401 in exempted paths, F841 in exempted paths].

    Two different quantities, and the document states both. The first is what
    CI enforces; the second is the historical residue sitting in the paths named
    by ruff.toml's per-file-ignores -- replication packages, dated experiment
    records and provenance archives. Reporting only the first would let the
    residue vanish from view, which is precisely the "declared debt" that had
    already drifted 176/47/47 -> 213/67/40 unnoticed.
    """
    enforced, how = _ruff_f_counts([])
    if enforced is None:
        return None, how
    residue, how2 = _ruff_f_counts(["--config", "lint.per-file-ignores={}"])
    if residue is None:
        return None, how2
    return ([sum(enforced.values()), residue["F401"], residue["F841"]],
            "ruff, enforced set and again with per-file-ignores disabled")


def table_coverage() -> tuple[list[int] | None, str]:
    rc, out = run([str(ROOT / "venv/bin/python"),
                   str(ROOT / "tools/enumerate_paper_tables.py")], ROOT)
    m = re.search(r"COVERED\s+(\d+)/(\d+)", out)
    if not m:
        return None, "UNKNOWN: enumerate_paper_tables.py printed no fraction"
    cov, tot = int(m.group(1)), int(m.group(2))
    # The doc writes this as "5 of 34 (15 %)", so the percentage is part of the
    # claim and is checked too -- a right fraction with a wrong percentage
    # beside it is still a document that misleads.
    return [cov, tot, round(100 * cov / tot)], "enumerate_paper_tables.py"


def src_coverage() -> tuple[list[int] | None, str]:
    """Whole-of-src coverage: REPORTED, never gated -- but its DENOMINATOR is.

    Gating the percentage at 5 per cent would be theatre. The number exists so
    the scoped 98.56 per cent in section 3 -- which covers 99 statements in two
    files -- can never be mistaken for the coverage of the programme.

    THE DENOMINATOR IS THE PART THAT MUST NOT DRIFT. AUDIT04 Phase 1: coverage
    can only enumerate files it has not executed when they sit inside an
    importable package. Seven directories under src/ had no __init__.py, so the
    report covered 25 of 54 files and the published figure was 13 per cent over
    less than half the code. With the markers in place the same command reports
    61 of 61 files and 5 per cent.

    A percentage over a partial denominator is worse than no percentage, so this
    REFUSES when the report and the disk disagree rather than returning a
    prettier number. That is the failure mode the seven missing markers were.
    """
    rc, out = run([str(ROOT / "venv/bin/python"), "-m", "pytest", "-q",
                   "tests/analysis", "--cov=src", "--cov-report=term",
                   "--cov-fail-under=0", "--tb=no", "-p", "no:cacheprovider"],
                  ROOT)
    m = re.search(r"^TOTAL\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+(\d+)%", out, re.M)
    if not m:
        return None, "UNKNOWN: no TOTAL line from coverage"

    reported = len(re.findall(r"^src/\S+\.py\s", out, re.M))
    on_disk = sum(1 for p in (ROOT / "src").rglob("*.py")
                  if "external" not in p.parts and "__pycache__" not in p.parts)
    if reported != on_disk:
        return None, (f"REFUSED: coverage reports {reported} files but {on_disk} "
                      f"exist under src/. A directory without __init__.py is "
                      f"invisible to coverage, so the percentage would be "
                      f"computed over a partial denominator.")
    return [int(m.group(3)), on_disk], "pytest --cov=src (denominator checked)"


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
# Any bold run. It used to be numeric-only, which silently skipped the table
# coverage row ("**5 of 34 (15 %)**") because of the word "of". A bold run with
# no digits in it yields no claim and is dropped below, so widening this cannot
# invent claims -- it only stops the gate quietly ignoring rows it cannot parse.
BOLD_NUM = re.compile(r"\*\*([^*]+)\*\*")


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
            in_section = ln.startswith("## 3.") or ln.startswith("## 4.")
            continue
        if not in_section:
            continue
        m = ROW.match(ln)
        if not m:
            continue
        label = m.group("label").strip()
        if label.startswith("---") or label.lower() in ("what", "gap"):
            continue
        claim = m.group("claim")
        groups = BOLD_NUM.findall(claim)
        if not groups:
            continue
        wanted = groups if any(k in label for k in MULTI_BOLD) else groups[:1]
        nums = [float(x) for g in wanted
                for x in re.findall(r"\d+(?:\.\d+)?", g)]
        if not nums:
            continue
        out.append((label, nums, claim.strip()))
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
            if how.startswith(FATAL):
                bad.append(f"{label}\n      {how}")
            else:
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
          f"in VERIFICATION.md sections 3 and 4.")
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
