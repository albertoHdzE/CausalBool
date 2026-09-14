"""AUDIT03-C — do our tests actually catch anything?

Four audit passes made the suite green. Green is cheap: this programme has
already found a parity harness printing "cases matched: 0/0 / all match: True",
a verifier reading a key one level too deep, eleven files exporting a literal
"OK", and three files reported green while syntactically broken. A test count is
not a measure of test quality. A KILL RATE is.

One mutant was run by hand on 2026-09-04 -- MAJORITY's tie threshold,
Floor[d/2]+1 -> Ceiling[d/2], breaking declared convention D-3 -- and five tests
across four sections caught it. That is a spot check, not a rate.

WHY THIS RUNS IN A GIT WORKTREE, and it is not fastidiousness. The hand-run
mutation restored Gates.m but NOT the artefacts, leaving five Status.txt files
reading FAIL and a rollup of OK=64 FAIL=5 TOTAL=69 in the working tree. That is
the stale-artefact class this audit spent a whole pass removing, reintroduced by
the tool built to test for it. A worktree shares the object store, so isolation
is cheap, and the working tree cannot be touched at all.

METHOD, and where it is weak.

  * Each mutant is a single, plausible edit to a DECLARED OWNER in
    GOVERNANCE/CORE.md -- an inverted comparison, an off-by-one, a dropped
    branch, a swapped constant. Not random noise: noise is easy to kill and
    flatters the rate.
  * Each mutant is VERIFIED TO APPLY. A patch that silently matches nothing
    would be scored "killed by nothing" and inflate the result; the harness
    refuses on a no-op.
  * THERE IS NO ROUTING. Every mutant faces every check that exists: the
    69-test MUnit suite, both pytest suites, and both closure tiers. The first
    version DID route by owner language, and it produced a false coverage gap --
    all four `py-dl-*` mutants "survived" the python tier while the gate that
    guards them, tools/test_description_length_parity.py, sits in the WOLFRAM
    tier because it executes a Wolfram producer. A routed kill rate measures the
    routing, not the suite. Cost is ~12 min per mutant; that is the price of the
    number meaning what it says.
  * SURVIVORS ARE NOT A SCORE. A surviving mutant is either a COVERAGE GAP or an
    EQUIVALENT MUTANT that changes nothing observable. Conflating the two is the
    classic mutation-testing error. Every survivor is listed for adjudication,
    never silently counted as a failure of the suite.
  * The kill rate is reported per owner WITH ITS DENOMINATOR. An owner with zero
    kills is the real finding, and is named.

Usage:
    venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --list
    venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --all
    venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --only gates
    venv/bin/python audit/AUDIT03_R2_collapse/mutation_harness.py --smoke 3
"""
from __future__ import annotations

import argparse
import collections
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKTREE = Path("/tmp/causalbool-mutation-worktree")
KERNEL = "/Applications/Wolfram.app/Contents/MacOS/WolframKernel"
RESULTS = ROOT / "audit" / "AUDIT03_R2_collapse" / "mutation_results.json"


@dataclass
class Mutant:
    mid: str
    owner: str          # the CORE.md owner this belongs to
    path: str           # file to patch, repo-relative
    old: str
    new: str
    tier: str           # "wolfram" | "python"
    note: str           # what real mistake this imitates
    result: str = ""
    killed_by: list = field(default_factory=list)
    seconds: float = 0.0


# ── The catalogue ────────────────────────────────────────────────────────────
# One to several per declared owner. Each imitates a mistake somebody could
# actually make, which is the only kind worth measuring.

