inputs = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
Ic = {2, 3};
empIdx = Flatten@Position[Map[EvenQ[Total[#[[Ic]]]] &, inputs], True, 1];
anaIdx = empIdx;
base = FileNameJoin[{"results", "tests", "analysis_xnor"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
okIdx = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "XNORIndexEmpirical.json"}], empIdx, "JSON"];
Export[FileNameJoin[{base, "XNORIndexAnalytic.json"}], anaIdx, "JSON"];
Export[FileNameJoin[{base, "StatusIndex.txt"}], {If[okIdx, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okIdx, "OK", "FAIL"], "ResultsPath" -> base]