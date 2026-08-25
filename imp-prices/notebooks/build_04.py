"""Notebook 04 — the visual pass. The objects, drawn, before any statistic.

This notebook inverts the order the package has used so far. Phases 1 and 2 went
straight from a binarisation to a score; the binary object those scores are about
was never once drawn. Here it is drawn first, and nothing is measured until it
has been looked at.
"""
from _nblib import code, md, write

CELLS = [
md("""
## 1. Why this notebook exists, and why it comes first

The index-set method was not discovered by writing down formulae. It was
discovered by looking at the distribution of ones and zeros, seeing a pattern in
it, and only then asking what table headers would express that pattern; the
behaviour formulae came after the headers, the formal equations after the
formulae, and the statistics arrived last, as justification for something already
seen. Exactness and speed were consequences of that order, not of the algebra.

Phases 1 and 2 of this package ran that order **backwards**. We binarised the
regimes and immediately scored gates against a null. The binary matrix that the
whole method eats has never been rendered. One figure existed in `figures/` for
the entire project before this notebook, and it belongs to the Phase 3 opening.

That is a Gate 1 failure sitting underneath every number in Phases 1 and 2. It
does not by itself make those numbers wrong — several were checked hard, and two
were withdrawn on audit — but it does mean **no one has seen the object they are
about**. This notebook is the missing look, and it deliberately measures nothing
until section 5.

**Reading rule for this notebook.** Sections 2 to 4 contain no statistics on
purpose. If a pattern is real it should be visible; if it is only visible after
being averaged, that is a fact about the averaging.
"""),

md("## 2. The raw series, at full length"),
code('''
from imp_prices import load_and_split, RegimeDiscretiser, SERIES, TARGET

split = load_and_split()
full = split.full
print("panel:", full.shape, "|", full.index[0].date(), "->", full.index[-1].date())
print("train rows:", len(split.train), " test rows:", len(split.test))

fig, axes = plt.subplots(len(full.columns), 1, figsize=(12, 1.35 * len(full.columns)),
                         sharex=True)
for ax, col in zip(axes, full.columns):
    ax.plot(full.index, full[col], lw=1.0, color="0.25")
    ax.axvline(split.train.index[-1], color="#D62728", lw=1.0, ls="--", alpha=0.8)
    ax.set_ylabel(col, fontsize=8, rotation=0, ha="right", va="center")
    ax.tick_params(labelsize=7)
axes[0].set_title("The seven series at full length. Dashed line = the train/test cut.\\n"
                  "Nothing is transformed here; this is what the panel is.", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_A1_raw_series.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
'''),

md("""
## 3. The ternary object — regimes as a colour band

The HMM turns each series into a three-state sequence. Before asking whether one
series predicts another, look at what the sequences *are*: how long the states
last, whether the series switch together, whether the panel has visible common
episodes.
"""),
code('''
disc = RegimeDiscretiser("gaussian").fit(split.train)
reg = disc.transform(full)
print("regime frame:", reg.shape)
print(reg.apply(lambda s: s.value_counts(normalize=True)).round(3).T)

import matplotlib.colors as mcolors
cmap = mcolors.ListedColormap(["#B2182B", "#EEEEEE", "#2166AC"])  # bear, stagnant, bull

fig, ax = plt.subplots(figsize=(12, 3.0))
ax.imshow(reg.T.to_numpy(), aspect="auto", cmap=cmap, vmin=0, vmax=2,
          interpolation="nearest")
ax.set_yticks(range(reg.shape[1])); ax.set_yticklabels(reg.columns, fontsize=8)
ticks = np.linspace(0, len(reg) - 1, 9).astype(int)
ax.set_xticks(ticks); ax.set_xticklabels([reg.index[t].strftime("%Y-%m") for t in ticks],
                                         fontsize=7, rotation=45, ha="right")
ax.grid(False)
ax.set_title("The ternary object. Red = bear, grey = stagnant, blue = bull.\\n"
             "Vertical stripes would mean the panel moves together; horizontal runs "
             "mean persistence.", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_A2_regime_band.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
'''),

md("""
## 4. The binary object — the thing the method actually eats

This is the render that should have existed before any Phase 1 number. Each
series becomes two bits, so the panel becomes a matrix of ones and zeros. All
three encodings are drawn, because the encoding is a choice and its consequences
should be *visible* rather than argued about.
"""),
code('''
from imp_prices.binarise import encode_frame, WIDTH, SUFFIX

encs = {k: encode_frame(reg, k) for k in ("thermometer", "binary", "onehot")}
for k, Bk in encs.items():
    print(f"{k:<12s} {Bk.shape[0]} rows x {Bk.shape[1]} nodes | "
          f"mean density {Bk.to_numpy().mean():.3f}")

fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.2))
for ax, (k, Bk) in zip(axes, encs.items()):
    ax.imshow(Bk.to_numpy(), aspect="auto", cmap="binary", vmin=0, vmax=1,
              interpolation="nearest")
    ax.set_xticks(range(Bk.shape[1]))
    ax.set_xticklabels(Bk.columns, fontsize=6, rotation=90)
    ax.set_title(f"{k}  ({Bk.shape[0]}x{Bk.shape[1]})", fontsize=9)
    ax.grid(False)
axes[0].set_ylabel("time ->", fontsize=8)
fig.suptitle("THE BINARY OBJECT. Black = 1, white = 0. This is what every gate, every "
             "index set and every\\ndescription length in Phases 1 and 1b was computed "
             "over, drawn here for the first time.", fontsize=9.5)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_A3_binary_object.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
'''),

md("""
### 4b. The same object with the columns grouped

Column order in the render above is the panel's order, which is arbitrary. If
there is block structure, an ordering that puts similar columns together will
show it, and one that does not will not. Both are shown so that the reordering
cannot manufacture the pattern.
"""),
code('''
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import pdist

B = encs["thermometer"]
M = B.to_numpy().astype(float)
# Order columns by similarity of their bit sequences (Hamming), which is a
# statement about co-occurrence in time and nothing else.
order = leaves_list(linkage(pdist(M.T, metric="hamming"), method="average"))

fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
for ax, (cols, ttl) in zip(axes, [(list(range(M.shape[1])), "panel order (arbitrary)"),
                                  (list(order), "grouped by co-occurrence")]):
    ax.imshow(M[:, cols], aspect="auto", cmap="binary", vmin=0, vmax=1,
              interpolation="nearest")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([B.columns[c] for c in cols], fontsize=6, rotation=90)
    ax.set_title(ttl, fontsize=9); ax.grid(False)
fig.suptitle("Does the object have blocks? Thermometer encoding, two column orders.",
             fontsize=9.5)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_A4_column_order.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
print("grouped order:", [B.columns[c] for c in order])
'''),

md("""
## 5. Now measure — but only what the pictures asked for

Two things dominate the renders above: the runs, and which corners of the
hypercube the data ever visits. Both are properties of the object rather than
summaries imposed on it.

### 5a. Run lengths — persistence made visible

Inherited anchor A11 puts one-month regime persistence at 79.31 per cent, and
that number is the bar Phase 1 failed to beat. A single percentage cannot say
whether persistence comes from a few long episodes or many short ones, and those
two worlds have very different effective sample sizes.
"""),
code('''
def runs(v):
    v = np.asarray(v); out, n = [], 1
    for a, b in zip(v, v[1:]):
        if a == b: n += 1
        else: out.append(n); n = 1
    out.append(n); return np.array(out)

rows = []
for col in B.columns:
    r = runs(B[col].to_numpy())
    rows.append({"node": col, "n_runs": len(r), "longest": int(r.max()),
                 "median_run": float(np.median(r))})
runtab = pd.DataFrame(rows)
print("The effective row count is the number of RUNS, not the number of months.")
print(runtab.to_string(index=False))
print(f"\\nnominal rows: {len(B)}   median runs across nodes: "
      f"{runtab['n_runs'].median():.0f}")

fig, ax = plt.subplots(figsize=(11, 3.4))
rng = np.random.default_rng(0)
for i, col in enumerate(B.columns):
    r = runs(B[col].to_numpy())
    ax.scatter(np.full(len(r), i) + rng.normal(0, 0.07, len(r)),
               r, s=12, alpha=0.55, color="0.3")
ax.set_xticks(range(len(B.columns)))
ax.set_xticklabels(B.columns, fontsize=6, rotation=90)
ax.set_ylabel("run length (months)")
ax.set_title("Every run in the object, drawn. Not a mean: the runs themselves.",
             fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_B1_runs.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
'''),

md("""
### 5b. The support — which corners of the hypercube are ever visited

**This is the step the whole programme turns on.** An index set is precisely the
set of input patterns that map to an output of one. Phases 1 and 1b fitted gates
without ever asking which input patterns the data *contains*. If the panel only
ever visits four of the eight corners of a three-input cube, then most of the
gate catalogue is indistinguishable on this data, and a "best gate" is a choice
made by the unvisited corners — that is, by nothing.
"""),
code('''
from itertools import combinations

def support(frame, cols):
    """Occupancy of the 2^k input patterns for a set of columns."""
    Mx = frame[list(cols)].to_numpy()
    k = len(cols)
    codes = Mx @ (1 << np.arange(k))
    return np.bincount(codes, minlength=1 << k)

k = 3
occ = []
for cols in combinations(list(B.columns), k):
    cnt = support(B, cols)
    occ.append({"cols": " + ".join(c.split(".")[0][:8] for c in cols),
                "visited": int((cnt > 0).sum()), "of": 1 << k,
                "top_share": float(cnt.max() / cnt.sum())})
occ = pd.DataFrame(occ).sort_values("visited")
print(f"Over all {len(occ)} triples of nodes, corners of the {1<<k}-corner cube "
      f"actually visited:")
print(occ["visited"].value_counts().sort_index().to_string())
print(f"\\nmedian corners visited: {occ['visited'].median():.0f} of {1<<k}")
print(f"median share of rows in the single most common corner: "
      f"{occ['top_share'].median():.3f}")
print("\\nLeast-covered triples:"); print(occ.head(6).to_string(index=False))
'''),

code('''
# Draw the support for a few triples rather than reporting only its size.
picks = list(combinations(list(B.columns), 3))
rng = np.random.default_rng(1)
chosen = [picks[i] for i in rng.choice(len(picks), 6, replace=False)]

fig, axes = plt.subplots(1, 6, figsize=(14, 2.9), sharey=True)
for ax, cols in zip(axes, chosen):
    cnt = support(B, cols)
    ax.bar(range(len(cnt)), cnt,
           color=["#CCCCCC" if c == 0 else "#2166AC" for c in cnt])
    ax.set_xticks(range(len(cnt)))
    ax.set_xticklabels([format(i, "03b") for i in range(len(cnt))],
                       fontsize=6, rotation=90)
    ax.set_title("\\n".join(c.split(".")[0][:9] for c in cols), fontsize=6.5)
axes[0].set_ylabel("rows at this corner", fontsize=8)
fig.suptitle("The support, drawn. Grey bars are corners the data NEVER visits; on those, "
             "any two gates that\\ndiffer only there are the same gate as far as this "
             "panel can tell.", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_B2_support.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
'''),

md("""
## 6. The dead columns, and a number that did not survive its own reference

The regime band in section 3 shows CPI as a single unbroken bar and USD_Idx as one
switch followed by six years of nothing. That is visible before any statistic, so
the statistic that follows is a measurement of something already seen rather than
a search for something to say.

Two questions have to be separated, because they have different cures: is a
column dead because **the series has no regimes**, or because **the fit
degenerated**? Twenty-nine non-convergence warnings fired during section 3.
"""),
code('''
lr = np.log(full).diff().dropna()
print("Log-return dispersion by series — the input the HMM sees:")
for c in full.columns:
    v = lr[c].to_numpy()
    print(f"   {c:<10s} sd={v.std():.5f}  min={v.min():+.5f}  max={v.max():+.5f}")

print("\\nRegime occupancy (3-state fit). An empty middle state means the fit "
      "collapsed to two:")
for c in reg.columns:
    print(f"   {c:<10s} {np.bincount(reg[c].to_numpy(), minlength=3)}")
'''),

md("""
CPI's log returns have a dispersion roughly forty times smaller than WTI's, and
the three-state fit puts every one of its months in one state. The middle state
is empty for three of the seven series, so for those the three-state model is a
two-state model wearing a third label. This is a property of the panel, not of
the evaluation window: it holds inside the training rows on their own.

### 6b. The number I nearly reported, and why it is withdrawn

Counting nodes that never change across the test window gives a striking figure.
Before it goes anywhere near a claim, it needs a reference: a node with four runs
in 198 months will often be constant across any 30-month window simply because
its runs are long. The reference below shifts each column circularly, which
preserves that column's own run structure exactly and randomises only where the
test window lands.
"""),
code('''
Mt = B.to_numpy()
n_rows, k_nodes = Mt.shape
te = np.isin(B.index, split.test.index)
obs = sum(1 for j in range(k_nodes) if len(np.unique(Mt[te, j])) == 1)

rng = np.random.default_rng(0)
null = np.array([
    sum(len(np.unique(np.roll(Mt[:, j], rng.integers(n_rows))[te])) == 1
        for j in range(k_nodes))
    for _ in range(5000)])

print(f"observed nodes constant across the test window : {obs} of {k_nodes}")
print(f"circular-shift null                            : median {np.median(null):.0f}, "
      f"5-95 pct [{np.percentile(null,5):.0f}, {np.percentile(null,95):.0f}]")
print(f"rank-based p                                   : {(null >= obs).mean():.4f}")
print("\\nVERDICT: not separable from the null. This is a restatement of the run")
print("structure, not an additional finding, and it is recorded as withdrawn.")
'''),

md("""
So the claim is **not** "eight of fourteen nodes are frozen out of sample". The
claim is the run structure itself, which is a direct property of the object and
needs no null because it is not a comparison:
"""),
code('''
rs = pd.DataFrame({
    "node": B.columns,
    "runs_in_198_months": [1 + int((B[c].to_numpy()[1:] != B[c].to_numpy()[:-1]).sum())
                           for c in B.columns]}).sort_values("runs_in_198_months")
print(rs.to_string(index=False))

fig, ax = plt.subplots(figsize=(9, 3.2))
colour = ["#B2182B" if v <= 5 else "#2166AC" for v in rs["runs_in_198_months"]]
ax.barh(range(len(rs)), rs["runs_in_198_months"], color=colour)
ax.set_yticks(range(len(rs))); ax.set_yticklabels(rs["node"], fontsize=7)
ax.set_xlabel("number of runs in 198 months")
ax.set_title("How often each node changes at all. Red = five runs or fewer:\\n"
             "these columns are close to constant and cannot carry a prediction.",
             fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_B3_run_counts.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
'''),

md("""
## 7. What the look changes

**The panel is not seven series.** It is one crude-oil factor observed three ways,
plus one partially active rate node, plus four nodes that barely move. The
co-occurrence ordering in section 4b found this without being told: it placed the
three `not_bear` oil nodes adjacent and the three `bull` oil nodes adjacent,
because WTI_CL, Brent_BZ and WTI_Spot are the same underlying object.

**This is the shape behind Gate 1.0.** Phase 1 concluded that the panel carries no
predictive content for the one-month WTI regime beyond the regime's own
persistence, and reported that as an explanation of the source dissertation's
failure. The conclusion stands, and now it has a mechanism that can be *seen*:
the candidate parents either do not move, or they are crude oil under another
name. A search over parent sets was never going to find anything, and no scoring
rule, description length or gate catalogue could have rescued it.

**The support is thin.** Across all 364 node triples the median triple visits five
of the eight corners of its cube, and the modal corner holds about seven-tenths of
the rows. A gate is a labelling of all eight corners, so most of what distinguishes
one gate from another in the catalogue is being decided on corners the data never
visits. That is not a defect of the method; it is a statement about how much this
panel can identify, and it should have been known before any gate was fitted.

**What this does not say.** It says nothing about whether the method works. It says
this panel cannot test it. That is the distinction Phase 3 exists to act on: move
to daily data, where the oil series have texture at the scale the pivots live on,
and drop the macro covariates that are constant at monthly resolution rather than
carrying them along as decoration.
"""),

md("""
---

# 8. Didactic appendix

Three things above are asserted compactly and are worth being able to *do* rather
than accept: how a month becomes bits, what a thin support looks like in the
geometry, and why persistence is such a hard bar. Each is built here at a size
that can be checked by hand.

## 8a. One month, turned into bits, by hand

The encoding is a two-step map: the HMM assigns each series a regime, and the
thermometer code turns each regime into two bits. Take April 2020 — the month WTI
futures printed negative — and follow every step.

The thermometer code is `bear -> (0,0)`, `stagnant -> (1,0)`, `bull -> (1,1)`. The
first bit answers *is this at least stagnant?* and the second *is this bull?* The
pattern `(0,1)` is unreachable by construction, which is what makes the code
order-preserving rather than an arbitrary relabelling.
"""),
code('''
lr = np.log(full).diff().dropna()
NAMES = {0: "bear", 1: "stagnant", 2: "bull"}
CODE = {0: (0, 0), 1: (1, 0), 2: (1, 1)}

when = "2020-04-30"
i = list(reg.index.strftime("%Y-%m-%d")).index(when)

print(f"ONE MONTH BY HAND: {when}\\n")
print(f"{'series':<10s} {'log return':>11s} {'state':>6s} {'name':>9s}   bits")
print("-" * 52)
for c in reg.columns:
    st = int(reg[c].iloc[i])
    print(f"{c:<10s} {lr[c].iloc[i]:>+11.5f} {st:>6d} {NAMES[st]:>9s}   {CODE[st]}")

row = B.iloc[i].to_numpy()
print("\\nthe 14-bit row, in column order:")
for c, b in zip(B.columns, row):
    print(f"    {b}   {c}")
print("\\nas a word:", "".join(map(str, row)))
'''),

md("""
Two things are visible in that single row, and neither needed a statistic.

WTI is **bear** while Brent is **bull** in the very same month: the two benchmark
crudes diverged in April 2020, which is exactly the storage crisis that drove WTI
negative and left seaborne Brent alone. So the three oil series are not
*identical* — they are one factor plus episodes.

And most of the bits in that row are zero, four of them from CPI and USD_Idx,
which are zero in **every** row. Those four positions in the word never change,
whatever month is chosen.

## 8b. The support, drawn as the cube it actually is

A three-input gate is a rule assigning an output to each of the eight corners of a
cube. Which corners the data visits therefore decides how much of that rule is
fixed by evidence and how much by nothing at all.
"""),
code('''
from itertools import combinations
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

CORNERS = np.array([[(i >> b) & 1 for b in range(3)] for i in range(8)])

def draw_cube(ax, cols, title):
    cnt = support(B, cols)
    for a in range(8):
        for b in range(a + 1, 8):
            if bin(a ^ b).count("1") == 1:
                ax.plot(*zip(CORNERS[a], CORNERS[b]), color="0.85", lw=0.8, zorder=1)
    vis = cnt > 0
    ax.scatter(CORNERS[vis, 0], CORNERS[vis, 1], CORNERS[vis, 2],
               s=30 + 900 * cnt[vis] / cnt.sum(), color="#2166AC",
               zorder=3, depthshade=False)
    if (~vis).any():
        ax.scatter(CORNERS[~vis, 0], CORNERS[~vis, 1], CORNERS[~vis, 2], s=90,
                   facecolors="none", edgecolors="#B2182B", linewidths=1.6,
                   zorder=3, depthshade=False)
    for a in range(8):
        ax.text(CORNERS[a, 0], CORNERS[a, 1], CORNERS[a, 2],
                f" {format(a,'03b')}:{cnt[a]}", fontsize=6,
                color="#B2182B" if cnt[a] == 0 else "0.2")
    ax.set_title(title, fontsize=7)
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1]); ax.set_zticks([0, 1])
    ax.tick_params(labelsize=5); ax.grid(False)

triples = list(combinations(list(B.columns), 3))
scored = sorted(((int((support(B, t) > 0).sum()), t) for t in triples),
                key=lambda z: z[0])
picks = [scored[-1][1], scored[len(scored) // 2][1], scored[0][1]]
labels = ["BEST covered", "MEDIAN triple", "WORST covered"]

fig = plt.figure(figsize=(13, 4.4))
for j, (t, lab) in enumerate(zip(picks, labels)):
    ax = fig.add_subplot(1, 3, j + 1, projection="3d")
    draw_cube(ax, t, lab + "\\n" + "\\n".join(t))
fig.suptitle("The cube the gate is defined on. Filled blue = a corner the data visits "
             "(size = how often);\\nhollow red = a corner it NEVER visits, where the "
             "gate's output would be set by nothing.", fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "figures", "04_C1_support_cube.png"),
                                dpi=130, bbox_inches="tight")
plt.show()
'''),

md("""
Turn the knob: how many gates does an unvisited corner actually confuse? Each
corner the data never reaches halves the number of rules this panel can tell
apart, because the two rules that differ only there are indistinguishable.
"""),
code('''
vis_counts = np.array([int((support(B, t) > 0).sum()) for t in triples])
print("Distinguishable Boolean functions of 3 inputs, given the corners visited:")
print(f"{'corners visited':>16s} {'triples':>9s} {'distinguishable rules':>24s}")
for v in sorted(set(vis_counts)):
    print(f"{v:>16d} {int((vis_counts == v).sum()):>9d} {2**v:>18d} of 256")
med = int(np.median(vis_counts))
print(f"\\nmedian triple: {med} corners -> {2**med} of the 256 three-input rules are "
      f"distinguishable.")
print("The rest are not wrong here. They are the SAME rule, as far as this panel "
      "can see.")
'''),

md("""
## 8c. Why persistence is such a hard bar

Anchor A11 records one-month regime persistence at 79.31 per cent on the GWP3
monthly sample. On the 198-row panel rebuilt here the same quantity is computed
below; the windows differ, so the two are reported separately rather than
reconciled.

The reason the bar is hard is structural rather than statistical. Predicting *the
same regime as last month* is free, uses no data, and is right on every month
that is not a turning point. To beat it a model must gain on the switches without
losing on the stays — and the stays vastly outnumber the switches.
"""),
code('''
y = reg[TARGET].to_numpy()
stays = int((y[1:] == y[:-1]).sum())
switches = int((y[1:] != y[:-1]).sum())
n_tr = stays + switches
print(f"target: {TARGET}, {n_tr} transitions on this 198-row panel")
print(f"   stays    : {stays:>4d}  ({stays/n_tr:.4f})  <- what the free rule gets right")
print(f"   switches : {switches:>4d}  ({switches/n_tr:.4f})  <- what it always gets wrong")
print(f"\\npersistence accuracy on this panel : {stays/n_tr:.4f}")
print(f"inherited anchor A11 (GWP3 sample)  : 0.7931")
print("Different windows. Reported separately, not reconciled.")
'''),

code('''
# THE KNOB. r = fraction of switches the model calls correctly.
#           f = fraction of stays it wrongly disturbs while chasing them.
r = np.linspace(0, 1, 101)
fig, ax = plt.subplots(figsize=(8.6, 4.0))
for f, col in zip([0.0, 0.02, 0.05, 0.10, 0.20],
                  plt.cm.viridis(np.linspace(0, 0.85, 5))):
    ax.plot(r, (stays * (1 - f) + switches * r) / n_tr, color=col, lw=1.6,
            label=f"disturbs {f:.0%} of stays")
ax.axhline(stays / n_tr, color="#B2182B", ls="--", lw=1.2,
           label=f"free persistence rule ({stays/n_tr:.3f})")
ax.set_xlabel("fraction of the switches the model calls correctly  (r)")
ax.set_ylabel("overall accuracy")
ax.set_title(f"Stays outnumber switches {stays}:{switches}, so every stay broken in "
             f"pursuit of a switch\\ncosts {stays/switches:.2f} switches to earn back.",
             fontsize=9)
ax.legend(fontsize=7.5); plt.tight_layout()
plt.savefig(os.path.join(ROOT, "figures", "04_C2_persistence_bar.png"),
            dpi=130, bbox_inches="tight")
plt.show()

print(f"break-even condition: r > {stays/switches:.3f} x f")
for f in (0.02, 0.05, 0.10):
    print(f"   disturbing {f:>4.0%} of stays requires calling "
          f"{min(1.0, stays/switches*f):>5.1%} of switches right merely to break even")
'''),

md("""
That is the whole difficulty in one line: **stays outnumber switches by roughly
three to one, so a model must be about three times more accurate on the switches
than it is disruptive on the stays simply to draw level with a rule that uses no
data at all.**

It also explains why Phase 1 was never going to be rescued by a better scoring
rule. A model can only clear this bar by anticipating turning points, and that
requires a variable that moves *before* the target does. The panel's near-constant
columns cannot move before anything, and the oil columns are the target itself
under other names.

The argument carries into Phase 3 unchanged. Re-targeting from "next month's
regime" to the clock — how long until the next directional-change pivot — was
chosen precisely because a running-median split puts the base rate near one half
by construction, so the free rule earns nothing and the comparison becomes
informative rather than a contest against arithmetic.
"""),
]

if __name__ == "__main__":
    write("04_the_visual_pass.ipynb", CELLS,
          "# 04 — The visual pass: the objects, drawn\n\n"
          "*Written after the assessor required that the method's own discovery order "
          "be restored — look at the distribution of ones and zeros first, and let the "
          "table headers, the formulae and the statistics follow from what was seen.*")
