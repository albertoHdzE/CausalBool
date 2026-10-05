"""Deliberate-mutation checks (BENCHMARK section 2): each mutation is applied to a
temporary copy of this package and must make a RELEVANT test fail by a failed test
(assertion or a raised verification error inside the test body), not by an import or
collection error. The working tree is never modified.

    (from index-deconvolution/) PYTHONPATH=experiments:.:../src ../venv/bin/python -B \
        -m hierarchy_dictionary.tests.mutations OUT_JSON
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
TS, TR = "tests/test_search.py", "tests/test_runner.py"

MUTATIONS = [
    ("donor_misreference", "search.py", "        node = nodes[j]\n", "        node = nodes[j - 1] if j else nodes[j]\n",
     f"{TS}::test_hop_depth_8_boundary"),
    ("omitted_exception", "search.py", "        node = f.patch(node, flips)", "        node = f.patch(node, flips[:-1])",
     f"{TS}::test_relations_exact_transforms_flip_caps_window_and_ties"),
    ("dropped_tail", "search.py", "        vb = ViewBuilder(bits, levels, o)",
     "        vb = ViewBuilder(bits[:o + L.m * L.span], levels, o)",
     f"{TS}::test_odd_tails_at_multiple_levels_and_both_origins"),
    ("free_dictionary_cost", "search.py", '                    prec["archive_bits"] = 8 * len(arc)',
     '                    prec["archive_bits"] = 8 * len(arc) - 8 * sum(len(w) // 8 for w in words)',
     f"{TS}::test_shared_word_witness_relation_beats_its_O_proposal_but_not_a0"),
    ("relation_hop_cap", "search.py", "if 1 + hops[j] > cfg.relation_hops:",
     "if 1 + hops[j] > cfg.relation_hops + 1:", f"{TS}::test_hop_depth_8_boundary"),
    ("free_a0_runtime", "runner.py",
     'row["deployment_wall_ns"] = a0_row["worker_wall_ns"] + res["worker_wall_ns"]',
     'row["deployment_wall_ns"] = res["worker_wall_ns"]',
     f"{TR}::test_completed_job_and_deployment_cost_includes_a0"),
    ("missing_as_zero", "report.py", 'rec[arm] = row["archive_bits"] if ok else None',
     'rec[arm] = row["archive_bits"] if ok else 0', f"{TR}::test_missing_values_are_unavailable_not_zero"),
    ("incomplete_over_invalid", "report.py",
     'state = "INVALID" if invalid else ("INCOMPLETE" if incomplete else "VALID_COMPLETE")',
     'state = "INCOMPLETE" if incomplete else ("INVALID" if invalid else "VALID_COMPLETE")',
     f"{TR}::test_invalid_precedes_incomplete_and_disables_recommendation"),
]


def run_one(name, fname, old, new, test) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix=f"hdd_mut_{name}_"))
    dst = tmp / "hierarchy_dictionary"
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns("__pycache__"))
    # the worker adds its own parent directory to sys.path; the reused multilevel owner
    # must resolve there too (a symlink to the unmodified package, never a copy)
    (tmp / "hierarchy_multilevel").symlink_to(PKG.parent / "hierarchy_multilevel")
    src = (dst / fname).read_text()
    occurrences = src.count(old)
    if occurrences != 1:
        shutil.rmtree(tmp, ignore_errors=True)
        return {"mutation": name, "applied": False, "occurrences": occurrences}
    (dst / fname).write_text(src.replace(old, new))
    env = dict(os.environ, PYTHONPATH=f"{tmp}:{ID_ROOT / 'experiments'}:{ID_ROOT}:{ID_ROOT.parent / 'src'}",
               PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-B", "-m", "pytest", str(dst / test), "-q",
                          "--tb=line", "-p", "no:cacheprovider"], cwd=str(ID_ROOT), env=env,
                         capture_output=True, text=True)
    tail = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", tail)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", tail)) else 0
    lines = [ln for ln in out.stdout.splitlines() if ln.startswith(("E ", "/", "FAILED")) or "Error" in ln][:6]
    (tmp / "hierarchy_multilevel").unlink()
    shutil.rmtree(tmp, ignore_errors=True)
    return {"mutation": name, "file": fname, "test": test, "applied": True, "exit": out.returncode,
            "summary": tail, "failed": failed, "errors": errors, "failure_lines": lines,
            "killed_by_test_failure": out.returncode == 1 and failed > 0 and errors == 0}


def main(out_path: str) -> int:
    res = [run_one(*m) for m in MUTATIONS]
    ok = all(r.get("killed_by_test_failure") for r in res)
    Path(out_path).write_text(json.dumps({"all_killed": ok, "mutations": res}, indent=1) + "\n")
    for r in res:
        print(r["mutation"], r.get("summary"), "KILLED" if r.get("killed_by_test_failure") else "SURVIVED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
