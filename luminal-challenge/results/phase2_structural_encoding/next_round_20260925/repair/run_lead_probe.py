"""Run the lead's R1 probe function against a named solver module, without its __main__.

Usage: PYTHONPATH=.reference:. python run_lead_probe.py MODULE OUTPUT
The lead's file is imported read-only; its PROBES.json is never written.
"""
import hashlib, importlib, importlib.util, json, sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
PROBE = ROOT / "results/phase2_structural_encoding/lead_objective_review_20260925/probes.py"
module_name, output = sys.argv[1], Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("lead_probes", PROBE)
probes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probes)
target = importlib.import_module(module_name)
# The probe imports ``research.objective_index_search as search`` inside the
# function; point that name at the module under test for the successor run.
import research
with mock.patch.object(research, "objective_index_search", target, create=True), \
        mock.patch.dict(sys.modules, {"research.objective_index_search": target}):
    try:
        result = probes.interrupted_validation()
        status = "COMPLETED"
    except AssertionError as exc:
        result, status = {"assertion": repr(exc)}, "ASSERTION_FAILED"
source = Path(target.__file__)
payload = {"module": module_name, "module_file": str(source.relative_to(ROOT)),
           "module_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "probe_sha256": hashlib.sha256(PROBE.read_bytes()).hexdigest(),
           "status": status, "result": result}
output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(json.dumps(payload, sort_keys=True))
