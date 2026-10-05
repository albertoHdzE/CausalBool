"""Supervisor replay of the reviewed notebook guard; outputs stay in this directory."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[3]
HARNESS = OUT.parent / "review_closure/scripts/execute_notebook_artifact_only.py"
spec = importlib.util.spec_from_file_location("reviewed_notebook_guard", HARNESS)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.PKG = OUT
guard.ORIGINAL = OUT / "original_17_hierarchy_search_v2.ipynb"
sys.argv = [str(HARNESS), str(REPO)]
code = guard.main()
if code:
    raise SystemExit(code)

_, negative = guard.run(
    guard.ORIGINAL, REPO, "original_negative_control",
    Path(tempfile.mkdtemp(prefix="hid_supervisor_nb_guard_")),
    REPO / "index-deconvolution/results", REPO / "index-deconvolution/src",
)
assert negative["exit_status"] == 1
assert any(e.get("name") == "hierarchy.search_v2"
           for e in negative["guard"]["refused"]), negative
(OUT / "original_notebook_negative_control.json").write_text(
    json.dumps(negative, indent=2) + "\n"
)
print("Original notebook negative control: inference import blocked as expected")
