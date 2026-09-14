"""io -- JSONL writer and reader, with sha256 self-validation.

Lines are terminated by '\n'. Empty lines are not emitted and are
rejected on read.
"""
from __future__ import annotations

import json
import math
import tempfile
import os
from pathlib import Path
from typing import Any, Iterable, Iterator

from .records import compute_sha256, legacy_canonical_bytes


def ensure_dir(path: os.PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_jsonl(path: os.PathLike, records: Iterable[dict[str, Any]], *, append: bool = False) -> int:
    """Write records in order; use ``append=True`` for durable append-only logs.

    Returns the number of records written.
    """
    p = Path(path)
    ensure_dir(p.parent)
    n = 0
    with p.open("a" if append else "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(_json_safe(r), sort_keys=True, separators=(",", ":"), allow_nan=False))
            f.write("\n")
            n += 1
        f.flush()
        os.fsync(f.fileno())
    return n


def read_jsonl(path: os.PathLike) -> Iterator[dict[str, Any]]:
    """Yield records; verify sha256 on the fly.

    Raises ``ValueError`` with the line number and the failing record's
    declared sha256 if a line is malformed or the digest does not match.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.rstrip("\r\n")
            if not line:
                raise ValueError(f"line {i}: empty JSONL record")
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"line {i}: invalid JSON: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"line {i}: top-level is not a JSON object")
            declared = obj.get("sha256")
            actual = compute_sha256(obj)
            legacy = __import__("hashlib").sha256(legacy_canonical_bytes(obj)).hexdigest()
            if declared not in {actual, legacy}:
                raise ValueError(
                    f"line {i}: sha256 mismatch: declared={declared!r} actual={actual!r}"
                )
            yield obj


def write_json(path: os.PathLike, record: dict[str, Any]) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    with p.open("w", encoding="utf-8") as f:
        json.dump(_json_safe(record), f, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")


def read_json(path: os.PathLike) -> dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"{p}: top-level is not a JSON object")
    declared = obj.get("sha256")
    actual = compute_sha256(obj)
    legacy = __import__("hashlib").sha256(legacy_canonical_bytes(obj)).hexdigest()
    if declared not in {actual, legacy}:
        raise ValueError(
            f"{p}: sha256 mismatch: declared={declared!r} actual={actual!r}"
        )
    return obj


def _json_safe(value: Any) -> Any:
    """Convert non-finite diagnostics to nullable JSON values."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def atomic_write_json(path: os.PathLike, record: dict[str, Any]) -> None:
    """Write one JSON checkpoint via same-directory replace."""
    target = Path(path)
    ensure_dir(target.parent)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(_json_safe(record), handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