MUTANTS: list[Mutant] = [
    # ---- Integration`Gates` : the twelve gate families -----------------------
    Mutant("gates-and-inverted", "Gates", "src/Packages/Integration/Gates.m",
           "myAnd[list_] := If[Count[list, 0] == 0, 1, 0]",
           "myAnd[list_] := If[Count[list, 0] > 0, 1, 0]",
           "wolfram", "AND inverted"),
    Mutant("gates-or-strict", "Gates", "src/Packages/Integration/Gates.m",
           "myOr[list_] := If[Count[list, 1] > 0, 1, 0]",
           "myOr[list_] := If[Count[list, 1] > 1, 1, 0]",
           "wolfram", "OR becomes at-least-two: an off-by-one in a threshold"),
    Mutant("gates-xor-parity", "Gates", "src/Packages/Integration/Gates.m",
           "myXor[list_] := Mod[Total[list], 2]",
           "myXor[list_] := Mod[Total[list] + 1, 2]",
           "wolfram", "XOR parity flipped: XOR and XNOR swapped"),
    Mutant("gates-nand", "Gates", "src/Packages/Integration/Gates.m",
           "myNand[list_] := If[Count[list, 0] > 0, 1, 0]",
           "myNand[list_] := If[Count[list, 0] >= 0, 1, 0]",
           "wolfram", "NAND becomes constant 1"),
    Mutant("gates-nor", "Gates", "src/Packages/Integration/Gates.m",
           "myNor[list_] := If[Count[list, 1] == 0, 1, 0]",
           "myNor[list_] := If[Count[list, 1] <= 1, 1, 0]",
           "wolfram", "NOR threshold loosened by one"),
    Mutant("gates-not", "Gates", "src/Packages/Integration/Gates.m",
           "myNot[list_] := 1 - First[list]",
           "myNot[list_] := First[list]",
           "wolfram", "NOT becomes identity"),
    Mutant("gates-implies-swap", "Gates", "src/Packages/Integration/Gates.m",
           "myImplies[list_] := myOr[{1 - list[[1]], list[[2]]}]",
           "myImplies[list_] := myOr[{list[[1]], 1 - list[[2]]}]",
           "wolfram", "IMPLIES antecedent/consequent swapped -- the ordered-pair "
                      "question AUDIT03-B raised"),
    Mutant("gates-nimplies", "Gates", "src/Packages/Integration/Gates.m",
           "myNImplies[list_] := myAnd[{list[[1]], 1 - list[[2]]}]",
           "myNImplies[list_] := myAnd[{1 - list[[1]], list[[2]]}]",
           "wolfram", "NIMPLIES operands swapped"),
    Mutant("gates-majority-tie", "Gates", "src/Packages/Integration/Gates.m",
           "th = If[TrueQ[Lookup[params, \"tiePolicy\", \"strict\"] === \"atOrAbove\"], Ceiling[d/2], Floor[d/2] + 1];",
           "th = If[TrueQ[Lookup[params, \"tiePolicy\", \"strict\"] === \"atOrAbove\"], Ceiling[d/2], Ceiling[d/2]];",
           "wolfram", "MAJORITY tie policy flipped: breaks declared convention D-3. "
                      "The hand-run mutant; 5 tests caught it."),
    Mutant("gates-kofn-strict", "Gates", "src/Packages/Integration/Gates.m",
           "Boole[Count[list, 1] >= k]",
           "Boole[Count[list, 1] > k]",
           "wolfram", "KOFN loses its non-strict branch -- the exact T4.7 defect"),
    Mutant("gates-canalising-branch", "Gates", "src/Packages/Integration/Gates.m",
           "If[list[[i]] == v, out, myOr[list]]",
           "If[list[[i]] == v, out, 0]",
           "wolfram", "CANALISING non-canalised branch becomes a constant 0 -- "
                      "the AUDIT02/P1 defect, reintroduced"),

    # ---- Integration`BioMetrics` : description length and C_formula ----------
    Mutant("dl-drop-indegree", "BioMetrics", "src/Packages/Integration/BioMetrics.m",
           "  cost += log2Int[n + 1];",
           "  (* mutant: in-degree field dropped *)",
           "wolfram", "D_formula loses the log2(n+1) in-degree field -- the very "
                      "field AUDIT03/R2b restored to make it decodable"),
    Mutant("dl-binomial-off", "BioMetrics", "src/Packages/Integration/BioMetrics.m",
           "cost += log2Int[Max[1, Binomial[n, d]]];",
           "cost += log2Int[Max[1, Binomial[n, d] + 1]];",
           "wolfram", "input-set field off by one inside the log"),
    Mutant("cformula-kofn", "BioMetrics", "src/Packages/Integration/BioMetrics.m",
           "\"KOFN\", log2Int[d + 1] + 1,",
           "\"KOFN\", 1 + d,",
           "wolfram", "C_formula KOFN branch reverts to the drifted 1+d form "
                      "found in two copies during the AUDIT03 collapse"),

    # ---- Integration`IndexAlgebra` -------------------------------------------
    Mutant("phi-no-reverse", "IndexAlgebra", "src/Packages/Integration/IndexAlgebra.m",
           "Reverse[IntegerDigits[",
           "(IntegerDigits[",
           "wolfram", "Phi bit-reversal dropped: LSB/MSB ordering silently swapped"),

    # ---- The standalone companion core ---------------------------------------
    Mutant("core-alloffsets", "CausalBoolCore", "papers/method/code/lib/CausalBoolCore.wl",
           "ws = weights[n][[free]];",
           "ws = weights[n][[free]][[;; UpTo[Max[0, Length[free] - 1]]]];",
           "wolfram", "allOffsets drops one free coordinate: the offset family "
                      "halves"),
    Mutant("core-composed-y5", "CausalBoolCore", "papers/method/code/lib/CausalBoolCore.wl",
           "y6 = Mod[input[[1]] + input[[3]] + y5, 2];",
           "y6 = Mod[input[[1]] + input[[3]] + input[[5]], 2];",
           "wolfram", "the composed 6-node update becomes the synchronous one -- "
                      "differs on exactly 32 of 64 rows, measured in AUDIT03"),
    Mutant("core-applygate-default", "CausalBoolCore", "papers/method/code/lib/CausalBoolCore.wl",
           "gate === \"NOT\",      1 - First[inputs],",
           "gate === \"NOT\",      First[inputs],",
           "wolfram", "companion-code NOT becomes identity: readers reproducing "
                      "the paper get a different engine"),

    # ---- src/scripts/NetworkIO.m : the corpus loader --------------------------
    Mutant("io-drop-logic", "NetworkIO", "src/scripts/NetworkIO.m",
           "\"logic\"",
           "\"gates\"",
           "wolfram", "corpus loader reads the classification LABEL instead of "
                      "the authoritative formula -- the AUDIT02/H defect that "
                      "two of five copies still carried"),

    # ---- src/description_lengths.py : the Python owner ------------------------
    Mutant("py-dl-gate-label", "description_lengths", "src/description_lengths.py",
           "cost = math.log2(len(GATE_LABELS))",
           "cost = math.log2(len(GATE_LABELS) - 1)",
           "python", "catalogue size off by one: eleven families priced, twelve used"),
    Mutant("py-dl-indegree", "description_lengths", "src/description_lengths.py",
           "        cost += math.log2(n + 1)",
           "        cost += math.log2(n)",
           "python", "in-degree field cannot encode d=0; Kraft sum breaks"),
    Mutant("py-dl-comb", "description_lengths", "src/description_lengths.py",
           "cost += math.log2(max(1, math.comb(n, degree)))",
           "cost += math.log2(max(1, math.comb(n, max(0, degree - 1))))",
           "python", "input-set field prices the wrong subset size"),
    Mutant("py-dl-kofn", "description_lengths", "src/description_lengths.py",
           "        cost += math.log2(degree + 1) + 1",
           "        cost += math.log2(degree + 1)",
           "python", "KOFN loses its strict-policy bit"),
    Mutant("py-dl-schema", "description_lengths", "src/description_lengths.py",
           "def schema_normal_form_length(",
           "def _unused_schema_normal_form_length(",
           "python", "D_schema producer renamed away: the primary measure vanishes"),

    # ---- src/causalbool_paths.py ---------------------------------------------
    Mutant("py-paths-root", "causalbool_paths", "src/causalbool_paths.py",
           'if (parent / "src").is_dir() and (parent / "results").is_dir():',
           'if (parent / "src").is_dir() or (parent / "results").is_dir():',
           "python", "repo-root detection loosened: matches the wrong ancestor"),
    Mutant("py-paths-figures", "causalbool_paths", "src/causalbool_paths.py",
           'return paper_root() / "figures"',
           'return paper_root()',
           "python", "figures directory collapses onto the paper root"),

    # ---- index-deconvolution/src/deconvolution.py -----------------------------
    Mutant("py-dnf-minimal", "deconvolution", "index-deconvolution/src/deconvolution.py",
           "def minimal_dnf(",
           "def _unused_minimal_dnf(",
           "python", "Quine-McCluskey owner renamed away"),
    Mutant("py-essential-vars", "deconvolution", "index-deconvolution/src/deconvolution.py",
           "def essential_variables(",
           "def _unused_essential_variables(",
           "python", "essential-variable detection removed"),

    # AUDIT04 Phase A. Both mutants above are REACHABILITY PROBES, so the
    # semantic denominator for this owner was ZERO and the report printed
    # NOT MEASURED: minimal_dnf and essential_variables are declared owners in
    # CORE.md whose assertion quality had never been tested. These five are the
    # semantic mutants that give the owner a denominator.
    #
    # `apply_mutant` replaces EVERY occurrence, so each `old` below is anchored
    # on enough context to be unique -- `y |= (1 << j)` alone appears twice, and
    # a mutant broader than its description does not isolate what it names.
    Mutant("dec-essential-invert", "deconvolution",
           "index-deconvolution/src/deconvolution.py",
           "if column[x] != column[x | bit]:",
           "if column[x] == column[x | bit]:",
           "python", "sensitivity inverted: essential set becomes its complement"),
    Mutant("dec-essential-top", "deconvolution",
           "index-deconvolution/src/deconvolution.py",
           "    for i in range(n):\n        # Create a number",
           "    for i in range(n - 1):\n        # Create a number",
           "python", "highest-indexed variable can never be found essential"),
    Mutant("dec-dnf-offset", "deconvolution",
           "index-deconvolution/src/deconvolution.py",
           "minterms = [y for y, v in enumerate(reduced) if v == 1]",
           "minterms = [y for y, v in enumerate(reduced) if v == 0]",
           "python", "DNF covers the OFF-set: the clause set is the complement"),
    Mutant("dec-dnf-polarity", "deconvolution",
           "index-deconvolution/src/deconvolution.py",
           "activators = [j for j in range(m) if (mask >> j) & 1 and (b >> j) & 1]",
           "activators = [j for j in range(m) if (mask >> j) & 1 and not ((b >> j) & 1)]",
           "python", "activators and inhibitors swapped: every clause negated"),
    Mutant("dec-reduce-index", "deconvolution",
           "index-deconvolution/src/deconvolution.py",
           "            if x & (1 << e):\n                y |= (1 << j)",
           "            if x & (1 << e):\n                y |= (1 << e)",
           "python", "reduced table indexed by ORIGINAL bit position, not the "
                     "reduced one: wrong whenever the essential set is not "
                     "contiguous from zero"),
]


