"""Builder for notebook 22 -- HID dictionary relations v1: paid periods and relations.

Regenerates notebooks/22_hierarchy_dictionary.ipynb. Standard library to build;
executing needs the CausalBool kernel and the saved run
results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1. Runs from the repository
root or the notebook directory. Output path: $NB22_OUT, default next to this builder.

Artifact-only. The notebook READS saved rows, archives, traces, tables and ledgers; it
imports only ``hierarchy.decode`` and ``hierarchy.ledger`` to re-check and explain saved
archive bytes. It runs no search, no encoder, no generator, no BDM and no job, and writes
nothing. Prose carries no measured number: every number is printed by a cell from a saved
artifact.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_d = HERE
while not os.path.isfile(os.path.join(_d, "PROTOCOL_order_discovery.md")):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, "notebooks"))               # the shared _nblib owner
from _nblib import BOOTSTRAP, code, md, write_notebook  # noqa: E402

SETUP = r'''
from pathlib import Path
_cands = [Path.cwd(), Path.cwd() / "index-deconvolution", Path(ROOT)]
ID_ROOT = next(p.resolve() for p in _cands
               if (p / "PROTOCOL_order_discovery.md").is_file()
               and (p / "results" / "hierarchy_dictionary_v1" / "dictionary-feasibility-v1-r1").is_dir())
ROOT = str(ID_ROOT)
for _p in (os.path.join(os.path.dirname(ROOT), "src"), ROOT):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)
sys.modules.pop("hierarchy", None)          # a sibling repo ships a module "hierarchy"
import json, hashlib, csv, collections, statistics
import numpy as np
import matplotlib.pyplot as plt
from hierarchy.decode import decode_archive                 # saved archives only
from hierarchy.ledger import archive_ledger                 # field ledger of saved bytes

RUN = ID_ROOT / "results" / "hierarchy_dictionary_v1" / "dictionary-feasibility-v1-r1"
def load(p):
    return json.loads(Path(p).read_text())
summary, decision = load(RUN / "summary.json"), load(RUN / "DECISION.json")
verification, audit = load(RUN / "verification.json"), load(RUN / "arithmetic_audit.json")
lock_sha = (RUN / "implementation_lock.sha256").read_text().strip()
def table(name):
    with open(RUN / "tables" / name) as fh:
        return list(csv.DictReader(fh))
views, gmap = table("views_D2.csv"), table("gap_map_D2.csv")
def num(x):
    return None if x in ("", "None", None) else float(x)
def arc(h):
    return (RUN / "archives" / h[:2] / f"{h}.isd").read_bytes()
print("lock:", lock_sha[:16], "| engineering verdict:", decision["engineering_verdict"],
      "| label:", decision["recommendation"])
print("verification pass:", verification["verification_pass"], "| audit pass:", audit["pass"],
      "| archives re-read by the audit:", audit["archives_read"], "| decodes:", audit["decodes"])
'''

cells = [
md(r"""
# 22 · HID dictionary relations v1: do paid periods and word relations pay?

**Question.** Notebook 21 found that multilevel word dictionaries never paid for
themselves against the accepted k = 1 archive (A0). Many dictionary words, however, are
internally periodic or are near-copies (complement, reversal, a few flipped bits) of an
earlier word. If those words are *described through* a period or an earlier word, and
the description is paid inside the same complete archive, does any proposal become
shorter than A0?

**Design.** Same 96 exposed strings, same views (8 widths × 2 origins × 4 levels, now
*without* branch pruning) and the same proposals G0–G3. Four dictionary modes per view:
**O** the original words; **P** a word with an exact dividing period becomes
REPEAT(period base); **R(O)/R(P)** each word may be the first eligible relation to one of
the eight preceding words (complement/reversal, then at most 8 paid bit flips, relation
chains at most 8 deep). Arms: A0 (k = 1), D0 = O, D1 = O + P, D2 = O + P + R(O) + R(P).
Every candidate is a full-input archive decoded independently; ties keep A0.

