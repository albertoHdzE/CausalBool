"""Supervisor audit of retained confirm-v1; never writes inside the frozen run.

Run with the repository venv. Arithmetic, completeness, byte/hash checks and
bootstrap are independent of hierarchy.report. Decoding and corpus regeneration
reuse the inspected production modules, so this is not a second codec proof.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "index-deconvolution"))
from hierarchy.corpus import split_cases  # noqa: E402
from hierarchy.decode import decode_archive  # noqa: E402

RUN = ROOT / "index-deconvolution/results/hierarchy_v1/confirm-v1"
OUT = ROOT / "index-deconvolution/results/hierarchy_v1_supervision/confirm-v1"
BASELINES = ("raw", "rle", "gaps", "period", "bernoulli", "context", "zlib", "lzma", "pair_grammar")
ABLATIONS = ("hid_no_schema", "hid_no_arithmetic", "hid_no_transform", "hid_flat", "hid_fixed8")
METHODS = set(BASELINES + ABLATIONS + ("hid_full", "baseline_best"))
STRUCTURED = ("F01", "F02", "F03", "F04", "F05", "F06", "F12")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def endpoint(by_case, split, families, seed, ablations=False):
    """Use the prescribed full Cartesian design, never infer it from present rows."""
    lengths = (256, 1024, 4096) if split == "confirmation" else (16384, 65536)
    reps = range(1000, 1020) if split == "confirmation" else range(2000, 2004)
    cells = []
    for fam in sorted(families):
        for n in lengths:
            pairs = []
            for rep in reps:
                values = []
                for rg in ("base", "ragged"):
                    m = by_case[f"{split}-{fam}-{n}-{rep:04d}-{rg}"]
                    full = m["hid_full"]
                    if ablations:
                        v = [(m[a]["archive_bits"] - full["archive_bits"]) / full["n_bits"]
                             for a in ABLATIONS]
                    else:
                        v = [(m["baseline_best"]["archive_bits"] - full["archive_bits"])
                             / full["n_bits"]]
                    values.append(v)
                pairs.append(np.mean(values, axis=0))
            cells.append(np.asarray(pairs))
    rng = np.random.default_rng(seed)
    samples = np.zeros((10000, cells[0].shape[1]))
    for cell in cells:
        indices = rng.integers(len(cell), size=(10000, len(cell)))
        samples += cell[indices].mean(axis=1) / len(cells)
    q = (0.005, 0.995) if ablations else (0.025, 0.975)
    return {"estimate": np.mean([c.mean(axis=0) for c in cells], axis=0).tolist(),
            "interval": np.quantile(samples, q, axis=0).T.tolist(),
            "cells": len(cells), "units": sum(len(c) for c in cells), "seed": seed}


def main():
    frozen = json.loads((RUN / "freeze.json").read_text())
    freeze_hash = sha(json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode())
    assert freeze_hash == (RUN / "freeze.sha256").read_text().split()[0]
    for group in ("source_sha256", "protocol_sha256", "documentation_sha256_informational"):
        for name, expected in frozen[group].items():
            assert sha((ROOT / name).read_bytes()) == expected, name
    delegation = json.loads((ROOT / "index-deconvolution/protocols/hierarchy_v1/DELEGATION_MANIFEST.json").read_text())
    for entry in delegation["files"]:
        assert sha((ROOT / entry["path"]).read_bytes()) == entry["sha256"]
    rows = [json.loads(s) for s in (RUN / "cases.jsonl").read_text().splitlines()]
    by_case = defaultdict(dict)
    for r in rows:
        assert r["method"] not in by_case[r["case_id"]], "duplicate method row"
        by_case[r["case_id"]][r["method"]] = r
    expected_cases = {}
    for split in ("confirmation", "transfer"):
        cases, manifest = split_cases(split)
        stored = [json.loads(s) for s in (RUN / f"corpus_manifest.{split}.jsonl").read_text().splitlines()]
        assert manifest == stored
        expected_cases.update({c.case_id: c for c in cases})
    assert set(expected_cases) == set(by_case)
    cache = {}
    for i, (cid, methods) in enumerate(sorted(by_case.items())):
        case = expected_cases[cid]
        assert set(methods) == METHODS
        disk_rows = json.loads((RUN / "rows" / f"{cid}.json").read_text())
        assert {r["method"]: r for r in disk_rows} == methods
        for m, r in methods.items():
            assert r["status"] == "ok" and r["decode_ok"] is True
            assert r["freeze_sha256"] == freeze_hash
            assert r["input_sha256"] == case.input_sha256 and r["n_bits"] == len(case.bits)
            for field in ("split", "family", "base_length", "replicate", "ragged"):
                assert r[field] == getattr(case, field)
            h = r["archive_sha256"]
            data = (RUN / r["archive_path"]).read_bytes()
            assert sha(data) == h and 8 * len(data) == r["archive_bits"]
            assert data[4] == r["selected_codec_id"]
            if h not in cache:
                decoded = decode_archive(data)
                cache[h] = (len(decoded), sha(decoded.encode("ascii")))
            assert cache[h] == (len(case.bits), case.input_sha256)
            if m.startswith("hid_"):
                assert r["archive_bits"] <= methods["raw"]["archive_bits"]
        best = min(BASELINES, key=lambda m: (methods[m]["archive_bits"], methods[m]["selected_codec_id"],
                                            (RUN / methods[m]["archive_path"]).read_bytes()))
        assert methods["baseline_best"]["selected_method"] == best
        assert methods["baseline_best"]["archive_sha256"] == methods[best]["archive_sha256"]
        if i % 200 == 0:
            print(f"verified {i + 1}/{len(by_case)} cases; {len(cache)} distinct archives", flush=True)
    primary = endpoint(by_case, "confirmation", STRUCTURED, 33001)
    ablations = endpoint(by_case, "confirmation", STRUCTURED, 33002, True)
    transfer = endpoint(by_case, "transfer", STRUCTURED, 33005)
    summary = json.loads((RUN / "summary.json").read_text())
    assert np.allclose(primary["estimate"][0], summary["primary"]["estimate_mean_saving_per_input_bit"], atol=1e-14, rtol=0)
    assert np.allclose(primary["interval"][0], summary["primary"]["ci95"], atol=1e-14, rtol=0)
    for i, a in enumerate(ABLATIONS):
        assert np.allclose(ablations["estimate"][i], summary["ablations"][a]["incremental_gain_per_input_bit"], atol=1e-14, rtol=0)
        assert np.allclose(ablations["interval"][i], summary["ablations"][a]["ci99"], atol=1e-14, rtol=0)
    assert np.allclose(transfer["interval"][0], summary["transfer_structured_aggregate"]["ci95_descriptive"], atol=1e-14, rtol=0)
    result = {"run_id": "confirm-v1", "freeze_sha256": freeze_hash,
              "review_script_sha256": sha(Path(__file__).read_bytes()),
              "checks_passed": True, "rows": len(rows), "cases": len(by_case),
              "distinct_archives_decoded": len(cache), "status_counts": dict(Counter(r["status"] for r in rows)),
              "split_rows": dict(Counter(r["split"] for r in rows)),
              "primary": primary, "ablation_order": ABLATIONS, "ablations": ablations,
              "transfer_descriptive": transfer,
              "all12_confirmation_descriptive": endpoint(by_case, "confirmation", tuple(f"F{i:02d}" for i in range(1, 13)), 43001),
              "limits": "Uses inspected production decoder and corpus generator; independent full-design completeness, hash/byte checks, portfolio selection and statistical recomputation. No inference rerun or proof of search optimality."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
