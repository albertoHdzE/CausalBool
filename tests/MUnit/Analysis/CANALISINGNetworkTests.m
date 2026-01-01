AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_canalising"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 4; Ic = {2, 3}; paramsN = <|"canalisingIndex" -> 2, "canalisingValue" -> 1, "canalisedOutput" -> 1|>;
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
empIdx = Flatten@Position[(Integration`Gates`ApplyGate["CANALISING", {#[[2]], #[[3]]}, paramsN] == 1) & /@ inputs, True, 1];
anaIdx = Integration`Gates`IndexSetNetwork["CANALISING", n, Ic, paramsN];
ok = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_3.csv"}], Normal[anaIdx], "CSV"];
Export[FileNameJoin[{base, "Status_network.txt"}], {If[ok, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[ok, "OK", "FAIL"], "ResultsPath" -> base]