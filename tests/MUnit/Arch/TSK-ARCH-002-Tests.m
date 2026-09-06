base = FileNameJoin[{"results", "tests", "arch2"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
dirs = {"experiments", "data", "results", "figures", "tests"};
exists = DirectoryQ /@ dirs;
writeChecks = Table[
  Quiet[Check[(s = OpenWrite[FileNameJoin[{dir, "writecheck.txt"}]]; Close[s]; True), False]], {dir, dirs}];
status = If[And @@ exists && And @@ writeChecks, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "Exists" -> exists, "WriteChecks" -> writeChecks, "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
