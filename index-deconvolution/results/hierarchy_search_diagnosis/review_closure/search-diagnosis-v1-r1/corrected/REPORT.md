# search-diagnosis-v1-r1 — report (corrected, reporting revision `report-r2`)

> **Corrected copy.** Computations: attempt `a1`, unchanged. The original
> `search-diagnosis-v1-r1/REPORT.md` is kept unchanged as a historical artifact. This
> copy answers Codex review R1–R3. Every number is unchanged from a1 and is read from
> `report-r2/outputs/`, regenerated from a1's saved records by the repaired reporting
> pipeline (0 numeric differences: `report-r2/outputs/comparison_with_a1.json`). Artifact
> names below refer to the a1 run directory unless prefixed `report-r2/`; `analysis/*`
> and `DECISION.json` have byte-for-byte equal numbers in `report-r2/outputs/`.

Date: 2026-10-03. Developer/executor: Claude Code. Supervisor: Codex.
Evidence role: **`posthoc_diagnostic`** on the accepted run `search-confirm-v2-r1`
(scientific freeze `0f0a72ef…1d49`). Every input was already encoded and inspected.
Nothing here is a confirmation, a superiority claim or a causal identification.

Every number below is read from an artifact of this run; the artifact is named beside
each table. Weighting, wherever an aggregate appears: base/ragged pair mean, unit mean
within a cell, equal cell weights. No intervals, p-values or significance decisions.

## 0. Completion and validity

| section | intended | completed `ok` | other | artifact |
|---|--:|--:|--:|---|
| D1 cases / rows | 1,792 / 28,672 | 1,792 / 28,672 | 0 problems | `d1/d1_checks.json` |
| D2 jobs (208 strings × B0, B8) | 416 | 416 | 0 | `analysis/resources.json` |
| D3 jobs (176 strings, 32 subsets each) | 176 | 176 | 0 | `analysis/resources.json` |
| D4 jobs / conversion records | 576 / 1,152 | 576 / 1,152 admissible | 0 unavailable | `analysis/d4_summary.json` |

Evidence gates (`DECISION.json` → `gates`): all jobs `ok`; B0 deterministic mismatches
**0** of 208; supplied references reproduced **176/176** (archive SHA-256 and length);
H − C identity failures **0** of 1,152; D1 problems **0**. No timeout, RSS breach,
worker error, decode failure or graph-limit rejection occurred in any section.
Resources (`analysis/resources.json`): D2 worker wall total 112.7 s, maximum 2.28 s,
peak RSS maximum 65.7 MiB; D3 11.7 s / 0.16 s / 28.5 MiB; D4 26.7 s / 0.06 s / 26.2 MiB —
against limits of 30 s and 1 GiB per worker.

D1 reproduces the **accepted** primary point estimate from the saved rows exactly:
`0.005605234982532739` over 21 cells (`d1/d1_tables.json` →
`accepted_primary_reproduction`). This is a preservation check, not a new endpoint.

## 1. D1 — where the bytes go (all 1,792 saved cases)

Artifacts: `d1/d1_tables.json` (per-cell tables), `d1/d1_cases.json` (per case:
bits of all 16 methods, status, portfolio winner, the full arm's selected stage,
B stop/cap fields, and eight exhaustive cost buckets for the six HID arms and the
portfolio, each summing to 8 × archive bytes).

Across the 76 family-size cells, the full arm is shorter than the portfolio on average
in 18, tied in 8 and longer in 50 (notebook 18, §2). The losing cells fall into three
groups by the portfolio's winning codec:

* **period / pair grammar** (most F01, F02, F03 and F05 cells; also transfer F10,
  outside D4): HID's selected stage is the legacy stage `L` in every case of F01 and
  F05 and of F03 at 1,024 and 4,096 bits (confirmation F03 at 256 bits selects `B` and
  loses to zlib); D4 measures the F01–F05 cells.
* **zlib, boundary families** (F12 at 4,096 and every transfer size; S02 at 65,536):
  the selected stage is `B` in confirmation F12 and mostly in S02; D2/D3 measure these.
* **bernoulli / context / lzma / zlib on F08–F11**: the largest per-bit losses in the
  run (for example confirmation F08: −0.45 bits per input bit). **No diagnostic in this
  phase targeted these losses.** F11 (with F06 and F07) was sampled only as a D2 control
  at 4,096 and 65,536 bits; F08–F10 appear only in D1; none was a D3 or D4 target.

The bucket map makes the period-cell loss concrete. In confirmation F01 at 256 bits the
portfolio spends envelope 0.2486 + `other_payload` 0.1429 bits per input bit, while the
full HID archive spends the same envelope plus DAG count/opcodes 0.146, parameters
0.1522, references 0.0839, literal payload 0.112 and padding 0.0301 (notebook 18, §2).
D1 describes where bytes go; it does not by itself identify a cause.

