base = FileNameJoin[{"results", "tests", "arch4"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
(* R4/W0.3: $VersionString is not a built-in — it stayed symbolic, so the verdict
   exported an unevaluated If (UNPARSEABLE). $Version is the real symbol. *)
ver = $Version;
SeedRandom[1234]; a = RandomInteger[{0, 1}, 16];
SeedRandom[1234]; b = RandomInteger[{0, 1}, 16];
okDet = (a === b);
okVer = StringQ[ver] && StringLength[ver] > 0;
Export[FileNameJoin[{base, "sequence.csv"}], a, "CSV"];
status = If[okDet && okVer, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[], ver}, "Text"];
Association["Status" -> status, "Deterministic" -> okDet, "VersionOK" -> okVer, "ResultsPath" -> base]