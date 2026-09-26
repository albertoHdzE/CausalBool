"""Run development_audit from the frozen D auditor bytes and from the current file.

The frozen copy resolves ROOT from its own location, so it is copied for the run
to a temporary sibling in research/ and removed afterwards.
Usage (from luminal-challenge/): PYTHONPATH=.reference:. ../venv/bin/python -s <this file>
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

RUN = Path("results/phase2_structural_encoding/third_round_20260925_resume")
TMP = Path("research/third_round_resume_zz_review_frozen_tmp.py")
out = {}
shutil.copyfile(RUN / "provenance/third_round_resume_audit.D_frozen.py", TMP)
try:
    for label, path in (("frozen", TMP), ("current", Path("research/third_round_resume_audit.py"))):
        spec = importlib.util.spec_from_file_location(f"audit_{label}", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        res = mod.development_audit(RUN, RUN / "DEVELOPMENT.json")
        out[label] = {"status": res["status"], "total_checks": res.get("total_checks"),
                      "findings": res["findings"][:10]}
finally:
    TMP.unlink()
print(json.dumps(out, indent=1))
(Path(__file__).parent / "D_AUDIT_BOTH.json").write_text(json.dumps(out, indent=1) + "\n")
