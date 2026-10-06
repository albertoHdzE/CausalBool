"""gap-ranking-v1-r1 -- declared import route (U3) and the outcome read-guard.

The route is three explicit PYTHONPATH entries, in order: the active
index-deconvolution/src, the adopted abstraction-validation-v1-r1-source-r2 and the
isolated seqdecon copy delivered under ../dependency/isolated/src.  Nothing is
installed and no .pth file is touched.  ``assert_route`` refuses a shadow import.

``install_outcome_guard`` is a run-local process guard: once installed, any attempt to
open or list a path inside the repository that is not on a short allowlist raises
PermissionError.  The score/rank process installs it before importing study code, so
it cannot read results_d, summaries, reports or FULL labels.
"""
from __future__ import annotations

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN_DIR = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(RUN_DIR, *[".."] * 4))
ID = os.path.join(REPO, "index-deconvolution")
SRC = os.path.join(ID, "src")
SOURCE_R2 = os.path.join(
    ID, "results", "causal_abstraction_validation", "abstraction-validation-v1-r1-source-r2")
SEQDECON_SRC = os.path.join(RUN_DIR, "dependency", "isolated", "src")
EGFR = os.path.join(ID, "results", "screen_identification", "corpus", "bio", "egfr_signaling.bnet")
OUTCOME_TREE = os.path.join(
    ID, "results", "causal_abstraction_validation", "abstraction-validation-v1-r1")

#: module -> declared source file (repository-relative or run-relative)
EXPECTED = {
    "deconvolution": os.path.join(SRC, "deconvolution.py"),
    "causalbool": os.path.join(SRC, "causalbool.py"),
    "ca_deconvolution": os.path.join(SRC, "ca_deconvolution.py"),
    "bnet": os.path.join(SRC, "bnet.py"),
    "reprogramming": os.path.join(SRC, "reprogramming.py"),
    "study": os.path.join(SOURCE_R2, "study.py"),
    "seqdecon": os.path.join(SEQDECON_SRC, "seqdecon", "__init__.py"),
    "seqdecon.operators": os.path.join(SEQDECON_SRC, "seqdecon", "operators.py"),
}

#: adopted identities of the active core (adoption.json) and the declared isolated copy
EXPECTED_SHA = {
    "deconvolution": "bd549796361abd1072ea6dbe5d050c8ae4d3f8552b1ecb5fda1a524e38b41a3a",
    "causalbool": "856cd0f29549f49685de43cc8bfe0796f96ca91457d649d97275b74fdafb1100",
    "ca_deconvolution": "cc6428ea96e4781a30f2b1bdda0f946ccfc86cfc7a4d2e149055c8183637b7cc",
    "bnet": "ced727588a86ac1bd54636662f182bdc18232d977253b29a7413e9976f0a2f4d",
    "reprogramming": "6d1af2597b5a1533151998b68e38dae7cda4b05eec905c80e44c2ba5b7cf5681",
    "study": "9ab57cb8a9ea0507c9f3a7f4af79703a4edab4561492b63d97fc3ffb40a192bb",
    "seqdecon": "0dbf97bcd3722c482703b9fb32d7f3203eef18aa8339b5fd9c275f33afabc809",
}
ROUTE = [SRC, SOURCE_R2, SEQDECON_SRC]
with open(os.path.join(RUN_DIR, "dependency", "ticket_closure.json")) as _fh:
    EXPECTED_SHA["seqdecon.operators"] = __import__("json").load(_fh)["operators_py_sha256"]["new"]


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def assert_route() -> dict:
    """Import every declared module, check its resolved file and hash, refuse shadows."""
    head = [os.path.abspath(p) for p in sys.path[1:1 + len(ROUTE)]]
    if head != ROUTE:
        raise RuntimeError(f"PYTHONPATH route mismatch: {head} != {ROUTE}")
    import importlib
    out = {}
    for name, path in EXPECTED.items():
        mod = importlib.import_module(name)
        got = os.path.abspath(mod.__file__)
        if got != path:
            raise RuntimeError(f"shadow import: {name} resolved to {got}, declared {path}")
        h = sha256(got)
        if name in EXPECTED_SHA and h != EXPECTED_SHA[name]:
            raise RuntimeError(f"identity mismatch: {name} {h}")
        out[name] = {"file": os.path.relpath(got, REPO), "sha256": h}
    # every other repository module loaded must be one of the declared ones
    # (the venv's .pth injects sibling repositories into sys.path after PYTHONPATH)
    projects = os.path.dirname(REPO) + os.sep
    venv = os.path.join(REPO, "venv") + os.sep
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        p = os.path.abspath(f)
        if p.startswith(projects) and not p.startswith(venv) and name not in EXPECTED \
                and not p.startswith(HERE + os.sep):
            raise RuntimeError(f"undeclared repository module {name} at {f}")
    return out


def install_outcome_guard(writable: str, extra_readable: tuple[str, ...] = ()) -> None:
    """Refuse any read or listing inside the repository outside the allowlist."""
    allowed = tuple(os.path.abspath(p) for p in (
        SRC, SOURCE_R2, SEQDECON_SRC, HERE, EGFR, writable, *extra_readable))
    outcome = OUTCOME_TREE + os.sep

    def ok(path) -> bool:
        if not isinstance(path, (str, bytes, os.PathLike)):
            return True                      # file descriptors
        p = os.path.abspath(os.fsdecode(path))
        if p.startswith(outcome):
            return False
        if not p.startswith(REPO + os.sep):
            return True                      # interpreter, stdlib, venv outside repo
        if p.startswith(os.path.join(REPO, "venv") + os.sep):
            return True
        return any(p == a or p.startswith(a + os.sep) for a in allowed)

    def hook(event, args):
        if event in ("open", "os.listdir", "os.scandir") and args and not ok(args[0]):
            raise PermissionError(f"outcome guard: {event} {args[0]!r} refused")
        if event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"):
            raise PermissionError(f"outcome guard: {event} refused")

    sys.addaudithook(hook)
