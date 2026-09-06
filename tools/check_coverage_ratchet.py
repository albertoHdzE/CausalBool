#!/usr/bin/env python3
# tools/check_coverage_ratchet.py — coverage floor guard (AUDIT04-P4f).
#
# The house `.coveragerc` uses a GLOBAL `fail_under` only, which is near-vacuous:
# a repository can pass 95% globally while the declared owner (description_lengths,
# causalbool_paths) sits at 0%. This guard removes that comfortable denominator
# by enforcing TWO floors at once: a declared global floor and a per-module
# floor for every module listed in the completed tier.
#
# Floors live in GOVERNANCE/COVERAGE_RATCHET.toml (JSON or TOML), not embedded
# in this script. The floor RATCHES: it may rise, never fall. A module whose
# measured coverage drops below its recorded floor is a regression (exit 1),
# even when the global figure is fine.
#
# Pure tier only — no Wolfram kernel required:
#   source venv/bin/activate && python -m pytest -q tests/analysis/ --cov=src --cov-report=json
#
# British English; no contractions.

from __future__ import annotations

import json
import sys
from pathlib import Path

# ------------------------------------------------------------------
# 1. Declared floor file — lives outside this script.
# ------------------------------------------------------------------

FLOOR_FILE = "GOVERNANCE/COVERAGE_RATCHET.toml"
# Fallback: also try JSON form if TOML is absent.
FLOOR_FILE_JSON = "GOVERNANCE/COVERAGE_RATCHET.json"

# ------------------------------------------------------------------
# 2. Coverage input — produced by the pure-tier command only.
# ------------------------------------------------------------------

COVERAGE_FILE = "coverage.json"

# ------------------------------------------------------------------
# 3. Main guard logic.
# ------------------------------------------------------------------

def read_toml_floors(path: str) -> tuple[float | None, dict[str, float]]:
    """Parse a minimal TOML-style floor file: global_floor and [module_floors]."""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    global_floor = None
    module_floors: dict[str, float] = {}
    in_module_floors = False
    for line in content.splitlines():
        # Skip comments.
        stripped = line.split('#', 1)[0].strip()
        if not stripped:
            continue
        # Detect [module_floors] section start.
        if stripped.startswith("[") and stripped.endswith("]"):
            in_module_floors = stripped == "[module_floors]"
            continue
        if in_module_floors and '=' in stripped:
            # Format: "path" = value
            key_part, _, val_part = stripped.partition('=')
            key = key_part.strip().strip('"').strip("'")
            val_str = val_part.strip()
            try:
                module_floors[key] = float(val_str)
            except ValueError:
                # Ignore non-numeric lines in the floor file.
                pass
        elif stripped.startswith("global_floor"):
            _, _, val = stripped.partition('=')
            val = val.strip()
            try:
                global_floor = float(val)
            except ValueError:
                pass
    return global_floor, module_floors


def read_json_floors(path: str) -> tuple[float | None, dict[str, float]]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    global_floor = data.get("global_floor")
    module_floors = data.get("module_floors", {})
    # Ensure values are floats.
    cleaned: dict[str, float] = {}
    for k, v in module_floors.items():
        try:
            cleaned[k] = float(v)
        except (ValueError, TypeError):
            pass
    return float(global_floor) if global_floor is not None else None, cleaned


def load_floors() -> tuple[float | None, dict[str, float]]:
    if Path(FLOOR_FILE).exists():
        return read_toml_floors(FLOOR_FILE)
    if Path(FLOOR_FILE_JSON).exists():
        return read_json_floors(FLOOR_FILE_JSON)
    return None, {}


