"""HID-search-v2 evaluation layer: case generation, retained development inputs,
stress generators S01/S02 and evaluation-only boundary metadata. Never imported by
inference (search_v2, consensus, segmentation).

F01-F12 units come from the unchanged ``corpus.generate_unit`` with the RNG
NAMESPACE passed as its seed-selection string; the study ROLE is stored separately.
A namespace may never start with ``development`` (that prefix switches the existing
generators to development parameter ranges). Stress units reuse ``stream_rng`` and
the existing word helpers in the draw order fixed by BENCHMARK.md section 3.

Reserved prospective namespaces can be generated only for a run directory that holds
a freeze for this study naming that role (``ReservedAccessError`` otherwise).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import corpus
from .corpus import (STREAMS, Case, GeneratorError, complement, primitive_word, rand_word,
                     rotate_right, stream_rng, tile)

S01_PERIODS = (37, 43, 59, 67, 97, 127, 193, 251)
S02_PREFIX_PERIODS = (19, 23, 29, 37)
S02_SUFFIX_PERIODS = (41, 43, 47, 53)


class ReservedAccessError(RuntimeError):
    """A reserved prospective namespace was requested without a valid freeze."""


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("ascii")).hexdigest()


def _choice(rng, seq):
    return seq[rng.randrange(len(seq))]


# ---------------------------------------------------------------------------
# Stress generators (BENCHMARK.md section 3)
# ---------------------------------------------------------------------------

def s01(N: int, rs, rc, rn, rep: int) -> tuple[str, dict]:
    p = _choice(rs, S01_PERIODS)
    word = primitive_word(rc, p)
    r = rs.randrange(p)
    clean = tile(rotate_right(word, r), N)
    divisor = 64 if rep % 2 == 0 else 16
    k = N // divisor
    flips = sorted(rn.sample(range(N), k))
    out = bytearray(clean.encode("ascii"))
    for q in flips:
        out[q] ^= 1
    return out.decode("ascii"), {"word": word, "period": p, "rotation_right": r,
                                 "density_divisor": divisor, "k": k, "flips": flips}


def s02(N: int, rs, rc, rn, rep: int) -> tuple[str, dict]:
    a = rs.randrange(N // 6, N // 3 + 1)
    b = rs.randrange(2 * N // 3, 5 * N // 6 + 1)
    p1 = _choice(rs, S02_PREFIX_PERIODS)
    p2 = _choice(rs, S02_SUFFIX_PERIODS)
    u1 = primitive_word(rc, p1)
    mid = rand_word(rc, b - a)
    u2 = primitive_word(rc, p2)
    z = tile(u1, a) + mid + tile(u2 + complement(u2) + u2[::-1], N - b)
    i = rn.randrange(N + 1)
    v = str(rn.getrandbits(1))
    inter = z[:i] + v + z[i:]
    d = rn.randrange(N + 1)
    out = inter[:d] + inter[d + 1:]
    return out, {"cuts_original": [a, b], "p1": p1, "p2": p2, "U1": u1, "U2": u2,
                 "insert_index": i, "insert_bit": v, "delete_index_intermediate": d,
                 "draw_order": ["rs:a", "rs:b", "rs:p1", "rs:p2", "rc:U1", "rc:R",
                                "rc:U2", "rn:i", "rn:v", "rn:d"]}


STRESS = {"S01": s01, "S02": s02}


def generate_unit(namespace: str, family: str, base_length: int, replicate: int
                  ) -> tuple[str, dict]:
    """One N = base_length + 3 unit under ``namespace`` (never a development prefix)."""
    if namespace.startswith("development"):
        raise ValueError("a search-v2 RNG namespace may not start with 'development'")
    if family in STRESS:
        N = base_length + 3
        rs, rc, rn = (stream_rng(namespace, family, base_length, replicate, s) for s in STREAMS)
        bits, meta = STRESS[family](N, rs, rc, rn, replicate)
        if len(bits) != N or bits.strip("01"):
            raise GeneratorError(f"{family} produced an invalid string")
        return bits, meta
    return corpus.generate_unit(namespace, family, base_length, replicate)


# ---------------------------------------------------------------------------
# Boundary metadata (evaluation only)
# ---------------------------------------------------------------------------

def edit_mapped_cuts(original_cuts, i: int, d: int, N: int) -> dict:
    """Map original construction cuts through one insertion (before element i of the
    original) and one deletion (index d of the intermediate), BENCHMARK.md section 3.

    Cut coordinate k is the boundary just before element k. Insertion-adjacent cuts are
    added only when the inserted element survives; the deletion join min(d, N) is added
    as specified. Returns final-coordinate candidates (unclipped) and the derivation."""
    mapped = []
    for k in original_cuts:
        k1 = k + 1 if i <= k else k
        k2 = k1 - 1 if d < k1 else k1
        mapped.append({"original": k, "after_insert": k1, "final": k2})
    survives = d != i
    extra = []
    if survives:
        j = i - 1 if d < i else i
        extra += [j, j + 1]
    join = min(d, N)
    cands = [m["final"] for m in mapped] + extra + [join]
    return {"mapped": mapped, "inserted_survives": survives,
            "insertion_adjacent": extra, "deletion_join": join, "candidates": cands}


def clip_cuts(cands, length: int) -> list[int]:
    return sorted({c for c in cands if 0 < c < length})


def boundary_reference_cuts(family: str, meta: dict, N: int, length: int) -> dict:
    """Supplied construction cuts for an F12 or S02 scored string, or unavailable."""
    if family == "S02":
        der = edit_mapped_cuts(meta["cuts_original"], meta["insert_index"],
                               meta["delete_index_intermediate"], N)
    elif family == "F12":
        l1, l2, _ = meta["region_lengths"]
        der = edit_mapped_cuts([l1, l1 + l2], meta["insert_index"], meta["delete_index"], N)
        der["schema_translation"] = ("F12 region_lengths -> original cuts l1, l1+l2; "
                                     "insert_index i and delete_index d use the same "
                                     "insert-before / delete-intermediate convention")
    else:
        return {"available": False, "reason": f"no construction boundaries for {family}"}
    return {"available": True, "cuts": clip_cuts(der["candidates"], length), "derivation": der}


# ---------------------------------------------------------------------------
# Role cases
# ---------------------------------------------------------------------------

def _require_freeze(study, role, run_dir: Path) -> None:
    fp = run_dir / "freeze.json"
    if not fp.is_file():
        raise ReservedAccessError(
            f"role {role.name} uses reserved namespace {role.rng_namespace}; no freeze in "
            f"{run_dir}: reserved strings are generated only after the freeze")
    fr = json.loads(fp.read_text())
    if fr.get("study") != study.name or role.name not in fr.get("design", {}).get("roles", {}):
        raise ReservedAccessError(f"freeze in {run_dir} does not declare {study.name}:{role.name}")


def generated_cases(study, role, run_dir: Path | None) -> tuple[list[Case], list[dict]]:
    if role.reserved:
        if run_dir is None:
            raise ReservedAccessError(f"role {role.name} is reserved; a run directory is required")
        _require_freeze(study, role, run_dir)
    cases, manifest = [], []
    for fam in role.families:
        for bl in role.base_lengths:
            for rep in role.replicates:
                bits, meta = generate_unit(role.rng_namespace, fam, bl, rep)
                for rg in (False, True):
                    s = bits if rg else bits[:bl]
                    cases.append(Case(study.case_id(role.name, fam, bl, rep, rg), role.name,
                                      fam, bl, rep, rg, s))
                manifest.append({
                    "unit_id": f"{role.name}|{fam}|{bl}|{rep}", "role": role.name,
                    "split": role.name, "rng_namespace": role.rng_namespace,
                    "evidence_role": role.evidence_role, "family": fam, "base_length": bl,
                    "replicate": rep, "N": bl + 3, "paired_offsets": [0, 3],
                    "case_ids": [study.case_id(role.name, fam, bl, rep, rg) for rg in (False, True)],
                    "full_sha256": _sha(bits), "base_sha256": _sha(bits[:bl]),
                    "params_evaluation_only": meta})
    return cases, manifest


def retained_cases(study, role, repo: Path) -> tuple[list[Case], list[dict]]:
    """Development inputs decoded from the immutable retained raw archives, each checked
    against its case record (input hash and length)."""
    from .decode import decode_archive
    src = repo / role.retained_run
    want = {}
    for fam in role.families:
        for bl in role.base_lengths:
            for rep in role.replicates:
                for rg in (False, True):
                    want[corpus.case_id(role.retained_split, fam, bl, rep, rg)] = (fam, bl, rep, rg)
    recs: dict = {}
    with open(src / "cases.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            if r["case_id"] in want and r["method"] in ("raw", "hid_full"):
                recs.setdefault(r["case_id"], {})[r["method"]] = r
    meta_by_unit = {}
    with open(src / f"corpus_manifest.{role.retained_split}.jsonl") as fh:
        for line in fh:
            m = json.loads(line)
            meta_by_unit[(m["family"], m["base_length"], m["replicate"])] = m
    cases, manifest = [], []
    for cid, (fam, bl, rep, rg) in want.items():
        r = recs.get(cid, {}).get("raw")
        if r is None:
            raise RuntimeError(f"retained run has no raw row for {cid}")
        data = (src / r["archive_path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != r["archive_sha256"]:
            raise RuntimeError(f"retained raw archive of {cid} differs from its row hash")
        bits = decode_archive(data)
        if _sha(bits) != r["input_sha256"] or len(bits) != r["n_bits"]:
            raise RuntimeError(f"retained input of {cid} does not match its case record")
        if recs[cid].get("hid_full", {}).get("input_sha256", r["input_sha256"]) != r["input_sha256"]:
            raise RuntimeError(f"retained rows of {cid} disagree on the input hash")
        new_id = study.case_id(role.name, fam, bl, rep, rg)
        cases.append(Case(new_id, role.name, fam, bl, rep, rg, bits))
        um = meta_by_unit[(fam, bl, rep)]
        manifest.append({
            "case_id": new_id, "role": role.name, "split": role.name,
            "evidence_role": "development", "family": fam, "base_length": bl,
            "replicate": rep, "ragged": rg, "n_bits": len(bits), "input_sha256": r["input_sha256"],
            "source_run": role.retained_run, "source_case_id": cid,
            "source_split": role.retained_split, "source_raw_archive": r["archive_path"],
            "source_raw_archive_sha256": r["archive_sha256"],
            "params_evaluation_only": um["params"], "N": um["N"]})
    return cases, manifest


def unit_metadata(manifest: list[dict]) -> dict:
    """(family, base_length, replicate) -> (N, evaluation-only parameters)."""
    out = {}
    for m in manifest:
        out[(m["family"], m["base_length"], m["replicate"])] = (m["N"], m["params_evaluation_only"])
    return out