Exploratory and descriptive, on exposed data: no interval, no test, no confirmation,
no fractal or causal claim. Run the first cell first.
"""),
code(BOOTSTRAP),
code(SETUP),
md(r"""
## 1. Completeness and the headline

Counts, the evidence state and the fixed label are read from `summary.json`. The label is
evaluated in the protocol's order: relation gain (D2 < D1 anywhere), then period gain
(D1 < D0), then control-only gain (D0 < A0), else no retained gain.
"""),
code(r"""
for k, v in summary["counts"].items():
    print(f"{k:34s} {v}")
rec = summary["recommendation"]
print()
print("label:", rec["label"])
for k in ("d2_beats_d1_cases", "d1_beats_d0_cases", "d0_beats_a0_cases", "d2_beats_a0_cases"):
    print(f"  {k:20s} {len(rec[k])} of {summary['counts']['strings']}")
"""),
md(r"""
## 2. Contrasts, with their reference points in the same table

saving(X, Y) = (bits(Y) − bits(X)) / n, positive when X is shorter; averaged base/ragged,
then replicates (48 pairs), then the 24 family-length cells equally. The A0 rows are the
reference distribution against which every arm is read.
"""),
code(r"""
print(f"{'contrast':22s} {'equal-cell mean':>16s}  strings b/t/w (of)   pairs b/t/w    cells b/t/w")
for k, v in summary["contrasts"].items():
    s, p, c = v["strings"], v["pairs_sign"], v["cells_sign"]
    print(f"{k:22s} {v['aggregate']:16.6f}  {s['better']:3d}/{s['tie']:3d}/{s['worse']:3d} ({s['available']})  "
          f"{p['better']:2d}/{p['tie']:2d}/{p['worse']:2d}       {c['better']:2d}/{c['tie']:2d}/{c['worse']:2d}")
"""),
md(r"""
## 3. Rendering the object: the closest a relation mode came

For every string, the shortest R(O) archive over all views is compared with A0. The
closest case in which relations were actually used, and shortened the view's own O
proposal, is opened below: its words (hex), the relations chosen, the archive length
of each mode in that view, and the byte ledgers of the saved relation archive and of A0.
A relation can make a view's own proposal much shorter than its O proposal and still not
beat A0; equal length is a tie, and ties keep A0.
"""),
code(r"""
per = summary["mode_contributions"]["per_string"]
gap = sorted(((r["best_bits_by_mode"]["R(O)"] - r["a0_bits"]), c) for c, r in per.items())
print("strings:", len(gap), "| min (R(O) best − A0) bits:", gap[0][0],
      "| median:", statistics.median(g for g, _ in gap), "| max:", gap[-1][0])
for m in ("O", "P", "R(O)", "R(P)"):
    rel = sorted((r["best_bits_by_mode"][m] - r["a0_bits"]) / r["a0_bits"] for r in per.values())
    print(f"  mode {m:5s} relative excess of the best view over A0: min {rel[0]:.4f}  median "
          f"{statistics.median(rel):.4f}  max {rel[-1]:.3f}  (of {len(rel)})")
# closest view, over all strings, in which R(O) used relations and beat that view's O
cand = [r for r in views if r["status"] == "EVALUATED" and num(r["relations_R(O)"])
        and num(r["R(O)_minus_O"]) is not None and num(r["R(O)_minus_O"]) < 0]
print("views where R(O) used relations and beat the same view's O:", len(cand), "of",
      sum(r["status"] == "EVALUATED" for r in views))
pick = min(cand, key=lambda r: (num(r["R(O)_best"]) - num(r["a0_bits"]), r["case_id"],
                                int(r["level"]), int(r["width"]), int(r["origin"])))
row0 = load(RUN / "rows" / f"{pick['case_id']}.D2.json")
tr = load(RUN / row0["trace_path"])
v = next(v for v in tr["views"] if (str(v["level"]), str(v["width"]), str(v["origin"])) ==
         (pick["level"], pick["width"], pick["origin"]))
