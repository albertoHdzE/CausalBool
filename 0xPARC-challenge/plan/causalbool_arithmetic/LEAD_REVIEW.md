# Lead review — CausalBool arithmetic integration

Status: accepted for the bounded milestone; not a 64-bit Q7 or Q8 result.

The submitted additive implementation was reviewed against
`plan/CAUSALBOOL_ARITHMETIC_LUNA.md`. Independent checks covered all supported
gate truth tables, comparison and exclusion truth tables through width 5,
the focused tests, the full challenge suite, and a fresh bounded verifier run.

Results:

* focused Boolean-arithmetic tests: 25 passed;
* complete challenge suite: 88 passed;
* verifier: PASS, including all 4096 width-4 Q7 triples (16 valid and 4080
  invalid) and exact local CausalBool deconvolution replay;
* Circom/snarkjs compilation: UNKNOWN because the pinned tools are absent.

Two defects were corrected during review. Repeated operands in OR/XOR lowering
now combine coefficients instead of overwriting them, and every invalid Q7
assignment is now checked against the serialized constraints rather than only
counted. Q7 public `n` bits also receive explicit Booleanity rows. The stored
verification evidence and report hashes/statistics were regenerated after
these corrections.

Accepted claims are limited to Q5/Q6 serialized-row correctness and the
exhaustive width-4 Q7 demonstration. Q7 width 64, Q8 implementation,
compiled-row/witness verification, and performance claims remain open and are
not implied by this review.
