#!/usr/bin/env python3
"""AUDIT01/T5.1 - `make verify-paper` engine.

Reads papers/method/artifact_baseline/artefacts.json. For every COVERED
artefact: runs its producer command, loads the produced JSON, and checks the
marker-delimited block in the .tex against the declared expectations
(values present, value counts, disclosure strings, metric invariants).
Exits non-zero listing mismatched ARTEFACT IDs (never silent, never counts
alone: each failure names the missing/incorrect value).

Volatile fields (wall-clock times) are excluded by policy, mirroring
tests/MUnit/BASELINE.md.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "papers/method/artifact_baseline/artefacts.json"


def block_text(tex_file: Path, block_id: str) -> str:
    text = tex_file.read_text()
    m = re.search(
        rf"%% ARTEFACT-BEGIN {re.escape(block_id)}.*?%% ARTEFACT-END {re.escape(block_id)}",
        text, re.S)
    if not m:
        raise AssertionError(f"markers for {block_id} not found in {tex_file}")
    return m.group(0)


def run_producer(cmd: str) -> None:
    subprocess.run(cmd, shell=True, cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check(art: dict) -> list[str]:
    errs: list[str] = []
    tex = ROOT / art["tex_file"]
    run_producer(art["producer_cmd"])
    produced = json.loads((ROOT / art["produced_json"]).read_text())
    blob = block_text(tex, art["block"])
    checks = art.get("checks", {})

    for val in checks.get("values_present", []):
        if val not in blob:
            errs.append(f"{art['id']}: expected value '{val}' absent from .tex block")
    for val, want in checks.get("value_count", {}).items():
        got = len(re.findall(rf"(?<![\d.]){re.escape(val)}(?![\d])", blob))
        if got != want:
            errs.append(f"{art['id']}: value '{val}' occurs {got}x, expected {want}")
    for s in checks.get("disclosure_present", []):
        if s not in blob:
            errs.append(f"{art['id']}: required disclosure string '{s}' absent")

    # AUDIT03/R2b — this block was DEAD, in two independent ways, and neither
    # was visible from its output.
    #
    #  1. It read checks["json_expect"], but every inventory entry carries
    #     json_expect as a SIBLING of checks, not inside it. The condition was
    #     therefore never true and no JSON value was ever compared: the gate
    #     checked only that certain strings appear in the .tex.
    #  2. Had it run, it would have raised. The resolver walked
    #     path.split("_"), so "D_formula_bits_round2" asked for produced["D"]
    #     and raised KeyError, which main() catches and reports as FAIL.
    #
    # Both are fixed here: the inventory is read from either location, and a
    # "_round2" suffix is stripped to recover the flat key rather than split on
    # every underscore. A missing key is now an ERROR, not a silent pass --
    # otherwise a typo in the inventory would disable the check it declares.
    expectations = {**checks.get("json_expect", {}), **art.get("json_expect", {})}
    for path, want in expectations.items():
        key = path[:-len("_round2")] if path.endswith("_round2") else path
        if key not in produced:
            errs.append(f"{art['id']}: json key '{key}' absent from "
                        f"{art['produced_json']} (declared as '{path}')")
            continue
        got = round(produced[key], 2) if path.endswith("_round2") else produced[key]
        if abs(got - want) > 1e-9:
            errs.append(f"{art['id']}: json {path}={got} != expected {want}")

    # AUDIT02/W0.5: json_expect resolves only flat top-level keys, so it cannot
    # reach a value inside a list of case records. json_paths is additive -- it
    # leaves json_expect and every existing entry untouched -- and supports
    # dotted paths with [i] indices and [Name=X] record selection, so a table
    # cell can be tied to the exact JSON field it was transcribed from.
    for path, want in checks.get("json_paths", {}).items():
        try:
            node = produced
            for part in path.split("."):
                while part.endswith("]"):
                    part, _, sel = part[:-1].partition("[")
                    if part:
                        node = node[part]
                        part = ""
                    if "=" in sel:
                        k, _, v = sel.partition("=")
                        hits = [r for r in node if str(r.get(k)) == v]
                        if len(hits) != 1:
                            raise KeyError(f"{sel} matched {len(hits)} records")
                        node = hits[0]
                    else:
                        node = node[int(sel)]
                if part:
                    node = node[part]
            got = node
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{art['id']}: json path '{path}' unresolvable: {exc}")
            continue
        if isinstance(want, (int, float)) and isinstance(got, (int, float)):
            if abs(got - want) > 1e-9:
                errs.append(f"{art['id']}: json {path}={got} != expected {want}")
        elif got != want:
            errs.append(f"{art['id']}: json {path}={got!r} != expected {want!r}")

    if checks.get("metrics_all_zero_mismatches"):
        runs = produced if isinstance(produced, list) else produced.get("runs", [])
        for r in runs:
            if r["nodeAuditMismatches"] != 0 or r["networkMismatchCells"] != 0:
                errs.append(f"{art['id']}: n={r['n']} seed={r['seed']} has "
                            f"nodeMM={r['nodeAuditMismatches']} netMM={r['networkMismatchCells']}")
    if "sampled_rows_per_run" in checks:
        rows = checks["sampled_rows_per_run"]
        runs = produced if isinstance(produced, list) else produced.get("runs", [])
        for r in runs:
            if r["sampledRows"] != rows:
                errs.append(f"{art['id']}: sampledRows {r['sampledRows']} != {rows}")
    return errs


def main() -> int:
    inv = json.loads(INVENTORY.read_text())
    failures: list[str] = []
    for art in inv["covered"]:
        try:
            failures.extend(check(art))
            print(f"PASS {art['id']}")
        except Exception as exc:  # noqa: BLE001 - report, then exit non-zero
            failures.append(f"{art['id']}: {type(exc).__name__}: {exc}")
            print(f"FAIL {art['id']}")
    for p in inv["pending"]:
        if not p.get("reason"):
            failures.append(f"PENDING entry without reason: {p}")
    if failures:
        print("\nVERIFY-PAPER FAILED — mismatched artefact IDs / errors:")
        for f in failures:
            print(" -", f)
        return 1
    print(f"\nVERIFY-PAPER OK ({len(inv['covered'])} covered, "
          f"{len(inv['pending'])} pending with reasons)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
