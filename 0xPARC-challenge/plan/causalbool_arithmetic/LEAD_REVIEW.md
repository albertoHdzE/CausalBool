# Lead review — CausalBool arithmetic integration

Status: accepted for the bounded milestone; not a 64-bit Q7 or Q8 result.

The submitted additive implementation was reviewed against
`plan/CAUSALBOOL_ARITHMETIC_LUNA.md`. Independent checks covered all supported
gate truth tables, comparison and exclusion truth tables through width 5,
the focused tests, the full challenge suite, and a fresh bounded verifier run.

Results:

* focused Boolean-arithmetic tests: 23 passed;
* complete challenge suite: 86 passed;
* verifier: PASS, including all 4096 width-4 Q7 triples (16 valid and 4080
  invalid) and exact local CausalBool deconvolution replay;
* Circom/snarkjs compilation: UNKNOWN because the pinned tools are absent.

One contract-quality correction was made during review: Q7 public `n` bits now
also receive explicit Booleanity rows. The stored verification evidence and
the report hashes/statistics were regenerated after that correction.

Accepted claims are limited to Q5/Q6 serialized-row correctness and the
exhaustive width-4 Q7 demonstration. Q7 width 64, Q8 implementation,
compiled-row/witness verification, and performance claims remain open and are
not implied by this review.
