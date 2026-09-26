"""Write PROGRESS.json for the r2 campaign from durable artifacts only.

Counts fsynced journal lines and stage summaries; imports no research code and
does no measurement work, so it can run during timing without competing load.
"""
import json
import sys
import time
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
RUN = AUDIT.parent / (sys.argv[1] if len(sys.argv) > 1 else "recovery_campaign_20260923_r3")
EXPECTED = {"p2": 1800, "p4": 7020, "p5": 24300}


def lines(path: Path) -> int:
    return sum(1 for line in path.open() if line.strip()) if path.is_file() else 0


def main() -> None:
    stages = {}
    for stage in ("p0", "p1", "p2", "p3", "p4", "p5"):
        summary = RUN / stage / "summary.json"
        stages[stage] = {"summary_written": summary.is_file()}
        if stage in EXPECTED:
            stages[stage].update(
                journal_commands=lines(RUN / "journals" / f"{stage}_commands.jsonl"),
                journal_rows=lines(RUN / "journals" / f"{stage}_rows.jsonl"),
                expected_rows=EXPECTED[stage])
    current = next((s for s in reversed(list(stages)) if (RUN / s).is_dir()), None)
    source = (AUDIT / "FINAL_SOURCE_SHA256.txt").read_text().splitlines()
    record = {
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run": str(RUN.relative_to(AUDIT.parents[2])),
        "latest_stage_directory": current,
        "stages": stages,
        "gates_written": (RUN / "gates.json").is_file(),
        "frozen_source_files": len(source),
        "last_successful_command": "see COMMANDS.jsonl (last record with exit_code 0)",
        "resume": ("The runner refuses an existing run directory and has no in-run "
                   "resume. If interrupted: preserve this run unchanged, record the "
                   "cause, and start a fresh self-contained run with the next unused "
                   "suffix (_r3) using the identical command from the frozen source; "
                   "never append into or merge with this directory."),
    }
    (AUDIT / "PROGRESS.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: v for k, v in stages.items() if v.get("journal_rows") or v["summary_written"]}))


if __name__ == "__main__":
    main()
