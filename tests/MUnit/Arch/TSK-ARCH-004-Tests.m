base = FileNameJoin[{"results", "tests", "arch4"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
ver = $VersionString;
SeedRandom[1234]; a = RandomInteger[{0, 1}, 16];
SeedRandom[1234]; b = RandomInteger[{0, 1}, 16];
okDet = (a === b);
okVer = StringContainsQ[ver, "Wolfram"];
Export[FileNameJoin[{base, "sequence.csv"}], a, "CSV"];
status = If[okDet && okVer, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[], ver}, "Text"];
Association["Status" -> status, "Deterministic" -> okDet, "VersionOK" -> okVer, "ResultsPath" -> base]