## 2. D2 — boundary budget ×8 (176 targets, 32 controls)

Artifacts: `analysis/d2_rows.json`, `analysis/d2_summary.json`, job records
`jobs/D2/*.json`, output archives under `archives/`.

**B0 reproduces the frozen stage exactly.** For every one of the 208 strings, B0's
`archive_bits`, `cuts`, `segments`, `counts`, `rounds`, `stop_reason`, `cap_hit` and
`unresolved_refinement` equal the saved full-arm stage-B telemetry; where the saved
final archive came from B (112 targets) B0's bytes are identical to it.

**B8 changes one string.** B0 hit a cap on 3 strings (`stress-S02-4096-4001-ragged`,
`stress-S02-65536-4000-ragged`, `transfer-F12-131072-5000-base`, all `root_trial_cap`).
With eight times the caps, all 208 B8 jobs stop by `no_strict_improvement`, and the
output differs from B0 on exactly one string:

| case | n | saved full H | B0 | B8 | portfolio |
|---|--:|--:|--:|--:|--:|
| `stress-S02-4096-4001-ragged` | 4,099 | 2,392 | 2,392 | **2,352** | 3,088 |

Its diagnostic opportunity is 40 bits on 4,099 input bits; the equal-cell mean
opportunity over the eight target cells is 7.62 × 10⁻⁵ bits per input bit, non-zero in
one cell (S02 4,096: 0.000610). The other two cap-hit strings gain nothing from the
larger caps. No control changes (0 of 32).

| cell | complete units | mean opportunity | B8 < H | B0 stop | B8 stop |
|---|--:|--:|--:|---|---|
| confirmation F12 256 | 20/20 | 0 | 0 | 40 no_strict_improvement | 40 no_strict_improvement |
| confirmation F12 1024 | 20/20 | 0 | 0 | 40 no_strict_improvement | 40 no_strict_improvement |
| confirmation F12 4096 | 20/20 | 0 | 0 | 40 no_strict_improvement | 40 no_strict_improvement |
| stress S02 4096 | 8/8 | 0.000610 | 1 | 15 no_strict + 1 root_trial_cap | 16 no_strict |
| stress S02 65536 | 8/8 | 0 | 0 | 15 no_strict + 1 root_trial_cap | 16 no_strict |
| transfer F12 16384 | 4/4 | 0 | 0 | 8 no_strict | 8 no_strict |
| transfer F12 65536 | 4/4 | 0 | 0 | 8 no_strict | 8 no_strict |
| transfer F12 131072 | 4/4 | 0 | 0 | 7 no_strict + 1 root_trial_cap | 8 no_strict |

Control cells (F01, F06, F07, F11 at 4,096 and 65,536; 16 units): opportunity 0 and
B8 = B0 everywhere. **Reading:** on these populations the specific B0→B8 increase changed
one output, and every B8 run stopped by `no_strict_improvement` rather than at a cap. That
is a result about this cap increase; it does not exclude resource limitations under other
searches or other budgets.

## 3. D3 — the supplied-cut subset space (truth-assisted, 176 targets)

Artifacts: `analysis/d3_rows.json` (per string: every subset's cost, every edge with
eligibility, strictness and delta, the three minima, barrier classification, charges),
`jobs/D3/*.json`, archives. Every saved list has exactly 5 distinct cuts, so every
string has 32 subsets (5,632 in total), all priced with one B0 instance per string,
all decoded. The full-cut subset reproduces the saved reference archive in 176/176.

Definitions: H = saved full HID bits, P = saved portfolio bits; "all", "eligible",
"strict" = cheapest subset over the whole space, over subsets reachable from the empty
partition by eligible one-cut edges (split segment ≥ 64 bits, positive children, ≤ 8
segments), and over those reachable by edges that also strictly shorten the archive.

| cell | strings | H > P | all < H | strict < H | all < P | strict < P | barriers | median (H − all)/n |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| confirmation F12 256 | 40 | 0 | 0 | 0 | 0 | 0 | 0 | −0.1243 |
| confirmation F12 1024 | 40 | 0 | 9 | 9 | 28 | 28 | 0 | −0.0312 |
| confirmation F12 4096 | 40 | 40 | 40 | 34 | 40 | 32 | 8 | +0.0840 |
| stress S02 4096 | 16 | 2 | 5 | 3 | 16 | 14 | 2 | −0.0020 |
| stress S02 65536 | 16 | 6 | 9 | 9 | 16 | 16 | 0 | +0.0054 |
| transfer F12 16384 | 8 | 8 | 8 | 7 | 8 | 6 | 2 | +0.1201 |
| transfer F12 65536 | 8 | 8 | 8 | 2 | 8 | 2 | 6 | +0.0903 |
| transfer F12 131072 | 8 | 8 | 8 | 4 | 8 | 4 | 4 | +0.0835 |

