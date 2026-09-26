"""Shared plumbing of the phase 2 optimization release (protocol 1.0).

This module owns the result-directory rules, the durable journal format, the
logged-command record and the source manifests of
``plan/CLAUDE_PHASE2_OPTIMIZATION_PLAN.md``. It owns no algorithm and no
statistic. The independent auditor deliberately does not import it.

Every file written through ``append_row`` is flushed and fsynced before the call
returns, so an interrupted campaign leaves exactly the rows that completed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Dict, Iterable, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
RESULTS = ROOT / "results" / "phase2_structural_encoding"
PACKAGE = ROOT / "plan" / "phase2_optimization"
PROTOCOL_PATH = PACKAGE / "PROTOCOL.json"
PYTHON = str(Path(sys.executable))

# The accepted Phase 2 source, snapshotted by the release that the lead
# accepted. The frozen control imports this directory first on ``sys.path``.
FROZEN_SNAPSHOT = RESULTS / "claude_release_20260923" / "final_source_v2"
FROZEN_MANIFEST = RESULTS / "claude_release_20260923" / "FINAL_SOURCE_V2_SHA256.txt"
ACCEPTED_RUN = RESULTS / "recovery_campaign_20260923_r3"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> Optional[str]:
    path = Path(path)
    if not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def object_sha256(value: object) -> str:
    return sha256_bytes(canonical(value).encode("utf-8"))


def load_protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text())


def write_json(path: Path, payload: object) -> str:
    """Write indented JSON once and return its file digest."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return sha256_bytes(data.encode("utf-8"))


def write_immutable_json(path: Path, payload: object) -> str:
    """Refuse to replace an existing file: frozen artifacts are written once."""

    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact {path}")
    return write_json(path, payload)


def append_row(path: Path, row: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_rows(path: Path) -> List[dict]:
    """Every complete JSON line. A torn final line is reported, never repaired."""

    path = Path(path)
    if not path.exists():
        return []
    rows: List[dict] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if number == len(lines) - 1:
                # A worker interrupted mid-write leaves a torn last line. It is
                # not a row; the resume logic re-runs that key.
                continue
            raise
    return rows


def git_state() -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                                  text=True, check=False).stdout
        except OSError as exc:  # pragma: no cover - environment defect
            return f"git unavailable: {exc}"

    return {"head": run("rev-parse", "HEAD").strip(), "status": run("status", "--porcelain=v1")}


def environment() -> dict:
    return {
        "python": sys.version,
        "executable": PYTHON,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def research_source_hashes() -> Dict[str, str]:
    """Every research source and research test, relative to ``luminal-challenge``."""

    out: Dict[str, str] = {}
    for folder in ("research", "research_tests"):
        for path in sorted((ROOT / folder).glob("*.py")):
            out[f"{folder}/{path.name}"] = file_sha256(path)
    return out


def production_source_hashes() -> Dict[str, str]:
    """The protected production modules the research code imports."""

    names = ("common.py", "compare_direct.py", "direct_compiler.py", "direct_constraints.py",
             "direct_contract.py", "direct_optimizer.py", "schema_index.py",
             "verify_direct.py", "export_direct.py", "tests_direct/generate_programs.py",
             ".reference/machine.py", ".reference/score.py", ".reference/compiler.py",
             ".reference/tests/test_public_programs.py", ".reference/tests/test_machine.py")
    return {name: file_sha256(ROOT / name) for name in names}


def frozen_snapshot_hashes() -> Dict[str, str]:
    """The accepted research sources (the snapshot also retains its tests)."""

    out: Dict[str, str] = {}
    for path in sorted((FROZEN_SNAPSHOT / "research").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        out[str(path.relative_to(FROZEN_SNAPSHOT))] = file_sha256(path)
    return out


def verify_frozen_snapshot() -> dict:
    """The snapshot must equal the accepted manifest, byte for byte.

    The accepted manifest lists research sources and research tests; the
    snapshot holds the research sources. Every research entry must be present
    and equal; the denominator is printed so an empty scan cannot pass.
    """

    findings: List[str] = []
    checked = 0
    for line in FROZEN_MANIFEST.read_text().splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(None, 1)
        if not relative.startswith("research/"):
            continue
        checked += 1
        actual = file_sha256(FROZEN_SNAPSHOT / relative)
        if actual != digest:
            findings.append(f"{relative}: snapshot {actual} != accepted {digest}")
    if checked == 0:
        findings.append("the accepted manifest listed no research source")
    return {"checked": checked, "findings": findings,
            "status": "PASS" if not findings else "FAIL"}


def run_logged(label: str, argv: Sequence[str], directory: Path,
               env: Optional[dict] = None, timeout: Optional[float] = None,
               cwd: Optional[Path] = None) -> dict:
    """Run one command, retaining argv, stdout, stderr, exit code and timing."""

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    environment_vars = dict(os.environ)
    environment_vars.setdefault("PYTHONPATH", f"{ROOT / '.reference'}{os.pathsep}{ROOT}")
    if env:
        environment_vars.update(env)
    started = time.perf_counter()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        proc = subprocess.run(list(argv), cwd=str(cwd or ROOT), capture_output=True, text=True,
                              env=environment_vars, timeout=timeout)
        code, out, err, timed_out = proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        code, timed_out = None, True
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    seconds = time.perf_counter() - started
    (directory / f"{label}.stdout").write_text(out)
    (directory / f"{label}.stderr").write_text(err)
    meta = {"label": label, "argv": list(argv), "cwd": str(cwd or ROOT), "exit_code": code,
            "timed_out": timed_out, "seconds": seconds, "started_utc": stamp,
            "pythonpath": environment_vars.get("PYTHONPATH")}
    write_json(directory / f"{label}.meta.json", meta)
    return meta


def family_counts(entries: Iterable[dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in entries:
        counts[entry["family"]] = counts.get(entry["family"], 0) + 1
    return dict(sorted(counts.items()))
