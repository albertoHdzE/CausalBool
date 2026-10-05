# Representation review v1 — artifact-only synthesis (`representation-review-v1-r1`)

Executor: Claude Code, 2026-10-04. Source of all measurements: the **accepted**
dictionary run `results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1` (lock
`19b53d32…`), read only. No encoder was run; no archive was built; no cap was changed.
Owners used: `hierarchy.decode.decode_archive`, `hierarchy.ledger.archive_ledger`.
Every input file is hashed before and after (`evidence_manifest_{pre,post}.json`).

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

Independent validation: `audit.py` (imports nothing from `analysis.py`) re-selects all
192 candidates, re-hashes and re-decodes them, re-checks the ledger slices, components,
margins, sign counts and quantiles — `audit_result.json`: pass, 0 problems.

## 3. Capability map (item 4)

Read-only source inspection plus saved witnesses (A0 rule kinds by family, `per_case.json`).

| operation | already in k = 1 (A0 = search-v2 `hid_full`) | witness in saved A0 | offered additionally by the dictionary phase |
|---|---|---|---|
| exact repetition | `infer._Search.periodic` / `local_props` "period[p]" → REPEAT; search-v2 P/C/D/G templates (`consensus.local_proposal`, `global_proposal`) | REPEAT in F01, F02, F03, F05, F06, F09, F12 | REPEAT of a dictionary word's period base (P), and REPEAT of token runs (G0) inside fixed-width views |
| noisy repetition / exceptions | `local_props` "noisy_period", "ap_run_patch"; search-v2 templates + PATCH (local or one global) | PATCH in F06 | PATCH on a related word (R), and on a gap template's whole core (G2/G3, ≤ 64 flips) |
| transformation | `infer._Search.relations`: XFORM exact matches only, flags 0–3, rotations 0/1/2/4/8, between literal nodes of a beam root | XFORM in F10 | XFORM **plus** PATCH (≤ 8 flips), restricted to the eight preceding dictionary words, rotation 0, chained (hops ≤ 8) |
| sharing / grammar | `grammar_props` (pair grammar over segment symbols, shared CONCAT rules), interned nodes, `rewrite` of shared sites | CONCAT in 54 strings | first-appearance dictionaries at fixed widths, origins and pairing levels; owner `pair_grammar` on the top stream (G1) |
| sparse / positional sets | AP_UNION, SCHEMA_UNION local proposals | AP in F04, F05, F09; SCHEMA in F05 | none |
| segmentation | `infer.segmentation_props`, search-v2 stage B boundaries | — | none (views are rigid grids with literal prefix/suffix) |

**Representation versus search.** Every dictionary-phase candidate is written in the
unchanged HID-v1 wire language (same seven opcodes); the phase changed **search**
(which DAGs are proposed), not the representation. Proposals that would alter the
**representation** are new opcodes or new cost models (e.g. a relation rule with its own
compact header, an implicit token width, a non-literal tail). Proposals that would alter
**search** only include relaxing the donor window, flip or hop caps, per-word (mixture)
rather than whole-dictionary selection, other rankings, or offering relations inside A0's
own segmentation. None of these was run or tested here.

## 4. Two hypotheses, compared (item 5)

**H1 — fixed-grid envelope cost.** Multilevel views write a full token-reference list
(CONCAT refs) and literal dictionary words over a rigid grid; A0's segmentation and
local primitives avoid most of that, so dictionary-level savings (periods, relations) are
smaller than the grid's fixed cost.
* *Distinguishing observation:* among candidates with the same dictionary content,
  archive length should track the token-reference bytes; a candidate whose refs were
  removed by an existing mechanism (e.g. relations offered inside A0's own segments)
  would either beat A0 (supports) or not (weakens).
* *Unmeasured:* any such counterfactual archive; whether the CONCAT-refs excess is
  removable at all within HID-v1.
* *Falsifier / counterexample:* a string where the best R candidate's CONCAT refs are no
  larger than A0's structure bytes yet it is still longer (would point elsewhere); the
  saved data contain no test of this because no candidate was constructed to hold refs
  fixed.
* *Minimal control:* the same candidate with relations disabled (mode O of the same
  view) — available, and it shows relations help within views, not against A0.

**H2 — search scope, not representation.** Whole-dictionary bundles, greedy
(flips, j, flags) ranking, the eight-word window and the hop cap kept the phase from
finding mixtures that would beat A0, although the representation could express them.
* *Distinguishing observation:* an exhaustive or per-word optimum over the *same* views
  and relation set, on small declared fixtures, that is shorter than the bundle optimum
  and than A0.
* *Unmeasured:* any mixture or alternative ranking; hop refusals (354,960 per R mode)
  are comparison events, not demonstrated lost savings.
* *Falsifier:* if the per-word optimum on those views is still ≥ A0 wherever the bundle
  is, H2 fails for these views.
* *Minimal control:* D2 bundle results on the same views (saved), and A0.

Neither hypothesis is supported as a cause by this evidence; the review explicitly does
not assume the hop cap or representation overhead is responsible.

## 5. Recommendation (item 6)

**STOP** further compression-extension development of the multilevel/dictionary line
for now. Reasons, from saved evidence only: (i) the accepted v3a confirmation found k = 4 HARMFUL
against k = 1 in aggregate, and the multilevel and dictionary phases added candidate
families without one archive shorter than k = 1 on the 96 exposed strings; (ii) the nearest results are ties obtained by rediscovering operations
k = 1 already has (exact complement XFORM in F10; REPEAT in F05); (iii) 30 of 96 strings
are not compressed by A0 at all, and every candidate on them stays 408+ bits longer, so
a gain there would need a representation change rather than a search change; (iv) the
only discriminating next experiment (H2's per-word optimum) would itself be encoder
development on the same exposed strings, with little prospect of supplying fresh
confirmation. No `DRAFT_NEXT_PROTOCOL.md` is written.

If the programme later resumes compression work, it should start from a fresh protocol
with genuinely held-out confirmation data and choose H1 or H2 explicitly. Separately,
**causal identification needs its own target and observation model** (what is
intervened on, what is observed, what counts as recovering the mechanism); neither a
dictionary hierarchy nor a compression gain substitutes for that target, and no causal,
self-similarity or fractal statement follows from this review.
