AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_not"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
tt = Integration`Gates`TruthTable["NOT", 1];
expectedTT = {{{0}, 1}, {{1}, 0}};
okTT = tt === expectedTT;
idx = Integration`Gates`IndexSet["NOT", 1];
expectedIdx = {1};
okIdx = idx === expectedIdx;
status = If[okTT && okIdx, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "TruthTable.json"}], tt, "JSON"];
Export[FileNameJoin[{base, "IndexSet.json"}], idx, "JSON"];
Association["Status" -> status, "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
