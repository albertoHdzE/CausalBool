# Next-protocol drafts after search-diagnosis-v1 (for supervisor review; corrected, `report-r2`)

> **Corrected copy** answering Codex review R1–R2. The original
> `search-diagnosis-v1-r1/NEXT_PROTOCOL_DRAFT.md` is kept unchanged as a historical
> artifact. Neither draft is approved for implementation or confirmation; each needs
> its own reviewed protocol.

Status: **draft only.** No seed has been generated, no reserved namespace touched, no
source version implemented. The (exploratory) recommendation is `BOTH_SEPARATELY`; the
two drafts below are independent studies, each with exactly one change, its own freeze
and its own review. Keeping them in separate source versions is a design preference for
clean contrasts, not a claim that a combined version could not be attributed (controlled
ablations can identify effects). Suggested order: Draft A first (corrected `DECISION.md`,
"Priority").

Common to both drafts:

* Start from the active source with the approved **R1 median patch** applied
  (`R1_diagnostics_median_repair.patch`, SHA-256 `e8da5c6b…96c5`) before the freeze, as
  the closure acceptance requires.
* Exposure inventory: every string of `search-confirm-v2-r1` (1,792 cases), its
  development/pilot roles and every string used in `search-diagnosis-v1` is **inspected**.
  They may be used for development and regression only, never for confirmation.
* Confirmation needs a new reserved namespace, generated only after the freeze, with
  the existing generators and the existing case-ID scheme. Names are proposed below;
  nothing is generated.
* Resources: the existing 30 s / 1 GiB per worker, at most two workers, a declared
  cumulative allowance, a new execution ledger, timeouts and errors kept in denominators.
* Analysis reuses `report.py` / `report_v2.py` owners (paired cell-stratified bootstrap,
  equal cell weights). No new statistics owner.

---

## Draft A — search: refine several coarse trials per boundary round

**Question.** Does letting stage B refine more than one coarse trial per round make it
propose the boundary positions it currently misses, and does that shorten the full
archive on the boundary families?

**Single change.** In `BoundarySearch.run` (owner `hierarchy/segmentation.py`), refine
the **k = 4 best distinct coarse trials** of each round (ranked by the existing key
`(archive length, parent start, cut, bytes)`) with the existing five-level refinement,
instead of only the best one; commit the best refined trial if strictly shorter, as now.
Everything else is unchanged: coarse grid, eligibility, leaf builder, strict rule,
tie-breaking, stopping, and the **B0 caps** (512 roots, 2,048 leaves, 256·n). Cap hits are
reported, not tuned.

**Why this change (a hypothesis to investigate, not an identified cause).** D2: the
B0→B8 cap increase changed 1 of 176 target outputs. D3: in all 72 losing boundary-family
strings a supplied partition is shorter than H and P, and the best strictly reachable
supplied-cut subset beats H in 68 of 176 strings. Of the 252 supplied cuts in those 68
subsets, 123 have no cut of B0's **returned** archive within 8 bits. That is proximity to
returned cuts: it cannot show which cuts B proposed, so it does not establish that cut
proposal is the obstacle rather than the accepted path, refinement or leaf construction.
The change tests one candidate — wider refinement of proposals — without touching the
language or budgets.

**Arms.** `hid_full` (frozen HID-search-v2 bytes, rerun) versus `hid_full_A` (identical
except the change); the nine-codec portfolio unchanged.

**Development (inspected strings only).** On the 176 D3 targets, pre-register before
running: (i) proposal coverage measured **directly** — the fraction of supplied cuts within
8 bits of at least one cut that B *proposed* (and, separately, *evaluated*) in any round,
read from an explicit per-round proposal log that the future protocol must specify and
that `search-diagnosis-v1` did not record (no new telemetry jobs were run for this
closure); (ii) the share of strings where `hid_full_A` is shorter, and longer, than
`hid_full` (a different B path can end longer, since only the stages before B are
shared). Proximity to returned cuts (B0: 129 of 252) may be reported only as a
descriptive secondary quantity; it is not the gate. The stop rule on (i) needs its
baseline from the same proposal log run on the frozen B, not the returned-cut value.

