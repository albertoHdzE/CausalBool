AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_not"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 3; i = 2;
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
empIdx = Flatten@Position[(Integration`Gates`ApplyGate["NOT", {#[[i]]}] == 1) & /@ inputs, True, 1];
anaIdx = Integration`Gates`IndexSetNetwork["NOT", n, {}, <|"i" -> i|>];
ok = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "IndexSetNetwork_NOT_i2.json"}], empIdx, "JSON"];
Export[FileNameJoin[{base, "Status_network_not.txt"}], {If[ok, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[ok, "OK", "FAIL"], "ResultsPath" -> base]