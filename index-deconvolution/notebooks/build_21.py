"""Builder for notebook 21 -- HID multilevel v1: words of several widths, several levels.

Regenerates notebooks/21_hierarchy_multilevel.ipynb. Standard library to build;
executing needs the CausalBool kernel and the saved run
results/hierarchy_multilevel_v1/multilevel-feasibility-v1-r1. Runs from the repository
root or the notebook directory. Output path: $NB21_OUT, default next to this builder.

Artifact-only. The notebook READS saved rows, archives, traces and tables; it imports
only ``hierarchy.decode`` and ``hierarchy.ledger`` to re-check and explain archive bytes.
It runs no search, no encoder, no generator, no BDM and no job. Prose carries no
measured number: every number is printed by a cell from a saved artifact.
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
               and (p / "results" / "hierarchy_multilevel_v1" / "multilevel-feasibility-v1-r1").is_dir())
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

RUN = ID_ROOT / "results" / "hierarchy_multilevel_v1" / "multilevel-feasibility-v1-r1"
def load(p):
    return json.loads(Path(p).read_text())
summary, decision = load(RUN / "summary.json"), load(RUN / "DECISION.json")
verification, audit = load(RUN / "verification.json"), load(RUN / "arithmetic_audit.json")
lock_sha = (RUN / "implementation_lock.sha256").read_text().strip()
def table(name):
    with open(RUN / "tables" / name) as fh:
        return list(csv.DictReader(fh))
strings, views, gmap = table("per_string.csv"), table("views_A3.csv"), table("gap_map_A3.csv")
def num(x):
    return None if x in ("", "None", None) else float(x)
print("lock:", lock_sha[:16], "| engineering verdict:", decision["engineering_verdict"],
      "| label:", decision["recommendation"])
print("verification pass:", verification["verification_pass"], "| audit pass:", audit["pass"],
      "| archives re-read by the audit:", audit["archives_read"])
'''

cells = [
md(r"""
# 21 · HID multilevel v1: reversible words at several widths and levels

**Question.** If a bit string is cut into words of width b (8 widths, 2 origins each)
and consecutive words are paired again and again (levels 1–4), do exact grammar
proposals over those word streams ever give a *shorter complete archive* than the
accepted search-v2 method (k = 1, "A0")? And where, by width and level, does
repetition support break down?

**Design.** 96 previously exposed strings, four arms: A0 (k = 1), A1 (width 8, level 1),
A2 (8 widths, level 1), A3 (8 widths, levels 1–4). Every augmentation starts from the
saved, verified A0 archive and may replace it only with a strictly shorter, independently
decoded archive. Every word, every dictionary entry, prefix and suffix is paid for in
the archive. Proposals per view: G0 runs, G1 the owner pair grammar, G2/G3 occurrence-gap
templates with paid patches.

This is exploratory, descriptive work on exposed data: no interval, no test, no
generalization, no fractal or causal claim. Run the first cell first.
"""),
code(BOOTSTRAP),
code(SETUP),
md(r"""
## 1. Completeness and the headline

Every count below is read from `summary.json`; the label rule is fixed in the protocol
(NO_RETAINED_GAIN if A3 never beats A0 on the 96 strings).
"""),
code(r"""
for k, v in summary["counts"].items():
    print(f"{k:34s} {v}")
rec = summary["recommendation"]
print()
print("label:", rec["label"], "| A3 < A0 on", rec["a3_beats_a0_strings"], "strings;",
      "A3 < A2 on", rec["a3_beats_a2_strings"], "; A2 < A0 on", rec["a2_beats_a0_strings"])
"""),
md(r"""
## 2. Contrasts, with their reference points in the same table

saving(A, B) = (bits(B) − bits(A)) / n, positive when A is shorter; averaged base/ragged,
then replicates, then the 24 family-length cells equally. The A0 rows give the reference
distribution against which the composites must be read.
"""),
code(r"""
print(f"{'contrast':22s} {'equal-cell mean':>16s}  strings b/t/w     cells b/t/w")
for k, v in summary["contrasts"].items():
    s, c = v["strings"], v["cells_sign"]
    print(f"{k:22s} {v['aggregate']:16.6f}  {s['better']:3d}/{s['tie']:3d}/{s['worse']:3d}      "
          f"{c['better']:2d}/{c['tie']:2d}/{c['worse']:2d}")
"""),
md(r"""
## 3. Rendering the object: the closest any proposal came

Saved per-view records give each view's shortest admissible archive. For every string we
take the view that came closest to A0 and print the excess. One string family is
periodic with a period that is itself a word width; there the G0 proposal (a REPEAT of
one word) reproduces the A0 bytes exactly — a duplicate, not a gain. These are
illustrations, not a selection of typical behaviour.
"""),
code(r"""
best = {}
for r in views:
    if r["best_bits"]:
        b, a = int(r["best_bits"]), int(r["a0_bits"])
        if r["case_id"] not in best or b < best[r["case_id"]][0]:
            best[r["case_id"]] = (b, a, r["width"], r["level"], r["origin"])
rel = sorted((b - a) / a for b, a, *_ in best.values())
print("strings:", len(best), "| min relative excess over A0:", round(rel[0], 4),
      "| median:", round(statistics.median(rel), 4), "| max:", round(rel[-1], 4))
for cid, (b, a, w, l, o) in sorted(best.items(), key=lambda kv: (kv[1][0] - kv[1][1]) / kv[1][1])[:4]:
    print(f"  {cid:38s} best {b:5d} bits vs A0 {a:5d}  (width {w}, level {l}, origin {o})")
