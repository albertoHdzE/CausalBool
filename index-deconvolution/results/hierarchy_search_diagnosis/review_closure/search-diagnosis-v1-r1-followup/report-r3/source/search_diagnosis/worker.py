"""Isolated diagnostic worker: ``python -S worker.py KIND OUT_PATH PARAMS_JSON`` < bits.

Runs under the existing watchdog contract: the parent (``runner.DiagJob``, a subclass
of ``hierarchy.benchmark._Job``) kills it after the wall limit, and the existing
``hierarchy.benchmark._rss_watch`` thread exits with ``RSS_EXIT`` above the RSS limit.
The result (info plus hex archives) is written atomically to OUT_PATH.

KIND is one of ``B0``/``B8`` (input-only: PARAMS_JSON must be ``{}``),
``D3`` (truth-assisted: ``{"cuts": [...]}``) and ``D4`` (``{"period": path,
"pair_grammar": path}`` naming the saved baseline archives).
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

if __name__ == "__main__":                      # script mode: make the package importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hierarchy.benchmark import RSS_LIMIT_BYTES, _rss_watch, atomic_write  # noqa: E402

from search_diagnosis import kernels as K  # noqa: E402


def run(kind: str, bits: str, params: dict) -> tuple[dict, dict]:
    if kind in K.CONFIGS:
        if params:
            raise ValueError("boundary-only jobs receive no parameters besides the config")
        return K.boundary(bits, kind)
    if kind == "D3":
        return K.supplied_subsets(bits, params["cuts"])
    if kind == "D4":
        return K.translate(bits, Path(params["period"]).read_bytes(),
                           Path(params["pair_grammar"]).read_bytes())
    raise ValueError(f"unknown job kind {kind!r}")


def main(argv: list[str]) -> int:
    kind, out_path, params = argv[0], argv[1], json.loads(argv[2])
    rss = int(argv[3]) if len(argv) > 3 else RSS_LIMIT_BYTES
    threading.Thread(target=_rss_watch, args=(rss,), daemon=True).start()
    bits = sys.stdin.read()
    t0 = time.perf_counter_ns()
    info, archives = run(kind, bits, params)
    wall = time.perf_counter_ns() - t0
    atomic_write(Path(out_path), json.dumps(
        {"kind": kind, "info": info, "compute_wall_ns": wall,
         "archives": {k: v.hex() for k, v in archives.items()}}, sort_keys=True).encode())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
