AppendTo[$Path, "src/Packages"];
Needs["Integration`Experiments`"];
base = FileNameJoin[{"results", "tests", "mixed001Comparison"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
inputsFor[n_Integer] := IntegerDigits[Range[0, 2^n - 1], 2, n];
predictiveEval[v_List, Ic_List, gate_String, params_Association] := Module[{bits = v[[Ic]]}, Which[
  gate === "OR", Boole[MemberQ[bits, 1]],
  gate === "AND", Boole[FreeQ[bits, 0] && Length[bits] > 0],
  gate === "XOR", Mod[Total[bits], 2],
  gate === "XNOR", 1 - Mod[Total[bits], 2],
  gate === "NAND", Boole[MemberQ[bits, 0]],
  gate === "NOR", Boole[FreeQ[bits, 1]],
  gate === "NOT", Module[{i = Lookup[params, "i", If[Length[Ic] == 1, Ic[[1]], Ic[[1]]]]}, 1 - v[[i]]],
  gate === "IMPLIES" || gate === "NIMPLIES", Module[{pair = Lookup[params, "pair", If[Length[Ic] >= 2, {Ic[[1]], Ic[[2]]}, {Ic[[1]], Ic[[1]]}]], a, b}, a = v[[pair[[1]]]]; b = v[[pair[[2]]]]; If[gate === "IMPLIES", Boole[(1 - a) == 1 || b == 1], Boole[a == 1 && b == 0]]],
  gate === "MAJORITY", Boole[Total[bits] >= Ceiling[Length[bits]/2]],
  gate === "KOFN", Module[{k = Lookup[params, "k", 1], strict = TrueQ[Lookup[params, "strict", False]]}, If[strict, Boole[Count[bits, 1] > k], Boole[Count[bits, 1] >= k]]],
  gate === "CANALISING", Module[{ci = Lookup[params, "canalisingIndex", If[Length[Ic] >= 1, Ic[[1]], Ic[[1]]]], vcan = Lookup[params, "canalisingValue", 1], cout = Lookup[params, "canalisedOutput", 0]}, If[v[[ci]] == vcan, cout, Boole[MemberQ[bits, 1]]]],
  True, 0
]];
runPredictiveMixedOnInputs[cm_, dyn_List, inputs_List, params_Association: <||>] := Module[{n = Length[dyn], out},
  out = Table[
    Module[{Ic = Flatten[Position[cm[[k]], 1]], p = Lookup[params, k, <||>]}, predictiveEval[inputs[[j]], Ic, dyn[[k]], p]],
    {j, 1, Length[inputs]}, {k, 1, n}
  ];
  out
];
compareOne[cm_, dyn_, params_: <||>] := Module[{rep, pred, t1, t2, acc, inputs, res},
  {t1, res} = AbsoluteTiming[Integration`Experiments`CreateRepertoiresDispatch[cm, dyn, params]];
  inputs = res["RepertoireInputs"]; rep = res["RepertoireOutputs"]; 
  {t2, pred} = AbsoluteTiming[runPredictiveMixedOnInputs[cm, dyn, inputs, params]];
  acc = N[Total[Flatten[Boole[MapThread[Equal, {rep, pred}, 2]]]] / Length[Flatten[rep]]];
  <|"baselineTime" -> N[t1], "predictiveTime" -> N[t2], "accuracy" -> acc|>
];
smallCases = {
  { {{0,1,0},{1,0,1},{0,1,0}}, {"AND","OR","XOR"}, <||> },
  { {{0,1,1},{1,0,0},{0,1,0}}, {"NAND","MAJORITY","OR"}, <||> }
};
mediumCases = {
  { {{0,1,1,0,0,0,0,0,0,0},{1,0,1,0,0,0,0,0,0,0},{0,0,0,1,1,0,0,0,0,0},{0,1,1,0,1,0,0,0,0,0},{0,0,0,0,0,1,0,0,0,0},{0,0,0,0,1,0,1,0,0,0},{0,0,0,0,0,1,0,0,0,0},{1,0,0,0,0,0,0,0,1,0},{0,1,0,0,0,0,0,0,0,1},{0,0,1,1,0,0,1,1,0,0}}, {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","KOFN"}, <|10 -> <|"k" -> 2|>|> }
};
phase1 = compareOne @@@ smallCases;
phase2 = compareOne @@@ mediumCases;
phase1Metrics = phase1[[All, {"accuracy","baselineTime","predictiveTime"}]];
phase2Metrics = phase2[[All, {"accuracy","baselineTime","predictiveTime"}]];
Export[FileNameJoin[{base, "Phase1.json"}], phase1Metrics, "JSON"];
Export[FileNameJoin[{base, "Phase2.json"}], phase2Metrics, "JSON"];
summary = <|"phase1Accuracy" -> (phase1[[All, "accuracy"]]), "phase1BaselineTime" -> (phase1[[All, "baselineTime"]]), "phase1PredictiveTime" -> (phase1[[All, "predictiveTime"]]), "phase2Accuracy" -> (phase2[[All, "accuracy"]]), "phase2BaselineTime" -> (phase2[[All, "baselineTime"]]), "phase2PredictiveTime" -> (phase2[[All, "predictiveTime"]])|>;
Export[FileNameJoin[{base, "Summary.json"}], AssociationMap[Identity, summary] // Normal, "JSON"];
status = If[Min[Flatten@{summary["phase1Accuracy"], summary["phase2Accuracy"]}] == 1., "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "ResultsPath" -> base, "Summary" -> summary]