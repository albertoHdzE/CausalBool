"""smoke -- run the Stage 1 pipeline and print the headline summary.

Usage:
    python -m doppel_challenge.smoke [out_dir]

The default out_dir is doppel-challenge/runs/stage1/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .driver import run_stage1_two_nets


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        out_dir = Path(argv[1]).resolve()
    else:
        out_dir = (Path(__file__).resolve().parents[1] / "runs" / "stage1").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = run_stage1_two_nets(out_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
