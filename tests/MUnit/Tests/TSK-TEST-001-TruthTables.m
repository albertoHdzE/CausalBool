AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

SeedRandom[123456];

base = FileNameJoin[{"results", "tests", "tests001"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

phi[j_, n_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2];
lsbInputs[n_Integer] := Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, 2^n - 1}];

truthMSB[gate_String, n_Integer, params_: <||>] := Integration`Gates`TruthTable[gate, n, params][[All, 2]];
truthLSB[gate_String, n_Integer, params_: <||>] := Module[{inputs = lsbInputs[n]}, Integration`Gates`ApplyGate[gate, #, params] & /@ inputs];

indexSetFromTruth[vals_List] := Flatten@Position[vals, 1];

maxArity = 6;
arityRange[binary_: True] := If[binary, Range[2, maxArity], {1}];

cases = Join[
  Table[{"AND", n, <||>}, {n, arityRange[]}],
  Table[{"OR", n, <||>}, {n, arityRange[]}],
  Table[{"XOR", n, <||>}, {n, arityRange[]}],
  Table[{"NAND", n, <||>}, {n, arityRange[]}],
  Table[{"NOR", n, <||>}, {n, arityRange[]}],
  Table[{"XNOR", n, <||>}, {n, arityRange[]}],
  Table[{"MAJORITY", n, <||>}, {n, arityRange[]}],
  {{"IMPLIES", 2, <||>}, {"NIMPLIES", 2, <||>}},
  {{"NOT", 1, <||>}},
  Table[{"KOFN", 2, <|"k" -> k|>}, {k, {1, 2}}],
  {{"CANALISING", 2, <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 0|>}}
];

computeOne[{gate_, n_, params_}] := Module[{msbTruth, lsbTruth, lsbIdx, mappedIdx, msbIdx, okOrd},
  msbTruth = truthMSB[gate, n, params];
  lsbTruth = truthLSB[gate, n, params];
  lsbIdx = indexSetFromTruth[lsbTruth];
  mappedIdx = Sort[phi[#, n] & /@ lsbIdx];
  msbIdx = indexSetFromTruth[msbTruth];
  okOrd = (Sort[msbIdx] === Sort[mappedIdx]);
  <|"gate" -> gate, "arity" -> n, "params" -> params, "okOrdering" -> okOrd, "MSBTruth" -> msbTruth, "LSBTruth" -> lsbTruth, "MSBIdx" -> msbIdx, "MappedLSBIdx" -> mappedIdx|>
];

timedResults = Table[Module[{t, r}, {t, r} = AbsoluteTiming[computeOne[cases[[i]]]]; Append[r, "timeSec" -> t]], {i, Length[cases]}];
results = timedResults;
allOK = And @@ (results[[All, "okOrdering"]]);

Export[FileNameJoin[{base, "TruthTables.json"}], results, "JSON"];
Export[FileNameJoin[{base, "OrderingCheck.json"}], results[[All, {"gate", "arity", "okOrdering", "MSBIdx", "MappedLSBIdx"}]], "JSON"];
Export[FileNameJoin[{base, "PerfTT001.json"}], results[[All, {"gate", "arity", "okOrdering", "timeSec"}]], "JSON"];
summaryLines = StringRiffle[Map[Function[r, r["gate"] <> "/" <> ToString[r["arity"]] <> ": " <> If[r["okOrdering"], "PASS", "FAIL"] <> " (" <> ToString[NumberForm[r["timeSec"], {4, 3}]] <> "s)"], results], "\n"];
Export[FileNameJoin[{base, "Report.txt"}], summaryLines <> "\nSUMMARY: " <> If[allOK, "OK", "FAIL"], "Text"];
Export[FileNameJoin[{base, "Status.txt"}], If[allOK, "OK", "FAIL"], "Text"];

Association["Status" -> If[allOK, "OK", "FAIL"], "ResultsPath" -> base]

