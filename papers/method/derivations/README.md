# Derivation documents — gate-family closed forms

Per-family derivations mandated by AUDIT01/T5.2 (D-6 CLOSED 2026-08-25:
**all twelve families**, author directive). Each document states the
family definition, the closed-form one-set, its band decomposition and
Φ-transport reading, and embeds the EXECUTED mechanical witness
(arity 2..6, elementwise equality vs the exhaustive LUT — never
cardinality alone). Witness JSONs: `verification/`.
Regenerate witnesses: `WolframKernel -script tools/t52_family_witnesses.wl`.

| Doc | Family | Cases (arity ≤ 6) | Failures |
|---|---|---|---|
| 01_causalBool_inputs | band framework | — | — |
| 02_cb_and / 02_cb_or | AND, OR | see files | — |
| 03_cb_xor.tex | XOR | 5 (arities 2, 3, 4, 5, 6) | 0 |
| 04_cb_nand.tex | NAND | 5 (arities 2, 3, 4, 5, 6) | 0 |
| 05_cb_nor.tex | NOR | 5 (arities 2, 3, 4, 5, 6) | 0 |
| 06_cb_xnor.tex | XNOR | 5 (arities 2, 3, 4, 5, 6) | 0 |
| 07_cb_not.tex | NOT | 5 (arities 2, 3, 4, 5, 6) | 0 |
| 08_cb_implies.tex | IMPLIES | 35 (arities 2, 3, 4, 5, 6) | 0 |
| 09_cb_nimplies.tex | NIMPLIES | 35 (arities 2, 3, 4, 5, 6) | 0 |
| 10_cb_majority.tex | MAJORITY | 5 (arities 2, 3, 4, 5, 6) | 0 |
| 11_cb_kofn.tex | KOFN | 40 (arities 2, 3, 4, 5, 6) | 0 |
| 12_cb_canalising.tex | CANALISING | 80 (arities 2, 3, 4, 5, 6) | 0 |
