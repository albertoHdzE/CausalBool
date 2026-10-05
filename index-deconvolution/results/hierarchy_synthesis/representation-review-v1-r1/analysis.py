"""Saved-archive comparison of the best R(O)/R(P) and best O D2 candidates with A0.

    (from index-deconvolution/) PYTHONPATH=.:../src ../venv/bin/python -B <this dir>/analysis.py

Artifact-only. Reads the accepted dictionary run's rows, D2 traces and stored archive
bytes; uses the owner decoder (``hierarchy.decode``) and byte ledger
(``hierarchy.ledger.archive_ledger``). Runs no encoder and builds no archive.

Selection (NEXT_CLAUDE item 2): over all D2 view proposals with an archive, the minimum
by (archive bits, saved request ordinal), restricted to modes {R(O), R(P)} ("best R")
or to mode O ("best O"). The selected proposal is necessarily its view-mode's retained
best (first shortest in that mode, lowest ordinal), so its bytes are on disk.

Authoritative partition: ``archive_ledger`` cuts the archive into consecutive disjoint
byte fields that reassemble it exactly. Components here are unions of whole fields:
  envelope            magic, codec id, n, payload length
  dag                 q_rules
  <KIND>.header       opcode and length/arity/count fields of rules of that kind
  <KIND>.refs         child ids (CONCAT child_ids, REPEAT/PATCH/XFORM child_id)
  <KIND>.payload      LITERAL packed bits, REPEAT copies, PATCH position deltas,
                      XFORM flags and rotation, AP/SCHEMA parameters
  <codec>.payload     every non-envelope field of a non-HID codec
Each byte belongs to exactly one component; per-word cost of shared DAG nodes is NOT
allocated (a shared rule is counted once, where it is written).
"""
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from hierarchy import codes as C
from hierarchy.decode import decode_archive
from hierarchy.ledger import archive_ledger