(`analysis/flags.json` → `restricted_path_barrier_observed.by_cell` and
`effect_H_minus_cheapest_all_per_input_bit_by_cell`; "all < H" is the same as
"eligible < H" in every string because there are **0 eligibility obstructions**.)

* In all **72** strings where the full arm loses to the portfolio, a supplied-cut
  partition in the unchanged leaf language is shorter than the saved full archive,
  and in each of them it is also shorter than the portfolio.
* **Restricted path barriers: 22 strings**, every one a **positive-cost step**
  (0 equality barriers). In the drawn example (`transfer-F12-65536-5001-base`,
  notebook 18 §4) the strict path stops at 31,120 bits; the next eligible edge adds the
  one-bit-adjacent supplied cut at +8 bits, after which the edges are strict down to
  22,480 bits, below both H (27,896) and P (23,272).
* Among the 87 strings with a supplied partition shorter than H, the cheapest strictly
  reachable subset is already shorter than H in 68. Strict reachability along some
  supplied-cut path does not show that B's automatic greedy path could reach that state.
* Descriptive, post-hoc: of the 252 supplied cuts in those 68 best strictly reachable
  subsets, 129 lie within 8 bits of a cut of the archive B0 **returned** and 123 do not
  (`report-r2/outputs/flags.json` → `descriptive_returned_B0_cut_proximity`; a1 name
  `descriptive_B0_cut_location`). The statistic reads the returned archive's cut tuple
  (`jobs/D2/*B0.json` → `info.cuts`), not the cuts B proposed or evaluated: a supplied
  position may have been proposed and rejected on an earlier partition. It measures
  proximity to returned cuts, not proposal coverage, and cannot rank proposal location,
  accepted path, refinement and leaf construction as causes.

This space is exact only over at most five supplied cuts and B's shortest-period leaf
heuristic. It is not an optimal segmentation, not a bound over HID descriptions, and not
proof that an automatic path meets the same barriers. The cuts come from generator
metadata; they never entered B0 or B8.

## 4. D4 — the saved baseline proposals written in HID (576 strings, 1,152 records)

Artifacts: `analysis/d4_rows.json` (per record: H, T, C, portfolio, both signed terms,
identity check, complete translated and baseline bucket ledgers), `analysis/d4_summary.json`,
`jobs/D4/*.json`, translated archives.

All 1,152 translations are admissible (≤ 4,096 rules, depth ≤ 64) and decode to the
saved input; H − C = (H − T) + (T − C) holds exactly for all of them.

* **No admissible translation is shorter than the saved full archive** (period 0/576,
  pair grammar 0/576): `missed_baseline_structure_observed = false`.
* **Every translation is longer than its own baseline** (576/576 each):
  `proposal_representation_penalty_observed = true`. Absolute T − C: period median 96
  bits (minimum 16, maximum 6,160); pair grammar median 472 bits (200 to 10,656)
  (`flags.json` → `absolute_T_minus_C_bits`).
* Period translations by shape (`d4_rows.json`): exact repeat, 46 records, T − C 40–48
  bits; repeat plus ragged tail literal, 350 records, 96–352 bits (median 112); a single
  literal when fewer than two copies fit, 180 records, 16–6,160 bits. The 6,160-bit
  record (`transfer-F05-65536-5003-base`, p = 59,392) is the specified literal case:
  the period codec sends p bits and tiles, the translation sends all n bits.
* Pair-grammar translations cost more per rule: each binary rule becomes a CONCAT with
  an opcode and an arity field besides its two references, and the two terminals become
  LITERAL rules; the mean bucket differences are references +928, opcodes +291 and
  parameters +283 bits per record.

**Loss decomposition where the translated method won the portfolio** (`flags.json` →
`d4_loss_decomposition_where_portfolio_winner_was_translated`): 386 strings; HID
loses on 367; on **282** of them H = T in **length** — the saved full archive has exactly
the translated length, so its loss to that baseline equals T − C arithmetically; on 85,
H < T (HID found something shorter than the translation but still longer than the
baseline). Equal length is not an equal proposal: of the 282, **261** are byte-identical
to the translation and **21** differ in bytes (`report-r2/outputs/key_numbers.json` →
`d4_hid_loses_H_eq_T_identical_bytes`, `…_different_bytes`; list in the supervisor's
`audit.json`). Neither case shows that no search change in the frozen language could do
better: D4 prices the translated proposal only.

