"""Post-freeze supervisor diagnostics. Not confirmatory performance evidence.

Reproduces reporting/validation defects, constructs a metadata-assisted legal
HID witness, and independently ranks regenerated BDM permutation scores.
All outputs go to hierarchy_v1_supervision, never to the frozen run.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "index-deconvolution"))
from hierarchy import diagnostics, report  # noqa: E402
from hierarchy.corpus import generate_unit  # noqa: E402
from hierarchy.decode import decode_archive  # noqa: E402
from hierarchy.infer import ABLATIONS, _Search  # noqa: E402
from hierarchy.model import NodeFactory, to_model  # noqa: E402
from hierarchy.wire import serialize_model  # noqa: E402

RUN = ROOT / "index-deconvolution/results/hierarchy_v1/confirm-v1"
OUT = ROOT / "index-deconvolution/results/hierarchy_v1_supervision/confirm-v1"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(s) for s in (RUN / "cases.jsonl").read_text().splitlines()]
    sub = [r for r in rows if r["split"] == "confirmation" and r["family"] == "F04"
           and r["base_length"] == 1024 and r["replicate"] == 1000]
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / "cases.jsonl").write_text("\n".join(json.dumps(r) for r in sub))
        got = report.summarise(p, {"confirmation": {"scored_strings": 1440}}, {"valid": True})
    defects = {"one_unit_from_420_required": got["primary"],
               "reported_counts": got["status_counts"]["confirmation"]["hid_full"],
               "negative_ci_censored_baseline": report.verdict((-.2, -.1), False, True),
               "negative_ci_invalid_engineering": report.verdict((-.2, -.1), True, False)}
    assert defects["one_unit_from_420_required"]["verdict"] == "supported"
    # Deliberately inject a wrong expansion. The current search silently rejects it.
    search = _Search("01", ABLATIONS["full"])
    with patch.object(NodeFactory, "expand", return_value="10"):
        search.consider(search.f.literal("01"), "supervisor_fault_injection")
    defects["candidate_mismatch"] = {"raised": False, "rejected_verify": search.counts["rejected_verify"]}
    defects["observed_rejected_verify_in_retained_run"] = sum(
        (r.get("search_counters") or {}).get("rejected_verify", 0) for r in rows)

    # This witness uses evaluation-only boundaries. It must NEVER enter benchmark
    # scoring, inference tuning on confirm-v1, or a claim of automatic discovery.
    bits, meta = generate_unit("transfer", "F12", 65536, 2000)
    bits = bits[:65536]
    factory = NodeFactory()

    def encode_segment(s):
        for period in range(1, min(64, len(s) // 2) + 1):
            if all(s[j] == s[j % period] for j in range(period, len(s))):
                copies, tail = divmod(len(s), period)
                node = factory.repeat(factory.literal(s[:period]), copies)
                return factory.concat((node, factory.literal(s[-tail:]))) if tail else node
        return factory.literal(s)

    l1, l2, _ = meta["region_lengths"]
    ins, delete = meta["insert_index"], meta["delete_index"]
    boundaries = [0, ins, ins + 1, l1 + 1, l1 + l2 + 1, delete, len(bits)]
    root = factory.concat([encode_segment(bits[l:r]) for l, r in zip(boundaries, boundaries[1:])])
    model = to_model(root)
    archive = serialize_model(model, len(bits))
    assert decode_archive(archive) == bits
    cid = "transfer-F12-65536-2000-base"
    rr = {r["method"]: r for r in rows if r["case_id"] == cid}
    witness = {"case_id": cid, "status": "posthoc_metadata_assisted_diagnostic_only",
               "boundaries": boundaries, "original_hid_bits": rr["hid_full"]["archive_bits"],
               "baseline_best_bits": rr["baseline_best"]["archive_bits"],
               "witness_bits": 8 * len(archive), "rules": len(model.rules), "depth": root.depth,
               "decode_ok": True, "archive_sha256": hashlib.sha256(archive).hexdigest(),
               "input_sha256": hashlib.sha256(bits.encode("ascii")).hexdigest()}
    assert witness["witness_bits"] < witness["original_hid_bits"]
    (OUT / "F12_oracle_boundaries_witness.isd").write_bytes(archive)
    controls = {}
    by_case = {}
    for r in rows:
        by_case.setdefault(r["case_id"], {})[r["method"]] = r
    for fam in ("F07", "F08", "F09"):
        values = []
        for m in by_case.values():
            h = m["hid_full"]
            if h["split"] == "confirmation" and h["family"] == fam:
                values.append((min(m["bernoulli"]["archive_bits"], m["context"]["archive_bits"])
                               - h["archive_bits"]) / h["n_bits"])
        controls[fam] = {"mean_saving_vs_two_statistical_codes": float(np.mean(values)),
                         "hid_shorter_strings": sum(v > 0 for v in values), "strings": len(values),
                         "scope": "descriptive comparator correction, not a new hypothesis test"}
    results = {"failure_reproductions": defects, "witness": witness,
               "controls_statistical_comparator": controls}
    (OUT / "failure_reproductions.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2), flush=True)

    original = json.loads((RUN / "diagnostics.json").read_text())
    jobs = [(fam, generate_unit("confirmation", fam, 1024, 1000)[0][:1024], "confirmation", 1000)
            for fam in diagnostics.DIAG_FAMILIES]
    pvals, matrices = {}, {}
    with ProcessPoolExecutor(max_workers=2) as pool:
        regenerated = list(pool.map(diagnostics._family_matrix, jobs))
    for (fam, _, _, _), (matrix, coverage) in zip(jobs, regenerated):
        assert coverage == [1024] * 24
        # Match specified Python decimal rounding; do not substitute np.round.
        a = np.array([[round(v, 10) for v in row] for row in matrix])
        rank = np.empty_like(a)
        for c in range(a.shape[1]):
            rank[:, c] = np.searchsorted(np.sort(a[:, c]), a[:, c], side="right") / len(a)
        t = rank.min(axis=1)
        pval = float(np.mean(t <= t[0]))
        assert pval == original["objects"][fam]["adaptive_p"]
        assert np.array_equal(np.array(matrix[0]), original["objects"][fam]["observed_scores"])
        pvals[fam] = pval
        matrices[fam] = matrix
    running = 0.0
    adjusted = {}
    for i, fam in enumerate(sorted(pvals, key=lambda f: (pvals[f], f))):
        running = max(running, min(1., (len(pvals) - i) * pvals[fam]))
        adjusted[fam] = running
        assert running == original["holm"][fam]["holm_adjusted"]
    bdm = {"all_match": True, "pvalues": pvals, "holm_adjusted": adjusted,
           "score_generation": "inspected production BDM owner and null generator reused",
           "ranking": "independent inclusive ranks, minimum across configurations and Holm correction",
           "score_matrices": matrices}
    (OUT / "bdm_reaudit.json").write_text(json.dumps(bdm, indent=2) + "\n")
    print("BDM: all ten adaptive p-values and Holm corrections independently reproduced.")


if __name__ == "__main__":
    main()
