AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_implies"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
ttImp = Integration`Gates`TruthTable["IMPLIES", 2];
expectedImp = {{{0, 0}, 1}, {{0, 1}, 1}, {{1, 0}, 0}, {{1, 1}, 1}};
okImpTT = ttImp === expectedImp;
idxImp = Integration`Gates`IndexSet["IMPLIES", 2];
okImpIdx = idxImp === {1, 2, 4};
ttNImp = Integration`Gates`TruthTable["NIMPLIES", 2];
expectedNImp = {{{0, 0}, 0}, {{0, 1}, 0}, {{1, 0}, 1}, {{1, 1}, 0}};
okNImpTT = ttNImp === expectedNImp;
idxNImp = Integration`Gates`IndexSet["NIMPLIES", 2];
okNImpIdx = idxNImp === {3};
status = If[okImpTT && okImpIdx && okNImpTT && okNImpIdx, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "TruthTableImplies.json"}], ttImp, "JSON"];
Export[FileNameJoin[{base, "IndexSetImplies.json"}], idxImp, "JSON"];
Export[FileNameJoin[{base, "TruthTableNImplies.json"}], ttNImp, "JSON"];
Export[FileNameJoin[{base, "IndexSetNImplies.json"}], idxNImp, "JSON"];
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