def load_coverage() -> dict:
    if not Path(COVERAGE_FILE).exists():
        return {}
    with open(COVERAGE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def compute_global_figure(data: dict) -> float:
    files = data.get("files", {})
    total_statements = 0
    covered_statements = 0
    for info in files.values():
        summary = info.get("summary", {})
        total_statements += summary.get("num_statements", 0)
        covered_statements += summary.get("covered_lines", 0)
    if total_statements == 0:
        return 0.0
    return (covered_statements / total_statements) * 100.0


def main() -> int:
    # Must refuse if the floor file is missing (nothing declared to protect).
    global_floor, module_floors = load_floors()
    if global_floor is None and not module_floors:
        print("CHECK-COVERAGE-RATCHET: FAIL  floor file missing or unreadable (no declared floor to enforce)")
        print(f"  expected: {FLOOR_FILE} or {FLOOR_FILE_JSON}")
        print("  denominator: 0 modules declared, 0 measured")
        return 1

    # Must refuse if coverage report is missing (stale or never produced).
    coverage_data = load_coverage()
    if not coverage_data or "files" not in coverage_data:
        print("CHECK-COVERAGE-RATCHET: FAIL  coverage report missing, stale, or measures zero modules")
        print(f"  expected: {COVERAGE_FILE}")
        print(f"  floor declared: {len(module_floors)} module floors + global {global_floor if global_floor is not None else 'none'}")
        return 1

    files = coverage_data.get("files", {})
    if not files:
        print("CHECK-COVERAGE-RATCHET: FAIL  coverage report measures zero modules (empty or corrupt)")
        print(f"  denominator: 0 / {len(module_floors) if module_floors else 0}")
        return 1

    # Compute measured figures.
    measured_global = compute_global_figure(coverage_data)
    measured_modules: dict[str, float] = {}
    below_floor_modules: list[str] = []
    for mod_path, floor_val in sorted(module_floors.items()):
        # The module path in the floor file may be a file path or module name.
        # Coverage JSON uses file paths; try both forms.
        file_path_in_coverage = mod_path
        # Also try stripping .py if path is just a basename; but the floor file
        # uses full relative paths (e.g. src/description_lengths.py).
        pct = 0.0
        if file_path_in_coverage in files:
            summary = files[file_path_in_coverage].get("summary", {})
            covered = summary.get("covered_lines", 0)
            total = summary.get("num_statements", 0)
            pct = (covered / total * 100.0) if total > 0 else 0.0
        else:
            # Try matching by basename or by stripping .py extension.
            basename = Path(file_path_in_coverage).name
            for f_path, info in files.items():
                f_basename = Path(f_path).name
                # Try exact basename match or basename without extension.
                if basename == f_basename or basename.replace(".py", "") == f_basename.replace(".py", ""):
                    summary = info.get("summary", {})
                    covered = summary.get("covered_lines", 0)
                    total = summary.get("num_statements", 0)
                    pct = (covered / total * 100.0) if total > 0 else 0.0
                    break
        measured_modules[file_path_in_coverage] = pct
        if pct < floor_val:
            below_floor_modules.append(file_path_in_coverage)

    # Print denominator clearly: modules declared, modules measured, global figure.
    #
    # AUDIT04 review: "N modules measured" originally counted only the DECLARED
    # floors, so a report covering 61 files printed "2 modules measured" and the
    # 59 with no floor at all were invisible. That is the comfortable denominator
    # this guard exists to remove, reappearing inside the guard itself. The
    # unfloored count is now printed on every run, so the size of the gap between
    # what is measured and what is DEFENDED can never be read off as zero.
    modules_declared = len(module_floors)
    modules_in_report = len(files)
    unfloored = modules_in_report - modules_declared
    print(f"CHECK-COVERAGE-RATCHET: denominator — {modules_in_report} modules in the "
          f"report, {modules_declared} with a declared floor, {unfloored} with NO "
          f"floor, global figure {measured_global:.2f}%")
    if global_floor is not None:
        print(f"  declared global floor: {global_floor:.2f}%")
        print(f"  measured global figure: {measured_global:.2f}%")
    else:
        print("  declared global floor: none declared")
    print(f"  modules below floor: {len(below_floor_modules)}")
    for mod in sorted(below_floor_modules):
        floor_text = f" (floor: {module_floors.get(mod, 'N/A'):.2f}%)" if mod in module_floors else ""
        measured_text = f" (measured: {measured_modules.get(mod, 0):.2f}%)"
        print(f"    BELOW FLOOR  {mod}{measured_text}{floor_text}")
    # Also report modules that could not be matched in coverage.
    unmatched_modules = [m for m in module_floors if m not in measured_modules or measured_modules[m] == 0]
    if unmatched_modules:
        print(f"  modules with zero or unmeasured coverage: {len(unmatched_modules)}")
        for mod in sorted(unmatched_modules):
            print(f"    UNMEASURED  {mod} (floor: {module_floors.get(mod, 'N/A'):.2f}%)")

    # Final verdict.
    global_breach = (global_floor is not None) and (measured_global < global_floor)
    floor_breach = len(below_floor_modules) > 0
    if global_breach or floor_breach:
        if global_breach:
            print(f"CHECK-COVERAGE-RATCHET: FAIL  global coverage {measured_global:.2f}% below declared floor {global_floor:.2f}%")
        if floor_breach:
            print(f"CHECK-COVERAGE-RATCHET: FAIL  {len(below_floor_modules)} module(s) below per-file floor")
        return 1

    print("CHECK-COVERAGE-RATCHET: clean — global and all per-module floors met; no regression detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
