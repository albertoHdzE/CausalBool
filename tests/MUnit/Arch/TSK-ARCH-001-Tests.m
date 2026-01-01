base = FileNameJoin[{"results", "tests", "arch"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
existsDoc = FileExistsQ["docs/architecture.md"];
existsTests = DirectoryQ["tests/MUnit"];
writeOK = Quiet[Check[(s = OpenWrite[FileNameJoin[{base, "writecheck.txt"}]]; Close[s]; True), False]];
status = If[existsDoc && existsTests && writeOK, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "DocExists" -> existsDoc, "TestsDirExists" -> existsTests, "WriteOK" -> writeOK, "ResultsPath" -> base]