def sh(cmd: list[str] | str, cwd: Path, timeout: int = 1800) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(cwd), shell=isinstance(cmd, str),
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


def assert_head_matches_working_tree() -> None:
    """Refuse if the working tree has uncommitted changes.

    AUDIT03-C, added after I wasted a run. The worktree is created from HEAD, so
    the code under test is the COMMITTED code -- but I started a run with the
    fix for a baseline failure still uncommitted in the working tree. The
    harness dutifully built a worktree without it, and would have spent five
    hours to conclude, correctly, that the baseline was red.

    Measuring HEAD is the right choice: a kill rate should describe what is
    committed, not what happens to be on disk. But then the harness must say so
    rather than let the two silently differ.
    """
    rc, out = sh(["git", "status", "--porcelain"], ROOT)
    dirty = [ln for ln in out.splitlines() if ln.strip()]
    if dirty:
        print("REFUSED: the working tree has uncommitted changes, and this "
              "harness measures HEAD.")
        print("  The result would describe code you have already changed:")
        for ln in dirty[:10]:
            print("   ", ln)
        if len(dirty) > 10:
            print(f"    ... and {len(dirty) - 10} more")
        print("  Commit (or stash) first, then re-run.")
        raise SystemExit(2)


def make_worktree() -> Path:
    if WORKTREE.exists():
        sh(["git", "worktree", "remove", "--force", str(WORKTREE)], ROOT)
        shutil.rmtree(WORKTREE, ignore_errors=True)
    rc, out = sh(["git", "worktree", "add", "--detach", str(WORKTREE), "HEAD"], ROOT)
    if rc != 0:
        raise SystemExit(f"REFUSED: could not create worktree.\n{out}")
    # The suites need the venvs, which are gitignored and so absent in a worktree.
    for link in ("venv",):
        src = ROOT / link
        if src.exists():
            (WORKTREE / link).symlink_to(src)
    return WORKTREE


