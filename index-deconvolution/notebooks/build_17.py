"""Builder for notebook 17 -- HID-search-v2: automatic discovery inside the unchanged
HID-v1 language, and its prospective benchmark.

Regenerates notebooks/17_hierarchy_search_v2.ipynb. Standard library to build;
executing needs the CausalBool kernel and the stored runs under
results/ (search-confirm-v2-r1, its review_closure erratum, and the HID-v1 confirm-v1-r1
summary). It may be executed from the repository root or the notebook directory.

Presentation only. The notebook READS saved artefacts (freeze, rows, archives, telemetry,
summary, claim ledger, diagnostics, the R1 diagnostic median erratum, arithmetic audit,
verification). It imports no encoder, search or corpus module: it never runs inference
and never generates strings, reserved or otherwise. The stage example is one retained
case, named by its case ID, decoded and parsed with the existing owners. Prose carries
no measured number: every number is printed by a cell. Notebook 16 and its historical
conclusion are untouched.

Presentation revision (review R1/R2, 2026-10-03): the earlier revision ran ``infer_v2``
on a constructed period-63 input and printed the frozen, upper-middle diagnostic
medians. This revision replaces that example with saved archives and displays the
corrected medians from ``review_closure/diagnostic_median_erratum.json``. The scientific
freeze and every saved scientific result are unchanged.
"""
import os
from _nblib import md, code, write_notebook, BOOTSTRAP

HERE = os.path.dirname(os.path.abspath(__file__))

SETUP = r'''
from pathlib import Path
# Explicit artefact root, whether executed from the repository root or the notebook directory.
_cands = [Path.cwd(), Path.cwd() / "index-deconvolution", Path(ROOT)]
ID_ROOT = next(p.resolve() for p in _cands
               if (p / "PROTOCOL_order_discovery.md").is_file()
               and (p / "results" / "hierarchy_search_v2" / "search-confirm-v2-r1").is_dir())
ROOT = str(ID_ROOT)
for _p in (os.path.join(os.path.dirname(ROOT), "src"), ROOT):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)
sys.modules.pop("hierarchy", None)          # a sibling repo ships a module "hierarchy"
import json, collections, hashlib
import numpy as np
import matplotlib.pyplot as plt
from hierarchy.decode import decode_archive                 # saved archives only
from hierarchy.ledger import archive_ledger, field_buckets, BUCKETS

BASE = ID_ROOT / "results" / "hierarchy_search_v2"
RUN = BASE / "search-confirm-v2-r1"
OLD = ID_ROOT / "results" / "hierarchy_v1" / "confirm-v1-r1"
ERRATUM = BASE / "review_closure" / "diagnostic_median_erratum.json"
for _a in (RUN / "freeze.json", RUN / "cases.jsonl", RUN / "diagnostics.json", OLD / "summary.json", ERRATUM):
    assert _a.is_file(), f"missing saved artefact: {_a}"
print("artefact root:", BASE)
freeze = json.loads((RUN / "freeze.json").read_text())
summary = json.loads((RUN / "summary.json").read_text())
claims = json.loads((RUN / "claim_ledger.json").read_text())
diag = json.loads((RUN / "diagnostics.json").read_text())
audit = json.loads((RUN / "arithmetic_audit.json").read_text())
verification = json.loads((RUN / "verification.json").read_text())
rows = [json.loads(x) for x in (RUN / "cases.jsonl").read_text().splitlines() if x.strip()]
by_case = collections.defaultdict(dict)
for r in rows:
    by_case[r["case_id"]][r["method"]] = r
# The six cumulative arms, ordered by the stages each one's saved telemetry declares.
_stages = {}
for r in rows:
    if r["method_kind"] == "hid_v2" and r.get("search_counters"):
        _stages.setdefault(r["method"], tuple(r["search_counters"]["stages_included"]))
ARM_ORDER = sorted(_stages, key=lambda m: len(_stages[m]))
assert [len(_stages[m]) for m in ARM_ORDER] == [1, 2, 3, 4, 5, 6]
print("run:", freeze["run_id"], "| study:", freeze["study"], "| frozen", freeze["frozen_at_utc"])
print("rows:", len(rows), "| cases:", len(by_case),
      "| engineering:", summary["engineering_status"], "| complete:", summary["study_complete"])
'''.strip()

