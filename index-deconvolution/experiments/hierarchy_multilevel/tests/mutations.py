"""Deliberate-mutation checks (ACCEPTANCE 2): each mutation is applied to a temporary
copy of this package and must make a RELEVANT test fail (a failed assertion, not an
import or collection error). The working tree is never modified.

    (from index-deconvolution/) PYTHONPATH=experiments:.:../src ../venv/bin/python -B \
        -m hierarchy_multilevel.tests.mutations OUT_JSON
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ID_ROOT = PKG.parents[1]

MUTATIONS = [
    ("tail_loss", "search.py", "self.suffix = x[self.core_end:]", 'self.suffix = ""',
     "tests/test_search.py::test_every_admissible_archive_round_trips_and_spans_are_lossless"),
    ("missing_dictionary_cost", "search.py", 'prec["archive_bits"] = 8 * len(arc)',
     'prec["archive_bits"] = 8 * len(arc) - 8 * sum(len(w) // 8 for w in levels[0].entries)',
     "tests/test_search.py::test_hand_cost_of_g0_includes_dictionary_and_envelope"),
    ("wrong_original_span", "search.py",
     "iv = [[origin + occ[s][0] * top.span, origin + (occ[s][0] + 1) * top.span] for s in singles]",
     "iv = [[occ[s][0] * top.span, (occ[s][0] + 1) * top.span] for s in singles]",
     "tests/test_search.py::test_weak_support_spans_in_original_bit_coordinates_hand"),
    ("free_incumbent_runtime", "runner.py",
     'row["deployment_wall_ns"] = a0_row["worker_wall_ns"] + res["worker_wall_ns"]',
     'row["deployment_wall_ns"] = res["worker_wall_ns"]',
     "tests/test_runner.py::test_completed_job_and_deployment_cost_includes_a0"),
    ("false_zero_modal_gap", "search.py", "    if not diffs:\n        return None, None",
     "    if not diffs:\n        return 0, 0.0",
     "tests/test_search.py::test_unavailable_is_never_zero"),
    ("false_zero_saving", "report.py",
     "return None if a is None or b is None or not n else (b - a) / n",
     "return 0.0 if a is None or b is None or not n else (b - a) / n",
     "tests/test_runner.py::test_missing_values_are_unavailable_not_zero"),
    ("tie_replaces_incumbent", "search.py", "if len(arc) < len(self.archive):",
     "if len(arc) <= len(self.archive):", "tests/test_search.py::test_ties_keep_the_earlier_incumbent"),
    ("incomplete_over_invalid", "report.py",
     'state = "INVALID" if invalid else ("INCOMPLETE" if incomplete else "VALID_COMPLETE")',
     'state = "INCOMPLETE" if incomplete else ("INVALID" if invalid else "VALID_COMPLETE")',
     "tests/test_runner.py::test_invalid_precedes_incomplete_and_disables_recommendation"),
]


def run_one(name, fname, old, new, test) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix=f"hml_mut_{name}_"))
    dst = tmp / "hierarchy_multilevel"
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns("__pycache__"))
    src = (dst / fname).read_text()
    occurrences = src.count(old)
    if occurrences != 1:
        return {"mutation": name, "applied": False, "occurrences": occurrences}
    (dst / fname).write_text(src.replace(old, new))
    env = dict(os.environ, PYTHONPATH=f"{tmp}:{ID_ROOT}:{ID_ROOT.parent / 'src'}",
               PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-B", "-m", "pytest", str(dst / test), "-q",
                          "--tb=line", "-p", "no:cacheprovider"], cwd=str(ID_ROOT), env=env,
                         capture_output=True, text=True)
    tail = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", tail)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", tail)) else 0
    shutil.rmtree(tmp, ignore_errors=True)
    return {"mutation": name, "file": fname, "test": test, "applied": True, "exit": out.returncode,
            "summary": tail, "failed": failed, "errors": errors,
            "killed_by_assertion": out.returncode == 1 and failed > 0 and errors == 0}


def main(out_path: str) -> int:
    res = [run_one(*m) for m in MUTATIONS]
    ok = all(r.get("killed_by_assertion") for r in res)
    Path(out_path).write_text(json.dumps({"all_killed": ok, "mutations": res}, indent=1) + "\n")
    for r in res:
        print(r["mutation"], r.get("summary"), "KILLED" if r.get("killed_by_assertion") else "SURVIVED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
