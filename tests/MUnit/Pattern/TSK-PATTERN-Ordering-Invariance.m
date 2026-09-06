Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/IndexAlgebra.m"];

patternSymbol[col_List] := Module[{z = Count[col, 0], o = Count[col, 1]}, If[z == Length[col], 0, If[o == Length[col], 1, "*"]]];

computePatterns[outputs_] := patternSymbol /@ Transpose[outputs];

lsbInputs[n_] := Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, 2^n - 1}];
msbInputs[n_] := Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];

(* Build outputs with dispatch for a given input set order *)
dispatchOutputs[cm_, dyn_, inputs_, params_: <||>] := Table[
  Table[Integration`Gates`ApplyGate[dyn[[k]], Part[input, Flatten@Position[cm[[k]], 1]], Lookup[params, k, <||>]], {k, Length[dyn]}],
  {input, inputs}
];

cases = {
  {2, {{1, 1}, {1, 1}}, {"XOR", "XNOR"}},
  {2, {{1, 1}, {1, 1}}, {"AND", "OR"}},
  {2, {{1, 1}, {1, 1}}, {"KOFN", "KOFN"}, <|1 -> <|"k" -> 0|>, 2 -> <|"k" -> 3|>|>}
};

results = Table[
  Module[{n = c[[1]], cm = c[[2]], dyn = c[[3]], params = If[Length[c] >= 4, c[[4]], <||>], patsLSB, patsMSB, ok},
    patsLSB = computePatterns[dispatchOutputs[cm, dyn, lsbInputs[n], params]];
    patsMSB = computePatterns[dispatchOutputs[cm, dyn, msbInputs[n], params]];
    ok = (patsLSB === patsMSB);
    <|"n" -> n, "dyn" -> dyn, "ok" -> ok, "pLSB" -> patsLSB, "pMSB" -> patsMSB|>
  ],
  {c, cases}
];

allOK = And @@ (results[[All, "ok"]]);

CreateDirectory["results/tests/pattern_ordering", CreateIntermediateDirectories -> True];
Export["results/tests/pattern_ordering/PatternsOrdering.json", results];
Export["results/tests/pattern_ordering/Status.txt", If[allOK, "OK", "FAIL"]];

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export["results/tests/pattern_ordering/Done.txt", DateString[], "Text"];
