# Bitácora 01 — Reference parity: the port is exact

**Date:** 2026-08-18
**Status:** complete. 19 tests, all passing.
**Ledger entries produced:** C1–C4.

---

## 1. What this step was for

Nothing in this package is worth measuring until the port is known to be exact.
Every comparison planned in Phase 1 is against numbers produced by
`reference/gwp3/gwp3_pipeline.py`; if the ported loader, splitter or discretiser
deviates by so much as a rounding, the comparison measures the port and not the
method. This is therefore a gate and not a convenience.

## 2. The environment is a scientific parameter, not plumbing

The first substantive decision was not about code. Baum-Welch is an iterative
optimiser over a likelihood surface with local optima; which optimum it lands in
depends on the linear-algebra stack underneath it. A first environment built from
the loose bounds in `pyproject.toml` resolved to numpy 2.5.2 and pandas 3.0.5,
against the GWP3 environment's numpy 2.2.6 and pandas 2.3.3 — and pandas 3.0
changes `groupby` semantics that `order_states` depends on for the state
ordering.

Rather than discover later that a discrepancy was environmental, the environment
was pinned to the GWP3 versions exactly, verified by inspecting
`GWP_1/RiskManagement/GWP3/.venv/lib/*/site-packages`. Four libraries already
matched (hmmlearn 0.3.3, scikit-learn 1.9.0, pgmpy 1.1.2, Python 3.13.12); four
were downgraded to match (numpy, pandas, scipy, matplotlib). `pyproject.toml`
now carries pins, not lower bounds, with the reason recorded in a comment.

This is worth stating because it is a general point about reproducibility, and
the GWP3 report makes the same point from the other side: §7, claim 5, observes
that the hidden Markov library Alvi used is no longer maintained, which forced
both GWP2 and GWP3 to substitute a different implementation, and that
"reproducibility claims resting on a specific software stack decay quite
quickly". We have now paid that cost once deliberately rather than discovering it
in a result.

## 3. What was checked

**3,124 independent numbers**, all identical to `reference/gwp3/results.json`
at 1e-4 absolute tolerance — and no cell came close to needing the tolerance.

| Object | Numbers | Covers |
| --- | --- | --- |
| `hmm_parity`, seven series | 161 | transition matrix, initial distribution, state means, persistence, log-likelihood, emission probabilities |
| `hmm_gaussian`, seven series | 161 | as above, with Gaussian means and standard deviations in place of emission probabilities |
| Split summary | 30 | GWP3 Table 3 in full |
| Decoded regime labels | 2,772 | 198 months × 7 series × 2 emission schemes, split across all three windows |

Agreement on the fitted parameters simultaneously certifies the restart policy
(ten Baum-Welch restarts, highest likelihood retained), the sticky Dirichlet
prior, the three-standard-deviation return cap, the state ordering by mean
change, and the emission scheme. Agreement on the decoded labels certifies the
filtered decoder on top of all of that.

Six of the fifteen inherited anchors are additionally re-derived without
consulting the reference file at all: the 199 × 7 panel, the 139/30/30 split at
its stated boundaries, parity persistence of exactly 0.000 with 189 switches,
Gaussian persistence 0.742 with 52 switches, the Table 9 regime economics to four
decimals, and the Table 5 window composition to one decimal.

## 4. The control on the control

Protocol rule R3 requires that an analyser be shown to detect what it claims to
detect. The analyser here is the truncation-invariance check that enforces strict
causality (rule R1): truncating the sample must leave every earlier decoded label
untouched, because a filtered decoder cannot see the future.

The first version of that check used a single truncation at month 120. A leaky
whole-window Viterbi decoder was then run through the identical check as a
positive control, and it changed **only 1 of 833 labels** at that cut. The test
would have passed a decoder that leaks. That is a near miss and it is recorded
here as such: the check was luck, not evidence.

The test was rewritten to sweep five truncation points, and the positive control
was promoted into the suite as `test_the_causality_test_has_teeth`, so that any
future weakening of the invariance check is caught by a test that must fail on a
leaky decoder. The filtered decoder changes zero labels at every cut.

This is the third artefact-class near miss in the wider programme, after the
trend-contamination trap at Level 4 and the fat-tail-driver trap at Level 5. In
all three cases the control caught what the intuition did not. It is also the
exact error class GWP3 caught in Alvi — a smoothed decode producing a nominal
100 per cent one-month-ahead accuracy — which is why the guard is a permanent
part of the suite rather than a one-off check.

## 5. What this does and does not license

**Licensed.** Every subsequent comparison against the GWP3 discretised frames.
Those frames are the shared input to both the belief network and the index-set
network, so a Phase 1 comparison now differs from GWP3 in exactly one component:
the model.

**Not licensed.** The belief network itself. `results.json` also holds
`validation_grid_A`, `validation_grid_B`, `baseline_k2_A`, `selected_A`,
`selected_B`, `modelA`, `modelB`, `modelC`, `cpd_forecast_B`, `benchmarks_test`,
`inference`, `directional`, `strategy` and `margin_search`, none of which has
been ported. Those are the comparison targets of Phase 1, and porting them is a
separate gate with its own parity test.

## 6. Incidental observations

- `hmmlearn` emits "Model is not converging" on a number of restarts. This is
  benign under the restart policy — the highest-likelihood solution is retained
  and the discarded restarts are exactly the ones that failed to improve — and
  GWP3 suppressed it globally with `warnings.filterwarnings("ignore")`. It is
  deliberately *not* suppressed in this package's library code: a silent
  optimiser is not something to inherit.
- The decoded frames lose the first month to differencing, so the training window
  contributes 138 rather than 139 decoded rows. GWP3's Table 5 reports 138
  training months for the same reason. The tests assert the row counts rather
  than assuming them.

## 7. Next

The Phase 1 feasibility gate (protocol §2, Gate 1.0), on the frames now
certified: contradiction rate and state-space coverage on the 139-month training
window, with a rule-110 positive control run through the identical analyser. Its
falsification criterion is already fixed and will not be relaxed.
