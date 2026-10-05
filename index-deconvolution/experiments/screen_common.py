"""screen_common.py

Shared glue for the identification screen (PROTOCOL_screen_identification.md).

This module OWNS NO PART OF THE METHOD.  Monolithic-code answers, recorded once:

  Q1 owners.  deconvolve / verify_forward / verify_forward_symbolic /
      network_roots / minimal_dnf -> src/deconvolution.py; random_network ->
      src/network_generator.py; num_attractors -> src/reprogramming.py;
      exact_query_representation -> papers/method/code/scalability_resource_envelope/;
      parse_bnet / network_to_bnet -> src/bnet.py; rule evaluation for the
      functional syntax of data/bio/processed -> src/integration/LogicParser.py.
  Q2 searched by body fragment (bnet writers, processed-JSON loaders, query
      engines, reachability): none other exists.  The bnet writer was missing and
      was added to its owner (src/bnet.py), not here.
  Q3 what is here is format conversion between our Network and each tool's
      input (a .bnet file, a dict for the query engine), subprocess plumbing for
      R, and timing.  None of it answers a question or recovers a model.
  Q4 the S3a script checks the dict adapter against causalbool.step with a
      printed denominator; the corpus script checks every tool's forward map
      against causalbool.step, and parse_bnet(network_to_bnet(net)) against net
      by canonical diagram identity.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDX = HERE.parent
ROOT = IDX.parent
for p in (ROOT / "papers/method/code/scalability_resource_envelope", IDX / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

RES = IDX / "results" / "screen_identification"
CORPUS = RES / "corpus"
RSCRIPT = "/usr/local/bin/Rscript"
QUIET = "--quiet" in sys.argv

from causalbool import Network  # noqa: E402


def log(*a) -> None:
    if not QUIET:
        print(*a, flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def network_to_json(net: Network) -> dict:
    return {"n": net.n, "C": net.C, "gates": net.gates, "params": net.params}


def network_from_json(d: dict) -> Network:
    return Network(n=d["n"], C=d["C"], gates=d["gates"], params=d["params"])


def canonical_names(n: int) -> list[str]:
    """Node names every tool accepts (NuSMV needs >= 2 characters, R identifiers)."""
    return [f"v{i:03d}" for i in range(n)]


def load_manifest() -> dict:
    return json.loads((CORPUS / "manifest.json").read_text())


def load_entry(entry: dict) -> Network:
    return network_from_json(json.loads((CORPUS / entry["network_json"]).read_text()))


def to_query_network(net: Network) -> dict:
    """Our Network -> the dict consumed by exact_query_representation (1-based)."""
    return {
        "n": net.n,
        "inputs_by_node": [[i + 1 for i in net.connected_inputs(k)] for k in range(net.n)],
        "gates": list(net.gates),
        "params_by_node": [dict(p) for p in net.params],
    }


def run_r(code: str, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run([RSCRIPT, "--vanilla", "-e", code], capture_output=True,
                          text=True, timeout=timeout,
                          env={**os.environ, "R_LIBS_USER": os.path.expanduser(
                              "~/Library/R/arm64/4.6/library")})


def r_lib_prelude() -> str:
    return ('.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths())); '
            'suppressMessages(library(BoolNet)); ')


def tool_versions() -> dict:
    import importlib.metadata as md
    v = {"python": sys.version.split()[0]}
    for pkg in ("dd", "z3-solver", "pyboolnet", "clingo"):
        try:
            v[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            v[pkg] = None
    r = run_r(r_lib_prelude() + 'cat(as.character(packageVersion("BoolNet")), R.version.string, sep="|")', 120)
    v["BoolNet"], v["R"] = (r.stdout.split("|") + [None, None])[:2]
    for exe in ("/opt/homebrew/bin/gringo", "/opt/homebrew/bin/clasp"):
        try:
            v[Path(exe).name] = subprocess.run([exe, "--version"], capture_output=True,
                                               text=True).stdout.splitlines()[0]
        except Exception as exc:  # noqa: BLE001
            v[Path(exe).name] = f"unavailable: {exc}"
    return v


def median_time(fn, repeats: int = 3):
    """Median wall time of ``repeats`` calls; returns (median_s, all_s, last_result)."""
    times, out = [], None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = fn()
        times.append(time.perf_counter() - t0)
    return sorted(times)[len(times) // 2], times, out
