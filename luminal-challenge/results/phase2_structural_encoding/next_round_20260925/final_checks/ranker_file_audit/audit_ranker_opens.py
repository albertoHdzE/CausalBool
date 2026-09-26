"""Re-run ranker processes under a file-open audit hook; compare with the recorded rows.

Every file opened by the process after start-up is recorded. Pass criterion: no
opened path is an oracle, split, EVALUATOR, record or fixture-manifest file, and the
ordering digest equals the recorded row's. Diagnostic only; rows are not modified.
Usage: python audit_ranker_opens.py RUN
"""
import json, subprocess, sys
from pathlib import Path

RUN = Path(sys.argv[1]); ROOT = RUN.parents[2]
HOOK = r'''
import sys, json
opened = []
def hook(event, args):
    if event == "open" and isinstance(args[0], str):
        opened.append(args[0])
sys.addaudithook(hook)
sys.argv = ["x", "--spec", SPEC]
import runpy, io, contextlib
buffer = io.StringIO()
with contextlib.redirect_stdout(buffer):
    try:
        runpy.run_module("research.next_round_ranker", run_name="__main__")
    except SystemExit:
        pass
print(json.dumps({"opened": opened, "stdout": buffer.getvalue()}))
'''
rows = [json.loads(l) for l in open(RUN / "stages/L_orderings/rows.jsonl")]
commands = {json.loads(l)["key"]: json.loads(l) for l in open(RUN / "stages/L_orderings/commands.jsonl")}
forbidden = ("oracle.json", "split.json", "EVALUATOR.json", "record.json", "MANIFEST.json", "FIXTURE_QUALIFICATION")
out = {"rows_checked": 0, "forbidden_opens": [], "digest_mismatches": [], "data_files_opened": set()}
for row in rows:
    spec = commands[row["key"]]["spec"]
    code = HOOK.replace("SPEC", repr(json.dumps(spec)))
    proc = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "PYTHONPATH": f"{ROOT/'.reference'}:{ROOT}"})
    data = json.loads(proc.stdout.strip().splitlines()[-1])
    result = json.loads(data["stdout"].strip().splitlines()[-1])
    out["rows_checked"] += 1
    for path in data["opened"]:
        if not path.endswith((".py", ".pyc", ".so", ".pth")) and "__pycache__" not in path:
            out["data_files_opened"].add(path)
        if any(path.endswith(f) for f in forbidden):
            out["forbidden_opens"].append([row["key"], path])
    if result["ordering_sha256"] != row["result"]["ordering_sha256"]:
        out["digest_mismatches"].append(row["key"])
out["data_files_opened"] = sorted(out["data_files_opened"])
out["status"] = "PASS" if out["rows_checked"] == 420 and not out["forbidden_opens"] and not out["digest_mismatches"] else "FAIL"
(Path(__file__).with_name("RANKER_FILE_AUDIT.json")).write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in out.items()}))