def drop_worktree() -> None:
    sh(["git", "worktree", "remove", "--force", str(WORKTREE)], ROOT)
    shutil.rmtree(WORKTREE, ignore_errors=True)
    sh(["git", "worktree", "prune"], ROOT)


def run_tier(tier: str, wt: Path) -> tuple[bool, list[str]]:
    """Run EVERYTHING that could catch a mutant. Returns (all_green, killers).

    AUDIT03-C, corrected after the first smoke run. The harness originally routed
    each mutant to the tier of the file it patched -- Python owners to pytest,
    Wolfram owners to MUnit. That biased the result DOWNWARD in a way that looked
    like a coverage gap: all four `py-dl-*` mutants "survived" the python tier
    while the gate that actually guards them,
    tools/test_description_length_parity.py, sits in the WOLFRAM tier because it
    executes a Wolfram producer.

    A mutant must be offered to every check that exists, or the kill rate
    measures the routing rather than the suite. So there is no routing: every
    mutant faces the MUnit suite, both pytest suites, and both closure tiers.
    The `tier` field is kept only to report cost.
    """
    killers: list[str] = []

    rc, out = sh(["zsh", "tests/MUnit/run-tests.sh", "--all"], wt, timeout=3600)
    for ln in out.splitlines():
        if not ln.startswith("FAIL:"):
            continue
        # A FALSE KILL, and the reason this filter exists. Under memory pressure
        # the Wolfram kernel segfaults and run-tests.sh prints
        #     FAIL: X -> PASS (kernel exit=139)
        # -- note "-> PASS": the TEST passed and the KERNEL died. BASELINE.md
        # records it as a flake mode. Counting it would attribute a crash to the
        # mutant and inflate the kill rate, which is the one number this harness
        # exists to get right.
        if "exit=139" in ln or "-> PASS" in ln:
            killers.append("FLAKE-IGNORED:" + ln.split("->")[0].replace("FAIL:", "").strip())
            continue
        killers.append("munit:" + ln.split("->")[0].replace("FAIL:", "").strip())

    py = str(ROOT / "venv/bin/python")
    rc_a, _ = sh([py, "-m", "pytest", "-q", "tests/analysis", "--tb=no"], wt, timeout=900)
    if rc_a != 0:
        killers.append("pytest:tests/analysis")
    rc_b, _ = sh([py, "-m", "pytest", "-q", "--tb=no"], wt / "index-deconvolution", timeout=900)
    if rc_b != 0:
        killers.append("pytest:index-deconvolution")

    for ct in ("pure", "wolfram"):
        rc_c, _ = sh(["zsh", "tools/run_closure.sh", ct], wt, timeout=3600)
        if rc_c != 0:
            killers.append(f"closure:{ct}")

    real = [k for k in killers if not k.startswith("FLAKE-IGNORED:")]
    return (len(real) == 0), killers


