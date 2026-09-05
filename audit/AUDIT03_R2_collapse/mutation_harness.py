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
]


def sh(cmd: list[str] | str, cwd: Path, timeout: int = 1800) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(cwd), shell=isinstance(cmd, str),
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default=None, help="owner substring")
    ap.add_argument("--smoke", type=int, default=0)
    a = ap.parse_args()

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

    wt = make_worktree()
    try:
        # Baseline: the tier must be GREEN before any mutant, or a "kill" would
        # merely be the pre-existing red.
        for tier in sorted({m.tier for m in selected}):
            green, fails = run_tier(tier, wt)
            print(f"baseline {tier}: {'GREEN' if green else 'RED ' + str(fails)}")
            if not green:
                print("REFUSED: baseline is not green; every mutant would score "
                      "as killed for the wrong reason.")
                return 2
        print()

        for i, m in enumerate(selected, 1):
            sh(["git", "checkout", "--", "."], wt)
            sh(["git", "clean", "-fd", "results", "figures"], wt)
            hits = apply_mutant(m, wt)
            if hits == 0:
                m.result = "NOT-APPLIED"
                print(f"[{i}/{len(selected)}] {m.mid}: NOT APPLIED "
                      f"(pattern absent) -- excluded from the denominator")
                continue
            t0 = time.time()
            green, fails = run_tier(m.tier, wt)
            m.seconds = time.time() - t0
            m.killed_by = fails
            m.result = "SURVIVED" if green else "KILLED"
            print(f"[{i}/{len(selected)}] {m.owner}/{m.mid}: {m.result} "
                  f"({len(fails)} test(s), {m.seconds:.0f}s)")
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

    RESULTS.write_text(json.dumps(
        {"n_selected": len(selected), "n_scored": len(scored),
         "n_killed": len(killed), "n_survived": len(survived),
         "n_not_applied": len(notapp),
         "mutants": [{"id": m.mid, "owner": m.owner, "tier": m.tier,
                      "result": m.result, "killed_by": m.killed_by,
                      "seconds": round(m.seconds, 1), "note": m.note}
                     for m in selected]}, indent=2))
    print(f"\nwritten: {RESULTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