m = next(mm for mm in v["modes"] if mm["mode"] == "R(O)")
print("\ncase:", row0["case_id"], "| view: width", v["width"], "level", v["level"], "origin", v["origin"],
      "| m =", v["m"], "k =", v["k"], "| A0 bits", row0["a0_archive_bits"])
for mm in v["modes"]:
    print(f"  mode {mm['mode']:5s} best {mm['best_bits']} bits ({mm['best_proposal']})  minus O: {mm['minus_O_bits']}")
words = v["dictionary"]
for w in words[:8]:
    print("  word", w["symbol"], hex(int(w["word"], 2)) if "word" in w else w)
for r in m["construction"]["relations"]:
    print("  relation:", r)
"""),
code(r"""
data, a0 = arc(m["best_sha256"]), arc(row0["a0_archive_sha256"])
x_sha = row0["input_sha256"]
print("relation archive decodes to the input:", hashlib.sha256(decode_archive(data).encode()).hexdigest() == x_sha,
      "| A0 decodes to the input:", hashlib.sha256(decode_archive(a0).encode()).hexdigest() == x_sha)
for name, b in (("R(O) candidate", data), ("A0", a0)):
    led = archive_ledger(b)
    kinds = collections.Counter()
    if led["model"] is not None:
        names = {f"rule{i}": type(r).__name__.upper() for i, r in enumerate(led["model"].rules)}
        for f in led["fields"]:
            kinds[names.get(f["owner"], f["owner"])] += f["bytes"]
    print(f"{name:15s} {len(b):4d} bytes | ledger sums to {sum(f['bytes'] for f in led['fields'])} | "
          f"codec {led['codec']} | bytes by rule kind {dict(kinds)}")
print("deployed D2 composite is A0:", row0["archive_sha256"] == row0["a0_archive_sha256"])
"""),
md(r"""
## 4. Same-view mode comparisons and the width-by-level map

Each comparison below pairs two modes *of the same view* (same words, same top stream,
same gaps, same factory), so the only difference is how the dictionary words are
described. The map pools 96 strings × 2 origins per cell; no view is pruned in this
phase, and the column "old mask would skip" counts views multilevel-v1 never evaluated.
"""),
code(r"""
mc = summary["mode_contributions"]
print(f"{'comparison':12s} {'shorter':>8s} {'equal':>8s} {'longer':>8s}   (denominator)")
for k, c in mc["same_view_comparisons"].items():
    print(f"{k:12s} {c.get('shorter', 0):8d} {c.get('equal', 0):8d} {c.get('longer', 0):8d}   "
          f"({mc['same_view_denominators'][k]})")
print("\nper view, the best archive of each mode against A0:", mc["view_mode_best_vs_a0"])
print("strings where a mode's best view beats the best O view:", mc["strings_where_mode_best_beats_O_best"])
"""),
code(r"""
W = sorted({int(g["width"]) for g in gmap}); Lv = sorted({int(g["level"]) for g in gmap})
def grid(key):
    M = np.full((len(Lv), len(W)), np.nan)
    for g in gmap:
        val = num(g[key])
        if val is not None:
            M[Lv.index(int(g["level"])), W.index(int(g["width"]))] = val
    return M
panels = [("views_P_shorter_than_O", "views P < O (same view)"),
          ("views_RO_shorter_than_O", "views R(O) < O (same view)"),
          ("median_RO_minus_O_bits", "median R(O) − O bits"),
          ("median_best_minus_a0_per_bit", "median (best − A0)/n")]
fig, axes = plt.subplots(1, 4, figsize=(18, 3.6))
for ax, (key, title) in zip(axes, panels):
    M = grid(key)
    im = ax.imshow(M, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(W)), W); ax.set_yticks(range(len(Lv)), Lv)
    ax.set_xlabel("word width b"); ax.set_ylabel("level"); ax.set_title(title)
    for i in range(len(Lv)):
        for j in range(len(W)):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}" if "median" in key else f"{int(M[i, j])}",
                        ha="center", va="center", fontsize=7, color="w")
    fig.colorbar(im, ax=ax, shrink=0.8)