def apply_mutant(m: Mutant, wt: Path) -> int:
    """Patch, and REFUSE on a no-op: an unapplied mutant would inflate the rate."""
    p = wt / m.path
    if not p.exists():
        return 0
    t = p.read_text(errors="replace")
    n = t.count(m.old)
    if n == 0:
        return 0
    p.write_text(t.replace(m.old, m.new))
    return n


def head_sha() -> str:
    rc, out = sh(["git", "rev-parse", "HEAD"], ROOT)
    return out.strip()


def write_results(selected: list[Mutant], sha: str, complete: bool) -> None:
    """Persist after EVERY mutant, not once at the end.

    AUDIT03-C, added after losing a run. The machine rebooted four hours into a
    28-mutant run; /tmp was cleared, taking the log with it, and because results
    were written only on completion, all ten finished mutants were gone. A
    measurement that costs four hours must survive a power cut, and the fix is
    four lines. `complete` records whether the file describes a finished run, so
    a partial file can never be mistaken for a final rate.
    """
    scored = [m for m in selected if m.result in ("KILLED", "SURVIVED")]
    killed = [m for m in scored if m.result == "KILLED"]
    RESULTS.write_text(json.dumps(
        {"head_sha": sha, "complete": complete,
         "n_selected": len(selected), "n_scored": len(scored),
         "n_killed": len(killed),
         "n_survived": len(scored) - len(killed),
         "n_not_applied": sum(1 for m in selected if m.result == "NOT-APPLIED"),
         "mutants": [{"id": m.mid, "owner": m.owner, "tier": m.tier,
                      "result": m.result, "killed_by": m.killed_by,
                      "seconds": round(m.seconds, 1), "note": m.note}
                     for m in selected]}, indent=2))


