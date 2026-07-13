"""Builder for notebook 09 -- the perfect trader, and an adversarial audit.

Regenerates notebooks/09_oracle_perfect_trader.ipynb.  Standard library to build;
executing needs the CausalBool kernel (matplotlib + numpy) plus the downloaded
finance/data_100 panel and results/exp31_stress_100.json.
"""
import os
from _nblib import md, code, write_notebook, BOOTSTRAP

HERE = os.path.dirname(os.path.abspath(__file__))

# extra path + data locations this notebook needs on top of the shared bootstrap
EXTRA = r'''
# Level 10 lives above the shared bootstrap's reach: add level9/level10 and the panels.
for _sub in ["level9", "level10"]:
    _p = os.path.join(ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)
import json
DATA_100 = os.path.join(ROOT, "finance", "data_100")   # 100 stocks (run level10/download_100.py)
RESULTS  = os.path.join(ROOT, "results", "exp31_stress_100.json")
from finance import load_yahoo_close

def load_stock(ticker):
    px = load_yahoo_close(os.path.join(DATA_100, ticker + ".json"))
    return [px[d] for d in sorted(px)]

with open(RESULTS) as _f:
    R100 = json.load(_f)        # precomputed 100-stock audit (fast to plot)
print("panel :", len(R100["rows"]), "stocks audited;  demo stock loads live below.")
'''.strip()

