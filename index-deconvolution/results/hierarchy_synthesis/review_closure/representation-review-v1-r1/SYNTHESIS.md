# Representation review v1 — artifact-only synthesis (`representation-review-v1-r1`), corrected for review R1/R2

*Closure copy, 2026-10-04.* The original
`results/hierarchy_synthesis/representation-review-v1-r1/SYNTHESIS.md` is preserved
unedited. This copy changes prose only: §2's audit paragraph and manifest sentence, §3's
capability table, §4 and §5. Every number is unchanged and is rechecked in
`closure_audit_result.json` and `numeric_equality.json`.

Executor: Claude Code, 2026-10-04. Source of all measurements: the **accepted**
dictionary run `results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1` (lock
`19b53d32…`), read only. No encoder was run; no archive was built; no cap was changed.
Owners used: `hierarchy.decode.decode_archive`, `hierarchy.ledger.archive_ledger`.
The original `evidence_manifest_{pre,post}.json` hashed 11,722 dictionary-run and source
files before and after, but **omitted the 96 raw input archives** that both original scripts
read; the supplemental `closure_manifest_{pre,post}.json` (created at closure, not
backdated) covers them against their CASES pins.

## 1. What was compared (item 2)

For each of the 96 strings, from the saved D2 trace:

* **best R** — the proposal with mode R(O) or R(P), any view, minimum by (archive bits,
  saved request ordinal);
* **best O** — the same over mode O;
* **A0** — the saved k = 1 archive (byte-identical to the search-v2 reference; checked).

