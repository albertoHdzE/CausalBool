BeginPackage["Integration`IndexAlgebra`"]
IndexSetUniverse::usage = "Return the universe of indices {1..2^n} for network size n";
IndexSetComplement::usage = "Return the complement of a set within the universe {1..2^n}";
IndexSetUnion::usage = "Union of index sets";
IndexSetIntersection::usage = "Intersection of index sets";
Phi::usage = "Bit-reversal mapping between MSB/LSB orderings: Phi[j,n]";
MapPhi::usage = "Map a list of indices via Phi for given n";
OneBandIndices::usage = "Indices where bit i equals 1 in ordered exhaustive inputs of length n";
ZeroBandIndices::usage = "Indices where bit i equals 0 in ordered exhaustive inputs of length n";
PatternIndices::usage = "PatternIndices[n, nodes, pattern] returns, in CLOSED FORM, the 1-based MSB-convention row indices of the n-bit exhaustive input table on which the given nodes carry the given 0/1 pattern. No enumeration of the 2^n table is performed.";
FilterRepertoireByOutput::usage = "FilterRepertoireByOutput[inRep, outRep, node, expected] returns <|\"Indices\", \"Inputs\", \"Outputs\"|> for the repertoire rows whose output at the given node equals expected. This is the EXHAUSTIVE baseline against which PatternIndices and the closed-form index sets are checked.";
Begin["`Private`"]
IndexSetUniverse[n_Integer] := Range[1, 2^n]
Phi[j_Integer, n_Integer] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2]
MapPhi[set_List, n_Integer] := Phi[#, n] & /@ set
IndexSetComplement[n_Integer, set_List] := Complement[IndexSetUniverse[n], set]
IndexSetUnion[sets__List] := Union[sets]
IndexSetIntersection[sets__List] := Intersection[sets]
OneBandIndices[n_Integer, i_Integer] := Module[{inputs}, inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}]; Flatten@Position[(#[[i]] == 1) & /@ inputs, True, 1]]
ZeroBandIndices[n_Integer, i_Integer] := Module[{inputs}, inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}]; Flatten@Position[(#[[i]] == 0) & /@ inputs, True, 1]]

(* AUDIT02/P4d — the ANALYTIC PARTIAL-PATTERN QUERY, made first-class.

   PatternIndices answers "which rows of the exhaustive input table carry this
   partial pattern" WITHOUT building the table: each (node, bit) constraint is a
   band, and the answer is their intersection. This is the query the manuscripts
   use to show that a specific set of inputs is obtained analytically rather than
   by enumerating 2^n.

   Provenance and equivalence: this supersedes findPatternIndices from the
   retired exploratory file archive/causal-exploratory/CausalBool.m, which computed the same
   object in the LSB convention via period = 2^(k-1) run arithmetic. The two
   agree exactly under Phi transport -- verified over 90 (n, node-set, pattern)
   cases at n = 3 and 4 with zero mismatches:

       findPatternIndices[nodes, pattern, n]  ===  MapPhi[PatternIndices[n, nodes, pattern], n]

   Convention: MSB row contract, matching Integration`Gates`IndexSet and
   IndexSetNetwork (GOVERNANCE/ORDERING.md). Transport to LSB via Phi, once. *)
PatternIndices[n_Integer, nodes_List, pattern_List] := Module[{bands},
  If[Length[nodes] =!= Length[pattern],
    Return[Failure["PatternIndices", <|"Reason" -> "nodes and pattern differ in length"|>]]];
  If[!AllTrue[nodes, 1 <= # <= n &],
    Return[Failure["PatternIndices", <|"Reason" -> "node index outside 1..n"|>]]];
  If[!AllTrue[pattern, # === 0 || # === 1 &],
    Return[Failure["PatternIndices", <|"Reason" -> "pattern must be 0/1"|>]]];
  If[nodes === {}, Return[IndexSetUniverse[n]]];
  bands = MapThread[If[#2 === 1, OneBandIndices[n, #1], ZeroBandIndices[n, #1]] &,
                    {nodes, pattern}];
  Sort[Apply[Intersection, bands]]
]

(* AUDIT02/P4d — exhaustive counterpart, supersedes filterByCondition from the
   same retired file. Kept as a named function precisely because it is the
   baseline the analytic result is judged against; a comparison is only evidence
   if both sides are nameable and reproducible. *)
FilterRepertoireByOutput[inRep_List, outRep_List, node_Integer, expected_] := Module[{idx},
  idx = Flatten@Position[outRep[[All, node]], expected];
  <|"Indices" -> idx, "Inputs" -> inRep[[idx]], "Outputs" -> outRep[[idx]]|>
]

End[]
EndPackage[]
