inputs = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
Ic = {2, 3};
empIdx = Flatten@Position[Map[OddQ[Total[#[[Ic]]]] &, inputs], True, 1];
anaIdx = Flatten@Position[Map[OddQ[Total[#[[Ic]]]] &, inputs], True, 1];
base = FileNameJoin[{"results", "tests", "analysis_xor"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
okIdx = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "XORIndexEmpirical.json"}], empIdx, "JSON"];
Export[FileNameJoin[{base, "XORIndexAnalytic.json"}], anaIdx, "JSON"];
Export[FileNameJoin[{base, "StatusIndex.txt"}], {If[okIdx, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okIdx, "OK", "FAIL"], "ResultsPath" -> base]