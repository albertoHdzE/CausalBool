"""Paths, fixed populations, saved-input loading and preservation records.

Membership is derived from the frozen study design (``hierarchy.study``) and the
phase contract, then checked against the saved rows; bits come only from decoding
each case's retained ``raw`` archive, whose hash must equal the row's input hash.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from hierarchy.benchmark import atomic_write, canonical, sha256_bytes, sha256_file
from hierarchy.corpus import case_id
from hierarchy.decode import decode_archive
from hierarchy.study import get_study

PKG = Path(__file__).resolve().parent
ID_ROOT = PKG.parents[1]                      # index-deconvolution/
REPO = ID_ROOT.parent
BASE_RUN = ID_ROOT / "results" / "hierarchy_search_v2" / "search-confirm-v2-r1"
BASE_FREEZE = "0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49"
RESULT_ROOT = ID_ROOT / "results" / "hierarchy_search_diagnosis"
RUN_ID = "search-diagnosis-v1-r1"
RUN_DIR = RESULT_ROOT / RUN_ID
PROTO_DIR = ID_ROOT / "protocols" / "hierarchy_search_diagnosis"
CONTRACT = PROTO_DIR / "contract.json"
DELEGATION = PROTO_DIR / "DELEGATION_MANIFEST.json"
PROTOCOL = ID_ROOT / "PROTOCOL_hierarchy_search_diagnosis.md"
KICKOFF = ID_ROOT / "KICKOFF_hierarchy_search_diagnosis.md"
REFERENCES = BASE_RUN / "diagnostics" / "boundary_reference" / "references.json"
EVIDENCE_ROLE = "posthoc_diagnostic"
STUDY = "search-v2"
ROLES = ("confirmation", "transfer", "stress")
HID_ARMS = ("hid_legacy", "hid_first_local", "hid_consensus_local", "hid_dense_local",
            "hid_global", "hid_full")


def contract() -> dict:
    return json.loads(CONTRACT.read_text())


def write_json(path: Path, obj) -> None:
    atomic_write(path, (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode())


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Fixed populations
# ---------------------------------------------------------------------------

def design_case_ids() -> list[str]:
    """Every case id of the accepted run, derived from the frozen study design."""
    study = get_study(STUDY)
    out = []
    for role in study.run_roles(BASE_RUN.name):
        r = study.role(role)
        for fam in r.families:
            for bl in r.base_lengths:
                for rep in r.replicates:
                    for ragged in (False, True):
                        out.append(case_id(r.prefix, fam, bl, rep, ragged))
    return sorted(out)


def _block_ids(block: dict) -> list[str]:
    return [case_id(block["role"], fam, bl, rep, ragged)
            for fam in block["families"] for bl in block["base_lengths"]
            for rep in block["replicates"] for ragged in (False, True)]


def section_ids(section: str) -> dict[str, list[str]]:
    """{'targets': [...], 'controls': [...]} (D2), or {'targets': [...]} (D3, D4)."""
    c = contract()
    if section == "D2":
        return {"targets": sorted(i for b in c["D2"]["targets"] for i in _block_ids(b)),
                "controls": sorted(i for b in c["D2"]["controls"] for i in _block_ids(b))}
    if section == "D3":
        return {"targets": section_ids("D2")["targets"]}
    if section == "D4":
        return {"targets": sorted(i for b in c["D4"]["populations"] for i in _block_ids(b))}
    raise ValueError(section)


def parse_case_id(cid: str) -> dict:
    role, fam, bl, rep, kind = cid.split("-")
    return {"case_id": cid, "role": role, "family": fam, "base_length": int(bl),
            "replicate": int(rep), "ragged": kind == "ragged",
            "unit": f"{role}|{fam}|{bl}|{rep}", "cell": f"{role}|{fam}|{bl}"}


# ---------------------------------------------------------------------------
# Saved inputs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Case:
    """The two attributes the reused ``hierarchy.benchmark._Job`` reads, plus provenance."""

    case_id: str
    bits: str
    input_sha256: str


def saved_rows(cid: str) -> dict[str, dict]:
    rows = json.loads((BASE_RUN / "rows" / f"{cid}.json").read_text())
    by = {}
    for r in rows:
        if r["method"] in by:
            raise RuntimeError(f"duplicate saved row {cid}/{r['method']}")
        by[r["method"]] = r
    return by


def saved_archive(row: dict) -> bytes:
    data = (BASE_RUN / row["archive_path"]).read_bytes()
    if sha256_bytes(data) != row["archive_sha256"] or 8 * len(data) != row["archive_bits"]:
        raise RuntimeError(f"saved archive mismatch: {row['case_id']}/{row['method']}")
    return data


def load_case(cid: str, rows: dict | None = None) -> Case:
    """Bits of ``cid`` by decoding its retained raw archive; the hash must match."""
    rows = rows or saved_rows(cid)
    raw = rows["raw"]
    bits = decode_archive(saved_archive(raw))
    h = hashlib.sha256(bits.encode()).hexdigest()
    if h != raw["input_sha256"] or len(bits) != raw["n_bits"] or \
            any(r["input_sha256"] != h for r in rows.values()):
        raise RuntimeError(f"decoded raw archive of {cid} does not match its input hash")
    return Case(cid, bits, h)


def references() -> dict[str, dict]:
    return {it["case_id"]: it for it in json.loads(REFERENCES.read_text())}


# ---------------------------------------------------------------------------
# Preservation
# ---------------------------------------------------------------------------

def _tree_hash():
    """The existing aggregate tree hash (experiments/preserve_confirm_v1_r1_sources.py)."""
    p = ID_ROOT / "experiments" / "preserve_confirm_v1_r1_sources.py"
    spec = importlib.util.spec_from_file_location("_preserve_owner", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tree_hash


PROTECTED_TREES = {
    "hierarchy_v1/confirm-v1": ID_ROOT / "results/hierarchy_v1/confirm-v1",
    "hierarchy_v1/confirm-v1-r1": ID_ROOT / "results/hierarchy_v1/confirm-v1-r1",
    "hierarchy_search_v2 (entire accepted results tree)": ID_ROOT / "results/hierarchy_search_v2",
    "protocols (all old packets)": ID_ROOT / "protocols",
}


def protected_files() -> list[Path]:
    files = sorted(p for p in (ID_ROOT / "hierarchy").rglob("*")     # bytecode excluded
                   if p.is_file() and "__pycache__" not in p.parts)
    files += [REPO / p for p in json.loads(DELEGATION.read_text())
              ["scientific_owner_baseline_sha256"]]
    files += [ID_ROOT / "notebooks" / n for n in (
        "16_hierarchical_index_generalization.ipynb", "17_hierarchy_search_v2.ipynb",
        "build_16.py", "build_17.py", "_nblib.py", "README.md")]
    files += [PROTOCOL, KICKOFF, CONTRACT, DELEGATION]
    return sorted(set(files))


def preservation_record() -> dict:
    tree_hash = _tree_hash()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                          text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                            cwd=REPO, capture_output=True, text=True).stdout
    rec = {"recorded_utc": utc(), "git_head": head,
           "git_status_sha256": sha256_bytes(status.encode()),
           "git_status_lines": len(status.splitlines()),
           "freeze_sha256_file": (BASE_RUN / "freeze.sha256").read_text().split()[0],
           "trees": {k: tree_hash(v) for k, v in PROTECTED_TREES.items()},
           "files": {str(p.relative_to(REPO)): sha256_file(p) for p in protected_files()
                     if p.exists()}}
    return rec, status


def compare_preservation(before: dict, after: dict) -> dict:
    diffs = []
    for k in before["trees"]:
        if before["trees"][k] != after["trees"].get(k):
            diffs.append(f"trees:{k}")
    for k, v in before["files"].items():
        if after["files"].get(k) != v:
            diffs.append(f"files:{k}")
    return {"differences": diffs, "unchanged": not diffs,
            "denominator": {"trees": len(before["trees"]), "files": len(before["files"])}}


def canonical_sha(obj) -> str:
    return sha256_bytes(canonical(obj))
