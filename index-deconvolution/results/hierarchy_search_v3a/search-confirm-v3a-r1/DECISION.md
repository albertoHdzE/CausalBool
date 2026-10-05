# Decision: HID-search-v3a (search-confirm-v3a-r1)

**Verdict: HARMFUL.** Ready for Codex review; not yet accepted.

* Contrast: equal-cell mean over six target cells of
  (bits(hid_full) − bits(hid_refine4)) / n, paired base/ragged units.
* Estimate: −0.0063290600504822 bits per input bit.
* 99% percentile interval (10,000 draws, seed 55001): [−0.00833260223670385, −0.004177554260442437].
* Population: 120 of 120 paired units, 240 strings; engineering-valid and complete; no
  HID raw fallback, no censored baseline, no missing row.
* Rule: upper bound < 0, so HARMFUL (precedence INVALID, INCOMPLETE, SUPPORTED, HARMFUL,
  INCONCLUSIVE).

Machine record: `DECISION.json`. Independent recomputation: `arithmetic_audit.json`.

**Follow-up merit.** As specified, under the same shared caps, this exact change does
not merit adoption: it lengthens archives on the declared mixture. The descriptive
record (k = 4 exhausts the shared length charge in 219 of 256 strings, while k = 1 never
does) suggests that seed count and the shared cap budget interact. Testing that would
be a new design with its own protocol; it is not authorized here and nothing beyond
this study was run.