cells = [
md(r"""
# 17 — HID-search-v2: better automatic proposals in the same exact language

Notebook 16 ended with a **negative** prespecified result: the HID-v1 search did not beat
the nine-codec portfolio on the structured confirmation population, although every
archive decoded exactly. A post-hoc probe (bitacora 39) then found short, legal,
input-only descriptions on noisy-period strings that the frozen search had missed.

This notebook presents the prospective test of that lead. The wire format, decoder,
baselines, generators and the legacy search are **unchanged**; only the proposals are
new, and every arm pays for its own complete computation, including a fresh legacy run.
Everything below is read from saved artefacts.
"""),
code(BOOTSTRAP),
code(SETUP),
md(r"""
## 1. The historical result that motivated this stage

The accepted HID-v1 primary result (correctness replay `confirm-v1-r1`), read from its
stored summary. It is a valid negative result about one search, not an impossibility
theorem.
"""),
code(r"""
old = json.loads((OLD / "summary.json").read_text())["primary"]
print("HID-v1 primary verdict:", old["verdict"])
print("estimate (bits saved per input bit):", old["estimate_mean_saving_per_input_bit"])
print("95% interval:", old["ci95"])
"""),
md(r"""
## 2. Exposure status and provenance

The reserved namespaces were generated only after the freeze; the freeze records an
exposure scan of every generated artefact under the study root, the complete executable
closure (import-probe verified) and a snapshot tar.
"""),
code(r"""
print("exposure check clean:", freeze["exposure_check"]["clean"])
print("files outside the closure loaded by the import probe:", freeze["import_probe"]["outside_closure"])
print("closure files frozen:", len(freeze["source_sha256"]), "| protocol files:", len(freeze["protocol_sha256"]))
print("snapshot members:", freeze["snapshot"]["members"], "| sha256", freeze["snapshot"]["sha256"][:16], "...")
print("design:", {r: v for r, v in freeze["design"]["expected"].items()},
      "| total strings", freeze["design"]["expected_total_strings"],
      "| total rows", freeze["design"]["expected_total_rows"])
"""),
md(r"""
## 3. The six cumulative arms, on one retained case

Stages: **L** legacy search; **P** first-block template, old period grid, 1,024-bit local
patches; **C** consensus template (per-phase majority) on the same grid; **D** the other
periods up to 256; **G** one global correction list; **B** bounded input-only boundary
search. Each arm keeps the smallest complete archive; ties keep the earlier one.

The example is an **illustration, not an endpoint**. It is one confirmation case named
by its ID — the base string of the first declared replicate of F06 (the noisy-period
family on which the P, C, D and G contrasts are read) at the middle size — and was not
chosen by comparing outcomes. Nothing is encoded here: each arm's saved archive is
hash- and length-checked against its row, decoded with the independent decoder and
compared with the case's recorded input hash; stages come from the saved telemetry.
"""),
code(r"""
CASE_ID = "confirmation-F06-1024-3000-base"          # explicit retained case; illustration only
case = by_case[CASE_ID]

def saved_archive(row):
    data = (RUN / row["archive_path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row["archive_sha256"] and 8 * len(data) == row["archive_bits"]
    return data

any_row = case[ARM_ORDER[0]]
print(f"case {CASE_ID}: family {any_row['family']}, n = {any_row['n_bits']} bits, "
      f"input sha256 {any_row['input_sha256'][:16]}...")
print("portfolio (baseline_best):", case["baseline_best"]["archive_bits"], "bits via",
      case["baseline_best"]["selected_method"], "| raw envelope:", case["raw"]["archive_bits"], "bits")
for name in ARM_ORDER:
    row = case[name]
    bits = decode_archive(saved_archive(row))
    assert hashlib.sha256(bits.encode()).hexdigest() == row["input_sha256"] and len(bits) == row["n_bits"]
    t = row["search_counters"]
    print(f"{name:<20} {row['archive_bits']:>6} bits  stages {''.join(t['stages_included']):<6} "
          f"selected {t['selected_stage']:<2} detail {t.get('selected_detail')}  decodes exactly: True")
"""),
code(r"""
t = case["hid_full"]["search_counters"]
print("hid_full stage by stage (saved telemetry): best candidate bits -> incumbent after the stage")
for s in t["stages_included"]:
    st = t["stages"][s]
    best = st.get("best_candidate_bits", st.get("archive_bits"))
    work = (f"periods attempted {st['periods_attempted']}" if "periods_attempted" in st else
            f"root trials {st['counts']['root_trials']}, stop {st['stop_reason']}" if s == "B" else
            f"unique archives serialized {st['serialized_unique']}, stop {st['stop_reason']}")
    print(f"  {s}: best {best}  incumbent {st['incumbent_bits_after']} ({st['incumbent_stage_after']})  "
          f"{work}  strict improvements {st['strict_improvements']}")
data = saved_archive(case["hid_global"])
led = archive_ledger(data)
print("hid_global exact cost buckets (bits):", field_buckets(data), "| total", 8 * len(data))
for i, rule in enumerate(led["model"].rules):
    print(i, type(rule).__name__, {k: (v if not isinstance(v, (tuple, str)) or len(v) < 12 else f"<{len(v)} items>")
                                   for k, v in rule.__dict__.items()})
"""),
md(r"""
## 4. Prospective population and counts

Expected versus present rows per role, and the status of every row. Resource fallbacks
(`timeout_raw`, `rss_limit_raw`) are deployed outcomes and stay in the population.
"""),
code(r"""
v = summary["validation"]
print("expected rows", v["expected_rows"], "| present", v["present_rows"],
      "| archives checked", v["archives_checked"], "| distinct decoded", v["distinct_archives_decoded"])
for role, per in summary["status_rates"].items():
    print(role, {m: {k: c for k, c in d.items() if k != "expected"} for m, d in per.items()
                 if m.startswith("hid") or m == "baseline_best"})
print("nesting:", summary["nesting"])
"""),
md(r"""
## 5. Primary endpoint and its gates

Confirmation F01–F06, F12; three sizes; twenty paired base/ragged units per cell;
$s(x) = (\text{bits(portfolio)} - \text{bits(hid\_full)})/n$, averaged within units,
within cells, then over the 21 cells equally. Positive favours HID-search-v2.
"""),
code(r"""
p = summary["primary"]
print("gate:", {k: p["gate"][k] for k in ("engineering_valid", "complete", "censored_count", "assessable")})
print("cells", p.get("cells"), "| paired units", p.get("units"), "| strings", p.get("strings"))
print("estimate (bits per input bit):", p.get("estimate_mean_saving_per_input_bit"))
print("95% percentile interval:", p.get("ci95"))
print("VERDICT:", p["verdict"])
print("strings HID better / tied / worse:", p.get("strings_hid_better"), p.get("strings_tied"), p.get("strings_hid_worse"))
print("independent arithmetic audit:", {k: audit[k] for k in ("independent_estimate", "abs_difference", "all_checks_pass")})
"""),
code(r"""
cells = [c for c in summary["cells"]["confirmation"] if c["family"] in p["families"]]
fig, ax = plt.subplots(figsize=(9, 3.2))
labels = [f"{c['family']}\n{c['base_length']}" for c in cells]
vals = [c["vs_portfolio"].get("mean_per_input_bit", np.nan) for c in cells]
ax.bar(range(len(cells)), vals, color=["#4c72b0" if v >= 0 else "#c44e52" for v in vals])
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(range(len(cells)), labels, fontsize=7)
ax.set_ylabel("saved bits per input bit\n(portfolio − hid_full)")
ax.set_title(f"Primary cells: mean over 20 paired units each (n = {sum(c['vs_portfolio']['units_complete'] for c in cells)} units)", fontsize=9)
plt.tight_layout(); plt.show()
"""),
md(r"""
## 6. Five targeted cumulative contrasts (99% intervals)

Each contrast adds one stage and is read on its target family only (F06 for P, C, D, G;
F12 for B), from one joint bootstrap draw. They are cumulative algorithm changes,
including their cost: not additive, not pure mechanism effects, and a positive contrast
cannot rescue a negative primary result.
"""),
code(r"""
for k, c in summary["contrasts"].items():
    print(f"{k:<12} {c['family']}  estimate {c.get('estimate_per_input_bit')}  99% CI {c.get('ci99')}  "
          f"reading {c['reading']}  units {c.get('units')}")
"""),
md(r"""
## 7. Descriptive transfer and parameter-shift stress (no verdicts)
"""),
code(r"""
for key in ("all_family_confirmation", "structured_transfer", "all_stress"):
    t = summary.get(key) or {}
    print(f"{key:<25} vs portfolio {t.get('full_vs_portfolio')} CI {t.get('full_vs_portfolio_ci95')} | "
          f"vs legacy {t.get('full_vs_legacy')} | units {t.get('units')} of {t.get('required_units')}")
print("structured transfer by size:", json.dumps(summary["transfer_by_size"], indent=0))
for c in summary["cells"].get("stress", []):
    print("stress", c["family"], c["base_length"], "vs portfolio", c["vs_portfolio"].get("mean_per_input_bit"),
          "| vs legacy", c["vs_legacy"].get("mean_per_input_bit"))
"""),
md(r"""
## 8. Where the bits go: exact cost components

Every deployed archive is cut into exhaustive, mutually exclusive field buckets whose sum
is exactly 8 × its byte length. Removing a bucket "on paper" is not a deployable code.
"""),
code(r"""
for k, c in summary["cost_components"].items():
    if not isinstance(c, dict) or "mean_bits" not in c:
        continue
    mb = c["mean_bits"]
    print(f"{k:<34} archives {c['archives']:>4}  mean total {c['mean_total_bits']:>9.1f}  " +
          "  ".join(f"{b[:10]}={mb[b]:.0f}" for b in BUCKETS))
"""),
md(r"""
## 9. Stage yield and resource events
"""),
code(r"""
for k, t in summary["stage_telemetry"].items():
    if k.startswith("confirmation|hid_full") or k.startswith("transfer|hid_full") or k.startswith("stress|hid_full"):
        print(k, "| rows", t["rows"], "| selected", t["selected_stage"],
              "| B caps", t["B_cap_hit"], "| B stops", t["B_stop_reason"])
print("resource nesting breaks:", summary["nesting"]["resource_nesting_break_count"])
res = summary["resources"]
for m in ARM_ORDER:
    r_ = res.get(m, {})
    print(f"{m:<20} median encode {r_.get('encode_s_median')}  max {r_.get('encode_s_max')}  peak RSS MB {r_.get('peak_rss_mb_max')}")
"""),
md(r"""
## 10. Supplied-boundary references: a restricted, evaluation-only diagnostic

For F12 and S02 strings the generator's construction cuts, mapped through its edits,
are used — after automatic encoding — to build one feasible partition with the same
leaf builder. Gap = (bits(hid_full) − min(reference, raw))/n, in bits per input bit;
negative means the automatic archive is shorter. This is not an oracle optimum and not
a bound on search error; it is never an incumbent.

**Erratum R1 (diagnostic only).** The frozen diagnostics reported the upper middle
observation as the median of an even-sized cell. The medians below are the conventional
sample medians from the identified erratum, derived from the saved reference records;
the stored value is shown beside each corrected one. Means, counts and signs are
unchanged, and no primary, contrast or descriptive result depends on these medians.
"""),
code(r"""
sb = diag["supplied_boundary_references"]
err = json.loads(ERRATUM.read_text())
assert err["run_id"] == freeze["run_id"] and err["all_checks_pass"]
assert err["freeze_sha256"] == (RUN / "freeze.sha256").read_text().split()[0]
for rel, h in err["input_sha256"].items():               # the erratum describes these exact bytes
    p = ID_ROOT.parent / rel
    assert hashlib.sha256(p.read_bytes()).hexdigest() == h, rel
print(sb["label"])
print("strings", sb["strings"], "| references available", sb["available"])
print("erratum:", ERRATUM.name, "| cells", err["cells_total"], "| medians corrected", err["cells_changed"])
for k, v in sb["by_cell"].items():
    e = err["cells"][k]
    assert all(v[f] == e["unchanged_quantities"][f] for f in e["unchanged_quantities"])
    assert e["original_gap_median"] == v["gap_median"]
    tag = f"CORRECTED (stored {v['gap_median']})" if e["changed"] else "unchanged"
    print(f"{k:<22} n {e['n_gaps']:>2}  gap mean {v['gap_mean']}  median {e['corrected_gap_median']}  [{tag}]  "
          f"auto shorter {v['automatic_shorter_than_reference']}  longer {v['automatic_longer_than_reference']}  ties {v['ties']}")
"""),
md(r"""
## 11. Verification and claim ledger

The record shown is the run directory's current `verification.json`; the cell states
whether it is byte-identical to the supervisor's retained `verify --full` record. Its
"notebook 17" line describes the notebook revision that existed when that verification
ran, not this presentation revision, whose execution checks are kept with the review
closure.
"""),
code(r"""
_vf = BASE / "supervision" / "verification_full.json"
print("verification.json identical to supervision/verification_full.json:",
      _vf.is_file() and _vf.read_bytes() == (RUN / "verification.json").read_bytes(),
      "| finished", verification.get("finished_utc"))
print("verification:", {k: verification.get(k) for k in ("engineering_status", "completeness", "exit_code")})
for c_ in verification.get("commands", []):
    print(f"  {c_['name']:<22} exit {c_['exit_code']}  {c_['tail'][-1] if c_['tail'] else ''}")
for c_ in claims:
    print(f"{c_['id']:<5} {c_['status']:<14} {c_['claim'][:100]}")
"""),
md(r"""
## What this study can and cannot say

* **Fresh instances, familiar generators.** The confirmation strings are new draws of the
  twelve declared families; this is not generalisation to unfamiliar structure.
* **One language, one resource policy.** Every number is a complete archive length under
  the unchanged HID-v1 format and the frozen budgets; it is not $K$, not a minimum over all
  programs, and not generator identification.
* **Contrasts are cumulative and costed.** A stage's contrast measures adding it to the
  previous arm under the same external limits, not a pure or additive mechanism effect.
* **Boundary references are restricted.** They use supplied metadata after encoding and a
  shortest-period leaf heuristic; they neither bound search error nor serve as a method.
"""),
]

write_notebook(cells, os.path.join(HERE, "17_hierarchy_search_v2.ipynb"))
