Get["experiments/mixed/Mixed.m"];
res = MixedValidationRun[3, 42];
base = FileNameJoin[{"results", "tests", "mixed002"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
Export[FileNameJoin[{base, "Status.txt"}], {If[res["ErrorRate"] == 0., "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[res["ErrorRate"] == 0., "OK", "FAIL"], "ErrorRate" -> res["ErrorRate"], "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