def load_previous(sha: str) -> dict[str, dict]:
    """Already-scored mutants from a previous run of the SAME commit.

    Keyed on the sha because a result for different code is not a result for
    this one. A mismatch discards everything rather than silently mixing two
    measurements.
    """
    if not RESULTS.exists():
        return {}
    try:
        d = json.loads(RESULTS.read_text())
    except Exception:
        return {}
    if d.get("head_sha") != sha:
        return {}
    return {m["id"]: m for m in d.get("mutants", [])
            if m.get("result") in ("KILLED", "SURVIVED", "NOT-APPLIED")}


def is_probe(m: Mutant) -> bool:
    """A reachability probe renames a public function away.

    DERIVED from the catalogue rather than hand-listed, so a probe added later
    cannot desynchronise from the exclusion list and quietly inflate the rate.
    """
    return m.old.startswith("def ") and "_unused_" in m.new


def real_killers(killed_by: list[str]) -> list[str]:
    """Killers, excluding tests the baseline already showed to be flaky.

    `len(killed_by)` includes FLAKE-IGNORED entries, so printing it produced
    lines reading `SURVIVED (3 test(s))`. The VERDICT was never computed from
    that count -- only the printed line was wrong -- but a report must not
    reproduce the same confusion.
    """
    return [k for k in killed_by if not str(k).startswith("FLAKE")]


