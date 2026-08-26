#!/usr/bin/env python
"""Adjudication dossier v2 (post adversarial review F2).

v1's bare-literal matching had no reference distribution and an unconditional
x100 rescale; its "68 FOUND-IN-ARTIFACT / 0 UNRESOLVED" headline overstated
traceability. v2 adds:
  * evidence CLASSES instead of a binary found/not-found:
      STRONG   >=4 decimal digits matched in a machine artifact (.json/.csv),
               no rescale needed
      WEAK     artifact match at 1-3 dp, or only via the x100 percent rescale
      PROSE    quoted in md/ipynb/txt but no machine artifact
      UNRESOLVED
  * DECOY REFERENCE COLUMNS: 95 random decoys per precision bucket (1,2,3,>=4)
    drawn from two DECLARED domains -- D1 uniform[0,1) (probability-like stats,
    the ledger's dominant domain) and D2 uniform[0,100) (mixed magnitudes) --
    run through the identical matcher, reported next to the real counts.

REPORT-FIRST: writes results/ledger_lint_full/adjudication_dossier_v2.md.
FINDINGS.md untouched here; corrections enter via dated addendum only.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "results" / "ledger_lint_full" / "adjudication_dossier_v2.md"

SEARCH_ROOTS = ["results", "reference", "notebooks", "bitacora"]
TEXT_SUFFIXES = {".json", ".csv", ".md", ".ipynb", ".txt"}
SKIP_PARTS = {".venv", "__pycache__", ".git"}
NUMTXT = re.compile(r"-?\d+\.\d+(?:[eE][-+]?\d+)?")


def load_report_unverified() -> dict:
    txt = (ROOT / "results" / "ledger_lint_full" / "report.md").read_text()
    out = {}
    for line in txt.splitlines():
        m = re.match(r"- \*\*(C\d+)\*\*:.*?UNVERIFIED: (\[.*?\])", line)
        if m:
            out[m.group(1)] = eval(m.group(2))  # noqa: S307 - own file, fixed format
    return out


def harvest_corpus():
    items = []
    for root in SEARCH_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if any(part in SKIP_PARTS for part in p.parts):
                continue
            if "ledger_lint_full" in p.parts:  # never harvest our own reports
                continue
            if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
                try:
                    items.append((str(p.relative_to(ROOT)), p.read_text(errors="replace")))
                except OSError:
                    pass
    return items


def round_match(token: str, val_txt: str, allow_rescale: bool):
    try:
        v = float(val_txt)
    except ValueError:
        return False
    nd = len(token.split(".")[1])
    t = float(token)
    if round(v, nd) == round(t, nd):
        return True
    return allow_rescale and round(v * 100, nd) == round(t, nd)


def classify_token(token: str, corpus):
    nd = len(token.split(".")[1])
    t = float(token)
    best = "UNRESOLVED"
    hit_artifact_weak = hit_artifact_strong = False
    prose_hit = False
    where = ""
    for rel, text in corpus:
        is_machine = rel.lower().endswith((".json", ".csv"))
        if rel.endswith("FINDINGS.md") and not is_machine:
            continue
        for nv in NUMTXT.findall(text):
            # STRONG demands the CLAIM itself be sharp (token >=4dp); artifact
            # side precision cannot rescue a coarse claim (decoys prove it).
            strong = is_machine and nd >= 4 and round_match(token, nv, False)
            weak = is_machine and not strong and round_match(token, nv, True)
            if strong:
                hit_artifact_strong = True
                where = f"{rel} (`{nv}`)"
                break
            if weak:
                hit_artifact_weak = True
                where = where or f"{rel} (`{nv}`)"
        if hit_artifact_strong:
            break
    if not hit_artifact_strong:
        for rel, text in corpus:
            if rel.lower().endswith((".json", ".csv")) or rel.endswith("FINDINGS.md"):
                continue
            for nv in NUMTXT.findall(text):
                if round_match(token, nv, True):
                    prose_hit = True
                    where = f"{rel} (`{nv}`)"
                    break
            if prose_hit:
                break
    if hit_artifact_strong:
        best = "STRONG"
    elif hit_artifact_weak:
        best = "WEAK"
    elif prose_hit:
        best = "PROSE"
    return best, where


def decoy_rates(corpus, per_bucket=95, seed=20260825):
    """Reference distribution: P(random decoy classified STRONG/WEAK) by
    precision bucket under two declared domains."""
    rng = random.Random(seed)
    out = {}
    for domain, lo, hi in (("D1[0,1)", 0.0, 1.0), ("D2[0,100)", 0.0, 100.0)):
        rows = {}
        for label, nd in (("1dp", 1), ("2dp", 2), ("3dp", 3), (">=4dp", 6)):
            s = w = 0
            for _ in range(per_bucket):
                tok = f"{rng.uniform(lo, hi):.{nd}f}"
                cls, _ = classify_token(tok, corpus)
                if cls == "STRONG":
                    s += 1
                elif cls == "WEAK":
                    w += 1
            rows[label] = (s, w)
        out[domain] = rows
    return out


def main():
    unv = load_report_unverified()
    corpus = harvest_corpus()
    print(f"rows: {len(unv)}; corpus files: {len(corpus)}")
    lines = [
        "# Adjudication dossier v2 — decoy-calibrated (supersedes v1 headline)",
        "",
        "Evidence classes: STRONG (>=4dp machine-artifact match, no rescale);",
        "WEAK (artifact match at 1-3dp or only via x100 rescale); PROSE (quoted",
        "in narrative files only); UNRESOLVED. Decoy reference distributions",
        "(95 decoys/bucket, identical matcher) printed beside real counts.",
        "'unverified' still does NOT mean 'wrong'. FINDINGS.md untouched here.",
        "",
    ]
    counts = {"STRONG": 0, "WEAK": 0, "PROSE": 0, "UNRESOLVED": 0}
    body = []
    for cid in sorted(unv, key=lambda c: int(c[1:])):
        body.append(f"## {cid}")
        for tok in unv[cid]:
            cls, where = classify_token(tok, corpus)
            counts[cls] += 1
            body.append(f"- `{tok}` → **{cls}** {('— ' + where) if where else ''}")
        body.append("")
    dec = decoy_rates(corpus)
    lines.append("## Decoy reference distributions (identical matcher)")
    lines.append("| domain | 1dp STRONG/WEAK | 2dp | 3dp | >=4dp |")
    lines.append("|---|---|---|---|---|")
    for dom, rows in dec.items():
        cells = " | ".join(f"{rows[b][0]}/95 STRONG, {rows[b][1]}/95 WEAK"
                           for b in ("1dp", "2dp", "3dp", ">=4dp"))
        lines.append(f"| {dom} | {cells} |")
    lines += ["", "## Real decimals"] + body
    lines += ["---",
              f"Headline: " + ", ".join(f"{k}={v}" for k, v in counts.items())
              + f" (total {sum(counts.values())}).",
              "Interpretation rule: only STRONG supports 'value stands on",
              "artifact' without further work; WEAK/PROSE keep the batch-rule",
              "VALUE verdicts but carry annotated-evidence status (decoy-",
              "calibrated uncertainty); nothing is retracted as wrong."]
    OUT.write_text("\n".join(lines) + "\n")
    print("counts:", counts, "->", OUT)


if __name__ == "__main__":
    main()