| cell | winner period / pair | HID loses | H = T | H < T | mean (T−C)/n period | mean (T−C)/n pair |
|---|--:|--:|--:|--:|--:|--:|
| confirmation F01 256 | 40 / 0 | 40 | 36 | 4 | 0.3845 | 1.0936 |
| confirmation F01 1024 | 40 / 0 | 40 | 40 | 0 | 0.0919 | 0.3234 |
| confirmation F01 4096 | 40 / 0 | 40 | 40 | 0 | 0.0251 | 0.0920 |
| confirmation F02 256 | 15 / 0 | 15 | 10 | 5 | 0.2485 | 1.9371 |
| confirmation F02 1024 | 20 / 0 | 20 | 20 | 0 | 0.0803 | 0.7493 |
| confirmation F02 4096 | 20 / 20 | 40 | 10 | 30 | 0.0230 | 0.2290 |
| confirmation F03 256 | 0 / 0 | 0 | 0 | 0 | 0.2019 | 1.5736 |
| confirmation F03 1024 | 40 / 0 | 40 | 20 | 20 | 0.1872 | 0.5032 |
| confirmation F03 4096 | 40 / 0 | 40 | 38 | 2 | 0.0449 | 0.1350 |
| confirmation F05 256 | 16 / 0 | 10 | 8 | 2 | 0.1768 | 1.0408 |
| confirmation F05 1024 | 9 / 0 | 7 | 2 | 5 | 0.0540 | 0.3191 |
| confirmation F05 4096 | 6 / 0 | 4 | 2 | 2 | 0.0183 | 0.1082 |
| transfer F01 16384 | 8 / 0 | 8 | 8 | 0 | 0.0067 | 0.0275 |
| transfer F01 65536 | 8 / 0 | 8 | 8 | 0 | 0.0016 | 0.0069 |
| transfer F01 131072 | 8 / 0 | 8 | 8 | 0 | 0.0009 | 0.0033 |
| transfer F02 16384 | 4 / 4 | 8 | 4 | 4 | 0.0048 | 0.0858 |
| transfer F02 65536 | 4 / 2 | 6 | 4 | 2 | 0.0012 | 0.0541 |
| transfer F02 131072 | 4 / 4 | 8 | 2 | 6 | 0.0009 | 0.0377 |
| transfer F03 16384 | 8 / 0 | 8 | 8 | 0 | 0.0093 | 0.0348 |
| transfer F03 65536 | 8 / 0 | 8 | 6 | 2 | 0.0053 | 0.0094 |
| transfer F03 131072 | 8 / 0 | 8 | 8 | 0 | 0.0021 | 0.0045 |
| transfer F05 16384 | 0 / 0 | 0 | 0 | 0 | 0.0037 | 0.0333 |
| transfer F05 65536 | 0 / 2 | 0 | 0 | 0 | 0.0166 | 0.0078 |
| transfer F05 131072 | 2 / 6 | 1 | 0 | 1 | 0.0005 | 0.0044 |

The penalty is mostly a fixed per-archive structural cost, so its per-bit size falls with
n (period, F01: 0.3845 at 256 bits to 0.0009 at 131,072). Under the accepted equal cell
weights, the small-size cells carry it into the primary estimate. T − C is the cost of
**this** translation of **this** proposal; it does not show that no shorter HID
description exists, and H − T and T − C are not added across populations to explain
the accepted primary estimate.

## 5. Flags

| flag | value | prevalence | effect | denominator |
|---|---|---|---|---|
| `budget_opportunity_observed` | true | 1 target string (S02 4096 cell) | 40 bits; equal-cell mean 7.62e-5 /bit | 176 targets, all B8 complete; controls 0/32 changed |
| `restricted_path_barrier_observed` | true | 22 strings, all positive-cost steps | median (H − all)/n per cell in §3 | 176 strings, 5,632 subsets; 0 eligibility obstructions |
| `missed_baseline_structure_observed` | false | 0 | — | 1,152 admissible records |
| `proposal_representation_penalty_observed` | true | 1,152 records (proposal-specific) | period median 96 bits, pair median 472 bits | 1,152 admissible records |

Recommendation (corrected `DECISION.md`): **BOTH_SEPARATELY**, exploratory.

## 6. What was learned and what was not

Learned, within these populations: the B0→B8 cap increase changed one output of 176
targets; the supplied-cut space in the unchanged leaf language contains partitions
shorter than both the full archive and the portfolio in every losing boundary-family
string, and in most strings the best such partition is strictly reachable from the empty
partition over supplied cuts; on period/grammar cells the saved full archive usually has
exactly the translated length (mostly, not always, the same bytes), so the loss there
equals that translation's measured penalty.

Not learned: why B stops where it does (imprecise cuts, unproposed cuts, rejected
proposals, the accepted path, or the shortest-period leaf heuristic) — returned cuts
cannot separate these; whether a shorter HID description of the period strings exists;
the cause of the 85 losses with H < T; the cause of the F06–F11 losses (F08, F09 and F11
carry the largest per-bit losses; F06, F07, F11 appear only as D2 controls, F08–F10 only
in D1); and anything about unfamiliar families or new draws.
