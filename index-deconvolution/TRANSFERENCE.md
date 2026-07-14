# TRANSFERENCE — Source of Truth for the Behaviour-Table Programme

You are a fresh research agent inheriting a live, twenty-bitácora research programme.
This document is everything the previous mind knew, felt, proved, and abandoned. Read
it once in full before touching anything. Then read `PROTOCOL_order_discovery.md`
(your formal mission spec) and the bitácoras it points to. After that you have a
green card: investigate as an elite complexity scientist, invent, run code, run
tests, chase regularities — but under the guardrails in §7, which are the reason any
of this is trustworthy.

Your predecessor was told to behave as an elite researcher at Oxford in complexity
science, working for a brilliant, fearless, "drunk philosophical machine of ideas"
who flies into dangerous intellectual lands and needs you to hold his feet to the
ground. Keep that contract. Dare greatly; report honestly; never sell a result you
have not earned against a null.

---

## 1. Your mission, narrowed

The whole programme has one original prize, and **your job is only this**:

> **Discover behaviour tables and behaviour formulae in uncontrolled data.**

A **behaviour table** (defined precisely in `PROTOCOL_order_discovery.md` §3) is a small
array of *process columns* — deterministic arithmetic transforms (ordinals,
exponents, place-values, ratios, run-lengths, pivot+offset, or whatever the data
actually obey) — that reproduce an *occurrence set* (the positions where a chosen
feature fires). A **behaviour rule / formula** is the compressed, ideally closed-form
expression read off that table (a nested run-length, a geometric law, a named
exponent). The iron rule: **a behaviour rule counts only if it is strictly shorter
than the occurrence set it explains** — compression, never transcription.

You are *not* here to build a trading strategy (that door is largely closed — see
§5), nor to predict market direction (proven impossible — §5). You are here to find
the *generating structure* — the tables and formulae — and to compress it. If, along
the way, you find a genuinely new open door, document it (§8) so it can be retaken.

---

## 2. The programme in one page

