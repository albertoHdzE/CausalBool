base = FileNameJoin[{"results", "tests", "arch"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
existsDoc = FileExistsQ["docs/architecture.md"];
existsTests = DirectoryQ["tests/MUnit"];
writeOK = Quiet[Check[(s = OpenWrite[FileNameJoin[{base, "writecheck.txt"}]]; Close[s]; True), False]];
status = If[existsDoc && existsTests && writeOK, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "DocExists" -> existsDoc, "TestsDirExists" -> existsTests, "WriteOK" -> writeOK, "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
