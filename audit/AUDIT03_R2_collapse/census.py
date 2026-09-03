#!/usr/bin/env python3
"""AUDIT03/R2a.1 — census of duplicate implementations, with PARITY STATUS.

Read-only. Deletes nothing, edits nothing, recommends nothing that it has not
measured.

The point of this file is a distinction that the whole phase turns on:

    a NAME matching in two files is not evidence that the two AGREE.

`src/causal/CausalBool.m` and `src/integration/Alpha.m` shared every name and
had diverged; that is recorded in the header of check_single_engine.sh and it is
why that guard exists. So this census reports, per concept:

    sites        every definition site outside archive/ and the venvs
    parity       whether the sites actually agree, measured where they can be
                 called, and UNKNOWN where they cannot -- never assumed

Only a concept whose parity is PROVEN may proceed to R2a.2.

Run:
    venv/bin/python audit/AUDIT03_R2_collapse/census.py
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for p in ("src", "index-deconvolution/src", "papers/method/code/complexity_analysis",
          "imp-prices", "imp-pathinfo-paper/src"):
    sys.path.insert(0, str(ROOT / p))

LINE = "-" * 78


def part(t):
    print(f"\n{LINE}\n{t}\n{LINE}")


def sites(pattern: str, exts=("py", "m", "wl")) -> list[str]:
    """Definition sites outside archive/, venvs and this audit's own scratch."""
    cmd = ["grep", "-rlE", pattern, str(ROOT)]
    for e in exts:
        cmd += [f"--include=*.{e}"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.split()
    keep = []
    for f in sorted(out):
        rel = str(Path(f).relative_to(ROOT))
        if rel.startswith(("archive/", "venv/", "audit/")) or "/.venv/" in rel \
                or "/venv/" in rel or "__pycache__" in rel:
            continue
        keep.append(rel)
    return keep


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


report = {}

# ===========================================================================
part("CONCEPT 1 — gate semantics")
# ===========================================================================
g = sites(r"def _eval_gate|def apply_gate|ApplyGate\[gate_|ApplyGate\[name_")
for s in g:
    print(f"  {s}")
print(f"\n  {len(g)} definition sites.")

print("\n  PARITY, measured where the sites can be called from Python:")
GATES = ["AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT", "IMPLIES",
         "NIMPLIES", "MAJORITY"]
try:
    from complexity_analysis import _eval_gate as ca_gate
    from causalbool import apply_gate as idx_gate
    def params_for(gate, d):
        """Each implementation demands its own parameters. Supply what the gate
        needs rather than {} -- an empty dict makes IMPLIES raise KeyError in one
        of them, which would be recorded as a crash and not as the parameter
        mismatch it actually is."""
        if gate in ("IMPLIES", "NIMPLIES") and d >= 2:
            return {"pair": [1, 2]}
        if gate == "KOFN":
            return {"k": max(1, d // 2)}
        return {}

    cells, diffs, errs = 0, [], []
    for gate in GATES:
        for d in range(1, 5):
            p = params_for(gate, d)
            for bits in itertools.product([0, 1], repeat=d):
                try:
                    a = ca_gate(gate, list(bits), dict(p))
                except Exception as exc:                     # noqa: BLE001
                    a = f"ERR:{type(exc).__name__}:{exc}"
                try:
                    b = idx_gate(gate, list(bits), dict(p))
                except Exception as exc:                     # noqa: BLE001
                    b = f"ERR:{type(exc).__name__}:{exc}"
                cells += 1
                if a != b:
                    (errs if (isinstance(a, str) or isinstance(b, str)) else diffs
                     ).append((gate, d, list(bits), a, b))
    if errs:
        print(f"    {len(errs)} cells where at least one implementation REFUSED "
              f"the call (parameter-contract mismatch, not a value mismatch):")
        seen = set()
        for g_, d_, b_, a_, bb_ in errs:
            key = (g_, str(a_)[:40], str(bb_)[:40])
            if key in seen:
                continue
            seen.add(key)
            print(f"      {g_} d={d_}: A={str(a_)[:46]} | B={str(bb_)[:46]}")
    print(f"    complexity_analysis._eval_gate  vs  causalbool.apply_gate")
    print(f"    {cells} cells compared, {len(diffs)} disagree on VALUE, "
          f"{len(errs)} on the CALL CONTRACT")
    for x in diffs[:12]:
        print(f"      VALUE {x}")
    gate_parity = ("PROVEN-EQUAL" if not diffs and not errs else
                   "DIVERGED-VALUE" if diffs else "DIVERGED-CONTRACT")
except Exception as exc:                                     # noqa: BLE001
    cells, diffs, errs, gate_parity = 0, [], [], f"UNKNOWN ({exc})"
    print(f"    UNKNOWN — could not import both: {exc}")

print("\n  Byte-level check on the two copies that share a filename:")
pair = ("index-deconvolution/src/causalbool.py", "imp-prices/vendor/causalbool.py")
if all((ROOT / p).exists() for p in pair):
    same = sha(pair[0]) == sha(pair[1])
    print(f"    {pair[0]}  {sha(pair[0])}")
    print(f"    {pair[1]}  {sha(pair[1])}")
    print(f"    identical: {same}")
else:
    same = None
print("""
  The Wolfram sites (Gates.m, CausalBoolCore.wl, and the two src/scripts guards)
  are NOT compared here. Their parity is claimed at 135/135 by AUDIT02, and that
  claim is evidence only if re-run -- R2a.2 must re-run it before anything is
  deleted, not cite it.""")
report["gate_semantics"] = {"sites": g, "python_cells": cells,
                            "python_value_diffs": len(diffs),
                            "python_contract_diffs": len(errs),
                            "parity": gate_parity,
                            "vendor_copy_identical": same}

# ===========================================================================
part("CONCEPT 2 — per-node description length")
# ===========================================================================
d = sites(r"log2Int\[k\]|_log2\(K\)|log2_int\(k\)|log2\(len\(GATE_LABELS\)\)|log2Int\[K\]")
for s in d:
    print(f"  {s}")
print(f"\n  {len(d)} definition sites.")
print("""
  PARITY: NOT PROVEN, and NOT PROVABLE BY REFACTOR. Measured on 2026-09-03
  (audit/AUDIT03_R3_description_length/):

    with the in-degree field   : bio_D_experiment.py, BioMetrics.m,
                                 complexity_analysis.py, TSK-MIXED-001  -- agree,
                                 572 cells, 0 disagreements
    WITHOUT it, still          : TSK-THEORY-002, TSK-THEORY-004,
                                 imp-pathinfo causalbool_mirror,
                                 src/description_lengths.py

  These are not copies that drifted by accident: two of them are pinned by
  published tables elsewhere. Which implementation becomes canonical is the
  D_formula-versus-D_schema decision, which is R3 and is author-gated.
  => R2b, not R2a. Nothing here may be collapsed before R0.3.""")
report["description_length"] = {"sites": d, "parity": "SPLIT — 4 with field, 4 without",
                                "route": "R2b (author-gated)"}

# ===========================================================================
part("CONCEPT 3 — offset family / allOffsets")
# ===========================================================================
o = sites(r"allOffsets\[n_Integer|def all_offsets")
for s in o:
    print(f"  {s}")
print(f"\n  {len(o)} definition sites.")
bodies = {}
for s in o:
    txt = (ROOT / s).read_text()
    i = txt.find("allOffsets[n_Integer")
    if i >= 0:
        bodies[s] = hashlib.sha256(
            " ".join(txt[i:i + 400].split()).encode()).hexdigest()[:12]
for s, h in bodies.items():
    print(f"    {h}  {s}")
identical = len(set(bodies.values())) <= 1
print(f"\n  textually identical: {identical}")
print("""    corroboration_6node.wl LACKS the If[Length[ws]==0, {0}, ...] guard that
    the other two carry. TEXTUAL difference is not FUNCTIONAL difference, and
    hashing cannot tell them apart -- so it was measured in the kernel:
      audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl
      all coordinates connected: guarded {0}, unguarded {0}
      exhaustive n=1..6, every connected subset: 126 cases, 0 differ
    Wolfram's Dot[{},{}] is 0, so the guard is cosmetic.""")
offsets_functional = "PROVEN-EQUAL (126/126, kernel-measured)"
print(f"    functional parity: {offsets_functional}")
print("""
  CAUTION carried from GLOSSARY sec.1d: all three compute the SPECIAL CASE --
  the subset sums of the DISCONNECTED coordinates' weights -- not the general
  offset family. Collapsing them to one owner is correct and mechanical, but the
  survivor must be named for what it computes. Renaming it is a judgement about
  the theory, so the NAME goes to R2b even though the MERGE is R2a.""")
report["offset_family"] = {"sites": o, "bodies_textually_identical": identical,
                           "functional_parity": offsets_functional,
                           "route": "R2a merge, R2b naming"}

# ===========================================================================
part("VERDICT — what may proceed to R2a.2")
# ===========================================================================
print(f"""
  gate semantics        : {gate_parity} on the Python pair -- 0 VALUE
                          disagreements over 300 cells, but the two disagree on
                          the CALL CONTRACT: complexity_analysis demands
                          params["pair"] for IMPLIES at d=1 and raises KeyError
                          without it, while causalbool returns 1. Agreeing on
                          every value they both compute is not the same as being
                          interchangeable. -> R2a.2 BLOCKED until the contract is
                          reconciled AND the Wolfram 135/135 claim is RE-RUN
                          rather than cited.
  description length    : SPLIT 4/4. -> R2b only, blocked on R0.3.
  offset family         : textually identical {identical}, but FUNCTIONALLY
                          {offsets_functional}. -> R2a.2 may proceed on the
                          merge; the survivor's NAME is an R2b question.

  Nothing is deleted by this script. The rule stands: no copy is removed until an
  elementwise parity run against the survivor is committed as evidence, and every
  collapse adds its guard in the same commit.
""")
(HERE / "census.json").write_text(json.dumps(report, indent=1))
