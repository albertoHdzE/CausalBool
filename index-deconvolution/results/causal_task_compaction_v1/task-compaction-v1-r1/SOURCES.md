# Sources and sections read (recorded before freeze)

Primary reference: Timo Knuutila, "Re-describing an algorithm by Hopcroft",
Theoretical Computer Science 250 (2001) 333-363, PII S0304-3975(99)00150-4.

- Retrieved 2026-10-05 from https://www.cs.cmu.edu/~cdm/resources/Knuutila2001.pdf
  with curl; the file is a 10-page PDF 1.2 excerpt covering journal pages 333-342.
- Retrieved-file SHA-256: ca60ed67b4d330d97788d4d2ef5856921380b1903dd583ef3d6756aa85c022ab
  (220,849 bytes). The PDF is not redistributed in this run; the hash identifies what was read.
- Sections read in full by the executor: §2.2 (strings, Definition 1 DFA, recognised
  language), §2.3 (minimal DFA, connectedness, state equivalence rho_A, congruence,
  Propositions 2-3), §2.4 (DFA as unary algebras), §3.1 (classical algorithm,
  Proposition 4: rho_0 = {A', A-A'}, rho_{i+1} = {(a,b) in rho_i | for all x: (x(a),x(b)) in rho_i},
  properties (1) descending, (2) stabilisation equals rho_A, (3) k <= |A|).
- Also read for context only (not relied on): §1, §2.1, §3.2-3.6 (atomic refinements,
  Proposition 5, Algorithms 1-3, derivation trees). Hopcroft's optimised algorithm and its
  O(m n log n) bound are NOT implemented or claimed; the implementation is the classical
  layer-wise recurrence of Proposition 4 with the previous label retained in the signature.
- No substitution of source was needed.

Model mapping and the all-start difference from Knuutila's connected-DFA setting: THEORY.md §5.
