AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_kofn"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 4; Ic = {2, 4};
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
empIdx_k1 = Flatten@Position[(Count[#[[Ic]], 1] >= 1) & /@ inputs, True, 1];
empIdx_k2 = Flatten@Position[(Count[#[[Ic]], 1] >= 2) & /@ inputs, True, 1];
anaIdx_k1 = Integration`Gates`IndexSetNetwork["KOFN", n, Ic, <|"k" -> 1|>];
anaIdx_k2 = Integration`Gates`IndexSetNetwork["KOFN", n, Ic, <|"k" -> 2|>];
okNet = (Sort[empIdx_k1] === Sort[anaIdx_k1]) && (Sort[empIdx_k2] === Sort[anaIdx_k2]);
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_4_k1.csv"}], Normal[anaIdx_k1], "CSV"];
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_4_k2.csv"}], Normal[anaIdx_k2], "CSV"];
Export[FileNameJoin[{base, "Status_network.txt"}], {If[okNet, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okNet, "OK", "FAIL"], "ResultsPath" -> base]