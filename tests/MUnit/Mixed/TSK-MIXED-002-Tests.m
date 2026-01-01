Get["experiments/mixed/Mixed.m"];
res = MixedValidationRun[3, 42];
base = FileNameJoin[{"results", "tests", "mixed002"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
Export[FileNameJoin[{base, "Status.txt"}], {If[res["ErrorRate"] == 0., "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[res["ErrorRate"] == 0., "OK", "FAIL"], "ErrorRate" -> res["ErrorRate"], "ResultsPath" -> base]