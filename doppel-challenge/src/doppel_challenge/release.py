"""Release-gate checks for the exact study namespace.

The gate is intentionally conservative: it validates artefacts already on
disk and reports missing optional dependencies as quarantined diagnostics.
It does not turn an exploratory approximate result into an exact result.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .io import read_json, read_jsonl
from .schema import validate_record
from .validation import validate_catalogue_manifest


def run_release_gate(study_dir: str | Path) -> dict[str, Any]:
    """Audit all exact catalogue runs and return a machine-readable verdict."""
    root = Path(study_dir)
    errors: list[str] = []
    runs: list[dict[str, Any]] = []
    if not root.exists():
        return {"status": "blocked", "errors": ["study_directory_missing"],
                "runs": [], "optional_dependencies": _optional_dependencies()}

    for catalogue_path in sorted(root.glob("*/*/catalogue.jsonl")):
        run_root = catalogue_path.parent
        rows = list(read_jsonl(catalogue_path))
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            check = validate_record(row)
            if not check["valid"]:
                errors.extend(f"{catalogue_path}:{row.get('perturbation_id')}:{error}"
                              for error in check["errors"])
            latest[row.get("perturbation_id")] = row
        manifest_path = run_root / "manifest.json"
        if not manifest_path.exists():
            errors.append(f"{run_root}:manifest_missing")
            manifest_check = {"valid": False, "errors": ["manifest_missing"]}
        else:
            manifest = read_json(manifest_path)
            manifest_check = validate_catalogue_manifest(manifest, list(latest.values()))
            errors.extend(f"{run_root}:manifest:{error}" for error in manifest_check["errors"])
        accepted = [row for row in latest.values() if row.get("accepted_validation")]
        if any(row.get("process_status") != "normal_exit" for row in accepted):
            errors.append(f"{run_root}:accepted_non_normal_process_status")
        runs.append({"path": str(run_root), "attempt_records": len(rows),
                     "latest_records": len(latest), "accepted_records": len(accepted),
                     "manifest_valid": manifest_check["valid"]})

    return {"status": "passed" if runs and not errors else "failed",
            "errors": errors, "runs": runs,
            "optional_dependencies": _optional_dependencies()}


def _optional_dependencies() -> dict[str, Any]:
    """Report optional analysis dependencies without making them mandatory."""
    available = importlib.util.find_spec("pybdm") is not None
    return {"pybdm": {"available": available,
                       "status": "available" if available else "quarantined_missing",
                       "scientific_role": "optional_native_mechanism_complexity"}}


__all__ = ["run_release_gate"]
