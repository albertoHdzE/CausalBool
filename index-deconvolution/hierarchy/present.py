"""Presentation only (outside the frozen sources): markdown tables and handoff artefacts.

Reads a stored run and writes ``report_tables.md`` and ``handoff_artifacts.json`` into
it. Every number comes from summary.json, claim_ledger.json, diagnostics.json, the rows
and the archive bytes; nothing is recomputed except decoding and hashing.

    PYTHONPATH=index-deconvolution:src python -m hierarchy.present --run-id confirm-v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .benchmark import run_dir
from .corpus import generate_unit
from .decode import decode_archive
from .ledger import archive_ledger, explain_model
from .report import STRUCTURED, load_rows


def _f(x, fmt="{:+.4f}"):
    return "—" if x is None else fmt.format(x)


def _ci(ci, fmt="{:+.4f}"):
    return f"[{fmt.format(ci[0])}, {fmt.format(ci[1])}]"


def _bits(case_id: str) -> str:
    split, fam, bl, rep, kind = case_id.split("-")
    full, _ = generate_unit(split, fam, int(bl), int(rep))
    return full if kind == "ragged" else full[:int(bl)]


def tables(d: Path) -> str:
    s = json.loads((d / "summary.json").read_text())
    led = json.loads((d / "claim_ledger.json").read_text())
    diag = json.loads((d / "diagnostics.json").read_text())
    out = []
    p = s["primary"]
    out.append("### Primary endpoint (confirmation, structured families F01–F06, F12)\n")
    out.append("| quantity | value |\n|---|---|")
    out.append(f"| evidence validity / completeness / censored baseline rows | "
               f"{p['evidence_validity']} / {p['evidence_completeness']} / {p['censored_baselines']} |")
    out.append(f"| declared units / available units | {p['required_units']} / {p['available_units']} |")
    if "estimate_mean_saving_per_input_bit" not in p:
        pd = p.get("partial_diagnostic") or {}
        out.append(f"| PARTIAL diagnostic (not the endpoint) | {_f(pd.get('estimate'), '{:+.5f}')} "
                   f"{_ci(pd['interval'], '{:+.5f}') if pd else ''} |")
        out.append(f"| **verdict** | **{p['verdict']}** |\n")
        return "\n".join(out) + "\n"
    out.append(f"| equal-weight mean saving per input bit | {_f(p['estimate_mean_saving_per_input_bit'], '{:+.5f}')} |")
    out.append(f"| 95% percentile bootstrap CI (10,000, seed 33001) | {_ci(p['ci95'], '{:+.5f}')} |")
    out.append(f"| cells / units / scored strings | {p['cells']} / {p['units']} / {p['strings']} |")
    out.append(f"| mean / median saving (bits per string) | {p['mean_saving_bits']:+.1f} / {p['median_saving_bits']:+.1f} |")
    out.append(f"| strings HID better / tied / worse | {p['strings_hid_better']} / {p['strings_tied']} / {p['strings_hid_worse']} |")
    out.append(f"| units missing; baseline rows not ok | {len(p['units_missing'])}; {len(p['baseline_not_ok'])} |")
    out.append(f"| **verdict** | **{p['verdict']}** |\n")
    out.append("### Every family and size, confirmation (descriptive 95% CIs)\n")
    out.append("| family | base | units | mean saving/bit | 95% CI | median bits | HID better/tied/worse |\n|---|---:|---:|---:|---|---:|---|")
    for r in s["families_confirmation"]:
        tag = " (structured)" if r["family"] in STRUCTURED else ""
        out.append(f"| {r['family']}{tag} | {r['base_length']} | {r['units_complete']} | "
                   f"{_f(r.get('mean_saving_per_input_bit'))} | {_ci(r['ci95_descriptive'])} | "
                   f"{r['median_saving_bits']:+.1f} | {r['strings_hid_better']}/{r['strings_tied']}/{r['strings_hid_worse']} |")
    out.append("\n### Ablations (structured confirmation population; 99% CIs, seed 33002)\n")
    out.append("| arm | (ablation − full) bits per input bit | 99% CI | reading |\n|---|---:|---|---|")
    for a, v in s["ablations"].items():
        out.append(f"| {a} | {v['incremental_gain_per_input_bit']:+.5f} | {_ci(v['ci99'], '{:+.5f}')} | {v['component_advantage']} |")
    t = s["transfer_structured_aggregate"]
    out.append("\n### Transfer (descriptive; four units per cell)\n")
    out.append(f"Structured aggregate: {t['estimate']:+.5f} per input bit, 95% CI {_ci(t['ci95_descriptive'], '{:+.5f}')}.\n")
    out.append("| family | base | mean saving/bit | 95% CI | median bits | better/tied/worse |\n|---|---:|---:|---|---:|---|")
    for r in s["transfer"]:
        out.append(f"| {r['family']} | {r['base_length']} | {_f(r.get('mean_saving_per_input_bit'), '{:+.5f}')} | "
                   f"{_ci(r['ci95_descriptive'], '{:+.5f}')} | {r['median_saving_bits']:+.1f} | "
                   f"{r['strings_hid_better']}/{r['strings_tied']}/{r['strings_hid_worse']} |")
    c = s["controls_aggregate"]
    out.append(f"\nStatistical controls F07–F09 (confirmation, descriptive, equal-weight aggregate "
               f"against the nine-code portfolio, seed {c['seed']}): {c['estimate']:+.5f} per input bit, "
               f"95% CI {_ci(c['ci95_descriptive'], '{:+.5f}')}.\n")
    a12 = s["all_families_confirmation_aggregate"]
    out.append(f"All twelve families, confirmation (descriptive, not the primary population, seed "
               f"{a12['seed']}): {a12['estimate']:+.5f} per input bit, 95% CI "
               f"{_ci(a12['ci95_descriptive'], '{:+.5f}')}.\n")
    out.append("Controls against the better of the two statistical codes alone, min(bernoulli, "
               "context) − hid_full (descriptive, unweighted string means):\n")
    out.append("| family | strings | mean saving/bit | HID shorter / tied / longer |\n|---|---:|---:|---|")
    for f, v in s["controls_vs_statistical_codes"].items():
        out.append(f"| {f} | {v['strings']} | {_f(v['mean_saving_per_input_bit_unweighted'], '{:+.5f}')} | "
                   f"{v['strings_hid_shorter']} / {v['strings_tied']} / {v['strings_hid_longer']} |")
    out.append("")
    out.append("### BDM diagnostics (replicate 1000, 1,024 bits, 199 marginal-preserving shuffles)\n")
    out.append("| object | adaptive p | Holm-adjusted | reject at 0.05 | selected configuration |\n|---|---:|---:|---|---|")
    for f, o in diag["objects"].items():
        h = diag["holm"][f]
        cfg = o["selected_config"]
        out.append(f"| {f} | {o['adaptive_p']:.3f} | {h['holm_adjusted']:.3f} | {h['reject_at_0.05']} | "
                   f"b={cfg['block']}, {cfg['boundary']}, r={cfg['rotation']} |")
    out.append(f"\nClaim status: {diag['claim_status']} (structured objects rejected after Holm: "
               f"{', '.join(diag['claim_detail']['structured_rejected_after_holm'])}).\n")
    out.append("### Claim ledger\n")
    out.append("| id | status | claim | estimate | uncertainty | evidence gate |\n|---|---|---|---|---|---|")
    for c in led:
        est = c["estimate"]
        est = f"{est:+.5f}" if isinstance(est, float) else ("—" if est is None else "see file")
        unc = c["uncertainty"]
        unc = _ci(unc, "{:+.5f}") if isinstance(unc, list) else ("—" if unc is None else str(unc))
        out.append(f"| {c['id']} | {c['status']} | {c['claim']} | {est} | {unc} | "
                   f"{c.get('evidence_gate') or '—'} |")
    out.append("\n### Completeness and resources\n")
    out.append("| split | method rows expected | present | ok | non-ok |\n|---|---:|---:|---:|---:|")
    for split, per in s["status_counts"].items():
        exp = sum(v["expected"] for v in per.values())
        pres = sum(v["present"] for v in per.values())
        ok = sum(v.get("ok", 0) for v in per.values())
        out.append(f"| {split} | {exp} | {pres} | {ok} | {pres - ok} |")
    out.append("\n| method | median encode s | max encode s | total encode s | total worker s | max RSS MB |\n|---|---:|---:|---:|---:|---:|")
    for m, v in s["resources"].items():
        out.append(f"| {m} | {v['encode_s_median']:.3f} | {v['encode_s_max']:.2f} | {v['encode_s_total']:.1f} | "
                   f"{v['worker_s_total']:.1f} | {v['peak_rss_mb_max']:.1f} |")
    budget = json.loads((d / "budget.json").read_text())
    out.append(f"\nWall-clock budget used: {budget['used_s']:.0f} s of {budget['total_s']:.0f} s.")
    return "\n".join(out) + "\n"


def artefact(d: Path, rows_by: dict, case_id: str, method: str, why: str) -> dict:
    r = rows_by[case_id][method]
    data = (d / r["archive_path"]).read_bytes()
    bits = _bits(case_id)
    decoded = decode_archive(data)
    led = archive_ledger(data)
    item = {"why": why, "case_id": case_id, "method": method, "n_bits": len(bits),
            "input_sha256": hashlib.sha256(bits.encode()).hexdigest(),
            "row_input_sha256": r["input_sha256"], "archive_path": r["archive_path"],
            "archive_sha256": hashlib.sha256(data).hexdigest(), "archive_bits": 8 * len(data),
            "row_archive_bits": r["archive_bits"], "decoded_equals_input": decoded == bits,
            "codec": led["codec"], "ledger_sum_bits": 8 * sum(f["bytes"] for f in led["fields"]),
            "bytes_by_owner": led["bytes_by_owner"], "fields": led["fields"],
            "baseline_best_bits": rows_by[case_id]["baseline_best"]["archive_bits"],
            "baseline_best_method": rows_by[case_id]["baseline_best"]["selected_method"],
            "raw_archive_bits": r["raw_archive_bits"], "stop_reason": r["stop_reason"],
            "best_source": r["best_source"]}
    if led["model"] is not None:
        item["graph"] = explain_model(led["model"])
    return item


def artefacts_md(d: Path) -> str:
    """Markdown for the handoff's representative artefacts, from handoff_artifacts.json."""
    arts = json.loads((d / "handoff_artifacts.json").read_text())
    out = []
    for i, a in enumerate(arts, 1):
        out.append(f"#### A{i}. {a['why']}\n")
        if "case_id" in a:
            out.append(f"- case `{a['case_id']}`, method `{a['method']}`, n = {a['n_bits']} bits")
            out.append(f"- input sha256 `{a['input_sha256']}` (regenerated; row says `{a['row_input_sha256'][:16]}…`)")
            out.append(f"- archive `{a['archive_path']}`, sha256 `{a['archive_sha256']}`")
            out.append(f"- archive {a['archive_bits']} bits (row {a['row_archive_bits']}); raw archive "
                       f"{a['raw_archive_bits']} bits; portfolio {a['baseline_best_bits']} bits "
                       f"({a['baseline_best_method']}); search stop `{a['stop_reason']}`, source `{a['best_source']}`")
        else:
            out.append(f"- target: 64 ones; oracle program `{a['oracle_program']}`; raw {a['raw_bits']} bits; "
                       f"restricted search {a['restricted_search_bits']} bits; full search {a['full_search_bits']} bits")
            out.append(f"- input sha256 `{a['input_sha256']}`, archive sha256 `{a['archive_sha256']}`")
        out.append(f"- decoded by `decode.py` equals the input: **{a['decoded_equals_input']}**; "
                   f"ledger sum {a['ledger_sum_bits']} bits = archive {a['archive_bits']} bits")
        if a.get("graph"):
            out.append("- graph (read back from the archive bytes):\n")
            out.append("  | id | op | length | refs | detail |\n  |---:|---|---:|---:|---|")
            for g in a["graph"]:
                det = {k: v for k, v in g.items() if k not in ("id", "op", "length", "referenced_by",
                                                              "expansion_prefix")}
                if "bits" in det and len(det["bits"]) > 40:
                    det["bits"] = det["bits"][:40] + "…"
                if "positions" in det:
                    det["positions"] = f"{len(det['positions'])} shown of {det.get('flips')}"
                out.append(f"  | {g['id']} | {g['op']} | {g['length']} | {g['referenced_by']} | "
                           f"{json.dumps(det)[:160]} |")
        if len(a["fields"]) <= 40:
            out.append("\n- exact byte ledger:\n")
            out.append("  | owner | field | bytes | hex |\n  |---|---|---:|---|")
            for f in a["fields"]:
                out.append(f"  | {f['owner']} | {f['field']} | {f['bytes']} | `{f['hex'][:48]}` |")
        else:
            by = {}
            for f in a["fields"]:
                by[f["owner"]] = by.get(f["owner"], 0) + f["bytes"]
            out.append(f"\n- exact byte ledger, summed per record ({len(a['fields'])} fields in "
                       f"`handoff_artifacts.json`): " + ", ".join(f"{k} {v}" for k, v in by.items())
                       + f" — total {sum(by.values())} bytes")
        out.append("")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args(argv)
    d = run_dir(a.run_id)
    (d / "report_tables.md").write_text(tables(d))
    rows = load_rows(d)
    by: dict = {}
    for r in rows:
        by.setdefault(r["case_id"], {})[r["method"]] = r
    conf = [c for c in by if c.startswith("confirmation-")]

    def saving(c):
        return by[c]["baseline_best"]["archive_bits"] - by[c]["hid_full"]["archive_bits"]
    success = max((c for c in conf if by[c]["hid_full"]["rule_count"] and by[c]["hid_full"]["rule_count"] >= 3
                   and by[c]["hid_full"]["family"] in STRUCTURED), key=lambda c: (saving(c), c))
    loss = min((c for c in conf if by[c]["hid_full"]["family"] in STRUCTURED), key=lambda c: (saving(c), c))
    fallback = sorted(c for c in conf if by[c]["hid_full"]["family"] == "F06"
                      and by[c]["hid_full"]["selected_codec_id"] == 0)
    arts = [artefact(d, by, success, "hid_full", "automatically inferred success: largest saving "
                     "among structured confirmation strings with >= 3 rules"),
            artefact(d, by, loss, "hid_full", "baseline loss: largest loss among structured "
                     "confirmation strings"),
            artefact(d, by, loss, "baseline_best", "the portfolio archive that wins that loss")]
    if fallback:
        arts.append(artefact(d, by, fallback[0], "hid_full", "noise case with literal fallback: "
                             "first F06 confirmation string where HID returned raw mode"))
    oracle_path = d.parent / "development" / "dev-v1" / "oracle.json"
    orc = json.loads(oracle_path.read_text())
    ex = [e for e in orc["tables"]["generated_le_64_leaves_1_4"]["examples"] if e["target"] == "1" * 64][0]
    data = bytes.fromhex(ex["grammar_only_archive_hex"])
    led = archive_ledger(data)
    arts.append({"why": "tiny oracle case: 64 identical bits, repetition beats the raw envelope",
                 "target": "1" * 64, "oracle_program": ex["grammar_only_program"],
                 "input_sha256": hashlib.sha256(("1" * 64).encode()).hexdigest(),
                 "archive_sha256": hashlib.sha256(data).hexdigest(), "archive_bits": 8 * len(data),
                 "raw_bits": ex["raw_bits"], "restricted_search_bits": ex["restricted_bits"],
                 "full_search_bits": ex["full_bits"],
                 "decoded_equals_input": decode_archive(data) == "1" * 64,
                 "ledger_sum_bits": 8 * sum(f["bytes"] for f in led["fields"]),
                 "fields": led["fields"], "graph": explain_model(led["model"])})
    (d / "handoff_artifacts.json").write_text(json.dumps(arts, indent=1))
    (d / "handoff_artifacts.md").write_text(artefacts_md(d))
    for x in arts:
        print(x["why"], "|", x.get("case_id", x.get("target", "")[:16]), "|", x["archive_bits"], "bits |",
              "ledger", x["ledger_sum_bits"], "| decoded", x["decoded_equals_input"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