def current_head_sha() -> str:
    """The SHA the working tree is at, by the repository's own git.

    A report printed against a stored `head_sha` that no longer matches the
    tree is the failure mode that landed in `8b8c0e3` ↔ `fc003f8`: the
    catalogue grew, the rate jumped from 23/25 to 30/30, and the file did
    not say so. AUDIT04-H task H0.2 makes the drift observable in --report.
    """
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def commits_behind(stored_sha: str, head_sha: str) -> int:
    """The number of commits between the stored run and the current HEAD.

    Negative results (the stored run is AHEAD of HEAD, i.e. a rewind) are
    reported as `0`; the staleness line still says `results are current at
    <sha>` because the recorded measurement is still the one to trust, just
    not against a SHA the tree no longer holds. A rewind should be loud in a
    different place, not here.
    """
    out = subprocess.run(
        ["git", "rev-list", "--count", f"{stored_sha}..{head_sha}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    n = int(out.stdout.strip())
    return max(n, 0)


def report() -> int:
    """Kill rate with its denominator, per owner, by instrument.

    A single headline rate hides the thing worth knowing: WHICH instrument
    caught each mutant. A mutant killed only by a closure gate is not evidence
    that the test suite checks the answer -- it is evidence that the programme
    notices, which is a weaker claim and a different one.
    """
    if not RESULTS.exists():
        print(f"REFUSED: no results at {RESULTS}. Run --all first.")
        return 2
    d = json.loads(RESULTS.read_text())
    if not d.get("mutants"):
        print("REFUSED: 0 mutants in the results file. A rate over nothing is not a rate.")
        return 2
    if not d.get("complete"):
        print(f"REFUSED: results are PARTIAL ({d.get('n_scored')}/{d.get('n_selected')} "
              "scored). A partial file must never be quoted as a final rate.")
        return 2

    # AUDIT04-H task H0.2 — the staleness contract. The first line printed
    # is ALWAYS a comparison of the stored `head_sha` against the current
    # HEAD. The line is not a footnote: --report's headline rate below is
    # valid only when this line says so, and the report must not silently
    # print a stale rate. The pre-existing SHA check in `load_previous` at
    # the resume path is unchanged; this is a separate consumer (the human
    # reading --report) and is enriched, not duplicated.
    stored = d.get("head_sha", "")
    head = current_head_sha()
    if stored == head:
        print(f"results are current at {stored}")
    else:
        n = commits_behind(stored, head)
        print(f"WARNING: results recorded at {stored}, HEAD is {head}, "
              f"{n} commits behind")

    probe_ids = {m.mid for m in MUTANTS if is_probe(m)}
    rows = [m for m in d["mutants"] if m.get("result") in ("KILLED", "SURVIVED")]
    sem = [m for m in rows if m["id"] not in probe_ids]
    pro = [m for m in rows if m["id"] in probe_ids]

    def instr(m):
        c = collections.Counter(str(k).split(":")[0] for k in real_killers(m["killed_by"]))
        return c.get("munit", 0), c.get("pytest", 0), c.get("closure", 0)

    unit_killed = [m for m in sem if sum(instr(m)[:2]) > 0]
    closure_only = [m for m in sem
                    if m["result"] == "KILLED" and sum(instr(m)[:2]) == 0]

    print(f"Mutation report — HEAD {d['head_sha'][:12]}, complete={d['complete']}")
    print(f"catalogue: {len(rows)} scored = {len(sem)} semantic + {len(pro)} "
          f"reachability probe(s)\n")
    k = sum(1 for m in sem if m["result"] == "KILLED")
    print(f"  SEMANTIC kill rate      {k}/{len(sem)} = {100*k/len(sem):.1f}%")
    print(f"  UNIT-TEST kill rate     {len(unit_killed)}/{len(sem)} = "
          f"{100*len(unit_killed)/len(sem):.1f}%   (MUnit or pytest caught it)")
    kp = sum(1 for m in pro if m["result"] == "KILLED")
    print(f"  probes (excluded)       {kp}/{len(pro)}   a kill proves only that "
          "something imports the owner\n")

    print(f"  {'owner':<22}{'killed':<10}{'semantic':<10}{'unit-killed':<13}verdict")
    for owner in sorted({m["owner"] for m in rows}):
        o = [m for m in rows if m["owner"] == owner]
        os_ = [m for m in o if m["id"] not in probe_ids]
        ok = sum(1 for m in o if m["result"] == "KILLED")
        ou = sum(1 for m in os_ if sum(instr(m)[:2]) > 0)
        # The unit-killed column is scored over the SEMANTIC subset only. An
        # owner probed but never mutated semantically has denominator 0, which
        # is "not measured" -- it must not read as a zero-kill finding.
        v = "ZERO unit-test kills" if os_ and ou == 0 else (
            "probes only — NOT MEASURED" if not os_ else "")
        print(f"  {owner:<22}{f'{ok}/{len(o)}':<10}{len(os_):<10}"
              f"{f'{ou}/{len(os_)}' if os_ else '—':<13}{v}")

    if closure_only:
        print(f"\n  killed ONLY by a governance gate — {len(closure_only)} of "
              f"{len(sem)} semantic mutants:")
        for m in closure_only:
            print(f"    {m['id']:<26}{m['note'][:58]}")

    surv = [m for m in rows if m["result"] == "SURVIVED"]
    print(f"\n  SURVIVORS — {len(surv)}. Each is a coverage gap OR an equivalent "
          "mutant; adjudicate, do not score.")
    for m in surv:
        print(f"    {m['id']:<26}{m['note'][:58]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="rates and per-owner table from the persisted results")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default=None, help="owner substring")
    ap.add_argument("--smoke", type=int, default=0)
    ap.add_argument("--resume", action="store_true",
                    help="skip mutants already scored for this exact HEAD")
    a = ap.parse_args()

    if a.report:
        return report()

    if a.list:
        print(f"{len(MUTANTS)} mutants across "
              f"{len({m.owner for m in MUTANTS})} owners\n")
        for m in MUTANTS:
            print(f"  {m.tier:8} {m.owner:20} {m.mid:26} {m.note[:60]}")
        return 0

    selected = [m for m in MUTANTS
                if not a.only or a.only.lower() in m.owner.lower()]
    if a.smoke:
        selected = selected[:a.smoke]
    if not selected:
        print("REFUSED: 0 mutants selected. A mutation run over nothing is not a result.")
        return 2

    print(f"Mutation run: {len(selected)} mutants, "
          f"{sum(1 for m in selected if m.tier == 'wolfram')} wolfram / "
          f"{sum(1 for m in selected if m.tier == 'python')} python")
    print("Isolated in a git worktree; the working tree is never touched.\n")

    assert_head_matches_working_tree()
    sha = head_sha()
    print(f"HEAD: {sha[:12]}")

    done: dict[str, dict] = {}
    if a.resume:
        done = load_previous(sha)
        if done:
            print(f"RESUMING: {len(done)} mutant(s) already scored for this "
                  f"exact commit; they will not be re-run.")
            for m in selected:
                if m.mid in done:
                    p = done[m.mid]
                    m.result, m.killed_by = p["result"], p["killed_by"]
                    m.seconds = p.get("seconds", 0.0)
        else:
            print("RESUMING: nothing reusable (no prior file, or it was for a "
                  "different commit -- results for other code are not results "
                  "for this one).")

    todo = [m for m in selected if not m.result]
    if not todo:
        print("Every selected mutant is already scored for this commit.")
        write_results(selected, sha, complete=True)
        return 0

    wt = make_worktree()
    try:
        # Baseline ONCE. This used to loop over the tier labels and so ran the
        # whole verification set twice, ~28 minutes for an identical answer,
        # because run_tier stopped routing by tier when the routing bias was
        # removed and this loop was not updated with it.
        green, fails = run_tier("all", wt)
        print(f"baseline: {'GREEN' if green else 'RED ' + str(fails)}")
        if not green:
            print("REFUSED: baseline is not green; every mutant would score "
                  "as killed for the wrong reason.")
            return 2
        print()

        for i, m in enumerate(todo, 1):
            sh(["git", "checkout", "--", "."], wt)
            sh(["git", "clean", "-fd", "results", "figures"], wt)
            hits = apply_mutant(m, wt)
            if hits == 0:
                m.result = "NOT-APPLIED"
                print(f"[{i}/{len(todo)}] {m.mid}: NOT APPLIED "
                      f"(pattern absent) -- excluded from the denominator")
                write_results(selected, sha, complete=False)
                continue
            t0 = time.time()
            green, fails = run_tier(m.tier, wt)
            m.seconds = time.time() - t0
            m.killed_by = fails
            m.result = "SURVIVED" if green else "KILLED"
            print(f"[{i}/{len(todo)}] {m.owner}/{m.mid}: {m.result} "
                  f"({len(fails)} test(s), {m.seconds:.0f}s)", flush=True)
            # Persist immediately: a reboot must cost one mutant, not the run.
            write_results(selected, sha, complete=False)
    finally:
        sh(["git", "checkout", "--", "."], wt)
        drop_worktree()

    scored = [m for m in selected if m.result in ("KILLED", "SURVIVED")]
    killed = [m for m in scored if m.result == "KILLED"]
    survived = [m for m in scored if m.result == "SURVIVED"]
    notapp = [m for m in selected if m.result == "NOT-APPLIED"]

    print("\n" + "=" * 70)
    print(f"KILL RATE: {len(killed)}/{len(scored)} mutants killed"
          + (f"  ({len(notapp)} not applied, excluded)" if notapp else ""))
    print("=" * 70)
    owners = sorted({m.owner for m in scored})
    for o in owners:
        k = [m for m in killed if m.owner == o]
        s = [m for m in scored if m.owner == o]
        flag = "   <-- ZERO KILLS" if not k else ""
        print(f"  {o:22} {len(k)}/{len(s)}{flag}")

    if survived:
        print("\nSURVIVORS — each is a COVERAGE GAP or an EQUIVALENT MUTANT.")
        print("These are different findings. Adjudicate; do not score.")
        for m in survived:
            print(f"  {m.owner}/{m.mid}\n      {m.note}")

    write_results(selected, sha, complete=True)
    print(f"\nwritten: {RESULTS.relative_to(ROOT)}  (complete, HEAD {sha[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
