AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_implies"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 3; pair = {1, 3};
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
empImp = Flatten@Position[((1 - #[[pair[[1]]]]) || #[[pair[[2]]]]) & /@ inputs, True, 1];
empNImp = Flatten@Position[(#[[pair[[1]]]] && (1 - #[[pair[[2]]]])) & /@ inputs, True, 1];
anaImp = Integration`Gates`IndexSetNetwork["IMPLIES", n, {}, <|"pair" -> pair|>];
anaNImp = Integration`Gates`IndexSetNetwork["NIMPLIES", n, {}, <|"pair" -> pair|>];
okImp = Sort[empImp] === Sort[anaImp];
okNImp = Sort[empNImp] === Sort[anaNImp];
Export[FileNameJoin[{base, "IndexSetNetwork_IMPLIES_pair1_3.json"}], empImp, "JSON"];
Export[FileNameJoin[{base, "IndexSetNetwork_NIMPLIES_pair1_3.json"}], empNImp, "JSON"];
Export[FileNameJoin[{base, "Status_network_pair.txt"}], {If[okImp && okNImp, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okImp && okNImp, "OK", "FAIL"], "ResultsPath" -> base]