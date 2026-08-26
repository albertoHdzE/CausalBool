# Level 18 — Individual vs universal clock model; prediction walkthrough

**Purpose.** Decide individual-vs-universal honestly: fit per-stock Hawkes
models vs one universal shape (per-stock baseline only) on the first 70% of
time; compare forecasts on the held-out 30%. Companion walkthrough turns the
clock model into day-level predictions and accumulated profit.

**Key results (qualitative).** Forecasting: the universal model wins — one law
beats a hundred fits. Trading: neither beats buy-and-hold (the honest negative).
The walkthrough's edge is real and lives at precise timescales, stated with its
tolerances in the bitácoras.

**Provenance.**
- Experiments: `exp40_individual_vs_universal.py`, `exp41_clock_prediction.py`
- Owning bitácoras: `bitacora/30_level18_individual_vs_universal.md`,
  `bitacora/31_level18_clock_prediction_walkthrough.md`
