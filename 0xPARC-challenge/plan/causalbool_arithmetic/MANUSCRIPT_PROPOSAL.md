# Manuscript proposal — held for lead review

This artifact is not a manuscript edit. It proposes only claims supported by
the new bounded evidence:

1. CausalBool's existing Boolean gate evaluator can be reused as the semantic
   execution layer for an additive acyclic Boolean-DAG compiler.
2. The compiler lowers supported gates to the existing serialized quadratic-row
   schema, with independent row replay and deterministic signal mappings.
3. Q5 is demonstrated for 64-bit range binding and Q6 for canonical field
   elements with one excluded. The checks are local serialized-row checks;
   Circom compilation is UNKNOWN here because the pinned compiler/toolchain is
   absent.
4. Q7 is a partial, exhaustive width-4 demonstration only. It is not a 64-bit
   factorization implementation, performance result, or target-size claim.
5. Q8 remains feasibility/design only. No factoring-performance, enumeration,
   or zero-knowledge-proof claim follows from this work.

The earlier reduced-table wording should be corrected precisely: the inverse
implementation stores a `reduced_truth_table` and calls `reduce_column`; whole
system interpretation does not erase that operation. Gate evaluation,
deconvolution, symbolic equivalence, and quadratic compilation are distinct
contributions and should be described separately.
