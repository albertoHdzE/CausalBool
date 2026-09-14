"""records -- schema-versioned JSON records for the doppel-challenge artefacts.

The shapes are defined in doppel-challenge/doc/01-record-schema.md.
This module provides:

  * the on-disk wire shape (to_dict / from_dict) for every record kind,
  * a sha256 self-digest computed over the canonical serialisation.

The canonical serialisation is the JSON object with sorted keys, no
whitespace, and the sha256 field set to the empty string. The digest is
then stored in the sha256 field. This makes every record self-describing
and immutable.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import secrets
import time
from typing import Any

SCHEMA_VERSION = "2.0.0"
RECORD_KINDS = frozenset({
    "shared_program_benchmark",
    "configuration",
    "base_network",
    "catalogue_row",
    "loss_row",
    "kl_row",
    "support_row",
    "ncd_row",
    "joint_row",
    "sweep_aggregate",
    "figure_manifest",
    "runtime_trace",
    "exclusion",
    "diagnostic",
    "approximate_repertoire",
    "scaling_benchmark",
    "full_behaviour_scaling_benchmark",
    "whole_repertoire_scaling_benchmark",
    "scale_pilot",
    "scale_pilot_case",
    "catalogue_manifest",
})


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _ulid_like() -> str:
    """A 26-character sortable identifier: 10-char timestamp + 16-char random.

    Not a true ULID (no Crockford base32 encoding), but the timestamp prefix
    gives global sortability and the random suffix is unique within the
    timestamp window for our purposes.  The schema requires uniqueness, not
    the spec.
    """
    ts = format(int(time.time() * 1000) % (10**10), "010d")
    rnd = secrets.token_hex(8)
    return ts + rnd


def canonical_bytes(record: dict[str, Any]) -> bytes:
    """Canonical bytes for sha256 computation.

    Sets the sha256 field to the empty string, sorts keys, and emits no
    whitespace.  This is the documented schema rule; the reader retains a
    legacy verifier for exploratory v1 artefacts.
    """
    obj = dict(record)
    obj["sha256"] = ""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def legacy_canonical_bytes(record: dict[str, Any]) -> bytes:
    obj = {k: v for k, v in record.items() if k != "sha256"}
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def compute_sha256(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def scientific_digest(record: dict[str, Any]) -> str:
    """Deterministic digest of scientific content, excluding volatile metadata."""
    excluded = {"sha256", "scientific_digest", "created_at", "run_id",
                "elapsed_seconds", "runtime_seconds", "peak_memory_bytes",
                "kernel_stderr", "kernel_stdout_prefix"}
    if record.get("record_kind") == "shared_program_benchmark" or str(record.get("record_kind", "")).startswith("joint_study_"):
        excluded.update({"compile_seconds", "serialization_seconds",
                         "decode_and_reference_validation_seconds", "dynamics_seconds"})
    def stable(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: stable(item)
                for key, item in value.items()
                if key not in excluded
                and not key.endswith(("_runtime_seconds", "_memory_bytes", "_rss_bytes",
                                      "_remaining_seconds"))
            }
        if isinstance(value, list):
            return [stable(item) for item in value]
        return value

    payload = stable(record)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


def make_envelope(record_kind: str, *, config_id: str, sweep_id: str | None) -> dict[str, Any]:
    if record_kind not in RECORD_KINDS:
        raise ValueError(f"unknown record_kind: {record_kind!r}")
    env = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": record_kind,
        "config_id": config_id,
        "sweep_id": sweep_id,
        # Common scientific-contract fields.  Exact producers replace these
        # defaults with their validation/provenance values; diagnostic and
        # historical-style records still remain self-describing.
        "observable": None,
        "approximation": None,
        "estimator_parameters": {},
        "uncertainty": None,
        "process_status": "not_run",
        "accepted_validation": False,
        "provenance": None,
        "sha256": "",
        "created_at": _utc_now_iso(),
    }
    env["sha256"] = compute_sha256(env)
    return env


def seal(record: dict[str, Any]) -> dict[str, Any]:
    """Recompute sha256 over a record and store it. Returns the record."""
    _replace_nonfinite(record)
    record["scientific_digest"] = scientific_digest(record)
    record["sha256"] = compute_sha256(record)
    return record


def _replace_nonfinite(value: Any) -> None:
    """Keep persisted records strict-JSON while status fields carry infinity."""
    if isinstance(value, dict):
        for key, item in list(value.items()):
            if isinstance(item, float) and not math.isfinite(item):
                value[key] = None
            else:
                _replace_nonfinite(item)
    elif isinstance(value, list):
        for item in value:
            _replace_nonfinite(item)


def new_ids(*, prefix: str | None = None) -> tuple[str, str | None]:
    """Return (config_id, sweep_id) -- sweep_id is None unless prefix given."""
    cid = _ulid_like()
    sid = _ulid_like() if prefix else None
    if prefix and sid is not None:
        sid = f"{prefix}{sid[10:]}"  # type: ignore[index]
    return cid, sid
