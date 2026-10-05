"""Run the reporting-pipeline tests against a frozen revision source (report-r2 or report-r3).

  run_tests.py r2|r3|r2+r3tests [pytest args]

``r2+r3tests`` copies the report-r2 source to a temporary directory and replaces only its
pipeline test file with report-r3's, to show the new regression tests fail on report-r2.

``common`` derives its paths from its own location; as in the revision runners, every Path
constant rooted at the source copy is re-rooted once onto the real index-deconvolution/ tree,
so the tests read a1's retained records. Reads only; writes nothing (no bytecode, no cache).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FOLLOWUP = HERE.parent
ID = FOLLOWUP.parents[3]
REPO = ID.parent
R2SRC = ID / "results/hierarchy_search_diagnosis/review_closure/search-diagnosis-v1-r1/report-r2/source"
R3SRC = FOLLOWUP / "report-r3" / "source"
if sys.argv[1] == "r2+r3tests":
    import shutil
    import tempfile
    SRC = Path(tempfile.mkdtemp(prefix="r2_with_r3_tests_")) / "source"
    shutil.copytree(R2SRC, SRC, ignore=shutil.ignore_patterns("__pycache__"))
    t = "search_diagnosis/tests/test_reporting_pipeline.py"
    shutil.copyfile(R3SRC / t, SRC / t)
else:
    SRC = {"r2": R2SRC, "r3": R3SRC}[sys.argv[1]]
sys.path[:0] = [str(SRC), str(ID), str(REPO / "src")]
from search_diagnosis import common as K  # noqa: E402

_OLD = K.ID_ROOT
for _name, _val in list(vars(K).items()):
    if isinstance(_val, Path) and _val.is_relative_to(_OLD) and _name not in ("PKG",):
        setattr(K, _name, ID / _val.relative_to(_OLD))
K.REPO = REPO
assert K.RUN_DIR == ID / "results/hierarchy_search_diagnosis/search-diagnosis-v1-r1"

import pytest  # noqa: E402

sys.exit(pytest.main(["-p", "no:cacheprovider", "--rootdir", str(SRC), str(SRC / "search_diagnosis/tests")]
                     + sys.argv[2:]))