cells = [
md(r"""
# 09 · The Perfect Trader — and an Adversarial Audit of the "Theorem"

**Read this even if you know nothing about markets or maths.** We will build, step by
step, the idea of a *perfect trader* who can see the future, ask a sharp question
about it, and then — wearing the hat of a hostile sceptic — try our hardest to prove
the result is fake. We keep only what survives the attack, on **100 stocks**, not a
hand-picked few.

The story in one breath:

1. A **pivot** is a turning point of a price — a peak or a trough.
2. The **perfect trader** (who sees the future) buys low and sells high, but pays a
   fee, so it only bothers with moves big enough to cover the fee.
3. **Claim:** the perfect trader's buy/sell days are *exactly the pivots* at a size
   set by the fee. We will find this is **true — but it is pure geometry**, true of
   any wiggly line, even random noise. It is *not* a market secret. We say so loudly.
4. The one thing that is genuinely about markets is the **clock**: *when* the turning
   points happen. They arrive in **bursts** (calm, calm, then a flurry). That
   clustering is real, survives a shuffle, and forecasts the next burst a little —
   on ~100 of 100 stocks.

Nothing here predicts whether a price will go **up or down** (that is impossible, and
proven elsewhere in this project). We only ever talk about *when things happen* and
*how big they are*.
"""),
code(BOOTSTRAP),
code(EXTRA),

md(r"""
## Step 1 · What is a pivot? (a turning point)

Take one real stock. Its price wiggles up and down. A **pivot** is a confirmed turning
point: we only call the top of a hill a "peak" once the price has fallen back down by
some percentage `theta` (say 2%). That rule ignores tiny jiggles and keeps the real
turns. Below, the orange dots are the pivots at `theta = 2%`.
"""),
code(r"""
from pivots import directional_change_pivots
TICKER = "KO"                       # Coca-Cola: a long, familiar series
price = load_stock(TICKER)
theta = 0.02
piv = directional_change_pivots(price, theta)
pt = [p.index for p in piv]; pv = [p.value for p in piv]

fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(price, color=INK, lw=0.6, label=f"{TICKER} price")
ax.scatter(pt, pv, s=8, color=BAD, zorder=3, label=f"pivots (theta={theta:.0%})")
ax.set_yscale("log"); ax.set_xlabel("trading day"); ax.set_ylabel("price (log)")
ax.set_title(f"{TICKER}: {len(price)} days, {len(piv)} turning points at 2%")
ax.legend(loc="upper left"); plt.tight_layout(); plt.show()
print(f"A pivot every ~{len(price)//len(piv)} trading days on average.")
"""),

md(r"""
## Step 2 · The perfect trader who can see the future

Now imagine a trader with a crystal ball: they know the whole future price. They want
to end with the most money, buying and selling as often as they like — **but** each
trade costs a fee (here a `c = 2%` round-trip cost). With a fee, trading tiny wiggles
loses money, so the perfect trader only acts on moves big enough to be worth it.

We compute this exactly with a short dynamic programme (`optimal_trades`). Green
triangles are its **buys**, red triangles its **sells**.
"""),
code(r"""
from oracle import optimal_trades, kappa_for_round_trip, round_trip_cost
c = 0.02
kappa = kappa_for_round_trip(c)               # per-trade cost giving a 2% round trip
tr = optimal_trades(price, kappa)
buys, sells = tr["buys"], tr["sells"]

fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(price, color=INK, lw=0.6)
ax.scatter(buys,  [price[i] for i in buys],  marker="^", s=22, color=OK,  label="perfect BUY",  zorder=3)
ax.scatter(sells, [price[i] for i in sells], marker="v", s=22, color=BAD, label="perfect SELL", zorder=3)
ax.set_yscale("log"); ax.set_xlabel("trading day"); ax.set_ylabel("price (log)")
ax.set_title(f"{TICKER}: the perfect trader's {len(buys)} buys and {len(sells)} sells (fee c=2%)")
ax.legend(loc="upper left"); plt.tight_layout(); plt.show()

import math
bh = math.log(price[-1]/price[0])
print(f"perfect-trader log-wealth : {tr['log_wealth']:.2f}   (buy-and-hold: {bh:.2f})")
print("The crystal ball wins, of course -- it is the answer key. We will NOT use it to")
print("predict direction; we only study WHEN it acts.")
"""),

md(r"""
## Step 3 · The claim — and the hostile audit

**The claim:** the perfect trader's action days are *exactly the pivots* at threshold
`theta = c`. Let us overlay them. If the claim holds, every orange pivot sits under a
trader action.
"""),
code(r"""
from oracle import oracle_points, match_sets
from point_process import pivot_indices
orc = oracle_points(price, kappa)
dc  = pivot_indices(price, c)
inside = sum(1 for i in dc if i in set(orc))
print(f"{TICKER}: {inside}/{len(dc)} pivots are exactly perfect-trader days "
      f"({100*inside/len(dc):.1f}% containment).")

fig, ax = plt.subplots(figsize=(11, 3.4))
ax.plot(price, color=INK, lw=0.5, alpha=0.7)
ax.scatter(dc,  [price[i] for i in dc],  s=26, facecolors="none", edgecolors=BAD, label="pivots")
ax.scatter(orc, [price[i] for i in orc], s=5,  color=OK, label="perfect-trader days")
ax.set_yscale("log"); ax.set_title(f"{TICKER}: pivots (rings) sit exactly on perfect-trader days (dots)")
ax.legend(loc="upper left"); plt.tight_layout(); plt.show()
"""),

md(r"""
### The sceptic strikes: "that is not a discovery, it is geometry"

A hostile evaluator immediately objects: *a rule that is exactly true is suspicious —
maybe it is true of any wiggly line, and tells us nothing about markets.* Good
objection. Let us test the identical claim on things that are **not** markets:

* a **random walk** (coin-flip prices, no structure),
* **pure random noise**,
* a smooth **sine wave**.

If the containment is ~100% on those too, the "theorem" is just geometry.
"""),
code(r"""
from controls import geometric_random_walk
import math, random
rng = random.Random(0)
gbm = geometric_random_walk(11000, 0.02, random.Random(1))
noise = [100.0]
for _ in range(11000): noise.append(noise[-1]*math.exp(0.02*rng.gauss(0,1)))
sine = [100.0 + 50*math.sin(t/20.0) for t in range(11000)]

def containment(s):
    o = set(oracle_points(s, kappa)); d = pivot_indices(s, c)
    return 100*sum(1 for i in d if i in o)/len(d)

vals = {
    "100 stocks\n(mean)": 100*R100["identity"]["mean_containment_stocks"],
    "random walk":        containment(gbm),
    "pure noise":         containment(noise),
    "sine wave":          containment(sine),
}
fig, ax = plt.subplots(figsize=(7.5, 3.4))
ax.bar(list(vals), list(vals.values()), color=[INK, "#888", "#aaa", HL])
ax.set_ylim(0, 105); ax.set_ylabel("pivots that are\nperfect-trader days (%)")
ax.axhline(100, color=BAD, lw=1, ls="--")
ax.set_title("The 'theorem' is ~100% on markets AND on noise -> it is pure geometry")
for i, v in enumerate(vals.values()):
    ax.text(i, v-6, f"{v:.1f}%", ha="center", color="white", fontweight="bold")
plt.tight_layout(); plt.show()
print("VERDICT: real and exact, but NOT a market fact. It is a construction identity.")
print("Its only worth: it lets us call the pivot clock the *perfect-opportunity* clock.")
"""),

md(r"""
## Step 4 · The one real market thing — the clock ticks in bursts

So where is the actual market structure? In the **timing** of the turning points. If
turning points arrived like clockwork, the gaps between them would all be similar. In
markets they do not: long quiet stretches are punctuated by flurries of turns. That is
**clustering**, or *self-excitation* — one turn tends to trigger more.

We compare the real gaps to a **shuffle** that keeps the same day-to-day moves but
scrambles their order (destroying any clustering). Below: the real event stream
(top) visibly clumps; the shuffle (bottom) is even.
"""),
code(r"""
from controls import return_shuffle
sh = return_shuffle(price, random.Random(3))
orc_sh = oracle_points(sh, kappa)

fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 2.6), sharex=True)
a1.eventplot(orc, colors=[INK], lineoffsets=0, linelengths=0.8, linewidths=0.4)
a1.set_yticks([]); a1.set_ylabel("real", rotation=0, ha="right", va="center")
a1.set_title(f"{TICKER}: turning points cluster in bursts (real) vs even (shuffled)")
a2.eventplot(orc_sh, colors=[HL], lineoffsets=0, linelengths=0.8, linewidths=0.4)
a2.set_yticks([]); a2.set_ylabel("shuffled", rotation=0, ha="right", va="center")
a2.set_xlabel("trading day"); plt.tight_layout(); plt.show()
"""),
md(r"""
We summarise the clustering with one number, the **branching ratio** `n` (from a
self-exciting "Hawkes" model): `n = 0` means clockwork/random, `n -> 1` means every
event triggers a long cascade. Across the **100 stocks**, `n` is well above its
shuffle, on essentially all of them.
"""),
code(r"""
se = R100["self_excitation"]
brs  = [r["branching_ratio"] for r in R100["rows"]]
brsn = [r["branching_null"]  for r in R100["rows"]]
fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 3.6))
ax.hist(brs, bins=20, color=OK, alpha=0.85, label="real")
ax.hist(brsn, bins=20, color="#bbb", alpha=0.85, label="shuffle (null)")
ax.set_xlabel("branching ratio n"); ax.set_ylabel("# stocks")
ax.set_title(f"Self-excitation on {R100['n_series']} stocks"); ax.legend()
ax.axvline(se["mean_branching"], color=INK, lw=1.5)

bx.scatter(brsn, brs, s=14, color=INK, alpha=0.6)
lim = [0, max(brs)+0.05]; bx.plot(lim, lim, color=BAD, ls="--", lw=1)
bx.set_xlabel("n on shuffle"); bx.set_ylabel("n on real")
bx.set_title(f"real > shuffle on {se['n_self_exciting']}/{R100['n_series']} stocks")
plt.tight_layout(); plt.show()
print(f"mean n = {se['mean_branching']:.3f} vs shuffle {se['mean_branching_null']:.3f}; "
      f"self-exciting on {se['n_self_exciting']}/{R100['n_series']} "
      f"({100*se['frac_self_exciting']:.0f}%).")
"""),

md(r"""
## Step 5 · Does the clock forecast? (a little, honestly)

The honest, tradable question is **not** "will the price rise?" (impossible) but
"**when will the next turning point arrive?**" We fit the burst model on the first 70%
of each stock's history and test it on the unseen last 30%, scoring how well it
predicts the timing of the held-out turning points, versus a memoryless baseline. A
positive score means the clustering genuinely carries forward.

The sceptic's check is built in: the perfect trader used the future, so we also run
the *fully causal* pivots (no crystal ball). They score the **same** — proving the
forecast has **no look-ahead cheat**, and equally that it adds nothing beyond the
plain pivot clock.
"""),
code(r"""
oo = R100["oos_forecast"]
gains_o = [r["oos_gain_oracle"] for r in R100["rows"]]
gains_p = [r["oos_gain_pivot"]  for r in R100["rows"]]
fig, ax = plt.subplots(figsize=(9, 3.6))
ax.hist(gains_o, bins=25, color=OK, alpha=0.85)
ax.axvline(0, color=INK, lw=1)
ax.axvline(oo["mean_oos_oracle"], color=BAD, lw=1.5,
           label=f"mean {oo['mean_oos_oracle']:+.3f}")
ax.set_xlabel("out-of-sample forecast gain (nats/event, >0 = beats baseline)")
ax.set_ylabel("# stocks"); ax.legend()
ax.set_title(f"Clock forecasts the NEXT turn on {oo['n_oos_positive']}/{R100['n_series']} stocks "
             f"(sign-test p = {oo['sign_test_p']:.1e})")
plt.tight_layout(); plt.show()
print(f"perfect-trader (future) gain {oo['mean_oos_oracle']:+.4f}  ==  "
      f"causal-pivot gain {oo['mean_oos_pivot']:+.4f}  -> no look-ahead cheat, no new info.")
print(f"GBM control clock branching = {R100['gbm_control']['branching']:.3f}  -> reads ~null (sane).")
"""),

md(r"""
## Step 6 · A curiosity — the cost is a "zoom level"

Each trader's fee sets the size of moves they care about — like a zoom level on the
price. Small fee: they trade tiny wiggles (many, fine events). Big fee: only large
swings (few, coarse events). We can ask how bursty the clock looks at each zoom. The
clustering peaks at an **intermediate** fee (~a couple of percent) and softens at both
ends — a gentle hump. We report it, with the caveat that the finest zoom is limited by
our model's slowest timescale, so treat the leftmost point cautiously.
"""),
code(r"""
cs = R100["cost_as_scale"]
xs = [r["c"] for r in cs]; ys = [r["mean_branching"] for r in cs]
es = [r["std_branching"] for r in cs]
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.errorbar(xs, ys, yerr=es, marker="o", color=INK, capsize=3, lw=1.5)
ax.set_xscale("log"); ax.set_xlabel("round-trip fee c (zoom level)")
ax.set_ylabel("clustering n"); ax.set_title("Opportunity clusters most at a couple of percent fee")
plt.tight_layout(); plt.show()
for r in cs:
    print(f"  fee {r['c']:.3f}:  n = {r['mean_branching']:.3f} +/- {r['std_branching']:.3f}")
print(f"per-stock peak at an interior fee: {R100['n_humped']}/{R100['n_series']} stocks.")
"""),

md(r"""
## Step 7 · The honest scorecard

The whole point of the audit is to separate what is **real and new** from what is
**geometry** or **already known**. Here is the verdict, kept deliberately blunt.
"""),
code(r"""
se, oo = R100["self_excitation"], R100["oos_forecast"]
rows = [
 ["Perfect trades = pivots at theta=c", "TRUE but GEOMETRY",
  f"~100% on stocks, GBM & noise alike; says nothing about markets"],
 ["Clock self-excites (bursts)", "REAL market signal",
  f"n={se['mean_branching']:.2f} vs shuffle {se['mean_branching_null']:.2f}; "
  f"{se['n_self_exciting']}/{R100['n_series']} stocks"],
 ["Clock forecasts next turn (OOS)", "REAL but INHERITED",
  f"{oo['n_oos_positive']}/{R100['n_series']} stocks, p={oo['sign_test_p']:.0e}; "
  f"= plain-pivot result, no crystal-ball cheat"],
 ["n(c) hump (cost = zoom)", "SUGGESTIVE",
  f"interior peak on {R100['n_humped']}/{R100['n_series']}; finest zoom instrument-limited"],
 ["Predict up/down direction", "IMPOSSIBLE",
  "not attempted; proven dead elsewhere in the project"],
]
fig, ax = plt.subplots(figsize=(12, 2.4)); ax.axis("off")
colecol = {"TRUE but GEOMETRY": HL, "REAL market signal": OK, "REAL but INHERITED": "#4a7",
           "SUGGESTIVE": BAD, "IMPOSSIBLE": "#888"}
tab = ax.table(cellText=rows, colLabels=["claim", "verdict", "evidence"],
               colWidths=[0.30, 0.20, 0.50], loc="center", cellLoc="left")
tab.auto_set_font_size(False); tab.set_fontsize(9); tab.scale(1, 1.5)
for (r_, c_), cell in tab.get_celld().items():
    if r_ == 0: cell.set_facecolor(INK); cell.set_text_props(color="white", fontweight="bold")
    elif c_ == 1: cell.set_text_props(color=colecol.get(rows[r_-1][1], INK), fontweight="bold")
plt.title("Scorecard: what survived the hostile audit on 100 stocks", fontweight="bold")
plt.tight_layout(); plt.show()
"""),

md(r"""
## What to take away

* The neat "perfect trader = pivots" rule is **real but not a discovery about
  markets** — it is geometry, true of any line. Its worth is only *interpretive*: it
  lets us call the turning-point clock the *perfect-opportunity* clock.
* The genuine market signal is small and about **timing, never direction**: turning
  points **cluster in bursts**, that clustering beats a shuffle on essentially all
  100 stocks, and it forecasts the *next* turn a little out of sample — but this is
  the plain pivot result we already had, not something the perfect trader added.
* A hostile audit is the point. We tried to break the result three ways (is it
  geometry? is the optimiser buggy? is the forecast a look-ahead cheat?) and reported
  exactly what each attack showed. What is left is modest, honest, and holds at scale.

*Reproduce:* `python level10/download_100.py` then `python level10/exp31_stress_100.py`
regenerate the panel and the JSON this notebook reads; `python notebooks/build_09.py`
rebuilds the notebook itself.
"""),
]

write_notebook(cells, os.path.join(HERE, "09_oracle_perfect_trader.ipynb"))
