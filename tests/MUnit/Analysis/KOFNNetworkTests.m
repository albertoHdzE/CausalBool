AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_kofn"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 4; Ic = {2, 4};
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
(* R4/W0.3: renamed identifiers — anaIdx_k1 parses as Pattern[anaIdx, Blank[k1]],
   so Set never fired and the comparison tested symbol names, not index sets. *)
empIdxK1 = Flatten@Position[(Count[#[[Ic]], 1] >= 1) & /@ inputs, True, 1];
empIdxK2 = Flatten@Position[(Count[#[[Ic]], 1] >= 2) & /@ inputs, True, 1];
anaIdxK1 = Integration`Gates`IndexSetNetwork["KOFN", n, Ic, <|"k" -> 1|>];
anaIdxK2 = Integration`Gates`IndexSetNetwork["KOFN", n, Ic, <|"k" -> 2|>];
okNet = (Sort[empIdxK1] === Sort[anaIdxK1]) && (Sort[empIdxK2] === Sort[anaIdxK2]);
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_4_k1.csv"}], Normal[anaIdxK1], "CSV"];
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_4_k2.csv"}], Normal[anaIdxK2], "CSV"];
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_4_empirical_k1.csv"}], empIdxK1, "CSV"];
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_4_empirical_k2.csv"}], empIdxK2, "CSV"];
Export[FileNameJoin[{base, "Status_network.txt"}], {If[okNet, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okNet, "OK", "FAIL"], "ResultsPath" -> base]