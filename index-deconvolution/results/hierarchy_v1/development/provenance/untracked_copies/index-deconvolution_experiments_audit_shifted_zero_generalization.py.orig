"""Reproduce the scientific-review checks for notebook 15; no new estimator.

Run from any directory. Scores delegate to the repository's declared owner.
The output records exploratory audit measurements, not a generalisation benchmark.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import random
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
sys.path.insert(0, str(REPO / "src"))
from description_lengths import PYBDM_PIN, bdm_1d


def score(s: str, b: int) -> dict:
    counts = Counter(s[i:i + b] for i in range(0, len(s) - b + 1, b))
    return {
        "block": b,
        "bdm": bdm_1d(s, block=b, remainder="drop"),
        "scored_bits": len(s) - len(s) % b,
        "dropped_bits": len(s) % b,
        "block_count": sum(counts.values()),
        "distinct_blocks": len(counts),
        "repeated_blocks": {k: v for k, v in sorted(counts.items()) if v > 1},
    }


def run() -> dict:
    shifted = ["1" * i + "0" + "1" * (7 - i) for i in range(8)]
    a64 = "".join(shifted)
    a72 = "1" * 8 + a64
    rng = random.Random(72)
    control = "".join(rng.choice("01") for _ in range(72))
    # These deliberately have distinct names: bitacora 32 reuses A for two objects.
    cases = ["1" * 8] + shifted
    cat = lambda indices: "".join(cases[j - 1] for j in indices)
    a24 = cat([1, 2, 3])
    ax64 = cat(range(1, 9))
    axm64 = cat([8, 1, 6, 7, 2, 4, 3, 5])
    patterns = {
        "A24_scratch": a24, "AX64": ax64, "AXM64": axm64,
        "P1": a24 * 2, "P2": a24 + ax64 + axm64, "P3": axm64 * 3,
    }
    scans = {}
    for name, s in {"A72_period9": a72, "R72_seed72": control}.items():
        rows = [score(s, b) for b in range(1, 13)]
        scans[name] = {
            "bits": s, "scores": rows,
            "argmin_1_to_12": min(rows, key=lambda r: r["bdm"])["block"],
            "argmin_2_to_12": min(rows[1:], key=lambda r: r["bdm"])["block"],
        }
    pattern_rows = {
        name: {"bits": s, "length": len(s), "scores": [score(s, b) for b in (8, 9, 12)]}
        for name, s in patterns.items()
    }
    zero_positions = [i for i, bit in enumerate(a64) if bit == "0"]
    # Exhaust all ordinary six-coordinate 0/1/* schemata implicitly: any
    # non-singleton cube contains an edge, so the absence of edges excludes it.
    zero_set = set(zero_positions)
    edges = [(x, x ^ (1 << j)) for x in zero_set for j in range(6)
             if x < (x ^ (1 << j)) and (x ^ (1 << j)) in zero_set]
    source = "('0'+'1'*8)*7+'0'"
    assert eval(source, {"__builtins__": {}}) == a64
    assert a72 == ("1" * 8 + "0") * 8
    assert zero_positions == list(range(0, 64, 9))
    assert not edges
    assert scans["A72_period9"]["argmin_2_to_12"] == 3
    assert pattern_rows["P3"]["scores"][2]["distinct_blocks"] == 15
    tracked_inputs = [
        Path(__file__), REPO / "src/description_lengths.py",
        PROJECT / "bitacora/32_shifted_zero_bdm_probe.md",
        PROJECT / "notebooks/15_shifted_zero_bdm_probe.ipynb",
        PROJECT / "notebooks/build_15.py",
    ]
    return {
        "status": "exploratory audit; not a generalisation benchmark",
        "provenance": {
            "python": platform.python_version(), "pybdm_pin": PYBDM_PIN,
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "working_tree_note": "Inputs include uncommitted work; hashes identify reviewed content.",
            "sha256": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in tracked_inputs},
        },
        "block_scans": scans,
        "patterns_of_patterns": pattern_rows,
        "source_length": {"expression": source, "characters": len(source),
                          "utf8_payload_bits": 8 * len(source.encode("utf-8")),
                          "target_bits": len(a64), "framing_included": False},
        "schema_bridge": {
            "zero_positions_A64": zero_positions,
            "six_bit_addresses": [f"{x:06b}" for x in zero_positions],
            "hamming_one_edges": edges,
            "consequence": "In the original six address coordinates, every all-zero-support cube is a singleton.",
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=PROJECT / "results/shifted_zero_generalization_audit.json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    if not args.quiet:
        print(f"Wrote {args.output}")
        print("A72: raw BDM minimum over 2..12 selects block 3, not period 9.")
        print("P3: block 12 has 16 blocks, 15 distinct; one block repeats twice.")
        print("A64: period expression has 136 UTF-8 payload bits; target has 64 bits.")
        print("A64 zero support: no Hamming-one neighbours in its six-bit addresses.")
