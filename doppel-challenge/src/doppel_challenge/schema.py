"""Small dependency-free validator for version-2 scientific records."""
from __future__ import annotations

import math
from typing import Any

from .records import RECORD_KINDS, SCHEMA_VERSION, compute_sha256, legacy_canonical_bytes, scientific_digest
import hashlib


def validate_record(record: dict[str, Any], *, require_digest: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return {"valid": False, "errors": ["record_not_object"]}
    required = {"schema_version", "record_kind", "config_id", "sha256"}
    errors.extend(f"missing:{key}" for key in sorted(required - set(record)))
    if record.get("record_kind") not in RECORD_KINDS:
        errors.append("unknown_record_kind")
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    if require_digest and "sha256" in record:
        expected = compute_sha256(record)
        legacy = hashlib.sha256(legacy_canonical_bytes(record)).hexdigest()
        if record["sha256"] not in {expected, legacy}:
            errors.append("sha256_mismatch")
    def finite(value: Any) -> None:
        if isinstance(value, float) and not math.isfinite(value):
            errors.append("non_finite_number")
        elif isinstance(value, dict):
            for item in value.values(): finite(item)
        elif isinstance(value, list):
            for item in value: finite(item)
    finite(record)
    if record.get("record_kind") == "catalogue_row":
        if "perturbation_id" not in record:
            errors.append("missing:perturbation_id")
        if record.get("divergence_status") == "infinite" and not record.get("infinite_kl"):
            errors.append("infinite_status_without_flag")
        if record.get("infinite_kl") and record.get("D_KL_nats") is not None:
            errors.append("infinite_kl_requires_null_value")
        if not record.get("infinite_kl") and record.get("D_KL_nats") is None:
            errors.append("finite_kl_requires_numeric_value")
        if record.get("process_status") != "normal_exit" and record.get("accepted_validation"):
            errors.append("accepted_record_has_non_normal_exit")
    if "scientific_digest" in record and record["scientific_digest"] != scientific_digest(record):
        errors.append("scientific_digest_mismatch")
    if record.get("record_kind") in {"shared_program_benchmark", "approximate_repertoire", "scaling_benchmark",
                                      "full_behaviour_scaling_benchmark",
                                      "whole_repertoire_scaling_benchmark", "scale_pilot",
                                      "scale_pilot_case"}:
        required_approximate = {"observable", "approximation", "estimator_parameters",
                                "uncertainty", "process_status", "accepted_validation",
                                "provenance"}
        errors.extend(f"missing:{key}" for key in sorted(required_approximate - set(record)))
        if record.get("record_kind") == "approximate_repertoire" and record.get("approximation") == "none_exact_full_state_space":
            errors.append("approximate_record_claims_exact")
    return {"valid": not errors, "errors": errors}
