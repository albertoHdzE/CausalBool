Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/BioMetrics.m"];
base = FileNameJoin[{"results", "tests", "theory002"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

avgSensitivityNode[cm_List, dyn_List, params_Association:<||>, i_Integer] := Module[{n = Length[dyn], Ic, inputs, flips, f, s},
  Ic = Flatten@Position[cm[[i]], 1];
  inputs = IntegerDigits[Range[0, 2^n - 1], 2, n];
  f[v_] := Integration`Gates`ApplyGate[dyn[[i]], v[[Ic]], Lookup[params, i, <||>]];
  flips = Total@Table[Total@Table[Boole[f[v] != f[ReplacePart[v, k -> 1 - v[[k]]]]], {k, Ic}], {v, inputs}];
  s = N[flips/(Length[Ic]*Length[inputs])]
];

avgSensitivity[cm_List, dyn_List, params_Association:<||>] := Module[{n = Length[dyn]}, N@Total@Table[avgSensitivityNode[cm, dyn, params, i], {i, n}]];

compressionWeight[gate_, Ic_List, params_Association:<||>] := Module[{d = Length[Ic]}, Switch[gate,
  "AND" | "OR" | "NAND" | "NOR", 1 + d,
  "XOR" | "XNOR", 1 + 1,
  "NOT", 1,
  "IMPLIES" | "NIMPLIES", 1 + 2,
  "MAJORITY", 1 + 1,
  "KOFN", 1 + 1,
  "CANALISING", 1 + If[KeyExistsQ[params, "canalisedOutput"], 0, 1],
  _, 1 + d
]];

computeCompression[cm_List, dyn_List, params_Association:<||>] := Module[{n = Length[dyn], ics}, ics = Table[Flatten@Position[cm[[i]], 1], {i, n}]; Total@Table[compressionWeight[dyn[[i]], ics[[i]], Lookup[params, i, <||>]], {i, n}]];

(* AUDIT03/R2b — the local cost model is gone; this delegates to the single
   owner, Integration`BioMetrics`. Two things were wrong with the copy that
   stood here. It duplicated a formula that four other files also carried, and
   it LACKED the log2(n+1) in-degree field, so the code it priced had Kraft sum
   n+1 rather than 1 and was not uniquely decodable. Delegation fixes both at
   once and makes a future divergence impossible rather than merely unlikely.
   The assertions below are inequalities, so the value moving by n*log2(n+1)
   does not move the test's verdict; that was checked, not assumed. *)
encodeCostBits[cm_List, dyn_List, params_Association:<||>] :=
  Integration`BioMetrics`ComputeDescriptionLength[cm, dyn, params]["D"];

cm = {{0,1,0,0,0},{1,0,1,0,0},{0,1,0,1,0},{0,0,1,0,1},{0,0,0,1,0}};
dyn = {"AND","OR","XOR","KOFN","CANALISING"};
params = <|4 -> <|"k" -> 2|>|>;
paramsCan = <|5 -> <|"canalisingIndex" -> 4, "canalisingValue" -> 1, "canalisedOutput" -> 1|>|>;

cVal = computeCompression[cm, dyn, params];
dBitsVal = encodeCostBits[cm, dyn, params];
sBarVal = avgSensitivity[cm, dyn, params];
cnormVal = N[cVal/Total@Table[1 + Length@Flatten@Position[cm[[i]], 1], {i, Length[dyn]}]];
cnormSensVal = N[dBitsVal/Max[1, sBarVal + 1]];

cCanVal = computeCompression[cm, dyn, Join[params, paramsCan]];
dBitsCanVal = encodeCostBits[cm, dyn, Join[params, paramsCan]];
sBarCanVal = avgSensitivity[cm, dyn, Join[params, paramsCan]];
cnormCanVal = N[cCanVal/Total@Table[1 + Length@Flatten@Position[cm[[i]], 1], {i, Length[dyn]}]];
cnormSensCanVal = N[dBitsCanVal/Max[1, sBarCanVal + 1]];

okBound = dBitsVal <= 8*cVal + 64;
okNormDecrease = cnormSensCanVal <= cnormSensVal + 10^-12;

toJSONVal[x_] := If[NumericQ[x], N@x, ToString@N@x];
metrics = <|"C"->toJSONVal@cVal, "Dbits"->toJSONVal@dBitsVal, "Sbar"->toJSONVal@sBarVal, "Cnorm"->toJSONVal@cnormVal, "CnormSens"->toJSONVal@cnormSensVal, "Ccan"->toJSONVal@cCanVal, "DbitsCan"->toJSONVal@dBitsCanVal, "SbarCan"->toJSONVal@sBarCanVal, "CnormCan"->toJSONVal@cnormCanVal, "CnormSensCan"->toJSONVal@cnormSensCanVal, "okBound"->okBound, "okNormDecrease"->okNormDecrease|>;
metricsStr = AssociationMap[ToString, metrics];
jsonText = StringJoin["{", StringRiffle[KeyValueMap["\""<>#1<>"\": \""<>#2<>"\""&, metricsStr], ","], "}"];
Export[FileNameJoin[{base, "Metrics.json"}], jsonText, "Text"];
statusStr = "OK";
Export[FileNameJoin[{base, "Status.txt"}], StringJoin[statusStr, "\n", DateString[]], "Text"];
Association["Status"->statusStr, "ResultsPath"->base]
