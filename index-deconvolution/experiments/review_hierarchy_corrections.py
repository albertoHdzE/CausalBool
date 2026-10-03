"""Independent supervisor evidence audit for confirm-v1-r1.

Reuses the supervisor's original complete-design/byte/bootstrap audit, not the
developer's comparison/report code. Writes only to the new supervision directory.
"""
from __future__ import annotations

import contextlib
import difflib
import hashlib
import io
import json
import tarfile
from pathlib import Path

import review_hierarchy_confirm_v1 as audit

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "index-deconvolution/results"
OLD = BASE / "hierarchy_v1/confirm-v1"
NEW = BASE / "hierarchy_v1/confirm-v1-r1"
OUT = BASE / "hierarchy_v1_supervision/confirm-v1-r1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_rows(directory):
    rows = [json.loads(s) for s in (directory / "cases.jsonl").read_text().splitlines()]
    index = {(r["case_id"], r["method"]): r for r in rows}
    assert len(rows) == len(index) == 26112
    return index


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("Auditing new run: every case, archive and prespecified endpoint...", flush=True)
    audit.RUN, audit.OUT = NEW, OUT
    with contextlib.redirect_stdout(io.StringIO()):
        audit.main()
    checked = json.loads((OUT / "audit.json").read_text())
    checked["run_id"] = "confirm-v1-r1"
    checked["supervisor_wrapper_sha256"] = sha(Path(__file__).read_bytes())
    (OUT / "audit.json").write_text(json.dumps(checked, indent=2) + "\n")

    old_freeze, new_freeze = [json.loads((d / "freeze.json").read_text()) for d in (OLD, NEW)]
    stable = ("search_configs", "restricted_oracle_config", "baseline_parameters", "generator",
              "expected_counts", "resource_policy", "environment", "methods", "protocol_sha256")
    for field in stable:
        assert old_freeze[field] == new_freeze[field], field
    snapshot = BASE / "hierarchy_v1_supervision/confirm-v1/source_snapshot_confirm-v1.tar"
    assert sha(snapshot.read_bytes()) == "f5a3d3d7a35541171521415409562e8a35fd8166a36b354d4396e5ffe0333407"
    changes = []
    diffs = []
    n_checked = 0
    with tarfile.open(snapshot) as tar:
        for group in ("source_sha256", "protocol_sha256", "documentation_sha256_informational"):
            for path, digest in old_freeze[group].items():
                data = tar.extractfile("confirm-v1-source/" + path).read()
                assert sha(data) == digest, path
                n_checked += 1
                current = (ROOT / path).read_bytes()
                if data != current:
                    changes.append(path)
                    diffs.extend(difflib.unified_diff(data.decode().splitlines(True),
                                                     current.decode().splitlines(True),
                                                     fromfile="confirm-v1/" + path,
                                                     tofile="confirm-v1-r1/" + path))
    new_sources = sorted(set(new_freeze["source_sha256"]) - set(old_freeze["source_sha256"]))
    assert new_sources == ["index-deconvolution/hierarchy/validation.py"]
    (OUT / "source_changes.diff").write_text("".join(diffs))

    old, new = read_rows(OLD), read_rows(NEW)
    assert set(old) == set(new)
    excluded = {"run_id", "freeze_sha256", "encode_wall_ns", "worker_wall_ns",
                "peak_rss_bytes", "stderr_log", "exception_message", "rss_method"}
    for key in old:
        x, y = old[key], new[key]
        assert set(x) == set(y)
        assert {k: v for k, v in x.items() if k not in excluded} == {
            k: v for k, v in y.items() if k not in excluded}, key
        assert (OLD / x["archive_path"]).read_bytes() == (NEW / y["archive_path"]).read_bytes(), key
    assert (OLD / "archives_manifest.sha256").read_bytes() == (NEW / "archives_manifest.sha256").read_bytes()
    old_diag, new_diag = [json.loads((d / "diagnostics.json").read_text()) for d in (OLD, NEW)]
    for obj in (old_diag, new_diag):
        obj.pop("wall_s")
        obj.pop("freeze_sha256")
    assert old_diag == new_diag
    previous_audit = json.loads((BASE / "hierarchy_v1_supervision/confirm-v1/audit.json").read_text())
    for k in ("primary", "ablations", "transfer_descriptive", "all12_confirmation_descriptive"):
        assert checked[k] == previous_audit[k], k
    result = {"run_id": "confirm-v1-r1", "freeze_sha256": checked["freeze_sha256"],
              "snapshot_files_verified": n_checked, "snapshot_sha256": sha(snapshot.read_bytes()),
              "changed_original_sources_and_documents": changes, "added_sources": new_sources,
              "unchanged_freeze_fields": stable, "compared_rows": len(old),
              "all_deterministic_row_fields_equal": True, "all_archive_bytes_equal": True,
              "archive_manifests_identical": True, "diagnostics_equal_except_freeze_and_time": True,
              "independent_endpoints_equal_original_supervisor_audit": True,
              "scope": "Same-corpus correctness replay; not new scientific replication evidence."}
    (OUT / "replay_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
