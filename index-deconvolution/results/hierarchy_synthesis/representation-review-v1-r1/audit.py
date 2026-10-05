"""Independent check of per_case.json / summary.json (imports nothing from analysis.py).

    (from index-deconvolution/) PYTHONPATH=.:../src ../venv/bin/python -B <this dir>/audit.py

Re-selects the best R and best O candidates from the D2 traces with its own loop (sort
by bits, then request ordinal), re-reads and re-hashes stored bytes, re-decodes them with
the owner decoder, re-derives full lengths and margins, checks that the ledger's fields
are disjoint consecutive slices covering the archive (offsets), checks every component
table sums to the full length, and recomputes the summary counts and quantiles.
"""
import hashlib
import json
import statistics
from pathlib import Path

from hierarchy.decode import decode_archive
from hierarchy.ledger import archive_ledger

HERE = Path(__file__).resolve().parent
ID = HERE.parents[2]
REPO = ID.parent
D = ID / "results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1"


def main() -> int:
    pc = json.loads((HERE / "per_case.json").read_text())["rows"]
    summ = json.loads((HERE / "summary.json").read_text())
    cases = {c["case_id"]: c for c in json.loads((ID / "protocols/hierarchy_multilevel_v1/CASES.json").read_text())["cases"]}
    problems, checked = [], 0
    margins = {"R": [], "O": []}
    by_codec = {}
    for r in pc:
        cid = r["case_id"]
        x = decode_archive((REPO / cases[cid]["references"]["raw"]["archive_path"]).read_bytes())
        a0row = json.loads((D / "rows" / f"{cid}.A0.json").read_text())
        a0 = (D / a0row["archive_path"]).read_bytes()
        if hashlib.sha256(a0).hexdigest() != r["a0_sha256"] or 8 * len(a0) != r["a0_bits"] or decode_archive(a0) != x:
            problems.append(f"{cid}: A0")
        if a0row["archive_sha256"] != cases[cid]["references"]["hid_full"]["archive_sha256"]:
            problems.append(f"{cid}: A0 differs from the saved k=1 reference")
        if sum(r["a0_components"].values()) != r["a0_bits"]:
            problems.append(f"{cid}: A0 components")
        tr = json.loads((D / json.loads((D / "rows" / f"{cid}.D2.json").read_text())["trace_path"]).read_text())
        props = [p for v in tr["views"] for p in v["proposals"] if p["archive_bits"] is not None]
        for tag, modes in (("R", {"R(O)", "R(P)"}), ("O", {"O"})):
            cand = sorted((p for p in props if p["mode"] in modes),
                          key=lambda p: (p["archive_bits"], p["request_ordinal"]))
            sel = cand[0]
            got = r[tag]
            if got["archive_sha256"] != sel["archive_sha256"] or got["request_ordinal"] != sel["request_ordinal"]:
                problems.append(f"{cid}.{tag}: selection")
            data = (D / "archives" / sel["archive_sha256"][:2] / f"{sel['archive_sha256']}.isd").read_bytes()
            if hashlib.sha256(data).hexdigest() != sel["archive_sha256"] or 8 * len(data) != sel["archive_bits"]:
                problems.append(f"{cid}.{tag}: bytes")
            if decode_archive(data) != x:
                problems.append(f"{cid}.{tag}: decode")
            led = archive_ledger(data)
            pos = 0
            for f in led["fields"]:
                b = bytes.fromhex(f["hex"])
                if data[pos:pos + len(b)] != b or len(b) != f["bytes"]:
                    problems.append(f"{cid}.{tag}: ledger field not a consecutive slice")
                    break
                pos += len(b)
            if pos != len(data):
                problems.append(f"{cid}.{tag}: ledger does not cover the archive")
            if sum(got["components"].values()) != 8 * len(data):
                problems.append(f"{cid}.{tag}: components")
            m = 8 * len(data) - 8 * len(a0)
            if m != got["margin_vs_a0_bits"] or abs(m / len(x) - got["margin_vs_a0_per_input_bit"]) > 1e-15:
                problems.append(f"{cid}.{tag}: margin")
            margins[tag].append(m)
            by_codec.setdefault((tag, a0[4]), []).append(m)
            checked += 1
    for tag in ("R", "O"):
        v = sorted(margins[tag])
        s = summ[tag]
        if s["shorter_equal_longer_vs_a0"] != [sum(x < 0 for x in v), sum(x == 0 for x in v), sum(x > 0 for x in v)]:
            problems.append(f"{tag}: sign counts")
        if s["margin_bits"]["median"] != statistics.median(v) or s["margin_bits"]["min"] != v[0] or s["margin_bits"]["max"] != v[-1]:
            problems.append(f"{tag}: quantiles")
    ro = [r["R"]["bits"] - r["O"]["bits"] for r in pc]
    if [sum(x < 0 for x in ro), sum(x == 0 for x in ro), sum(x > 0 for x in ro)] != \
            [summ["best_R_minus_best_O"][k] for k in ("shorter", "equal", "longer")]:
        problems.append("R minus O counts")
    codec = {f"{t}|codec{c}": {"n": len(v), "median_margin_bits": statistics.median(v), "min": min(v), "max": max(v)}
             for (t, c), v in sorted(by_codec.items())}
    out = {"pass": not problems and checked == 192, "problems": problems, "selections_checked": checked,
           "strings": len(pc), "margin_by_a0_codec (0 raw, 1 hid)": codec,
           "not_used": ["analysis.py", "any encoder"], "reused": ["hierarchy.decode", "hierarchy.ledger"]}
    (HERE / "audit_result.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
