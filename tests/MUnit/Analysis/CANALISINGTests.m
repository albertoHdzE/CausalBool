AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_canalising"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
(* Case A: arity=3, canalisingIndex=1, value=1, output=0 (collapse to 0 when x1=1; else OR over all inputs) *)
paramsA = <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 0|>;
ttA = Integration`Gates`TruthTable["CANALISING", 3, paramsA];
idxA = Integration`Gates`IndexSet["CANALISING", 3, paramsA];
inputs3 = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
empIdxA = Flatten@Position[(Integration`Gates`ApplyGate["CANALISING", #, paramsA] == 1) & /@ inputs3, True, 1];
okA = Sort[idxA] === Sort[empIdxA];
(* Case B: arity=3, canalisingIndex=2, value=0, output=1 (collapse to 1 when x2=0; else OR) *)
paramsB = <|"canalisingIndex" -> 2, "canalisingValue" -> 0, "canalisedOutput" -> 1|>;
ttB = Integration`Gates`TruthTable["CANALISING", 3, paramsB];
idxB = Integration`Gates`IndexSet["CANALISING", 3, paramsB];
empIdxB = Flatten@Position[(Integration`Gates`ApplyGate["CANALISING", #, paramsB] == 1) & /@ inputs3, True, 1];
okB = Sort[idxB] === Sort[empIdxB];
status = If[okA && okB, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "IndexSet_caseA.json"}], idxA, "JSON"];
Export[FileNameJoin[{base, "IndexSet_caseB.json"}], idxB, "JSON"];
Export[FileNameJoin[{base, "TruthTable_caseA.json"}], ttA, "JSON"];
Export[FileNameJoin[{base, "TruthTable_caseB.json"}], ttB, "JSON"];
Association["Status" -> status, "ResultsPath" -> base]