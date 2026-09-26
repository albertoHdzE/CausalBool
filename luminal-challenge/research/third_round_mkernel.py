"""Stage M2 of the third round: kernel replay rows (30 programs x 3 reps x 2 versions).

Each row is one fresh process. It loads one frozen M0 workload (its sha256 is
checked against ``WORKLOAD_MANIFEST.json``), prepares the exact inputs OUTSIDE
the timed region, then times ONE cold replay of the captured events through
either R0's own methods (``baseline_kernel``) or the nominated shared-state
kernel (``shared_state_kernel``). After timing, an untimed second replay with
fresh certificate statistics checks parity against the capture: every output
digest, every per-call emission count and the whole certificate stream.

The shared row also measures the integration upper estimate named in
``MECHANISM_SPEC.json``: one attribute read through one extra Python call per
event, on the same event list.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

from research import efficiency_search as es
from research import optimization_common as oc
from research import third_round_common as tc
from research import third_round_kernel as tk
from research import third_round_workload as tw

STAGE = "M_kernel"
MODE = "kernel"


class _Holder:
    __slots__ = ("D",)

    def __init__(self, D) -> None:
        self.D = D


def _adapter(holder):
    return holder.D


def integration_estimate(prepared: dict) -> float:
    holder = _Holder({})
    started = time.perf_counter()
    for _ in prepared["events"]:
        _adapter(holder)
    return time.perf_counter() - started


def worker(spec: dict) -> dict:
    path = Path(spec["workload_path"])
    raw = gzip.decompress(path.read_bytes())
    digest = oc.sha256_bytes(raw)
    if digest != spec["workload_sha256"]:
        raise RuntimeError("workload differs from the frozen manifest")
    prepared = tw.prepare(json.loads(raw))
    version = spec["arm_id"]
    replay = {"baseline_kernel": tw.replay_baseline,
              "shared_state_kernel": tk.replay_shared}[version]
    stats = es.PropagationStats()
    started = time.perf_counter()
    replay(prepared, stats, record=False)
    seconds = time.perf_counter() - started
    extra = integration_estimate(prepared) if version == "shared_state_kernel" else 0.0
    check_stats = es.PropagationStats()
    check = tw.compare_to_capture(prepared, replay(prepared, check_stats, record=True),
                                  check_stats)
    return {"family": tc.family_of(spec["seed"]), "replay_seconds": seconds,
            "integration_estimate_seconds": extra, "events": len(prepared["events"]),
            "timed_certificates": stats.stream_length, "parity": check}


def specs(run: Path) -> list:
    manifest = json.loads((Path(run) / "WORKLOAD_MANIFEST.json").read_text())
    out = []
    for seed_text, item in sorted(manifest["workloads"].items()):
        for rep in range(tc.KERNEL_REPS):
            for version in tc.KERNEL_VERSIONS:
                out.append({"stage_id": STAGE, "program_sha256": item["program_sha256"],
                            "seed": int(seed_text), "repetition": rep, "arm_id": version,
                            "mode_key": MODE, "workload_path": item["path"],
                            "workload_sha256": item["sha256"]})
    return sorted(out, key=lambda s: (tc.stable_seed([tc.SEED_ARM_ORDER, s["stage_id"],
                                                      s["program_sha256"], s["repetition"],
                                                      s["arm_id"], s["mode_key"]]),
                                      s["arm_id"], s["mode_key"]))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec")
    parser.add_argument("--run")
    args = parser.parse_args(argv)
    if args.spec:
        sys.stdout.write(json.dumps(worker(json.loads(args.spec)), sort_keys=True) + "\n")
        return 0
    all_specs = specs(Path(args.run))
    if len(all_specs) != tc.EXPECTED_ROWS[STAGE]:
        raise RuntimeError(f"{len(all_specs)} specs, expected {tc.EXPECTED_ROWS[STAGE]}")
    report = tc.run_stage(Path(args.run), STAGE, all_specs, "research.third_round_mkernel")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
