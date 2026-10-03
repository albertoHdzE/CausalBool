#!/bin/zsh
# Re-run the supervisor's audit of the retained confirm-v1 run against its ORIGINAL
# sources, extracted from the non-importable snapshot into a temporary tree. Read-only
# for the repository: the run is reached by a symlink and the audit writes to the
# temporary directory. Exit 0 iff the audit passes and equals the stored audit.json.
#   zsh index-deconvolution/experiments/audit_confirm_v1_from_snapshot.sh
set -eu
REPO=${0:A:h:h:h}
SUP=$REPO/index-deconvolution/results/hierarchy_v1_supervision/confirm-v1
T=$(mktemp -d /tmp/hid_confirm_v1_audit.XXXX)
tar -xf $SUP/source_snapshot_confirm-v1.tar -C $T
R=$T/confirm-v1-source
(cd $R && sed 's/  \[.*\]$//' $SUP/source_snapshot_confirm-v1.sha256 | shasum -a 256 -c --quiet)
RUNLINK=$R/index-deconvolution/results/hierarchy_v1/confirm-v1
cmp $RUNLINK/freeze.json $REPO/index-deconvolution/results/hierarchy_v1/confirm-v1/freeze.json
rm -r $RUNLINK
ln -s $REPO/index-deconvolution/results/hierarchy_v1/confirm-v1 $RUNLINK
mkdir -p $R/index-deconvolution/experiments $T/out
cp $REPO/index-deconvolution/protocols/hierarchy_v1/DELEGATION_MANIFEST.json $R/index-deconvolution/protocols/hierarchy_v1/
cp $REPO/index-deconvolution/KICKOFF_hierarchical_index_generalization.md $R/index-deconvolution/
cp $REPO/index-deconvolution/experiments/review_hierarchy_confirm_v1.py $R/index-deconvolution/experiments/
cd $R
$REPO/venv/bin/python - $T/out $SUP/audit.json <<'EOF'
import json, sys
from pathlib import Path
sys.path.insert(0, "index-deconvolution/experiments")
import review_hierarchy_confirm_v1 as A
import hierarchy
assert hierarchy.__file__.startswith(str(Path.cwd())), hierarchy.__file__
A.OUT = Path(sys.argv[1])
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    A.main()
a = json.loads((A.OUT / "audit.json").read_text()); b = json.loads(Path(sys.argv[2]).read_text())
a.pop("review_script_sha256"); b.pop("review_script_sha256")
print("original sources from snapshot:", hierarchy.__file__)
print("audit of confirm-v1 under its original sources equals stored audit.json:", a == b)
sys.exit(0 if a == b else 1)
EOF
