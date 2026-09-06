Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/Experiments.m"];
nVals = {3, 4};
gates = {"AND","OR"};
phi[j_, n_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2];
lsbInputs[n_] := Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, 2^n - 1}];
applyGateOnLSB[gate_, v_, Ic_, params_] := Integration`Gates`ApplyGate[gate, Part[v, Ic], params];
lsbIndexSet[gate_, n_, Ic_, params_] := Module[{inputs = lsbInputs[n], res}, res = Table[If[applyGateOnLSB[gate, inputs[[j]], Ic, params] == 1, j, Nothing], {j, 1, Length[inputs]}]; res];
msbIndexSet[gate_, n_, Ic_, params_] := Integration`Gates`IndexSetNetwork[gate, n, Ic, params];
IcSamples[n_] := If[n >= 3, {{2, 3}}, {{1}}];
paramsForCase[gate_, n_] := Which[
  gate === "KOFN", <|"k" -> 1|>,
  gate === "CANALISING", <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 0|>,
  gate === "NOT", <|"i" -> If[n >= 2, 2, 1]|>,
  gate === "IMPLIES" || gate === "NIMPLIES", <|"pair" -> {1, If[n >= 2, 2, 1]}|>,
  True, <||>
];
checkOne[gate_, n_, Ic_] := Module[{params = paramsForCase[gate, n], lsbSet, msbSet, mapped},
  lsbSet = lsbIndexSet[gate, n, Ic, params];
  mapped = phi[#, n] & /@ lsbSet;
  msbSet = msbIndexSet[gate, n, Ic, params];
  Sort[mapped] === Sort[msbSet]
];
cases = Flatten[Table[Table[{gate, n, IcSamples[n][[1]]}, {gate, gates}], {n, nVals}], 1];
results = (Function[{t}, With[{g = t[[1]], nn = t[[2]], ic = t[[3]]}, <|"gate" -> g, "n" -> nn, "Ic" -> ic, "ok" -> checkOne[g, nn, ic]|>]]) /@ cases;
allOK = And @@ (results[[All, "ok"]]);
CreateDirectory["results/tests/theory005", CreateIntermediateDirectories -> True];
Export["results/tests/theory005/OrderingPolicy.json", results];
Export["results/tests/theory005/Status.txt", If[allOK, "PASS", "FAIL"]];

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export["results/tests/theory005/Done.txt", DateString[], "Text"];