All 192 selected archives were on disk (each is its view-mode's retained best), hash to
their recorded sha256 and decode to the input. Unavailable evidence: **none**.

**Authoritative partition.** `archive_ledger` cuts an archive into consecutive, disjoint
byte fields that reassemble it exactly (the audit re-checks offsets). Components are
unions of whole fields: `envelope`; `dag` (q_rules); per rule kind `KIND.header`
(opcode, length/arity/count/foreground), `KIND.refs` (child ids), `KIND.payload` (literal
bits, copies, patch deltas, xform flags/rotation, AP/schema parameters); `raw.payload`
for a literal-codec A0. No field is split or double-counted; shared DAG rules are counted
once where written; **no per-word allocation is made**. Per-case components:
`per_case_components.csv`; full records: `per_case.json`; flat table: `per_case.csv`.

## 2. Results over all 96 strings (item 3)

Margins are candidate bits − A0 bits (positive: A0 shorter).

| | shorter / equal / longer than A0 | byte-identical to A0 | margin min | q25 | median | q75 | max |
|---|---|---:|---:|---:|---:|---:|---:|
| best R | 0 / 6 / 90 | 1 | 0 | 416 | 628 | 1,560 | 4,384 |
| best O | 0 / 2 / 94 | 1 | 0 | 408 | 516 | 1,560 | 4,272 |

By A0 codec (audit): A0 is the **raw literal on 30 strings** (families F02, F07, F08,
F09, F11) and a HID DAG on 66. On the raw-A0 strings the best margins are 408–1,608 bits
(median 484 R, 456 O); on HID-A0 strings 0–4,384 (median 652 R, 528 O).

Equal-length cases (best R): F05-1024-3000-base (byte-identical rediscovery of A0, 144
bits), F05-1024-3000-ragged (200, distinct bytes, already tied by mode O),
F10-1024-3000-base and F10-1024-3001-base (440), F10-4096-3000-base (696) and
F10-4096-3001-base (688). Erratum to the frozen dictionary HANDOFF §1, which wrote "440 or
688 bits": one of the four F10 ties is 696 bits. The frozen file is not edited.

**Three distinct notions, kept apart:**

| notion | evidence | result |
|---|---|---|
| within-view improvement (same view, mode vs O) | saved `summary.json` | R(O) < O in 1,243 of 6,096 views (2,628 equal, 2,225 longer); R(P) < O 1,359; P < O 368 |
| best-over-views improvement (best R vs best O, per string) | this review | R shorter on 14, equal on 28, longer on 54 strings (median +40 bits; range −104…+464) |
| beating A0 | this review / accepted study | 0 of 96, for both best R and best O |

So relations shorten a view's own proposal often, shorten the *best* proposal over views
for 14 strings, and never reach below A0.

**Component accounting (sum over 96 strings, best R minus A0, bits):** CONCAT refs
+61,104, LITERAL payload +59,296, CONCAT header +17,024, LITERAL header +16,600, XFORM
+9,728 (all fields), PATCH +10,528, REPEAT +1,992, envelope +216, dag +240; offset by
A0 components absent in the candidates: raw payload −73,848, AP_UNION −2,624, SCHEMA
−416. Best O minus A0 is similar (CONCAT refs +64,776, LITERAL payload +62,696, LITERAL
header +30,200). Positive deltas by case (best R): CONCAT refs 90, CONCAT header 78,
LITERAL header 61, LITERAL payload 60 of 96. **This is accounting, not a cause**: it says
where the candidate's bytes are, not why no search found a shorter archive. Selected
views are mostly level 1 (best R: w64-l1 54, w4-l1 32, w8-l1 6, w32-l1 2, w64-l2 2),
so the deeper levels rarely supplied the best candidate.

Independent validation. The original `audit.py` re-selected and re-decoded all 192
candidates and checked component *sums*, margins, sign counts and min/median/max; it did
not reconstruct component labels, did not check q25/q75 or normalized margins, and did
not enforce the exact case set first (review R2). The closure audit `closure_audit.py`
does all of these: exact 96-case set before any comparison; field-by-field per-case
components and deltas from the owner ledger; every derivable summary field including
all declared quantiles of both margin distributions and of best R minus best O; both
CSV tables; input n and hash after decoding; raw archives against CASES pins. Real data:
pass. Moving 8 bits from CONCAT.refs to LITERAL.payload (sum unchanged), raising a
reported q25, and replacing a case with a duplicate are each rejected by the intended
check (`closure_audit_result.json`).

## 3. Capability map (item 4)

Read-only source inspection plus saved witnesses (A0 rule kinds by family, `per_case.json`).

Column 2 lists **source capabilities** (code that can propose the operation); column 3
lists **saved-archive witnesses** (a rule kind present in a saved A0 archive). A
capability is not a witness, and a witness is not evidence of the search path that
produced it: a CONCAT rule alone does not certify shared grammar reuse, and no saved
archive witnesses segmentation. Capabilities were read from source; no inference was run.

| operation | source capability in k = 1 (A0 = search-v2 `hid_full`) — code only | saved-archive witness (rule kind in A0) | offered additionally by the dictionary phase |
|---|---|---|---|
| exact repetition | `infer._Search.periodic` / `local_props` "period[p]" → REPEAT; search-v2 P/C/D/G templates (`consensus.local_proposal`, `global_proposal`) | REPEAT in F01, F02, F03, F05, F06, F09, F12 | REPEAT of a dictionary word's period base (P), and REPEAT of token runs (G0) inside fixed-width views |
| noisy repetition / exceptions | `local_props` "noisy_period", "ap_run_patch"; search-v2 templates + PATCH (local or one global) | PATCH in F06 | PATCH on a related word (R), and on a gap template's whole core (G2/G3, ≤ 64 flips) |
| transformation | `infer._Search.relations`: XFORM exact matches only, flags 0–3, rotations 0/1/2/4/8, between literal nodes of a beam root | XFORM in F10 | XFORM **plus** PATCH (≤ 8 flips), restricted to the eight preceding dictionary words, rotation 0, chained (hops ≤ 8) |
| sharing / grammar | `grammar_props` (pair grammar over segment symbols, shared CONCAT rules), interned nodes, `rewrite` of shared sites | CONCAT rule present in 54 strings (does not by itself certify shared reuse or the grammar search path) | first-appearance dictionaries at fixed widths, origins and pairing levels; owner `pair_grammar` on the top stream (G1) |
| sparse / positional sets | AP_UNION, SCHEMA_UNION local proposals | AP in F04, F05, F09; SCHEMA in F05 | none |
| segmentation | `infer.segmentation_props`, search-v2 stage B boundaries (code-only capability) | none in any saved archive | none (views are rigid grids with literal prefix/suffix) |

**Representation versus search.** Every dictionary-phase candidate is written in the
unchanged HID-v1 wire language (same seven opcodes); the phase changed **search**
(which DAGs are proposed), not the representation. Proposals that would alter the
**representation** are new opcodes or new cost models (e.g. a relation rule with its own
compact header, an implicit token width, a non-literal tail). Proposals that would alter
**search** only include relaxing the donor window, flip or hop caps, per-word (mixture)
rather than whole-dictionary selection, other rankings, or offering relations inside A0's
own segmentation. None of these was run or tested here.

## 4. Two hypotheses, compared (item 5)

Neither hypothesis is established as a cause by this evidence; the review does not
assume the hop cap or representation overhead is responsible.

**H1 — fixed-grid envelope cost.** Multilevel views write a full token-reference list
(CONCAT refs) and literal dictionary words over a rigid grid; A0's segmentation and
local primitives avoid most of that, so dictionary-level savings (periods, relations) are
smaller than the grid's fixed cost.
* *What the saved ledgers can test (descriptive, not causal):* a declared inequality on
  the existing component tables, for example whether, per string, the best candidate's
  CONCAT.refs + LITERAL excess over A0 exceeds its margin. This needs no new archive.
  That reference bytes correlate with, or account for, total length is accounting; it
  neither confirms nor falsifies H1 as a cause.
* *Missing for a causal reading:* a controlled intervention that changes the reference
  cost while holding the rest fixed. No such archive exists; this is a limitation of the
  evidence, distinct from what the ledgers can describe.
* *Available comparison:* mode O of the same view (relations disabled) shows relations
  help within views, not against A0; it does not vary the grid cost.

**H2 — search scope, not representation.** Whole-dictionary bundles, greedy
(flips, j, flags) ranking, the eight-word window and the hop cap may have kept the phase
from finding archives that beat A0, although the HID-v1 format could express them.
* *What a test would require:* independent per-word minima need not minimize a shared
  DAG's total cost, so a per-word optimum is not an oracle. An oracle would be a joint
  optimization of the full archive length over an explicitly declared finite candidate
  set; its conclusion would apply to that set only, not to all same-format methods.
* *Unmeasured:* any such joint optimum, mixture or alternative ranking; hop refusals
  (354,960 per R mode) are comparison events, not demonstrated lost savings.
* *Available comparison:* D2 bundle results on the same views (saved), and A0.

No oracle, encoder or counterfactual archive was implemented or run.

## 5. Recommendation (item 6)

**STOP** further compression-extension development of the multilevel/dictionary line,
as a **research-priority judgment**, not as a conclusion that further gain is impossible.
Grounds, from saved evidence only:

1. *Observed retained gain is zero.* The accepted v3a confirmation found k = 4 HARMFUL
   against k = 1 in aggregate; the multilevel and dictionary phases added candidate
   families without one archive shorter than A0 on the 96 exposed strings (best R:
   0 shorter, 6 equal, 90 longer; best O: 0 / 2 / 94).
2. *The nearest results are ties* reached by operations k = 1 already has (exact
   complement XFORM in F10; REPEAT in F05).
3. *Further work is additional cost with no observed return.* On the 30 strings where
   A0 selected a raw literal, every candidate stays 408–1,608 bits longer. That A0
   selected a raw literal does not certify that no shorter archive exists in the same
   language: A0 is a finite heuristic. Stronger search under the unchanged HID-v1 format
   remains **untested, not impossible**, and this evidence does not show that a
   representation change is necessary.
4. *Priority.* Given (1)–(3), other questions in the programme are judged more
   worthwhile than continued search development on this line now.

The evidence does not single out one discriminating next experiment: H1 (§4) admits a
descriptive test on saved ledgers and would need a controlled intervention for a causal
reading; H2 would need a declared finite joint optimization; other controlled
experiments are not ruled out. Development on exposed examples could in principle be
followed by a separately frozen fresh evaluation; none is prescribed here, because the
extension produced no gain to confirm. No `DRAFT_NEXT_PROTOCOL.md` is written and no
next encoder protocol is proposed.

Separately, **causal identification needs its own target and observation model** (what
is intervened on, what is observed, what counts as recovering the mechanism); neither a
dictionary hierarchy nor a compression gain substitutes for that target, and no causal,
self-similarity or fractal statement follows from this review.