plt.tight_layout(); plt.show()
print("cells:", len(gmap), "| evaluated view instances:", sum(int(g["evaluated"]) for g in gmap),
      "| views whose best archive is shorter than A0:", sum(int(g["views_best_shorter_than_a0"]) for g in gmap))
"""),
md(r"""
## 5. What the dictionary constructions contained

Counts of periodic replacements and of selected relations (flags: 1 complement, 2
reversal, 3 both; flips are paid patch positions; hops are relation-chain depth, capped
at 8). These describe the dictionaries; they are not savings.
"""),
code(r"""
con = summary["construction"]
for k, v in con["counts"].items():
    print(f"{k:34s} {v}")
print("relation flags:", con["relation_flags"])
print("relation flip counts:", con["relation_flip_counts"])
print("relation hops:", con["relation_hops"])
for arm in ("D0", "D1", "D2"):
    c = summary["workload"][arm]["counters"]
    print(f"{arm}: requests {c['requests']}, serialized {c['serialized']}, decoded {c['decoded']}, "
          f"duplicates {c['duplicates']}, patch rejections {c['patch_rejections']}, graph rejections "
          f"{c['graph_rejections']}, relation comparisons {c['relation_comparisons']}")
"""),
md(r"""
## 6. Engineering invariants, the old A3 comparison and every attempt

The nesting checks (D0 ≤ old A3, D1 ≤ D0, D2 ≤ D1, and every old-A3 view reproduced byte
for byte in D0's O mode) are invariants of the construction on complete searches, not
evidence of benefit. Failed development attempts are retained and listed.
"""),
code(r"""
print("nesting:", summary["nesting"]["checked"], "| violations:", len(summary["nesting"]["violations"]))
print("audit problems:", audit["problem_count"], "| candidate archives re-decoded:", audit["candidate_archives_checked"])
for line in (RUN / "ledger" / "attempts.jsonl").read_text().splitlines():
    a = json.loads(line)
    print(f"- {a['attempt']:14s} {a['result']}")
"""),
md(r"""
## 7. What it cost

Physical totals count each job once. The attributed deployment cost charges the single
A0 run in full to every composite, so no composite is cheaper than A0.
"""),
code(r"""
rt = summary["runtime"]
print("A0 worker wall (s): sum", round(rt["physical"]["A0_worker_wall_s"]["sum"], 2),
      "max", round(rt["physical"]["A0_worker_wall_s"]["max"], 3))
for arm in ("D0", "D1", "D2"):
    d = rt["attributed_deployment"][arm]["deployment_wall_s"]
    p = rt["physical"][f"{arm}_worker_wall_s"]
    print(f"{arm}: augmentation sum {p['sum']:.2f} s, max {p['max']:.3f} s | deployment (A0 + aug) "
          f"median {d['median']:.3f} s, max {d['max']:.3f} s")
print("all new jobs, worker wall sum (s):", round(rt["physical"]["all_new_jobs_worker_wall_s_sum"], 2))
"""),
md(r"""
## What this result can and cannot say

* **A negative engineering-feasibility result on exposed strings.** Paying for words
  through their periods or through relations to earlier words often shortens a view's
  own proposal, but under this fixed candidate rule no complete archive was shorter
  than A0. The searches completed, so this is not a time-out artefact; it is still only
  this finite heuristic (whole-dictionary bundles, eight predecessors, eight flips).
* **Maps are diagnostics** computed on exposed data; they do not locate a universal word
  length, threshold or mechanism.
* **No fractal or causal reading.** A grammar over a static string has no time axis and
  no intervention model; relations between words are structural descriptions only.
"""),
]

write_notebook(cells, os.environ.get("NB22_OUT", os.path.join(HERE, "22_hierarchy_dictionary.ipynb")))