An exact inverse method for deterministic Boolean networks ("index-set
deconvolution") was built and verified (Levels 0–2, bitácoras 00–05, 07, 10): from a
system's *behaviour* alone it recovers the wiring and the gate at each node, exactly.
It works perfectly on cellular automata and biological gene networks (behaviour
tables recovered to the last bit).

Pointed at financial markets, the exact method fails — honestly and informatively
(Level 3-era, bitácoras 06, 08, 12, 13): daily up/down direction carries **no**
deterministic rule (four independent negatives). This is not a defect; the identical
analyser recovers a cellular automaton as fully deterministic in the same breath.

The breakthrough was to stop assuming the *representation* (the digits/bits of the
numbers) carries the information, and to describe a series by **where its salient
points fall** — its **pivots** — along two axes, time and value (Levels 4–7,
bitácoras 14–18). The finding, robust against every null: the information lives in a
**clock** — the *timing* of pivots, not their sizes. That clock is a self-similar
fractal point process, largely shared across instruments, with sub-diffusive legs.
Level 8 (bitácora 19) turned it into a risk (not return) strategy with an honest
ceiling. Level 9 (bitácora 20) found the clock's *generator*: a self-exciting Hawkes
process, three numbers, strongly self-exciting but sub-critical (branching ratio
n≈0.69).

So the market's behaviour table is not in its prices. It is in the **arithmetic of
when its turning points occur**, and that arithmetic has a short generating program.
Your frontier is to push the *tables and formulae* of that structure further, and to
test the flagship idea in §6.

---

## 3. What is PROVEN — the closed doors (do not re-litigate)

Each of these was established against controls and nulls. Re-running them wastes
time; cite the bitácora instead.

- **Direction is unforecastable.** Daily up/down sign has no deterministic rule and
  no out-of-sample edge. Evidence, four independent angles: contradiction rate 0.66
  vs a rule-110 CA's 0.00 (b06); whole-pattern lookup ~0 coverage, markets never
  revisit a configuration (b12); no deterministic backbone survives a shuffle (b13);
  behaviour-table LZ at shuffle baseline (b14). **Do not try to predict direction.**
- **Cross-sectional "one stock explains another" is dead.** Confounded (co-move 0.56,
  up to 0.83), non-identifiable, and intractable at scale (b11, b12).
- **Exact program / Turing-machine search on the raw price is a dead end.** The price
  path is (near-)incompressible; the shortest program that reproduces it is itself.
  A richer model class only worsens overfitting and identifiability. Algorithmic
  Probability must be aimed at the *structure*, never the raw series (see §6, b20).
- **The exact deconvolution needs exhaustive or locality-bounded data.** It is linear
  in the number of nodes (bit-by-bit essentiality, O(n²·2ⁿ)), but presupposes the
  2ⁿ-row repertoire; the wall is *owning that data*. Locality rescues cellular
  automata; markets have no locality, so the exact route does not apply to them
  (bitácora 01, "Complexity, and the data wall").

Two artifact traps were caught and must never be re-introduced (they are the reason
to trust everything else):

1. **Trend contamination (Level 4).** On multi-decade data the *additive* difference
   |x[t]−x[t−1]| inherits the price level, so a "volatility" unit degenerates into a
   step function (Hurst 0.95, huge fake forecast). Fix: the **scale-free relative
   difference** and the `trend_contamination` guard (`level4/binarise.py`).
2. **Fat-tail marginal artifact (Level 5).** In event time the move-size
   autocorrelation looks like ~0.5 "memory", but it is a mechanical consequence of
   the heavy-tailed marginal — the return-shuffle carries it just as strongly. The
   real signal is the *clock*, which the shuffle does not carry. **Always use the
   return-shuffle null** for anything derived from pivots.

---

## 4. What is TRUE and compressible — the structure you are extending

All measured on 12 multi-decade daily series (`finance/data_long/`), each against the
return-shuffle null.

- **The clock clusters and forecasts.** Pivot timing is self-similar and beats a
  shuffle out of sample (short-wait forecast +0.108 over null, 12/12, p=2.4e-4; b16).
- **The clock is a fractal point process.** Fano-factor exponent α≈0.5 (count-Hurst
  ≈0.75), roughly scale-invariant across reversal scales θ (b17).
- **The clock is largely shared.** Cross-instrument activity correlation 0.48, common
  signal explains R²≈0.45 — but it is *synchronous, not lead-lag predictive* (b17).
- **Sizes carry no memory beyond the fat-tail marginal.** The driver is (near-)i.i.d.
  in event time; the information is purely in the clock (b16).
- **Occurrence gaps obey Benford's law** far better than raw prices (b16) — the
  representation-free encoding is naturally scale-free.
- **Legs are sub-diffusive.** Within a leg, |Δv| ~ Δt^H with H≈0.34 vs the Brownian
  0.5; the *anomaly* (excess over the null) is scale-invariant (b18, b19).
- **The clock has a generator.** A three-number Hawkes (μ, α, β) with branching ratio
  n≈0.69 beats Poisson out of sample 12/12, compresses ~1382 events to 3 numbers, and
  regenerates the fractal clustering (b20). Strongly self-exciting, sub-critical.

These are your raw material. The behaviour *table* of the clock is still incomplete:
you have named columns (density, persistence, Hurst, fractal α, Hawkes n) but not a
single closed-form *formula* that regenerates the pivot occurrence set to the last
digit the way the controlled regime does. **Closing that gap is the prize.**

---

## 5. Open doors — ranked, with concrete first experiments

1. **The oracle / perfect-trader behaviour table (FLAGSHIP — see §6).** Build the
   behaviour table of the *in-hindsight optimal trades*, and test whether it *is* the
   clock. Highest value; start here.
2. **Multi-scale / power-law Hawkes kernel.** The single-exponential kernel
   under-captures the self-similarity (regenerated Fano 0.41 vs real 0.49). A sum of
   exponentials or a power-law kernel should close it and re-open the criticality
   question at finer sampling. This is the literal *behaviour formula* of the clock.
   Code lives in `level9/hawkes.py`; generalise the kernel.
3. **Value-axis symbolic dynamics (the user's prefix idea).** Coarse-grain the value
   axis by significant-digit prefix — *sweep* the coarseness, never fix it — to
   *manufacture recurrence* (raw prices never repeat; coarse symbols do). Then
   recover the symbol→symbol transition structure (a behaviour table on the value
   axis) and the per-symbol recurrence clock (fractal?). This is the twin of the
   time-axis pivot work and is genuinely under-explored. Related field:
   computational mechanics / ε-machines (Crutchfield) — reconstruct the minimal
   generative automaton and measure its statistical complexity.
4. **Soft / approximate gates (the user's "gate + catalyser" idea).** A column close
   to a gate = base gate ⊕ sparse correction, found exactly by Walsh–Hadamard
   (Fourier) analysis or nearest-gate Hamming distance. The CANALISING gate already IS
   a catalyser. Best home: **biological** near-gate genes currently reported as LUT —
   show they are "gate + 1–2 corrections" that compress. Guard: must beat the raw
   look-up table in description length AND beat a shuffle out of sample, else it is
   overfitting. (On markets this will likely be a controlled negative — do it on
   biology first.)
5. **The joint (Δt, Δv) density.** Only the two marginals and two correlations are
   studied. The cross-leg coupling "a long calm precedes a big move" is a proven
   *null* (b18); the coupling lives *within* a leg. Model the full 2-D law.
6. **Clock of the clock, done properly.** A partial hierarchy exists (bursts of
   bursts) but attenuates with depth (b18). A multi-scale Hawkes may explain why.

---

## 6. THE FLAGSHIP: the oracle / perfect-trader behaviour table

The user's idea, sharpened into a rigorous programme — and it hides a beautiful
theorem you should verify first.

**Setup.** For one asset, the "perfect moves" are the in-hindsight optimal buy/sell
points that maximise cumulative return. With unlimited transactions and *zero* cost
this is trivial and useless (buy every up-tick). With a realistic **per-round-trip
cost c**, the optimal policy only trades when a move exceeds c — and the optimal
buy/sell points become exactly the **directional-change pivots at reversal threshold
θ = c**. (Verify this: the optimal-trading-with-fee dynamic program and the
directional-change construction should return the same point set when θ = c. If they
do, you have proved that *the perfect-trader's action points are the pivots at a
threshold set by transaction cost* — a clean, publishable equivalence.)

**Why this matters for behaviour tables.** It means the **oracle occurrence set = the
pivot occurrence set at θ_cost**, so the behaviour table of optimal trading *is* the
behaviour table of the clock, specialised to a cost-determined scale. Suddenly you
have a *supervised target* with an economic meaning, and every clock result inherits
a trading interpretation:

- The clock's self-excitation (Hawkes n≈0.69) becomes: *optimal trade opportunities
  arrive in self-exciting bursts.*
- Forecasting the clock's next event becomes: *forecasting when the next
  cost-covering move will arrive* — the honest tradable question (not direction, but
  timing and sufficiency of the next move).

**Experiments to run (Level 10 candidate):**
1. Compute the oracle points (optimal-trade DP with fee c) for each long series;
   confirm they coincide with directional-change pivots at θ=c. Report the match.
2. Build their behaviour table: gap law, Fano exponent, Hawkes fit — reuse
   `level5`–`level9`. Is the oracle clock the same self-exciting fractal we found?
3. The real test: fit the Hawkes on the first 70% and ask whether its forward
   intensity forecasts the *next oracle event's timing* on the held-out 30%, beating
   a Poisson and a shuffle. If yes, the clock is the behaviour table of tradable
   opportunity; if no, report the honest negative.
4. Cross-asset: do oracle clocks share the common activity signal (b17)? If a
   *market-wide* oracle clock exists, that is a systematic opportunity calendar.

Guardrail specific to this idea: the oracle is computed with look-ahead **by
construction** (it is the answer key). It may be used only as a *target to explain
and to forecast out of sample* — never as a feature. Any forecast must be committed
on past data and validated on the future, against the shuffle. Do not let the answer
key leak into the predictor.

---

## 7. Guardrails — non-negotiable, the reason to trust anything

1. **Agnosticism.** Assume nothing about the origin of the data. The method must run
   unchanged on any numeric sequence. Prefer representation-free, scale-invariant
   constructions.
2. **Compression, not transcription.** A behaviour rule is a discovery only if it is
   strictly shorter than the occurrence set it explains. A column with as many free
   numbers as it reproduces is not a column.
3. **Out-of-sample, against a null.** Commit every regularity on an earlier segment;
   validate on a held-out later segment; compare against a **marginal-preserving
   shuffle** (time-shuffle for bits; **return-shuffle** for anything from pivots — it
   preserves the fat tails and kills only temporal order). A signal no stronger on
   the real data than on its shuffle is a multiple-testing artifact.
4. **Controls that must behave.** A deterministic control (rule-110 CA) must be
   recovered as structured; a random/Poisson control and a GBM must come out null.
   If your instrument does not separate these, it is miscalibrated — fix it before
   believing any market result.
5. **Report the residual and keep the negatives.** Honesty over salesmanship. Two of
   the programme's most valuable results are negatives. State ceilings plainly.
6. **Suspect large effects.** The two artifact traps (§3) both first appeared as
   *exciting* large numbers. When a result looks too good, hunt the confound before
   celebrating.

---

## 8. The codebase, and how to run it

Everything is standard-library Python (deterministic, seeded) except the notebooks,
which need matplotlib/numpy via the registered **CausalBool** kernel (the repo
`../venv`). Layers are self-contained; each level does not touch the ones below it.

- `src/` — the exact deconvolution (Level 0–2). `causalbool.py` (forward model,
  `Network`, `repertoire`), `deconvolution.py` (`essential_variables`,
  `identify_gate`, `deconvolve`, `verify`), `ca_deconvolution.py`, `bnet.py`
  (biological), `finance.py` (loaders, binarisation), `network_generator.py`,
  `reprogramming.py`.
- `level2/`–`level9/` — the order-discovery programme. Most reusable for you:
  - `level5/pivots.py` — directional-change pivots, legs (Δt, Δv). The core object.
  - `level5/occurrence_geometry.py` — fractal dimension, Benford, intrinsic-time
    memory.
  - `level5/controls.py` — `load_long_sequences`, `return_shuffle`,
    `geometric_random_walk`. **Use these nulls everywhere.**
  - `level6/point_process.py` — Fano exponent, activity signal, MFDFA Hurst.
  - `level6/shared_clock.py` — align instruments, common signal.
  - `level9/hawkes.py` — Hawkes log-likelihood, fit, simulate, OOS. Generalise its
    kernel for open door #2.
- `notebooks/` — 9 executed, didactic notebooks (00–08) with embedded plots. Read
  them to *see* every result; run with the CausalBool kernel. Each has a from-anywhere
  bootstrap. `build_*.py` regenerate them.
- `finance/data/` — 23 tickers, 3 years (aligned). `finance/data_long/` — 12
  instruments, ~30+ years (the workhorse). To fetch more daily history: Yahoo v8 with
  explicit `period1`/`period2` unix timestamps and `interval=1d` (NOT `range=max`,
  which silently downsamples to monthly).
- `results/` — one JSON per experiment. `bitacora/` — the scientific logbook, 00–20.
- Data for biology: `../data/bio/raw/*.bnet` (outside this folder).
- Wolfram cross-check (only if you touch the exact core):
  `HOME=/Users/alberto /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script <abs-path>`;
  `$ScriptCommandLine` is empty under `-script`; pass args via environment variables.

Run the full test suite (must stay green):
```
python -m pytest level9 level8 level7 level6 level5 level4 level3 level2 tests -q
```
Current state: **78 tests pass; HEAD b839bfd; 21 bitácoras (00–20)**.

---

## 9. How to document, so the work can be retaken

The previous mind will return and continue from your bitácoras. Leave a trail it can
pick up cold.

- **One bitácora per level/finding**, numbered continuously. The next is
  `bitacora/21_*.md`. Style: British English, no contractions, precise, honest,
  every claim with its null and its residual. State what is strong, what is weak,
  what is a negative. End with a "Verification" section giving the exact commands and
  the test count.
- **Self-contained code layer per level** (`level10/`, `level11/`, …). Do not modify
  lower levels; import and reuse. Standard library only for the core; keep it
  deterministic and seeded. Add a `README.md` and a `test_levelNN.py`.
- **One `--quiet`-capable experiment script per result**, writing a JSON to
  `results/`. Fix repeated warnings at source.
- **Commit per finding**, substantive message (what, against which null, honest
  verdict). Do not add an AI as co-author.
- **Hand back to me:** append to this `TRANSFERENCE.md` a short "STATE AT HANDBACK"
  section at the very end each time you pause — HEAD SHA, one-line confirmed state,
  the single most promising open door, and the one command to reproduce your last
  result. That is the hook the returning mind will grab.

---

## 10. The "feelings" — hard-won taste to inherit

Things that are true but not provable, the intuition distilled from twenty bitácoras:

- **The order is in the *when*, not the *what*.** Every time we looked at values we
  found noise or trend; every time we looked at the *timing and spacing of events* we
  found structure. Follow the clock.
- **Self-similarity is the signature.** Real market structure showed up as
  scale-invariance (across reversal scale θ, across window size, across the amplitude
  bands). If a putative rule only appears at one hand-picked scale, distrust it;
  sweep the scale and demand invariance.
- **Big, clean effects are usually confounds.** Both artifact traps arrived dressed
  as triumphs. Excitement is a smell to investigate, not a result.
- **The shuffle is your conscience.** The return-shuffle (marginal-preserving) is the
  single most important tool in the box. When in doubt, shuffle and re-measure.
- **Negatives are load-bearing.** The proof that direction is unforecastable is what
  makes the clock result meaningful. Do not chase the closed doors; their being shut
  is information.
- **Compression is the whole game.** A behaviour table earns its name only by being
  shorter than what it explains. Three Hawkes numbers standing in for 1382 events is
  worth more than any curve that merely fits.

---

## 11. Your first day

1. Read this file, then `PROTOCOL_order_discovery.md`, then bitácoras 14–20 (the
   order-discovery arc), then run the test suite (expect 78 green).
2. Skim notebooks 04–08 to *see* the clock, the pivots, the Hawkes.
3. Build the flagship (§6): compute the oracle/perfect-trader points, verify they
   equal directional-change pivots at θ=cost, and build their behaviour table. This
   is the highest-value, most novel, and most rigorous next step, and it unifies the
   trading question with the behaviour-table mission without violating any guardrail.
4. If it opens a new door, write `bitacora/21_*.md`, commit, and append a "STATE AT
   HANDBACK" here.

Dare greatly. Shuffle everything. Keep the negatives. Compress or it does not count.

---

## STATE AT HANDBACK

- HEAD: `b839bfd` (Level 9). Working tree: clean except the user's own edits to
  `src/deconvolution.py` (explanatory comments) and `notebooks/00_*.ipynb` — leave
  them.
- Confirmed state: 78 tests pass; the clock is a strongly self-exciting, sub-critical
  (n≈0.69) fractal point process with a 3-number Hawkes generator that beats the
  shuffle out of sample.
- Most promising open door: **§6, the oracle / perfect-trader behaviour table** — and
  the theorem that the perfect trades are pivots at θ=transaction-cost.
- Reproduce the last result: `python level9/exp29_hawkes_clock.py`.

---

## STATE AT HANDBACK (Level 10, 2026-07-13)

- HEAD: Level 10 commit (this finding). Working tree otherwise as before (the user's
  own edits to `src/deconvolution.py` and `notebooks/00_*.ipynb` — leave them).
- Confirmed state: 87 tests pass (78 + 9 new in `level10/`). The flagship (§6) is
  **closed, and the theorem lands exactly**: the in-hindsight optimal trades under a
  per-round-trip cost c ARE the directional-change pivots at threshold θ = c —
  exact containment DC(θ=c) ⊆ oracle (guaranteed by the confirmation geometry
  H/L ≥ 1+θ = 1+c = the profitability threshold; proved, verified 11/12 exact, the
  12th a measure-zero break-even tie), the oracle a 0.4% superset (the greedy-vs-global
  residual). The oracle clock is the Level 9 self-exciting fractal (n=0.685, Fano 0.51,
  OOS +0.055 nats/event 12/12) — reported honestly as confirmation of b20, not a new
  forecast. GBM control reads null. NEW object: transaction cost is a renormalisation
  scale; n(c) is non-monotone, a hump peaking at percent-level costs (0.40→0.685→0.48).
- Most promising open door: **open door #2 — the multi-scale / power-law Hawkes kernel**
  (`level9/hawkes.py`). The single-exponential kernel under-reproduces the clustering
  (Fano 0.41 sim vs 0.49 real, b20) and the n(c) hump/fine-scale softening in b21 is
  partly instrument-limited by the 250-day decay-grid ceiling. A sum-of-exponentials or
  power-law kernel should close both and re-open the criticality question at fine c.
  Second: **open door #3, value-axis symbolic dynamics** (the prefix/ε-machine idea),
  genuinely under-explored.
- Reproduce the last result: `python level10/exp30_oracle_clock.py`.

---

## STATE AT HANDBACK (Level 10 adversarial audit + 100 stocks, 2026-07-13)

- HEAD: the Level 10 audit commit (this finding). 87 tests pass.
- Confirmed state, told straight after a hostile audit (bitacora 22):
  - The bitacora-21 "theorem" (perfect trades = pivots at θ=c) is a **geometric
    identity**, not a market fact — containment ~1.0 on stocks, GBM AND noise/sine
    alike. My b21 framing ("the headline", "closes the flagship") was overselling;
    corrected. Its only worth is interpretive (cost = reversal scale).
  - The DP is provably optimal (200/200 vs brute force). The OOS forecast has **no
    look-ahead leak** (causal pivots score the same) but is therefore **b20 relabelled,
    no new info**.
  - Scaled to **100 freshly-downloaded stocks** (`finance/data_100/`, slimmed+committed):
    the one real market claim — the clock self-excites — **survives**, weaker than the
    12 survivors: n=0.613 vs shuffle 0.014, self-exciting **99/100**, Fano 0.494. OOS
    forecast positive **94/100** (p=2e-21). GBM control reads null. n(c) hump survives
    qualitatively (interior peak 88/100) but soft at the extremes (fine scale
    instrument-limited by the 250-day Hawkes decay grid).
  - Didactic notebook `notebooks/09_oracle_perfect_trader.ipynb` (9 plots, executed
    from a foreign cwd, reads committed slimmed panel + results JSON).
- Most promising open door: **open door #2, the multi-scale / power-law Hawkes kernel**
  — it should lift the OOS/Fano and de-artefact the fine-scale end of n(c), and re-open
  the criticality question. Everything points there now.
- Reproduce the last result: `python level10/exp31_stress_100.py` (needs
  `finance/data_100/`, already committed; or re-fetch with `level10/download_100.py`).

---

## STATE AT HANDBACK (Level 11 — Fourier + multi-scale Hawkes, 2026-07-13)

- HEAD: the Level 11 commit. 95 tests pass (87 + 8 new in `level11/`).
- Confirmed state (bitacora 23), two follow-ups, each vs controls:
  - **Fourier (confirmation, not discovery):** spectral exponent of daily returns
    +0.072 (white; control white noise -0.001), of |returns| -0.320 and of the pivot
    activity clock -0.541 (red; control random walk -1.812). Values are spectrally
    white, the clock is red 1/f — the same split the pivots found, re-derived in a
    second language. No discrete periodic line → nothing new to trade. Fourier
    corroborates, does not rescue.
  - **Multi-scale / power-law Hawkes (HONEST NEGATIVE):** naive power-law kernel (sum
    of exponentials, 3 free numbers), fit by plain ML, does WORSE than the single
    exponential — it slides to gamma≈0, n≈0.11 (near-Poisson) and regenerates Fano
    -0.003 vs single-exp 0.355 vs real 0.512; OOS +0.001 vs single +0.059. Root cause
    (verified, not a bug — reduces exactly to level9 at K=1): the Hawkes likelihood is
    LOCAL, the Fano clustering is GLOBAL; enriching the kernel lets the optimiser walk
    away from the clustering. Open door #2's naive form is closed; the honest next step
    is a clustering-targeted objective (method-of-moments / Fano-matching) or finer
    (intraday) sampling, NOT a fancier kernel fit by likelihood.
  - Notebook `notebooks/09_oracle_perfect_trader.ipynb` extended: survivorship-weakness
    explanation (0.69→0.61, softening-not-collapsing is the credential), the Fourier
    split, and the multi-scale negative — 12 plots, executed from a foreign cwd.
  - **Trading verdict, restated for the user:** NOT a winning return strategy (direction
    unforecastable); only a risk tool (b19 ceiling: Sharpe 0.70→0.73, drawdown/tail cut).
- Most promising open door: a **clustering-targeted fit** of a multi-scale kernel
  (method-of-moments matching the Fano curve), or move to intraday data where the fine
  timescales are populated and the criticality question (n→1) can be re-opened.
- Reproduce the last result: `python level11/exp32_multiscale_and_fourier.py`.

---

## STATE AT HANDBACK (Level 12 — symbolic action dynamics, 2026-07-13)

- HEAD: the Level 12 commit. 101 tests pass (95 + 6 new in `level12/`).
- Confirmed state (bitacora 24), testing the user's "actions-not-direction" idea:
  - **The 'what' is 0 bits, the 'when' is ~1 bit.** Action-type order (buy/sell/buy/sell)
    is forced alternation → conditional entropy 0.0000 bits; the coarse timing symbol
    carries 0.9924 bits. The user's thesis (order is in the when, not the what) confirmed
    exactly and quantitatively.
  - **Two clocks turn out to be one (honest null on asymmetry).** Split the pivot clock
    into the BUY clock (troughs) and SELL clock (peaks): both have n=0.572, both forecast
    OOS +0.09 over shuffle 12/12 — statistically indistinguishable (branching equal to
    6dp; different loglik, so grid quantisation not a bug). The DC construction is
    symmetric under sign-flip, so no entry/exit asymmetry exists to exploit. One
    symmetric opportunity clock, seen twice.
  - **'Half the game' costed:** a predictable clock is risk control, NOT half the money —
    profit is direction × timing (multiplicative), and the direction factor is dead.
- Most promising open door: unchanged — a **clustering-targeted multi-scale kernel** or
  **intraday data** (b23). The symbolic/schema route (Holland wildcards on the timing
  symbols) is unlikely to beat the Hawkes persistence given b16/b20, but a full
  ε-machine reconstruction of the timing-symbol sequence remains formally open (door #3).
- Reproduce the last result: `python level12/exp33_action_symbols.py`.

---

## STATE AT HANDBACK (Level 13 — spacetime deconvolution, 2026-07-13)

- HEAD: the Level 13 commit. 107 tests pass (101 + 6 new in `level13/`).
- Confirmed state (bitacora 25), testing the user's "rotate the plot → scale-free
  (price×time) grid → deconvolve it as a CA/network repertoire" idea:
  - **Coarse-graining fixes the b12 obstruction (real methodological gain):** scale-free
    log-level symbolisation makes market configurations recur — recurrence 0.785→1.000 as
    bins coarsen. The deconvolution is WELL-POSED for the first time (b12 died because raw
    prices never recur).
  - **Control triad, persistence-controlled (raw lift is a trivial-persistence trap → use
    lift-EXCESS over shuffle):** logistic-map control lift-excess +0.418 (instrument
    detects a rule); MARKET lift-excess −0.004 (6/12), contradiction 0.921 = its shuffle
    0.908; GBM null. So the market has NO deterministic rule beyond its marginal, even in
    this scale-free 2-D representation. The "network" the deconvolution returns for a
    market is degenerate; the logistic control's is a real rule.
  - This is the most rigorous form yet of "is a market a cellular automaton" — now
    well-posed — and the answer is no. Order is in the clustering of WHEN (the clock), not
    in a Boolean law over values, at any resolution reached.
- Most promising open door: unchanged — clustering-targeted multi-scale kernel or
  intraday data (b23); the value-axis ε-machine (door #3) is now well-posed to attempt
  but expected null on determinism (may still have compressible *statistical* structure).
- Reproduce the last result: `python level13/exp34_spacetime_deconvolution.py`.

---

## STATE AT HANDBACK (Level 14 — buy/sell behaviour formulae, 2026-07-13)

- HEAD: the Level 14 commit. 115 tests pass (107 + 8 new in `level14/`).
- Confirmed state (bitacora 26), the user's refined idea (the two strands are the BUY
  pattern and the SELL pattern, each with a behaviour table/formula):
  - **No exact closed-form formula** for either pattern (0/100 stocks; cv_gaps≈0.77) —
    the honest controlled-vs-uncontrolled boundary; a periodic control IS flagged exact,
    so the instrument works.
  - **Statistical behaviour formula (3-number Hawkes) earns its name** on 100 stocks vs
    shuffle: compresses ~129×, self-exciting n≈0.456, regenerates gaps (KS≈0.19) and
    ~half the Fano clustering, forecasts OOS +0.026 beating shuffle 82–83/100. Buy and
    sell are symmetric (n 0.456≈0.455).
  - **Direction kept honest:** the two patterns mark direction in HINDSIGHT only (they
    ARE the turns); no forward direction call is licensed (side = trivial alternation,
    timing = weak clock edge = risk control not return).
  - Dedicated notebook `notebooks/10_buy_sell_behaviour_formulae.ipynb` (1 stock → 100 →
    zoom-in "match"; 7 plots; executed from foreign cwd).
- Most promising open door / EXPLICIT NEXT STEP the user asked for: **the fusion equation
  = a mutually-exciting BIVARIATE Hawkes** (buy⇄sell cross-excitation matrix), the
  physics-style merge of the two univariate formulae. Off-diagonal A_bs, A_sb = the
  base-pairing. Fit it, test whether the join carries more than the two apart, OOS vs
  shuffle. This is `level15/` — the "first two separate equations, then fuse" the user
  described. (Prior: cross-terms will mostly encode the trivial alternation; test honestly.)
- Reproduce the last result: `python level14/exp36_behaviour_formulae.py`.