**Not yet executable.** Before this draft becomes a protocol it needs a finite total
compute budget for the refinement of k trials per round, and fully specified scheduling
and tie rules for selecting and refining the k trials.

**Target population (confirmation).** New reserved namespace
`search_v3a_confirmation`: F12 at 4,096 bits, 20 new replicates × {base, ragged}; F12
transfer at 16,384, 65,536 and 131,072, 4 replicates each; S02 at 4,096 and 65,536,
8 replicates each. Controls F01, F06, F07, F11 at 4,096 bits, 2 replicates each.

**Decision rule.** Primary contrast: (bits(`hid_full`) − bits(`hid_full_A`)) / n,
unit/cell weighted over the target cells, 99% percentile interval, fixed seed declared in
the freeze. Supported if the lower bound > 0; harmful if the upper bound < 0; otherwise
not detected. Secondary, descriptive: the same contrast against the portfolio, cap-hit
counts, and controls (any control change is reported; none is expected).

**What it would not show.** That B is optimal, that the supplied cuts are the right
target, or anything about non-boundary families.

---

## Draft B — representation: a truncating repeat

**Question.** How much of the period-type deficit is the cost of writing a ragged
periodic string as REPEAT + tail LITERAL + CONCAT?

**Single change.** Add one opcode **TILE(child, length)**: the child's expansion
repeated and truncated to `length` bits. Owners: `hierarchy/model.py` (rule and factory),
`hierarchy/wire.py` (serializer), the independent `hierarchy/decode.py`, and
`consensus.periodic`, which emits TILE instead of REPEAT + tail + CONCAT when the length is
not a multiple of p. This is a new wire version; its decoder stays independent and its
golden archives are hand-derived. Nothing else changes: no search change, no new
proposal, no change to the portfolio.

**Prediction before implementation (per proposal only).** For each saved ragged-period
translation, write down the fully specified rewritten proposal (TILE replacing REPEAT +
tail LITERAL + CONCAT) and compute its exact cost T′ under the new wire version, with full
serialization accounting: graph sharing and pruning, rule IDs, variable-length fields and
the new wire envelope. That is arithmetic on saved bytes and fixes, per proposal, the
expected T′ before any encoding. It does **not** give an exact prediction of the full
method's H′ from H = T: with TILE available the incumbent, the proposals or the search
path can differ, and the 282 equal-length strings include 21 whose saved archive is not
the translated proposal. The full method's H′ is measured, not predicted. The measured
exact-repeat translations (T − C = 40–48 bits) do not use the tail construction and are
unchanged by TILE; that is a statement about those translations, not a floor for every
HID description. Sign reversals against the period codec are therefore not predicted;
whether they occur is an empirical question for the study.

**Arms.** `hid_full` (frozen) versus `hid_full_B` (TILE available to every stage that
builds periodic nodes); portfolio unchanged.

**Development (inspected strings only).** Verify every pre-computed per-proposal T′
exactly on the D4 population; a disagreement there is a defect in the rewrite or its
accounting, to fix before the freeze. Report the full method's measured H′ beside it; a
difference between H′ and T′ is not by itself a codec defect.

**Target population (confirmation).** New reserved namespace `search_v3b_confirmation`:
F01, F02, F03, F05 at 256, 1,024 and 4,096 bits, 20 replicates × {base, ragged}; controls
F06 and F12 at 1,024 bits, 4 replicates each.

**Decision rule.** Primary contrast (bits(`hid_full`) − bits(`hid_full_B`)) / n over the
twelve target cells, 99% percentile interval, declared seed; supported if lower bound > 0.
Secondary, descriptive: the contrast against the portfolio by cell, and agreement of the
measured with the pre-computed per-proposal T′.

**What it would not show.** That HID can beat a specialised period codec on purely
periodic strings, or anything about F06–F11.

---

## Not proposed

No change is proposed for F06–F11, which carry the largest per-bit losses (F08, F09,
F11). This diagnosis did not target their losses: F06, F07 and F11 were sampled only as
D2 controls (4,096 and 65,536 bits), none was a D3 or D4 target, and F08–F10 appear only
in D1. A diagnostic of those cells would precede any algorithm there.
