base = FileNameJoin[{"results", "tests", "arch2"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
dirs = {"experiments", "data", "results", "figures", "tests"};
exists = DirectoryQ /@ dirs;
writeChecks = Table[
  Quiet[Check[(s = OpenWrite[FileNameJoin[{dir, "writecheck.txt"}]]; Close[s]; True), False]], {dir, dirs}];
status = If[And @@ exists && And @@ writeChecks, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "Exists" -> exists, "WriteChecks" -> writeChecks, "ResultsPath" -> base]