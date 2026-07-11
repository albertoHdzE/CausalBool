"""Builder for notebook 08 -- from structure to strategy."""
import os
from _nblib import md, code, write_notebook, BOOTSTRAP

HERE = os.path.dirname(os.path.abspath(__file__))

cells = [
md(r"""
# 08 · From Structure to a Strategy — An Honest Answer

The natural question: can all this structure make money? The honest answer is
**yes for risk, no for return**. Direction is unforecastable (we proved it at every
level), so nothing here bets on which way a price goes. But the **clock**
(volatility) *is* forecastable — so we can manage **risk**: size positions inversely
to forecast risk and de-risk ahead of turbulence. The win is a smoother ride, not a
bigger return.
"""),
code(BOOTSTRAP),

md(r"""
## 1. Tail losses live where the clock is high

First, the reason a risk strategy can work at all. Split days by whether the clock
(recent volatility) is high or low, and look at the worst 5% of next-day losses (the
**expected shortfall**). The tail is far deeper when the clock is high — so avoiding
those days removes the fat part of the tail.
"""),
code(r"""
from shared_clock import aligned_prices
import math, statistics
names, M = aligned_prices()
R = [[math.log(M[i][t]/M[i][t-1]) for t in range(1, len(M[i]))] for i in range(len(names))]

def cvar(xs, q=0.05):
    k = max(1, int(q*len(xs))); return statistics.mean(sorted(xs)[:k])

hi, lo = [], []
for r in R:
    clock = [statistics.pstdev(r[t-21:t]) if t >= 21 else 0.0 for t in range(len(r))]
    valid = list(range(21, len(r)-1))
    thr = sorted(clock[t] for t in valid)[int(2/3*len(valid))]
    hi.append(cvar([r[t+1] for t in valid if clock[t] >= thr]))
    lo.append(cvar([r[t+1] for t in valid if clock[t] <  thr]))

fig, ax = plt.subplots(figsize=(6.5, 3))
ax.bar(["clock LOW", "clock HIGH"], [np.mean(lo), np.mean(hi)], color=[OK, BAD])
ax.set_ylabel("5% expected shortfall\n(next-day loss)")
ax.set_title(f"Tail is {np.mean(hi)/np.mean(lo):.1f}× deeper when the clock is high")
for i, v in enumerate([np.mean(lo), np.mean(hi)]):
    ax.text(i, v-0.001, f"{v:.2%}", ha="center", va="top", color="white", fontweight="bold")
plt.tight_layout(); plt.show()
"""),

md(r"""
## 2. The backtest: buy-and-hold vs volatility targeting

We run a walk-forward, cost-aware portfolio over ~30 years. Everything uses only
past data. **A** is plain buy-and-hold. **B/C** target a constant volatility, scaling
exposure down when the forecast clock is loud. No scheme ever bets on direction.
"""),
code(r"""
from strategy import backtest, metrics
Rs = [[M[i][t]/M[i][t-1]-1 for t in range(1, len(M[i]))] for i in range(len(names))]   # simple returns

schemes = {
    "A buy & hold":        dict(scheme="buyhold",   vol_forecast="trailing"),
    "B vol-target (trail)":dict(scheme="voltarget", vol_forecast="trailing"),
    "C vol-target (clock)":dict(scheme="voltarget", vol_forecast="har"),
}
results = {}
for label, kw in schemes.items():
    bt = backtest(Rs, target_vol=0.10, lev_cap=1.5, cost_bps=10, warmup=252, **kw)
    results[label] = (bt["daily"], metrics(bt["daily"], warmup=252))

fig, ax = plt.subplots(figsize=(10, 4))
colors = {"A buy & hold": INK, "B vol-target (trail)": HL, "C vol-target (clock)": OK}
for label, (daily, _) in results.items():
    eq = np.cumprod([1+x for x in daily[252:]])
    ax.plot(eq, label=label, color=colors[label], lw=1.6)
ax.set_yscale("log"); ax.set_ylabel("growth of $1 (log)"); ax.set_xlabel("trading days")
ax.legend(); ax.set_title("Equity curves — similar growth, very different smoothness")
plt.tight_layout(); plt.show()
"""),

md(r"""
## 3. The scoreboard

The vol-targeted schemes barely change the Sharpe ratio, but they **slash the worst
drawdown and the tail loss**. That is the whole point: a much smoother ride for a
similar risk-adjusted return.
"""),
code(r"""
labels = list(results.keys())
sharpe = [results[l][1]["sharpe"] for l in labels]
mdd    = [results[l][1]["max_drawdown"] for l in labels]
cv     = [results[l][1]["cvar_5pct_daily"] for l in labels]

fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
for ax, vals, title, fmt in zip(
        axes, [sharpe, mdd, cv],
        ["Sharpe ratio (higher better)", "max drawdown (closer to 0 better)", "5% daily CVaR (closer to 0 better)"],
        ["{:.2f}", "{:.0%}", "{:.2%}"]):
    bars = ax.bar(labels, vals, color=[INK, HL, OK])
    ax.set_title(title, fontsize=10); ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v, fmt.format(v), ha="center",
                va="bottom" if v >= 0 else "top", fontsize=8, fontweight="bold")
plt.tight_layout(); plt.show()

print("scheme                 Sharpe   maxDD    CVaR5%")
for l in labels:
    m = results[l][1]
    print(f"{l:22s} {m['sharpe']:5.2f}  {m['max_drawdown']:6.0%}  {m['cvar_5pct_daily']:7.2%}")
"""),

md(r"""
## Takeaways — and the honest ceiling

* Because tail losses **concentrate where the clock is high**, de-risking on the
  clock removes the fat part of the tail.
* Volatility targeting cuts the **worst drawdown by about a third** and the daily
  tail loss by ~30%, at a **marginally better Sharpe** — a materially smoother ride.
* But there is **no return alpha**: the fancy clock forecast does not beat simple
  trailing volatility once trading costs are paid, and *direction is unforecastable*.
  The programme buys **understanding and risk control**, not a money machine.

## The whole journey, in one line

An **exact inverse** for deterministic networks (00–02) meets **markets** and fails
honestly (03); dropping the assumption that digits carry the information (04),
markets reveal a **self-similar, shared, fractal clock** in the timing of their
turning points (05–07) — real structure that governs **risk**, not direction (08).
"""),
]

write_notebook(cells, os.path.join(HERE, "08_from_structure_to_strategy.ipynb"))