"""),
code(r"""
cid = min(best, key=lambda c: ((best[c][0] - best[c][1]) / best[c][1], c))
row = load(RUN / "rows" / f"{cid}.A3.json")
tr = load(RUN / row["trace_path"])
v = min((v for v in tr["views"] if v["description_gap"]["best_bits"] is not None),
        key=lambda v: (v["description_gap"]["best_bits"], v["view_index"]))
print(cid, "| view: width", v["width"], "level", v["level"], "origin", v["origin"],
      "| m =", v["m"], "k =", v["k"], "| prefix", v["prefix_bits"], "suffix", v["suffix_bits"])
print("top stream (first 16 tokens):", v["top_stream"][:16])
print("dictionary:", v["dictionary"][:2])
for p in v["proposals"]:
    print(f"  {p['proposal']}: {p['status']:30s} bits {p['archive_bits']}  "
          f"same bytes as A0: {p['archive_sha256'] == row['a0_archive_sha256']}")
a0 = (RUN / row["archive_path"]).read_bytes()
x_sha = hashlib.sha256(decode_archive(a0).encode()).hexdigest()
print("deployed composite == A0:", row["archive_sha256"] == row["a0_archive_sha256"],
      "| decodes to the recorded input:", x_sha == row["input_sha256"])
led = archive_ledger(a0)
print("A0 byte ledger:", led["bytes_by_owner"], "| total bytes", len(a0))
"""),
md(r"""
## 4. The width-by-level map

Each cell pools 96 strings × 2 origins. A deeper cell summarises only the views whose path
was *not* stopped (saturation k = m, or a single symbol), so its population is a
selected subset: the counts are printed with every median. Weak support is the share of
bits under singleton words plus the literal prefix/suffix; the description gap is
(shortest view archive − A0) / n.
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
panels = [("evaluated", "views evaluated (of 192)"), ("median_k_over_m", "median k/m"),
          ("median_weak_support_fraction", "median weak support"),
          ("median_minus_a0_per_bit", "median (best − A0)/n")]
fig, axes = plt.subplots(1, 4, figsize=(17, 3.6))
for ax, (key, title) in zip(axes, panels):
    M = grid(key)
    im = ax.imshow(M, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(W)), W); ax.set_yticks(range(len(Lv)), Lv)
    ax.set_xlabel("word width b"); ax.set_ylabel("level"); ax.set_title(title)
    for i in range(len(Lv)):
        for j in range(len(W)):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}" if key != "evaluated" else f"{int(M[i, j])}",
                        ha="center", va="center", fontsize=7, color="w")
    fig.colorbar(im, ax=ax, shrink=0.8)
plt.tight_layout(); plt.show()
print("cells:", len(gmap), "| views shorter than A0 in any cell:", sum(int(g["shorter_than_a0"]) for g in gmap),
      "| views with no admissible candidate:", sum(int(g["no_admissible_candidate"]) for g in gmap))
"""),
md(r"""
## 5. Three different "gaps", kept apart

1. **Occurrence gaps** — distances between repeats of one word; the G2/G3 templates use
   the two most frequent. When the template plus at most 64 paid bit flips cannot
   reproduce the view, the proposal is rejected (no archive).
2. **Weak repetition support** — bits under words that occur once. Saturated views
   (every word distinct) end their path; their words can still be internally periodic,
   which this proxy does not see.
3. **Description gap** — the measured code-length difference to A0.
"""),
code(r"""
for arm in ("A1", "A2", "A3"):
    print(arm, summary["workload"][arm]["proposal_status"])
sat = [r for r in views if r["status"] == "EVALUATED" and r["k"] == r["m"]]
print("\nsaturated evaluated views:", len(sat), "| of which with at least one internally periodic word:",
      sum(1 for r in sat if int(r["dict_proper_repeat"]) > 0))
"""),
md(r"""
## 6. What it cost

Physical totals count each job once. The attributed deployment cost charges the single
A0 run in full to every composite (A0 then augmentation), so no composite is cheaper than A0.
"""),
code(r"""
rt = summary["runtime"]
print("A0 worker wall (s): sum", round(rt["physical"]["A0_worker_wall_s"]["sum"], 2),
      "max", round(rt["physical"]["A0_worker_wall_s"]["max"], 3))
for arm in ("A1", "A2", "A3"):
    d = rt["attributed_deployment"][arm]["deployment_wall_s"]
    p = rt["physical"][f"{arm}_worker_wall_s"]
    print(f"{arm}: augmentation sum {p['sum']:.2f} s, max {p['max']:.3f} s | deployment (A0 + aug) "
          f"median {d['median']:.3f} s, max {d['max']:.3f} s")
"""),
md(r"""
## What this result can and cannot say

* **A negative engineering-feasibility result on exposed strings.** Under this fixed
  vocabulary (paid words, paired words, runs, owner pair grammar, gap templates with at
  most 64 flips) no proposal was shorter than A0. It does not show that multilevel
  structure is absent; it shows these proposals did not pay for their dictionaries here.
* **Maps are diagnostics,** computed on exposed data; deeper cells are selected subsets.
  They do not locate a universal word length or threshold.
* **No fractal or causal reading.** A grammar hierarchy over a static string has no time
  axis and no intervention model.
"""),
]

write_notebook(cells, os.environ.get("NB21_OUT", os.path.join(HERE, "21_hierarchy_multilevel.ipynb")))
