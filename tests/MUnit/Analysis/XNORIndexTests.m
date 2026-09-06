inputs = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
Ic = {2, 3};
empIdx = Flatten@Position[Map[EvenQ[Total[#[[Ic]]]] &, inputs], True, 1];
anaIdx = empIdx;
base = FileNameJoin[{"results", "tests", "analysis_xnor"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
okIdx = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "XNORIndexEmpirical.json"}], empIdx, "JSON"];
Export[FileNameJoin[{base, "XNORIndexAnalytic.json"}], anaIdx, "JSON"];
Export[FileNameJoin[{base, "StatusIndex.txt"}], {If[okIdx, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okIdx, "OK", "FAIL"], "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
