AppendTo[$Path, "src/Packages"];
Needs["Integration`Alpha`"];
Needs["Integration`Gates`"];
allInputs[n_] := Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
nodeInputs[cm_, input_, n_] := Module[{idx}, idx = Flatten[Position[cm[[n]], 1]]; Part[input, idx]];
applyGateOutputs[cm_, dynamic_, input_] := Module[{n, out}, out = Table[Integration`Gates`ApplyGate[dynamic[[n]], nodeInputs[cm, input, n]], {n, 1, Length[dynamic]}]; out];
MixedValidationRun[noNodes_Integer, seed_Integer] := Module[{gates, cm, dynamic, inputs, outputsAlpha, outputsAlpha2, diffs, errRate, base, figbase, rep},
SeedRandom[seed];
gates = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR"};
cm = Table[If[i == j, 0, RandomInteger[{0, 1}]], {i, 1, noNodes}, {j, 1, noNodes}];
dynamic = Table[RandomChoice[gates], {noNodes}];
rep = Integration`Alpha`CreateRepertoires[cm, dynamic];
inputs = rep["RepertoireInputs"];
outputsAlpha = rep["RepertoireOutputs"];
outputsAlpha2 = Integration`Alpha`RunDynamic[cm, dynamic]["RepertoireOutputs"];
(* AUDIT01/T4.1 (ORDERING.md §5): unsupported-gate cells now carry an explicit
   Failure["UnsupportedGate"] on BOTH legacy sides instead of silently-stale equal
   values (F24). Such cells are consistent-by-construction and are excluded from
   the error rate; genuine value mismatches still count. The unsupported-cell
   count is disclosed rather than hidden. *)
pairConsistent[a_, b_] := Or[a === b,
   MatchQ[{a, b}, {Failure["UnsupportedGate", _], Failure["UnsupportedGate", _]}]];
diffs = MapThread[Boole[! pairConsistent[#1, #2]] &, {outputsAlpha, outputsAlpha2}, 2];
unsupportedCells = Count[Flatten[outputsAlpha], Failure["UnsupportedGate", _]];
errRate = N[Total[Flatten[diffs]]/Length[Flatten[diffs]]];
base = FileNameJoin[{"results", "mixed", "validation"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
figbase = FileNameJoin[{"figures", "mixed"}]; If[!DirectoryQ[figbase], CreateDirectory[figbase, CreateIntermediateDirectories -> True]];
Export[FileNameJoin[{base, "cm.csv"}], cm, "CSV"];
Export[FileNameJoin[{base, "dynamic.csv"}], dynamic, "CSV"];
Export[FileNameJoin[{base, "Inputs.csv"}], inputs, "CSV"];
Export[FileNameJoin[{base, "OutputsAlpha.csv"}], outputsAlpha, "CSV"];
Export[FileNameJoin[{base, "OutputsAlpha2.csv"}], outputsAlpha2, "CSV"];
Export[FileNameJoin[{base, "Diffs.csv"}], diffs, "CSV"];
Export[FileNameJoin[{base, "Metrics.json"}], <|"ErrorRate" -> errRate, "UnsupportedGateCells" -> unsupportedCells|>, "JSON"];
Export[FileNameJoin[{figbase, "MixedValidation.png"}], Graphics[Text[Style["ErrorRate = " <> ToString[errRate], 14]]], "PNG"];
Association["ErrorRate" -> errRate, "UnsupportedGateCells" -> unsupportedCells, "ResultsPath" -> base, "FiguresPath" -> figbase]
]