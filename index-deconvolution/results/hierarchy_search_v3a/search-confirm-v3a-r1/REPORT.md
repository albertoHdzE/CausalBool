# HID-search-v3a report: four refinement seeds against one (search-confirm-v3a-r1)

Freeze `05dd799d154e5e53a36bac7dca49f0438ca27b58b2df94c045eeca2fa6dd69e5`. Every number
below is copied from a saved artifact named in brackets. Status: **ready for Codex
review; not yet accepted**.

## Primary result: HARMFUL

On the six declared target cells, refining the four best distinct coarse partitions
(`hid_refine4`, k = 4) produced **longer** complete archives than the accepted one-seed
method (`hid_full`, k = 1). The paired, equal-cell mean of
(bits(hid_full) − bits(hid_refine4)) / n is **−0.0063290600504822** bits per input bit,
with two-sided 99% percentile interval **[−0.00833260223670385, −0.004177554260442437]**
(10,000 draws, seed 55001, 120 of 120 paired units, 240 target strings) [DECISION.json].
The upper bound is below zero, so the prespecified reading is HARMFUL. Evidence is
engineering-valid and complete; no HID job fell back to raw, no baseline was censored,
and no row is missing [summary.json#validation, verification.json].

The independent audit re-read 2,816 of 2,816 encoder archives with zero problems and
recomputed the point estimate, the six cell means and the interval from archive
bytes; all three agree with the saved decision [arithmetic_audit.json].

## Six cells (descriptive; the interval above is the only inference)

| Cell | Unit mean saving | Strings better / tie / worse (of 40) | Units better / tie / worse (of 20) |
|---|---:|---:|---:|
| boundary · F12 · 4096 | −0.013471845267138327 | 0 / 14 / 26 | 0 / 0 / 20 |
| boundary_large · F12 · 16384 | −0.02968636473938946 | 0 / 15 / 25 | 0 / 0 / 20 |
| boundary_large · F12 · 65536 | 0.0 | 0 / 40 / 0 | 0 / 20 / 0 |
| boundary_large · F12 · 131072 | 0.0 | 0 / 40 / 0 | 0 / 20 / 0 |
| boundary_stress · S02 · 4096 | 0.006880584441327153 | 18 / 17 / 5 | 12 / 5 / 3 |
| boundary_stress · S02 · 65536 | −0.001696734737692562 | 0 / 25 / 15 | 0 / 10 / 10 |

[summary.json#cells]. The **beneficial** cases are confined to S02 at 4,096 bits; the
largest single gain is `boundary_stress-S02-4096-8011-ragged` (0.12686020980727006 bits
per input bit). The **harmful** cases concentrate in F12 at 4,096 and 16,384 bits; the
largest single loss is `boundary_large-F12-16384-7018-base` (−0.0537109375), where k = 1
selected stage B and k = 4 ended with stage L's archive [tables/per_string.csv]. Of the
71 target strings where k = 4 was worse, 25 changed the selected stage from B to L and 46
stayed with B; all 18 improvements stayed with B [tables/per_string.csv].

The eight control units (F01, F06, F07, F11 at 4,096 bits) are tied in all 16 strings;
no control changed [summary.json#controls, #changed_controls]. Controls may change in
principle and were not a zero-change promise.

## What the search did (cost and search diagnostics, not mechanism)

| Quantity (256 strings per arm) | hid_full (k = 1) | hid_refine4 (k = 4) |
|---|---:|---:|
| B stop: no strict improvement | 248 | 36 |
| B stop: leaf_length_charge_cap | 0 | 219 |
| B stop: root_trial_cap | 8 | 1 |
| Selected stage B / L / G / raw | 133 / 111 / 4 / 8 | 108 / 136 / 4 / 8 |
| Commits (total) | 576 | 323 |
| Trial requests (events, total) | 98,171 | 110,590 |
| Newly serialized admissible (total) | 90,791 | 81,739 |
| Cached requests (total) | 7,372 | 28,631 |
| Distinct proposed cuts (total) | 72,466 | 75,078 |
| Returned cuts (total) | 577 | 511 |

[summary.json#hid_telemetry, #trace]. A cap exit is a normal deterministic outcome
that returns the best complete archive serialized so far. Under the shared caps, the
four seeds' refinements spent the shortest-period length charge (256 n) in 219 of 256
strings, so the k = 4 search committed fewer rounds. This co-occurs with the loss; the
design does not identify it as the cause. Wall and RSS were measured with the trace
observer on (instrumented): the largest HID worker wall was 10.87 s (k = 1) and 11.2 s
(k = 4) against the 30 s limit, with peak RSS 287 MiB and 286 MiB against 1 GiB
[summary.json#resources].

Against the nine-baseline portfolio (descriptive only, all constituents available for
all 120 units), the equal-cell means are −0.03977557690580706 (k = 1) and
−0.04610463695628927 (k = 4): on these cells both HID arms are longer than the best
baseline [summary.json#versus_portfolio]. This is not a portfolio test.

## Development (inspected inputs; no gate on efficacy)

All 1,792 retained search-v2 strings were re-encoded by `hid_full`: 1,792 of 1,792
archives are byte-identical to the accepted ones, with zero differences across the
deterministic fields and timing-stripped telemetry, and the configuration dictionary
and hash are unchanged [../development/compatibility.json]. On the 176 inspected
development targets, k = 4 was better on 28, tied on 104 and worse on 44 strings, with
equal-cell mean −0.005369688185455944 [../development/development_summary.json]. The
direction is the same as the prospective result, on inspected data.

## Scope and limits

* One algorithm change (k = 1 to k = 4, everything else fixed) on one fixed mixture of
  six cells. Not evidence about other families, sizes, caps or seed counts, and not a
  claim about the nine-method portfolio.
* Fresh instances of familiar generators (F12, S02), not unfamiliar families.
* A complete-archive code length under one fixed language and resource policy; not
  Kolmogorov complexity, not causal identification, not generator recovery.
* The trace describes what the search proposed, evaluated and returned; no prospective
  comparison with true cuts was made.
* The accepted search-v2 conclusion is unchanged by this study.
