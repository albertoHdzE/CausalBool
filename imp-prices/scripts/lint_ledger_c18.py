#!/usr/bin/env python
"""Ledger lint for FINDINGS.md entry C18 (AUDIT01/T2.1, step 3).

Asserts that every statistic the C18 row of imp-prices/FINDINGS.md quotes as a
live claim appears, at numeric equality (percentages modulo rounding to one
decimal), in the artifact the row cites: results/b4_description_length.json,
pinned by content sha256 prefix 160d8437a2eb20dc. Also asserts bitacora/04's
dated addendum carries the same corrected hill-climb triple.

Checks performed
  1. pin integrity      : JSON content_sha256 startswith the pinned prefix.
  2. index-set clause   : 22 distinct winners over 300 resamples, modal 26.7%.
  3. CPT clause         : 4 distinct winners, modal {WTI_CL} at 51.7%.
  4. hill-climb clause  : 6 distinct winners over 120 resamples, modal
                          {WTI_Spot} at 37.5%, WTI_CL second at 33.3%.
  5. full-sample clause : index-set full-sample winner {WTI_CL} at 5.3%.
  6. addendum parity    : bitacora/04's AUDIT01/T2.1 addendum quotes the same
                          corrected hill-climb triple (6, WTI_Spot, 37.5).
  7. superseded triple  : the wrong historical triple must NOT appear as a live
                          claim inside the C18 row itself (it may appear only
                          inside the dated correction note, quoted as history).

Exit codes: 0 all checks pass; 1 any mismatch (named). Run on scratch copies
with --findings/--bitacora/--json for the planted-mismatch control.

    .venv/bin/python scripts/lint_ledger_c18.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from imp_prices.config import RESULTS

PIN_PREFIX = "160d8437a2eb20dc"
CORRECTION_MARKER = "Correction 2026-08-24 (AUDIT01/T2.1)"
ADDENDUM_MARKER = "Addendum 2026-08-24 (AUDIT01/T2.1)"


def fail(msg):
    print(f"LINT FAIL: {msg}")
    return 1


def norm(token):
    r"""Unescape markdown underscores in set names: {WTI\_CL} -> WTI_CL."""
    return token.replace("\\_", "_")


def pct(fraction):
    return round(100.0 * fraction, 1)


def lint(findings_path, bitacora_path, json_path):
    problems = []

    with open(json_path) as fh:
        doc = json.load(fh)
    if not str(doc.get("content_sha256", "")).startswith(PIN_PREFIX):
        problems.append(
            f"pin integrity: content_sha256 {doc.get('content_sha256')!r} "
            f"does not carry pinned prefix {PIN_PREFIX}")

    bs = doc.get("bootstrap", {})
    for key in ("index-set", "cpt", "hill_climb"):
        if key not in bs:
            problems.append(f"JSON missing bootstrap block {key!r}")
    if problems:
        return problems

    text = open(findings_path).read()

    # The C18 row = the single table line starting '| C18 |'.
    row_match = re.search(r"^\| C18 \|(.*)$", text, re.M)
    if not row_match:
        return ["C18 row not found in FINDINGS"]
    row = row_match.group(1)

    # ---- clause: index-set stability ------------------------------------
    m_is = re.search(r"index-set code length yields \*?\*?(\d+)\*?\*? distinct "
                     r"winning parent sets over (\d+) resamples "
                     r"\(modal ([\d.]+) per cent\)", row)
    if not m_is:
        problems.append("C18 row: cannot locate index-set clause")
    else:
        n_is, nb_is, mod_is = m_is.groups()
        blk = bs["index-set"]
        if int(n_is) != blk["n_distinct_winners"]:
            problems.append(f"index-set distinct winners: prose {n_is} vs JSON "
                            f"{blk['n_distinct_winners']}")
        if int(nb_is) != blk["n_boot"]:
            problems.append(f"index-set n_boot: prose {nb_is} vs JSON {blk['n_boot']}")
        if abs(float(mod_is) - pct(blk["modal_frequency"])) > 0.051:
            problems.append(f"index-set modal frequency: prose {mod_is}% vs JSON "
                            f"{pct(blk['modal_frequency'])}%")

    # ---- clause: CPT stability ------------------------------------------
    m_cpt = re.search(r"the CPT's \*?\*?(\d+)\*?\*? \(modal \{([^}]+)\}, "
                      r"([\d.]+) per cent\)", row)
    if not m_cpt:
        problems.append("C18 row: cannot locate CPT clause")
    else:
        n_cpt, set_cpt, mod_cpt = m_cpt.groups()
        blk = bs["cpt"]
        if int(n_cpt) != blk["n_distinct_winners"]:
            problems.append(f"CPT distinct winners: prose {n_cpt} vs JSON "
                            f"{blk['n_distinct_winners']}")
        if norm(set_cpt) != norm(blk["modal_parents"]):
            problems.append(f"CPT modal set: prose {{{set_cpt}}} vs JSON "
                            f"{{{blk['modal_parents']}}}")
        if abs(float(mod_cpt) - pct(blk["modal_frequency"])) > 0.051:
            problems.append(f"CPT modal frequency: prose {mod_cpt}% vs JSON "
                            f"{pct(blk['modal_frequency'])}%")

    # ---- clause: hill climbing (corrected triple) ------------------------
    m_hc = re.search(r"hill climbing yields \*?\*?(\d+)\*?\*? over (\d+) resamples "
                     r"\(modal \{([^}]+)\}, ([\d.]+) per cent", row)
    if not m_hc:
        problems.append("C18 row: cannot locate hill-climbing clause")
    else:
        n_hc, nb_hc, set_hc, mod_hc = m_hc.groups()
        blk = bs["hill_climb"]
        if int(n_hc) != blk["n_distinct_winners"]:
            problems.append(f"hill-climb distinct winners: prose {n_hc} vs JSON "
                            f"{blk['n_distinct_winners']}")
        if int(nb_hc) != blk["n_boot"]:
            problems.append(f"hill-climb n_boot: prose {nb_hc} vs JSON {blk['n_boot']}")
        if norm(set_hc) != norm(blk["modal_parents"]):
            problems.append(f"hill-climb modal set: prose {{{set_hc}}} vs JSON "
                            f"{{{blk['modal_parents']}}}")
        if abs(float(mod_hc) - pct(blk["modal_frequency"])) > 0.051:
            problems.append(f"hill-climb modal frequency: prose {mod_hc}% vs JSON "
                            f"{pct(blk['modal_frequency'])}%")

    # ---- clause: full-sample winner frequency ----------------------------
    m_fs = re.search(r"full-sample winner \{([^}]+)\} is chosen in only "
                     r"([\d.]+) per cent", row)
    if not m_fs:
        problems.append("C18 row: cannot locate full-sample-winner clause")
    else:
        set_fs, pct_fs = m_fs.groups()
        top = {norm(r["parents"]): r["frequency"]
               for r in bs["index-set"]["top"]}
        if norm(set_fs) not in top:
            problems.append(f"full-sample winner {{{set_fs}}} absent from "
                            f"index-set top list")
        elif abs(float(pct_fs) - pct(top[norm(set_fs)])) > 0.051:
            problems.append(f"full-sample frequency: prose {pct_fs}% vs JSON "
                            f"{pct(top[norm(set_fs)])}%")

    # ---- superseded triple must not be a live claim in the row ------------
    if CORRECTION_MARKER not in text:
        problems.append("FINDINGS missing dated correction marker "
                        f"{CORRECTION_MARKER!r}")
    if re.search(r"yields \*?\*?5\*?\*? over 120 resamples", row):
        problems.append("C18 row still carries the superseded hill-climb triple "
                        "(5 over 120) as a live claim")

    # ---- bitacora addendum parity -----------------------------------------
    btext = open(bitacora_path).read()
    idx = btext.find(ADDENDUM_MARKER)
    if idx < 0:
        problems.append(f"bitacora/04 missing addendum marker {ADDENDUM_MARKER!r}")
    else:
        addendum = btext[idx:]
        hc = bs["hill_climb"]
        want_triple = (str(hc["n_distinct_winners"]),
                       "{" + hc["modal_parents"] + "}",
                       f"{100 * hc['modal_frequency']:g}%")
        plain = addendum.replace("\\_", "_")
        for piece in want_triple:
            if piece not in plain:
                problems.append(f"bitacora/04 addendum lacks corrected-triple "
                                f"element {piece!r}")
        if PIN_PREFIX[:16] not in addendum:
            problems.append("bitacora/04 addendum does not trace the pinned hash")

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--findings", default=None)
    ap.add_argument("--bitacora", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    findings = args.findings or os.path.join(base, "FINDINGS.md")
    bitacora = args.bitacora or os.path.join(base, "bitacora",
                                             "04_b4_description_length.md")
    jpath = args.json or os.path.join(RESULTS, "b4_description_length.json")

    problems = lint(findings, bitacora, jpath)
    if problems:
        for p in problems:
            print(f"LINT FAIL: {p}")
        print(f"lint_ledger_c18: {len(problems)} problem(s)")
        return 1
    print("lint_ledger_c18: PASS — every C18 statistic matches its pinned "
          "artifact; addendum carries the identical corrected triple.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
