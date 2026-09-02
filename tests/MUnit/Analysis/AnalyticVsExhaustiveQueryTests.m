(* AUDIT02/P4c — the analytic-over-exhaustive claim, across the full catalogue.

   The manuscripts' demonstrative claim is that the closed-form index set answers
   "which inputs produce this output" WITHOUT enumerating 2^n. This test pins
   that claim for all twelve families by comparing the two routes elementwise:

     exhaustive route : createRepertoireByResult[g, arity, 1, params]
                        -> input vectors, LSB-first order
                        -> their positions in the LSB enumeration
                        -> transported to the MSB convention via Phi
     analytic  route : Integration`Gates`IndexSet[g, arity, params]
                        -> 1-based MSB positions of the one-set

   Phi is the bit-reversal transport (identical to Integration`IndexAlgebra`Phi);
   it is required because the two routes use opposite bit conventions. Comparing
   them without it would measure the convention offset, not the discrepancy.

   Judgement is the symmetric difference of the two index sets, reported with its
   location (convention U8) -- never a count or a cardinality match.

   Arity scope mirrors Integration`Gates`ApplyGate: NOT is arity-1, IMPLIES and
   NIMPLIES are binary (they read inputs[[2]]), everything else 1..4. *)

Get["src/integration/Alpha.m"];
Get["src/Packages/Integration/Gates.m"];

phi[j_, n_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2];

families = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT",
            "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING"};
params = <|"k" -> 2|>;
arities[g_] := Which[
  g === "NOT", {1},
  MemberQ[{"IMPLIES", "NIMPLIES"}, g], {2, 3, 4},
  True, {1, 2, 3, 4}];

records = Flatten[Table[
   Module[{lsbAll, exhaustiveInputs, positions, mapped, analytic, sd},
    lsbAll = Reverse[Reverse[#] & /@ Tuples[{1, 0}, a]];
    exhaustiveInputs = createRepertoireByResult[g, a, 1, params];
    positions = Flatten[Position[lsbAll, #] & /@ exhaustiveInputs];
    mapped = Sort[phi[#, a] & /@ positions];
    analytic = Sort[Integration`Gates`IndexSet[g, a, params]];
    sd = Union[Complement[mapped, analytic], Complement[analytic, mapped]];
    <|"Gate" -> g, "Arity" -> a,
      "ExhaustiveMapped" -> mapped, "Analytic" -> analytic,
      "SymDiff" -> sd, "Equal" -> (mapped === analytic)|>
   ], {g, families}, {a, arities[g]}], 1];

failures = Select[records, Not[#["Equal"]] &];
ok = (failures === {});

CreateDirectory["results/tests/analysis_analyticvsexhaustive", CreateIntermediateDirectories -> True];
Export["results/tests/analysis_analyticvsexhaustive/AnalyticVsExhaustive.json",
  <|"pairsCompared" -> Length[records],
    "families" -> Length[families],
    "failures" -> Length[failures],
    "failingPairs" -> failures,
    "ok" -> ok|>];
Export["results/tests/analysis_analyticvsexhaustive/Status.txt", If[ok, "PASS", "FAIL"]];
Export["results/tests/analysis_analyticvsexhaustive/Debug.txt", StringJoin[
  "pairsCompared=", ToString[Length[records]], "\n",
  "failures=", ToString[Length[failures]], "\n",
  If[failures === {}, "",
     "FAILING:\n" <> StringRiffle[
       (ToString[#["Gate"]] <> " arity=" <> ToString[#["Arity"]] <>
        " symDiff=" <> ToString[#["SymDiff"]]) & /@ failures, "\n"]]
]];
