"""Preserve the confirm-v1-r1 source identity before HID-search-v2 edits the package.

PROTOCOL_hierarchy_search_v2.md section 3. Read-only on both historical run trees.

  snapshot   record the working-tree status, verify the approved patch hash and the
             active sources against the r1 freeze (one disclosed exception), hash both
             old run trees, and write a deterministic tar of the r1 source/protocol
             dependency set (historical bytes only) with a member manifest;
  trees      re-hash both old run trees and compare with the recorded "before" state.

Outputs go to results/hierarchy_search_v2/preservation/ and to the snapshot path the
protocol suggests. An existing snapshot is reused only if every member matches the
freeze; a conflicting artefact is never overwritten.
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ID = REPO / "index-deconvolution"
RUNS = {"confirm-v1": ID / "results/hierarchy_v1/confirm-v1",
        "confirm-v1-r1": ID / "results/hierarchy_v1/confirm-v1-r1"}
R1 = RUNS["confirm-v1-r1"]
R1_FREEZE_SHA = "f970efff16a2d08bf1dd22eee1386c164af5ba67b22137fefcf06cd182b27f5c"
PATCH = ID / "results/hierarchy_v1_supervision/confirm-v1-r1/validator_closure/validator_closure.patch"
PATCH_SHA = "587d7bc0e0b9f598a80be99776655e3cc8d1df355cfa62884e7fbd8ee5809346"
SUP = ID / "results/hierarchy_v1_supervision/confirm-v1-r1"
SNAPSHOT = SUP / "source_snapshot_confirm-v1-r1.tar"
MANIFEST = SUP / "source_snapshot_confirm-v1-r1.sha256"
PREFIX = "confirm-v1-r1-source/"
OUT = ID / "results/hierarchy_search_v2/preservation"
KNOWN = {"path": "src/description_lengths.py",
         "historical": "052786ca6f2e399cdf19a77743d5f4013f6856abf69a2034c4f944732775524e",
         "active": "b6fb6eaf1a81323bc81858cdadf22184315a7364602546275af0edb997018d36",
         "recovery": Path("/Users/alberto/Documents/projects/CausalBool_validator_closure/"
                          "baseline/src/description_lengths.py")}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def tree_hash(root: Path) -> dict:
    """Aggregate hash of every regular file below ``root`` (sorted relative paths)."""
    files = sorted(p for p in root.rglob("*") if p.is_file() or p.is_symlink())
    h = hashlib.sha256()
    n = 0
    total = 0
    for p in files:
        rel = p.relative_to(root).as_posix()
        data = p.read_bytes()
        h.update(rel.encode() + b"\0" + sha(data).encode() + b"\n")
        n += 1
        total += len(data)
    return {"files": n, "bytes": total, "aggregate_sha256": h.hexdigest()}


def r1_members() -> list[tuple[str, str, str]]:
    """(path, frozen sha256, group) for every source/protocol/doc file the r1 freeze names."""
    fr = json.loads((R1 / "freeze.json").read_text())
    if sha(canonical(fr)) != R1_FREEZE_SHA or (R1 / "freeze.sha256").read_text().strip() != R1_FREEZE_SHA:
        raise SystemExit("r1 freeze does not hash to f970efff...; refusing")
    out = []
    for group in ("source_sha256", "protocol_sha256", "documentation_sha256_informational"):
        for p, h in sorted(fr[group].items()):
            out.append((p, h, group))
    return out


def historical_bytes(path: str, want: str) -> tuple[bytes, str]:
    """Bytes of ``path`` with the r1 hash: the active file, or for the one disclosed
    exception the verified retained recovery copy. Anything else is a hard stop."""
    active = (REPO / path).read_bytes()
    if sha(active) == want:
        return active, "active working tree"
    if path == KNOWN["path"] and sha(active) == KNOWN["active"]:
        rec = KNOWN["recovery"].read_bytes()
        if sha(rec) != want:
            raise SystemExit(f"recovery copy of {path} does not have the historical hash")
        return rec, f"retained recovery copy {KNOWN['recovery']}"
    raise SystemExit(f"unexplained drift: {path} active {sha(active)}, r1 froze {want}")


def build_tar(members) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, data in members:
            ti = tarfile.TarInfo(PREFIX + name)
            ti.size, ti.mtime, ti.mode = len(data), 0, 0o644
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def cmd_snapshot() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rec: dict = {"recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    rec["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                                     text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all", "--",
                             "index-deconvolution/hierarchy", "index-deconvolution/src",
                             "src/description_lengths.py", "index-deconvolution/protocols",
                             "index-deconvolution/experiments"],
                            cwd=REPO, capture_output=True, text=True).stdout
    (OUT / "working_tree_status_before.txt").write_text(status)
    full_status = subprocess.run(["git", "status", "--porcelain=v1"], cwd=REPO,
                                 capture_output=True, text=True).stdout
    rec["working_tree_status_lines_repository"] = len(full_status.splitlines())
    (OUT / "working_tree_status_repository_before.txt").write_text(full_status)
    rec["patch"] = {"path": str(PATCH.relative_to(REPO)), "sha256": sha(PATCH.read_bytes()),
                    "approved_sha256": PATCH_SHA, "matches": sha(PATCH.read_bytes()) == PATCH_SHA}
    if not rec["patch"]["matches"]:
        raise SystemExit("approved patch hash mismatch")
    members, checks = [], []
    for path, want, group in r1_members():
        data, origin = historical_bytes(path, want)
        active = sha((REPO / path).read_bytes())
        checks.append({"path": path, "group": group, "r1_sha256": want, "active_sha256": active,
                       "active_matches_r1": active == want, "snapshot_origin": origin})
        members.append((path, data))
    for name in ("freeze.json", "freeze.sha256"):
        rel = f"index-deconvolution/results/hierarchy_v1/confirm-v1-r1/{name}"
        members.append((rel, (REPO / rel).read_bytes()))
    rec["source_checks"] = checks
    rec["active_mismatches"] = [c["path"] for c in checks if not c["active_matches_r1"]]
    if rec["active_mismatches"] != [KNOWN["path"]]:
        raise SystemExit(f"unexpected active state: {rec['active_mismatches']}")
    lines = [f"{sha(d)}  {p}  [{g}]" for (p, d), (_, _, g) in
             zip(members, r1_members() + [("", "", "run_freeze")] * 2)]
    tar = build_tar(members)
    manifest = "\n".join(lines) + "\n"
    if SNAPSHOT.exists():
        if SNAPSHOT.read_bytes() != tar or MANIFEST.read_text() != manifest:
            raise SystemExit(f"{SNAPSHOT} exists and differs; never overwritten")
        rec["snapshot_action"] = "existing identical snapshot reused"
    else:
        SNAPSHOT.write_bytes(tar)
        MANIFEST.write_text(manifest)
        rec["snapshot_action"] = "written"
    rec["snapshot"] = {"path": str(SNAPSHOT.relative_to(REPO)), "sha256": sha(tar),
                       "members": len(members), "manifest": str(MANIFEST.relative_to(REPO))}
    rec["snapshot_member_verification"] = verify_snapshot()
    rec["old_run_trees_before"] = {k: tree_hash(v) for k, v in RUNS.items()}
    env = {"python": sys.version, "executable": sys.executable}
    try:
        import numpy
        env["numpy"] = numpy.__version__
    except ImportError:
        env["numpy"] = None
    rec["environment_at_snapshot"] = env
    rec["r1_frozen_environment"] = json.loads((R1 / "freeze.json").read_text())["environment"]
    (OUT / "preservation_before.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"snapshot": rec["snapshot"], "action": rec["snapshot_action"],
                      "member_verification": rec["snapshot_member_verification"]["all_match"],
                      "trees": rec["old_run_trees_before"]}, indent=1))
    return 0


def verify_snapshot() -> dict:
    """Every tar member hashes to the r1 freeze; the tar holds nothing else."""
    want = {p: h for p, h, _ in r1_members()}
    fr_rel = "index-deconvolution/results/hierarchy_v1/confirm-v1-r1/"
    seen, bad = 0, []
    with tarfile.open(SNAPSHOT) as tar:
        for m in tar.getmembers():
            name = m.name[len(PREFIX):]
            data = tar.extractfile(m).read()
            if name in want:
                if sha(data) != want.pop(name):
                    bad.append(name)
            elif name == fr_rel + "freeze.json":
                if sha(canonical(json.loads(data))) != R1_FREEZE_SHA:
                    bad.append(name)
            elif name == fr_rel + "freeze.sha256":
                if data.decode().strip() != R1_FREEZE_SHA:
                    bad.append(name)
            else:
                bad.append(f"unexpected member {name}")
            seen += 1
    return {"members_checked": seen, "mismatched": bad, "absent": sorted(want),
            "all_match": not bad and not want}


def cmd_trees() -> int:
    before = json.loads((OUT / "preservation_before.json").read_text())["old_run_trees_before"]
    after = {k: tree_hash(v) for k, v in RUNS.items()}
    res = {"recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "before": before, "after": after, "identical": before == after,
           "snapshot_member_verification": verify_snapshot()}
    (OUT / "preservation_after.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"identical": res["identical"],
                      "snapshot_ok": res["snapshot_member_verification"]["all_match"]}))
    return 0 if res["identical"] and res["snapshot_member_verification"]["all_match"] else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"snapshot": cmd_snapshot, "trees": cmd_trees}.get(cmd, lambda: sys.exit(
        "usage: preserve_confirm_v1_r1_sources.py snapshot|trees"))())
