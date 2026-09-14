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
    # AUDIT04-E: was keyed on "tests/analysis", which was the whole Python suite
    # as far as every command was concerned while 24 declared-by-nothing files ran
    # nowhere. Both numbers are checked -- the test count AND the file count --
    # because a suite can lose an entire file and keep a plausible test count.
    "Declared Python suite": "collect_root",
    "index-deconvolution": "collect_deconv",
    "Owners named in": "core_index",
    "Test files classified": "test_manifest",
    # AUDIT04: moved off the NOT CHECKED list. Running the suite needs a kernel;
    # checking the CLAIM only needs the tracked rollup, and while it was unwatched
    # it drifted to 69/69 against a manifest declaring 72.
    "MUnit suite": "munit_rollup",
    # AUDIT04: same lesson, same week. This row read "2 of 61" while the floor
    # file held 6 entries. Its producer already printed the pair on every run;
    # nothing was reading it.
    "Modules with a declared coverage floor": "coverage_floors",
    "Replication packages": "collect_subprojects",
    # Section 4 rows. The lint debt was recorded as 176/47/47 and had drifted to
    # 213/67/40 unnoticed, because the first version of this gate parsed only
    # section 3 -- the page's own "where verification is thin" table was the
    # part with no verification on it.
    "Lint hygiene debt": "lint_debt",
    "Manuscript tables with a producer wired": "table_coverage",
    "Coverage of `src/` as a whole": "src_coverage",
    # Section 5. Added 2026-09-05 with the mutation result: the moment a rate is
    # written onto this page it becomes a claim, and every claim needs a gate.
    # Both rates are checked, not just the headline -- the whole point of the
    # pair is that quoting only the 92% would merge two different statements.
    "semantic kill rate": "mutation_semantic",
    "unit-test kill rate": "mutation_unit",
    # Section 5b.1. AUDIT04-H acceptance: the gate covers the six median-null
    # figures and the six tail counts; planted changes go red. Each row keys
    # on the cell name and returns the two figures the row carries, so a
    # planted change to any one of the twelve numbers hits one row.
    "index-set / er": "bio_summary_index_set_er",
    "index-set / deg": "bio_summary_index_set_deg",
    "index-set / gate": "bio_summary_index_set_gate",
    "BDM / er": "bio_summary_bdm_er",
    "BDM / deg": "bio_summary_bdm_deg",
    "BDM / gate": "bio_summary_bdm_gate",
}

