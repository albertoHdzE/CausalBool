#!/usr/bin/env python3
"""AUDIT03/R1.1 — a BOUNDED FALSIFICATION of my own triage.

At R0 I classified 23 commits into three groups and asserted of thirteen of
them:

    "These 13 commits were settled solely by elementwise comparison against an
     exhaustive truth table, an independent implementation, or a byte-level
     diff, and none quotes a codelength or judges expressibility."

That is a claim about my own work, made by me, and a general "review it again"
invitation would reproduce whatever blindness produced it. So this is run the
other way round: the claim is fixed, the evidence is fixed, and the task is to
BREAK it. A commit moves MECHANICAL -> ECONOMIC on either of two triggers:

  T1  its VERDICT depends on a quantity measured in bits;
  T2  its VERDICT depends on a judgement about what the method should express.

The distinction that matters, and the one that makes this test non-trivial: a
commit may MENTION bits without its verdict DEPENDING on them. Regenerating an
artefact that happens to contain a bit-count is not the same as deciding
something by comparing bit-counts. So the search is deliberately over-inclusive
-- every candidate marker in the message and the full diff -- and each hit is
then adjudicated against the two triggers rather than counted.

Run:
    venv/bin/python audit/AUDIT03_R1_correct_the_record/falsify_mechanical_triage.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

MECHANICAL = ["8463895", "2072d7c", "0603eb4", "5646fbd", "2ee4d59", "aca0842",
              "5567064", "d420b3b", "a4de229", "85717ab", "b166b36", "8ebf794",
              "f245195"]

# T1 markers: anything that could carry a verdict expressed in bits.
BITS = re.compile(
    r"\bbits?\b|\blog2|\blog_2|Log\[2|description[ _]length|D_formula|D_schema"
    r"|encodeNodeCost|encodeCostBits|\bentropy\b|Shannon|\bBDM\b|\bZIP\b"
    r"|compression ratio|codelength|code length|Kraft|\bH_total\b",
    re.I)

# T2 markers: anything that could carry a judgement about expressibility.
EXPRESS = re.compile(
    r"expressib|expressiv|cannot express|can express|should express"
    r"|\bcatalogue\b|\bcoverage\b|covers? all|family set|new family"
    r"|twelve famil|13 famil|thirteenth|256 rules|ECA rules",
    re.I)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True).stdout


def context(text: str, rx: re.Pattern, width: int = 90) -> list[str]:
    out = []
    for m in rx.finditer(text):
        line = text[max(0, m.start() - width // 2): m.end() + width // 2]
        line = " ".join(line.split())
        if line not in out:
            out.append(line)
    return out


def main() -> int:
    print("AUDIT03/R1.1 — bounded falsification of the MECHANICAL triage")
    print("claim under test: none of these 13 quotes a codelength or judges")
    print("                  expressibility as part of its VERDICT\n")

    report = {}
    print(f"  {'commit':<9}{'msg-bits':>9}{'msg-expr':>9}{'diff-bits':>10}"
          f"{'diff-expr':>10}   files")
    for c in MECHANICAL:
        msg = git("log", "-1", "--format=%B", c)
        diff = git("show", "--unified=0", "--format=", c)
        nfiles = len([ln for ln in git("show", "--stat", "--format=", c).splitlines()
                      if "|" in ln])
        rec = {
            "subject": git("log", "-1", "--format=%s", c).strip(),
            "msg_bits": context(msg, BITS),
            "msg_express": context(msg, EXPRESS),
            "diff_bits": context(diff, BITS)[:12],
            "diff_express": context(diff, EXPRESS)[:12],
            "files_touched": nfiles,
        }
        report[c] = rec
        print(f"  {c:<9}{len(rec['msg_bits']):>9}{len(rec['msg_express']):>9}"
              f"{len(rec['diff_bits']):>10}{len(rec['diff_express']):>10}"
              f"   {nfiles}")

    hits = {c: r for c, r in report.items()
            if r["msg_bits"] or r["msg_express"]
            or r["diff_bits"] or r["diff_express"]}
    print(f"\n  {len(hits)} of {len(MECHANICAL)} commits contain at least one "
          f"marker and require adjudication.")
    print("  A marker is NOT a falsification: mentioning bits is not the same")
    print("  as deciding by bits. Each is adjudicated below against T1/T2.\n")

    for c, r in hits.items():
        print("-" * 78)
        print(f"{c}  {r['subject']}")
        for label, key in (("T1 bits (message)", "msg_bits"),
                           ("T2 express (message)", "msg_express"),
                           ("T1 bits (diff)", "diff_bits"),
                           ("T2 express (diff)", "diff_express")):
            for line in r[key]:
                print(f"    [{label}] {line}")

    (HERE / "falsification_evidence.json").write_text(json.dumps(report, indent=1))
    print("-" * 78)
    print(f"\nevidence written: {HERE / 'falsification_evidence.json'}")
    print("Adjudication is recorded in FALSIFICATION.md — it is a judgement and")
    print("belongs in prose with its reasons, not in a script's exit code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
