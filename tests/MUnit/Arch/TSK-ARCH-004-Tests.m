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

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