# Rows carrying SEVERAL bold figures rather than one. Everywhere else only the
# first bold group is read, because the coverage row's second group is a
# threshold ("fails below **95 %**") and asserting a measurement against a
# threshold is how a gate ends up checking the wrong thing.
MULTI_BOLD = {"Lint hygiene debt", "Coverage of `src/` as a whole",
              # AUDIT04-E: tests AND files. A suite that silently stops
              # collecting a whole file keeps a plausible test count, which is
              # how 24 files went unrun without any number looking wrong.
              "Declared Python suite",
              # AUDIT04-H: each §5b.1 cell row carries the median-null gap and
              # the exceed==0 count as two separate bolded values. A gate that
              # only checked the first would let a wrong tail count sit on the
              # page beside a right gap.
              "index-set / er", "index-set / deg", "index-set / gate",
              "BDM / er", "BDM / deg", "BDM / gate"}

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
    """Test count AND file count for the declared Python suite.

    No path argument: pytest.ini names the directories and conftest.py takes
    membership from tests/MUnit/MANIFEST.tsv, so this is the declared suite by
    construction rather than by a path repeated in four places.

    The FILE count is checked as well as the test count because they fail
    differently. A whole file can stop being collected -- which is precisely what
    happened to 24 of them -- while the test count still looks like a number
    somebody chose.
    """
    n = collected(ROOT, ROOT / "venv/bin/python", None)
    rc, out = run([str(ROOT / "venv/bin/python"), "-m", "pytest",
                   "--collect-only", "-q", "-p", "no:cacheprovider"], ROOT)
    files = {m for m in re.findall(r"^(tests/\S+\.py)::", out, re.M)}
    if n is None or not files:
        return None, "UNKNOWN: pytest collected nothing"
    return [n, len(files)], "pytest --collect-only (declared suite)"


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

    AUDIT04-E: the command ran `tests/analysis` and so measured 12.63 per cent
    while the DECLARED suite measured 29.90. The denominator of FILES was being
    guarded carefully and the denominator of TESTS was not guarded at all, which
    is the same defect one level up. There is no path argument now: pytest.ini
    names the directories and conftest.py takes membership from the manifest.

    Reads coverage.json rather than the terminal TOTAL line, because that line
    rounds to whole per cent and the row states two decimals. The report goes to
    a TEMPORARY file: the repository's coverage.json belongs to the ratchet gate,
    which refuses on a stale one, and two gates writing one artefact is how a
    later run silently grades an earlier run's numbers.
    """
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        jpath = Path(td) / "cov.json"
        rc, out = run([str(ROOT / "venv/bin/python"), "-m", "pytest", "-q",
                       "--cov=src", "--cov-report=term",
                       f"--cov-report=json:{jpath}",
                       "--cov-fail-under=0", "--tb=no", "-p", "no:cacheprovider"],
                      ROOT)
        if not jpath.is_file():
            return None, "UNKNOWN: coverage wrote no JSON report"
        data = json.loads(jpath.read_text())

    files = data.get("files", {})
    if not files:
        return None, "REFUSED: coverage report contains 0 files"

    on_disk = sum(1 for p in (ROOT / "src").rglob("*.py")
                  if "external" not in p.parts and "__pycache__" not in p.parts)
    if len(files) != on_disk:
        return None, (f"REFUSED: coverage reports {len(files)} files but {on_disk} "
                      f"exist under src/. A directory without __init__.py is "
                      f"invisible to coverage, so the percentage would be "
                      f"computed over a partial denominator.")

    with_stmts = [f for f, v in files.items() if v["summary"]["num_statements"] > 0]
    at_zero = [f for f in with_stmts if files[f]["summary"]["percent_covered"] == 0]
    pct = round(data["totals"]["percent_covered"], 2)
    return ([pct, on_disk, len(at_zero), len(with_stmts)],
            "pytest --cov=src over the declared suite (denominator checked)")


def _mutation_report() -> tuple[str | None, str]:
    """Live output of the harness's own reporter.

    Not a re-read of mutation_results.json: the reporter REFUSES on a partial or
    empty run, and routing through it means this gate inherits that refusal
    instead of re-implementing it. Enriching the owner rather than duplicating
    its logic -- `monolithic-code` Q3.
    """
    rc, out = run([str(ROOT / "venv/bin/python"),
                   str(ROOT / "audit/AUDIT03_R2_collapse/mutation_harness.py"),
                   "--report"], ROOT)
    if rc != 0:
        return None, f"UNKNOWN: mutation reporter refused (rc={rc})"
    return out, "mutation_harness.py --report"


def _mutation_rate(kind: str) -> tuple[list[float] | None, str]:
    out, how = _mutation_report()
    if out is None:
        return None, how
    m = re.search(rf"{kind}\s+kill rate\s+(\d+)/(\d+) = ([\d.]+)%", out, re.I)
    if not m:
        return None, f"UNKNOWN: reporter printed no {kind} rate"
    return [float(m.group(1)), float(m.group(2)), float(m.group(3))], how


def mutation_semantic() -> tuple[list[float] | None, str]:
    return _mutation_rate("SEMANTIC")


def mutation_unit() -> tuple[list[float] | None, str]:
    return _mutation_rate("UNIT-TEST")


# ── §5b.1 Bio comparator values (AUDIT04-H) ─────────────────────────────────
#
# The bio summary block at `results/bio/null_summary.json` carries, per
# (measure, null kind) cell, a `median_gap_to_median_null` and a
# `separating_at_exceed_0` count. VERIFICATION.md §5b.1 quotes both in a
# 3-cell row per cell. Reading them through the JSON is the gate's job; a
# planted change in any one of the twelve values must turn one of these
# six rows red.
#
# The earlier 4-cell `ER null / median gap −27.68` rows in §5b's main table
# are NOT gated by design: the row is a 4-cell layout, the parser only
# handles 2 or 3, and the 6 best-null `median_gap_bits` figures are
# already cross-checked at the source by the byte-identical diff that
# H1.2 records. The new 3-cell sub-table in §5b.1 is what the H1
# acceptance criterion names.

_BIO_PATH = ROOT / "results/bio/null_summary.json"


def _bio_cell(measure: str, kind: str) -> tuple[list[float] | None, str]:
    """[median_gap_to_median_null, separating_at_exceed_0] for one cell.

    The two figures are checked in document order: gap, then count. The
    row's `231` denominator is left unbolded in the document on purpose
    — a denominator that disagrees with the artefact is the producer's
    own self-check, not the gate's, and bolding it would make the gate
    assert against a value that the producer does not own.

    The summary file at `results/bio/null_summary.json` is shaped by
    `Null_Generator_HPC._block`: the three null kinds (`er`, `deg`,
    `gate`) sit at the top level for the index_set measure, while the
    BDM cells are nested one level deeper under a `bdm` parent. Both
    shapes are read here.

    The gap is rounded to two decimal places before being returned, so
    the value the gate compares is the same one a reader sees on the
    page. Full precision lives in the JSON; a planted change of a few
    units in the last decimal place is the same value to the page, and
    asserting a more-precise value than the page states would let a
    rounding-style change pass.
    """
    import json
    if not _BIO_PATH.exists():
        return None, f"UNKNOWN: {_BIO_PATH} absent"
    data = json.loads(_BIO_PATH.read_text())
    try:
        if measure == "index_set":
            cell = data[kind]
        else:
            cell = data[measure][kind]
        gap = cell["median_gap_to_median_null"]
        count = cell["separating_at_exceed_0"]
    except (KeyError, TypeError) as e:
        return None, f"REFUSED: {measure}/{kind} missing field: {e}"
    return [round(float(gap), 2), float(count)], "results/bio/null_summary.json"


def bio_summary_index_set_er() -> tuple[list[float] | None, str]:
    return _bio_cell("index_set", "er")


def bio_summary_index_set_deg() -> tuple[list[float] | None, str]:
    return _bio_cell("index_set", "deg")


def bio_summary_index_set_gate() -> tuple[list[float] | None, str]:
    return _bio_cell("index_set", "gate")


def bio_summary_bdm_er() -> tuple[list[float] | None, str]:
    return _bio_cell("bdm", "er")


def bio_summary_bdm_deg() -> tuple[list[float] | None, str]:
    return _bio_cell("bdm", "deg")


def bio_summary_bdm_gate() -> tuple[list[float] | None, str]:
    return _bio_cell("bdm", "gate")


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


def coverage_floors() -> tuple[list[int] | None, str]:
    """How many modules carry a declared coverage floor, out of the report total.

    The ratchet has printed this pair on every run since it landed; the document
    still said "2 of 61" once the floor file had grown to 6. Reading the guard's
    own denominator line is the whole fix.

    A missing or stale coverage.json makes the ratchet REFUSE, and that refusal
    must read as UNKNOWN rather than as agreement -- a floor count taken from a
    report that describes a tree which no longer exists is not a measurement.
    """
    rc, out = run([str(ROOT / "venv/bin/python"),
                   str(ROOT / "tools/check_coverage_ratchet.py")], ROOT)
    m = re.search(r"(\d+) modules in the report, (\d+) with a declared floor", out)
    if not m:
        return None, "UNKNOWN: check_coverage_ratchet.py printed no denominator"
    return [int(m.group(2)), int(m.group(1))], "check_coverage_ratchet.py"


def munit_rollup() -> tuple[list[int] | None, str]:
    """The MUnit suite count, read from the TRACKED rollup artefact.

    AUDIT04: this row was on the NOT CHECKED list because running the suite needs
    a WolframKernel, and it went stale exactly as an unwatched number does -- the
    page read 69/69 while the manifest had declared 72 since `61ca2f8`.

    But the CLAIM does not need a kernel to check; only the RUN does. The rollup
    is a tracked text file, so this reads it and check_test_manifest.sh separately
    forces it to be a full run whose TOTAL equals the declared test count. The
    two together mean a stale page and a stale rollup cannot agree with each
    other by both being wrong.

    A rollup with no SCOPE=all is UNKNOWN, not a pass: a partial run's TOTAL is
    a real number measured over the wrong denominator, which is the failure mode
    this whole page exists to make impossible.
    """
    rollup = ROOT / "results/tests/runall/Status.txt"
    if not rollup.exists():
        return None, "UNKNOWN: results/tests/runall/Status.txt is absent"
    line = rollup.read_text(errors="ignore").splitlines()[0]
    m = re.search(r"OK=(\d+)\s+FAIL=(\d+)\s+TOTAL=(\d+)", line)
    if not m:
        return None, f"UNKNOWN: rollup line is unparseable: {line!r}"
    if "SCOPE=all" not in line:
        return None, f"UNKNOWN: rollup is not a full run: {line!r}"
    ok, fail, total = (int(m.group(i)) for i in (1, 2, 3))
    if fail != 0:
        return None, f"{FATAL} rollup records {fail} failing test(s): {line!r}"
    return [ok, total], "results/tests/runall/Status.txt (SCOPE=all)"


# ── the document side ───────────────────────────────────────────────────────

# The third cell is optional: section 5's rate table is two columns, and a row
# regex that silently skips it would let a rate onto the page ungated -- the
# exact class of hole this file was written to close.
ROW = re.compile(r"^\|(?P<label>[^|]+)\|(?P<claim>[^|]+)\|(?:(?P<gate>[^|]*)\|)?\s*$")
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
            # AUDIT04-H: the original regex only matched `## 5.` literally, so
            # the §5a and §5b sub-sections (where the bio comparator table now
            # lives) were silently ignored by the parser. The fix is the same
            # intent, widened: any `## ` whose second character is `3`, `4` or
            # `5` opens a parsable section. No other top-level heading in this
            # document starts with those digits.
            head = ln[3:4]
            in_section = head in ("3", "4", "5")
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
        # Compared as FLOATS. `int(x)` was truncating, so a document claiming
        # 92.4% would have matched a tool printing 92.0%. Integer claims still
        # compare equal against integer results (92 == 92.0).
        want = nums
        if [float(x) for x in got] != want:
            bad.append(f"{label}\n      document says {want}\n      {how} says {got}")
        else:
            print(f"  OK   {label}: {got}  ({how})")

    total = len(claims)
    print(f"\nVERIFICATION-NUMBERS: checked {checked} of {total} numeric claims "
          f"in VERIFICATION.md sections 3, 4 and 5.")
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

    # AUDIT04-H task H0.3 — the page that checks itself. The sentence about
    # this gate (the "for 12 of its 44 numbers" line) used to be a footnote
    # about a thing that checked the document, while nothing checked the
    # footnote. A planted wrong figure here would not move any other claim;
    # the gate would print "checked 12 of 44" and exit 0 and the wrong
    # number would sit on the page until somebody read the prose aloud.
    #
    # The three counts in that sentence are now parsed from the document and
    # compared against what the gate has just computed. A planted change
    # must exit non-zero naming it; a clean state exits 0 with a confirmation
    # line. The three numbers do not include the {n}-of-{m} rate as one
    # figure: they are three independent counts (checked, total, unchecked)
    # and each has its own producer — `total = checked + unchecked + unknown`
    # is held, not asserted.
    self_bad = self_check_counts(DOC.read_text(), checked, total, len(unchecked),
                                 len(unknown))
    if self_bad:
        print("\n  MISMATCH -- the page's own summary of this gate disagrees with what it computed:")
        for s in self_bad:
            print(f"    - {s}")
        return 1
    print(f"\n  SELF-CHECK: prose counts (checked={checked}, total={total}, "
          f"unchecked={len(unchecked)}, unknown={len(unknown)}) agree with the page.")
    return 0


def self_check_counts(text: str, checked: int, total: int,
                      unchecked: int, unknown: int) -> list[str]:
    """Re-derive the page's own self-describing counts and compare.

    The three numbers in the §3 sub-section are bound to the same quantities
    the gate has just computed: how many of the parsed claims it checked,
    how many there were in total, and how many it did not check (the
    remainder over the UNKNOWN+bad pile is the "names the N it does not"
    figure on the page). A `bad` count > 0 is already returned at exit 1
    above; this function only looks at the counts that are settled.

    Returns an empty list on agreement, a list of human-readable lines on
    disagreement. The caller decides the exit code.
    """
    bad: list[str] = []

    def first_int(pattern: str) -> int | None:
        m = re.search(pattern, text)
        return int(m.group(1)) if m else None

    # "for 12 of its 44 numbers" — the section heading carries the SAME two
    # numbers the gate has just computed. Reading it twice from one regex
    # would tie the two to each other and let a paired typo pass; each is
    # parsed independently and compared independently.
    m_heading = re.search(r"for\s+(\d+)\s+of\s+its\s+(\d+)\s+numbers", text)
    if m_heading:
        h_checked, h_total = int(m_heading.group(1)), int(m_heading.group(2))
        if h_checked != checked:
            bad.append(f"heading says checked={h_checked}, gate computed {checked}")
        if h_total != total:
            bad.append(f"heading says total={h_total}, gate computed {total}")

    # "Of the **44 numeric rows** it checks **12** and **names the 32 it does not**"
    prose_total = first_int(r"\*\*(\d+)\s+numeric rows\*\*")
    prose_checked = first_int(r"checks\s+\*\*(\d+)\*\*")
    # The "it does not" sits INSIDE the same bold as the number, and the
    # opening ** is BEFORE "names the", not between it and the number.
    prose_unchecked = first_int(r"\*\*names the\s+(\d+)\s+it does not\*\*")

    if prose_total is not None and prose_total != total:
        bad.append(f"prose says total=**{prose_total}**, gate computed {total}")
    if prose_checked is not None and prose_checked != checked:
        bad.append(f"prose says checked=**{prose_checked}**, gate computed {checked}")
    if prose_unchecked is not None and prose_unchecked != unchecked:
        bad.append(f"prose says unchecked=**{prose_unchecked}**, gate computed {unchecked}")
    return bad


if __name__ == "__main__":
    sys.exit(main())
