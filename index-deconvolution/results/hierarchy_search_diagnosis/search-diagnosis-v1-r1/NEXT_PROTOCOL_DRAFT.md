# Next-protocol drafts after search-diagnosis-v1 (for supervisor review)

Status: **draft only.** No seed has been generated, no reserved namespace touched, no
source version implemented. The recommendation is `BOTH_SEPARATELY`; the two drafts
below are independent studies, each with exactly one change, its own freeze and its own
review. They must not share a source version. Suggested order: Draft A first (see
`DECISION.md`, "Priority").

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

**Why this change.** D2: caps are not binding (B8 changed 1/176 targets). D3: in all 72
losing boundary-family strings a supplied partition is shorter than H and P, the best
strictly reachable one beats H in 68/176 strings, and about half of its useful cuts (123
of 252) have no B0 cut within 8 bits. The change targets cut *proposal*, the obstacle
the diagnosis points to, without touching the language or budgets.

**Arms.** `hid_full` (frozen HID-search-v2 bytes, rerun) versus `hid_full_A` (identical
except the change); the nine-codec portfolio unchanged.

**Development (inspected strings only).** On the 176 D3 targets, pre-register before
running: (i) the fraction of supplied cuts with a B cut within 8 bits; (ii) the share of
strings where `hid_full_A` is shorter, and longer, than `hid_full` (a different B path
can end longer, since only the stages before B are shared). Stop the line (no
confirmation) if (i) does not rise above the B0 value 129/252.

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

**Prediction before implementation.** From the saved D4 ledgers, compute exactly, per
record, the bytes TILE would remove (the CONCAT rule and the tail LITERAL rule, minus the
TILE length field) and therefore the predicted T′ for every ragged-period translation and
the predicted change in H for the 282 H = T strings. This is arithmetic on saved bytes,
not an experiment, and fixes the expected effect before any encoding. The exact-repeat
floor (T − C = 40–48 bits) is unaffected, so sign reversals against the period codec are
**not** expected; the target is the size of the deficit.

**Arms.** `hid_full` (frozen) versus `hid_full_B` (TILE available to every stage that
builds periodic nodes); portfolio unchanged.

**Development (inspected strings only).** Verify the predicted byte changes exactly on the
D4 population; any disagreement is a defect to fix before the freeze.

**Target population (confirmation).** New reserved namespace `search_v3b_confirmation`:
F01, F02, F03, F05 at 256, 1,024 and 4,096 bits, 20 replicates × {base, ragged}; controls
F06 and F12 at 1,024 bits, 4 replicates each.

**Decision rule.** Primary contrast (bits(`hid_full`) − bits(`hid_full_B`)) / n over the
twelve target cells, 99% percentile interval, declared seed; supported if lower bound > 0.
Secondary, descriptive: the contrast against the portfolio by cell, and agreement of the
measured with the predicted byte change.

**What it would not show.** That HID can beat a specialised period codec on purely
periodic strings, or anything about F06–F11.

---

## Not proposed

No change is proposed for F06–F11, which this diagnosis did not examine and which carry
the largest per-bit losses (F08, F09, F11). A diagnostic of those cells would precede any
algorithm there.
