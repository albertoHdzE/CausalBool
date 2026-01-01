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
