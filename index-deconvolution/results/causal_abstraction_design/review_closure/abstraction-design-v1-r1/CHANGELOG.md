# CHANGELOG — closure of REVIEW R1–R3 for `abstraction-design-v1-r1`

Originals untouched; corrected copies in `corrected/`. Scientific declarations and review metadata
are kept distinct (literature confirmations are attributed to the Codex REVIEW, not re-read here).

## R1 — β and intervention grouping
- MODEL §5 rewritten: β_fine keeps (op, coordinate, local position, value); every class a singleton,
  so E4 ≡ E3 under β_fine. Value-preserving maps (F1 val, F3 val, identity) scored only under β_fine.
- Coarse grouping kept only as declared hypotheses H-COARSE (lossy F1, F2, F4) and H-OUT (F3),
  scored separately; representative rule and REP-NOEXIST / MEMBER-NOEXIST / NOT-EVALUABLE defined.
- R1 counterexample explained by hand (M2, τ=1, x=0: φ_0 → 2, φ_1 → 3); F1 val analogue.
- MODEL §4: "recodings always consistent" replaced by individual-existence theorem.
- Fixtures FX-R1a/b/c, FX-REP added (witnesses only; not run). P2 wording makes the local bit
  explicit. Track-V counts unchanged: 30,976 pairs, 2,080 expected failures.

## R2 — scope and decision table
- DESIGN §5: endpoints re-scoped (E2 autonomous, E3 per-q, E4 shared-β with intended / inspected /
  evaluable pairs); §5.1 exclusive primary labels (CONTROL, AUT-FAIL, RESTRICTED, AUT-ONLY,
  NOT-FULL-INCOMPLETE, INCOMPLETE, FULL) with failure over missingness; §5.2 coarse labels.
- DESIGN §6 scoped to A / Q / β; X restricted to autonomous support closure (also MODEL, §A.4).
- Majority-F3 stop rule removed (DRAFT §8); replaced by a descriptive count (DRAFT §4.4).

## R3 — execution specification
- Canonical ids 0–134 / 0–140 and D row ids 0–2,729 (MODEL §4); audit subset row ≡ 0 mod 10 =
  273 of 2,730 (exactly 10 %), frozen before D.
- Track G: N = 124 (n=8) / 130 (n=10) after excluding 11 recoding/constant controls; duplicates kept;
  F2 in population with R UNAVAILABLE; per-trajectory occurrence sets pooled by count.
- E7: description length deferred; only execution/selection costs.
- Tests before freeze; freeze hashes implementation sources; canonical scientific-field comparison.
- Owner `index-deconvolution/src/deconvolution.py` proposed (`OWNERSHIP_TICKET.md`). Import route:
  `PYTHONPATH=index-deconvolution/src`, bare names (grep-confirmed import style; not executed).
- Gap owner path corrected to `../series-deconvolution/src/seqdecon/operators.py:gaps`; U2 (no
  block-value extractor) and U3 (no import route) recorded as unresolved dependencies.
- Proposed budget 2,160 s executor + 300 s reserve; < 300 s compute marked unmeasured.

## Nonblocking
- "3 of 5" scales; autonomous-only triviality (M1, rule 90); first-occurrence-label wording;
  "repeated structure found" endpoint withdrawn; nesting a candidate construction; Song–Grochow and
  Israeli–Goldenfeld rows updated per REVIEW.

## Arithmetic reconciled (hand)
124 = 135 − 11; 130 = 141 − 11; 11 = 9 F1 val + identity + constant. Ids: F1 45 + F2 4 + F3 30/36 +
F4 54 + C 2 = 135/141. Rows: 3·675 + 705 = 2,730; ⌊2,729/10⌋ + 1 = 273. 630 = 30·5·3 + 36·5.
