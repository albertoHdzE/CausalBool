AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_kofn"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
idxNonstrict = Integration`Gates`IndexSet["KOFN", 3, <|"k" -> 2|>];
idxStrict = Integration`Gates`IndexSet["KOFN", 3, <|"k" -> 2, "strict" -> True|>];
okStrict = (idxStrict === {8}) && (idxNonstrict === {4, 6, 7, 8});
Export[FileNameJoin[{base, "IndexSet_k2_strict.json"}], idxStrict, "JSON"];
Export[FileNameJoin[{base, "IndexSet_k2_nonstrict.json"}], idxNonstrict, "JSON"];
Export[FileNameJoin[{base, "Status_strict.txt"}], {If[okStrict, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okStrict, "OK", "FAIL"], "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