HERE = Path(__file__).resolve().parent
ID = HERE.parents[2]
REPO = ID.parent
D = ID / "results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1"
CASES = ID / "protocols/hierarchy_multilevel_v1/CASES.json"
HEADER = {"opcode", "length", "arity", "q_flip", "q_ap", "q_schema", "foreground"}
REFS = {"child_id"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def components(data: bytes) -> tuple[dict, dict]:
    led = archive_ledger(data)
    kinds = {}
    if led["model"] is not None:
        kinds = {f"rule{i}": C.OP_NAMES[r.op] for i, r in enumerate(led["model"].rules)}
    comp = Counter()
    for f in led["fields"]:
        own, fld = f["owner"], f["field"].split("[")[0]      # labels are indexed: child_id[3]
        if own == "envelope":
            key = "envelope"
        elif own == "dag":
            key = "dag"
        elif own in kinds:
            k = kinds[own]
            key = f"{k}.header" if fld in HEADER else (f"{k}.refs" if fld in REFS else f"{k}.payload")
        else:
            key = f"{led['codec']}.payload"
        comp[key] += 8 * f["bytes"]
    if sum(comp.values()) != 8 * len(data):
        raise AssertionError("ledger partition does not sum to the archive")
    model = led["model"]
    info = {"codec": led["codec"], "rules": len(model.rules) if model else None,
            "rule_kinds": dict(Counter(kinds.values())) if model else None,
            "dag_depth": model.depth() if model else None}
    return dict(sorted(comp.items())), info


def pick(tr: dict, modes) -> tuple | None:
    best = None
    for v in tr["views"]:
        for p in v["proposals"]:
            if p["mode"] in modes and p["archive_bits"] is not None:
                key = (p["archive_bits"], p["request_ordinal"])
                if best is None or key < best[0]:
                    best = (key, p, v)
    return best


def main() -> int:
    cases = json.loads(CASES.read_text())["cases"]
    rows, unavailable = [], []
    for c in cases:
        cid = c["case_id"]
        x = decode_archive((REPO / c["references"]["raw"]["archive_path"]).read_bytes())
        a0row = json.loads((D / "rows" / f"{cid}.A0.json").read_text())
        d2row = json.loads((D / "rows" / f"{cid}.D2.json").read_text())
        tr = json.loads((D / d2row["trace_path"]).read_text())
        a0 = (D / a0row["archive_path"]).read_bytes()
        a0c, a0i = components(a0)
        rec = {"case_id": cid, "family": c["family"], "base_length": c["base_length"],
               "replicate": c["replicate"], "ragged": c["ragged"], "n_bits": len(x),
               "a0_sha256": sha(a0), "a0_bits": 8 * len(a0), "a0_decodes": decode_archive(a0) == x,
               "a0_components": a0c, "a0_info": a0i}
        for tag, modes in (("R", ("R(O)", "R(P)")), ("O", ("O",))):
            b = pick(tr, modes)
            if b is None:
                rec[tag] = None
                unavailable.append(f"{cid}: no {tag} candidate")
                continue
            (bits, ordn), p, v = b
            m = next(mm for mm in v["modes"] if mm["mode"] == p["mode"])
            path = D / "archives" / p["archive_sha256"][:2] / f"{p['archive_sha256']}.isd"
            if not path.is_file():
                rec[tag] = None
                unavailable.append(f"{cid}: {tag} bytes not retained ({p['archive_sha256'][:12]})")
                continue
            data = path.read_bytes()
            comp, info = components(data)
            con = m.get("construction") or {}
            rec[tag] = {"mode": p["mode"], "proposal": p["proposal"], "request_ordinal": ordn,
                        "view": [v["level"], v["width"], v["origin"]], "m": v["m"], "k": v["k"],
                        "status": p["status"], "archive_sha256": p["archive_sha256"],
                        "is_view_mode_best": m["best_sha256"] == p["archive_sha256"],
                        "bytes_match_hash": sha(data) == p["archive_sha256"],
                        "bits": 8 * len(data), "decodes": decode_archive(data) == x,
                        "margin_vs_a0_bits": 8 * len(data) - 8 * len(a0),
                        "margin_vs_a0_per_input_bit": (8 * len(data) - 8 * len(a0)) / len(x),
                        "byte_identical_to_a0": data == a0,
                        "relations_in_view_mode": con.get("relations_selected"),
                        "period_replacements_in_view": None,
                        "components": comp, "component_minus_a0": {
                            k: comp.get(k, 0) - a0c.get(k, 0) for k in sorted(set(comp) | set(a0c))},
                        "info": info}
        if rec["R"] and rec["O"]:
            rec["R_minus_O_bits"] = rec["R"]["bits"] - rec["O"]["bits"]
        else:
            rec["R_minus_O_bits"] = None
        rows.append(rec)
    (HERE / "per_case.json").write_text(json.dumps({"rows": rows, "unavailable": unavailable}, indent=1) + "\n")
    with open(HERE / "per_case.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case_id", "n_bits", "a0_bits", "a0_codec", "R_mode", "R_proposal", "R_view",
                    "R_bits", "R_margin_bits", "R_margin_per_bit", "R_identical_a0", "O_view", "O_bits",
                    "O_margin_bits", "O_identical_a0", "R_minus_O_bits", "R_sha256", "O_sha256", "a0_sha256"])
        for r in rows:
            R, O = r["R"] or {}, r["O"] or {}
            w.writerow([r["case_id"], r["n_bits"], r["a0_bits"], r["a0_info"]["codec"], R.get("mode"),
                        R.get("proposal"), "-".join(map(str, R.get("view") or [])), R.get("bits"),
                        R.get("margin_vs_a0_bits"), R.get("margin_vs_a0_per_input_bit"),
                        R.get("byte_identical_to_a0"), "-".join(map(str, O.get("view") or [])),
                        O.get("bits"), O.get("margin_vs_a0_bits"), O.get("byte_identical_to_a0"),
                        r["R_minus_O_bits"], R.get("archive_sha256"), O.get("archive_sha256"), r["a0_sha256"]])
    with open(HERE / "per_case_components.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case_id", "archive", "component", "bits"])
        for r in rows:
            for k, val in r["a0_components"].items():
                w.writerow([r["case_id"], "A0", k, val])
            for tag in ("R", "O"):
                if r[tag]:
                    for k, val in r[tag]["components"].items():
                        w.writerow([r["case_id"], f"best_{tag}", k, val])
    # distributions
    def q(vals):
        vals = sorted(vals)
        return {"n": len(vals), "min": vals[0], "q25": vals[len(vals) // 4], "median": statistics.median(vals),
                "q75": vals[(3 * len(vals)) // 4], "max": vals[-1]}
    summ = {}
    for tag in ("R", "O"):
        av = [r[tag] for r in rows if r[tag]]
        summ[tag] = {"available": len(av), "unavailable": len(rows) - len(av),
                     "margin_bits": q([a["margin_vs_a0_bits"] for a in av]),
                     "margin_per_input_bit": q([a["margin_vs_a0_per_input_bit"] for a in av]),
                     "shorter_equal_longer_vs_a0": [sum(a["margin_vs_a0_bits"] < 0 for a in av),
                                                    sum(a["margin_vs_a0_bits"] == 0 for a in av),
                                                    sum(a["margin_vs_a0_bits"] > 0 for a in av)],
                     "byte_identical_to_a0": sum(a["byte_identical_to_a0"] for a in av),
                     "modes": dict(Counter(a["mode"] for a in av)),
                     "proposals": dict(Counter(a["proposal"] for a in av)),
                     "views_width_level": dict(Counter(f"w{a['view'][1]}-l{a['view'][0]}" for a in av)),
                     "all_decode": all(a["decodes"] for a in av), "all_hash_ok": all(a["bytes_match_hash"] for a in av)}
        tot = Counter()
        for a in av:
            for k, val in a["component_minus_a0"].items():
                tot[k] += val
        summ[tag]["component_minus_a0_sum_over_cases_bits"] = dict(sorted(tot.items()))
        summ[tag]["component_minus_a0_cases_positive"] = dict(sorted(Counter(
            k for a in av for k, val in a["component_minus_a0"].items() if val > 0).items()))
    ro = [r["R_minus_O_bits"] for r in rows if r["R_minus_O_bits"] is not None]
    summ["best_R_minus_best_O"] = {"n": len(ro), "shorter": sum(v < 0 for v in ro), "equal": sum(v == 0 for v in ro),
                                   "longer": sum(v > 0 for v in ro), "dist": q(ro)}
    summ["a0_codecs"] = dict(Counter(r["a0_info"]["codec"] for r in rows))
    summ["a0_rule_kinds_present"] = dict(Counter(k for r in rows for k in (r["a0_info"]["rule_kinds"] or {})))
    summ["unavailable"] = unavailable
    # three distinct notions, from saved summary.json and traces (counts, not recomputed searches)
    s = json.loads((D / "summary.json").read_text())
    summ["three_notions"] = {
        "within_view_R(O)_vs_O": s["mode_contributions"]["same_view_comparisons"]["R(O)_vs_O"],
        "within_view_R(P)_vs_O": s["mode_contributions"]["same_view_comparisons"]["R(P)_vs_O"],
        "within_view_P_vs_O": s["mode_contributions"]["same_view_comparisons"]["P_vs_O"],
        "best_over_views_R_vs_O_strings": [summ["best_R_minus_best_O"][k] for k in ("shorter", "equal", "longer")],
        "beats_A0_strings_R_O": [summ["R"]["shorter_equal_longer_vs_a0"][0], summ["O"]["shorter_equal_longer_vs_a0"][0]]}
    (HERE / "summary.json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: summ[k] for k in ("best_R_minus_best_O", "a0_codecs", "unavailable")}))
    for tag in ("R", "O"):
        print(tag, json.dumps({k: summ[tag][k] for k in ("margin_bits", "shorter_equal_longer_vs_a0",
                                                         "byte_identical_to_a0", "modes", "proposals")}))
        print(tag, "component sum minus A0:", summ[tag]["component_minus_a0_sum_over_cases_bits"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
