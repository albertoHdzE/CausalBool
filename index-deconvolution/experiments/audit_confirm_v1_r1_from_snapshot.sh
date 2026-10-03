#!/bin/zsh
# Re-run the supervisor's numerical audit of the retained confirm-v1-r1 run against its
# ORIGINAL sources, extracted from source_snapshot_confirm-v1-r1.tar into a temporary
# tree (the r1 description-length owner there is the historical 052786ca... bytes, not
# the active file). Read-only for the repository: the run is reached through a symlink,
# the audit writes only to the temporary directory, and neither the run's
# verification.json nor the stored audit.json is touched.
# Exit 0 iff every snapshot member matches the r1 freeze and the audit equals the
# stored supervisor audit.json (script-identity fields excluded).
#   zsh index-deconvolution/experiments/audit_confirm_v1_r1_from_snapshot.sh
set -eu
REPO=${0:A:h:h:h}
SUP=$REPO/index-deconvolution/results/hierarchy_v1_supervision/confirm-v1-r1
RUN=$REPO/index-deconvolution/results/hierarchy_v1/confirm-v1-r1
T=$(mktemp -d /tmp/hid_confirm_v1_r1_audit.XXXX)
tar -xf $SUP/source_snapshot_confirm-v1-r1.tar -C $T
R=$T/confirm-v1-r1-source
(cd $R && sed 's/  \[.*\]$//' $SUP/source_snapshot_confirm-v1-r1.sha256 | shasum -a 256 -c --quiet)
RUNLINK=$R/index-deconvolution/results/hierarchy_v1/confirm-v1-r1
cmp $RUNLINK/freeze.json $RUN/freeze.json
cmp $RUNLINK/freeze.sha256 $RUN/freeze.sha256
rm -r $RUNLINK
ln -s $RUN $RUNLINK
mkdir -p $R/index-deconvolution/experiments $T/out
cp $REPO/index-deconvolution/protocols/hierarchy_v1/DELEGATION_MANIFEST.json $R/index-deconvolution/protocols/hierarchy_v1/
cp $REPO/index-deconvolution/KICKOFF_hierarchical_index_generalization.md $R/index-deconvolution/
cp $REPO/index-deconvolution/experiments/review_hierarchy_confirm_v1.py $R/index-deconvolution/experiments/
cd $R
$REPO/venv/bin/python - $T/out $SUP/audit.json $RUNLINK <<'EOF'
import contextlib, io, json, sys
from pathlib import Path
sys.path.insert(0, "index-deconvolution/experiments")
import review_hierarchy_confirm_v1 as A
import hierarchy
assert hierarchy.__file__.startswith(str(Path.cwd())), hierarchy.__file__
A.RUN, A.OUT = Path(sys.argv[3]), Path(sys.argv[1])
with contextlib.redirect_stdout(io.StringIO()):
    A.main()
a = json.loads((A.OUT / "audit.json").read_text()); b = json.loads(Path(sys.argv[2]).read_text())
for k in ("review_script_sha256", "supervisor_wrapper_sha256", "run_id"):
    a.pop(k, None); b.pop(k, None)
print("original r1 sources from snapshot:", hierarchy.__file__)
print("primary estimate:", a["primary"].get("estimate"), "ci95:", a["primary"].get("ci95"))
print("audit of confirm-v1-r1 under its original sources equals stored audit.json:", a == b)
sys.exit(0 if a == b else 1)
EOF
