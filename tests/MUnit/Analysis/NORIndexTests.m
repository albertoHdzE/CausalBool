inputs = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
Ic = {2, 3};
(* Empirical one-set: connected bits all 0 *)
empOne = Flatten@Position[Map[And @@ Map[# == 0 &, #[[Ic]]] &, inputs], True, 1];
(* Empirical zero-set is the complement *)
allIdx = Range[Length[inputs]];
empZero = Complement[allIdx, empOne];
base = FileNameJoin[{"results", "tests", "analysis_nor"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
okZeroOne = Sort[empOne] === {1, 5} && Sort[empZero] === {2, 3, 4, 6, 7, 8};
Export[FileNameJoin[{base, "NOROneIndices.json"}], empOne, "JSON"];
Export[FileNameJoin[{base, "NORZeroIndices.json"}], empZero, "JSON"];
Export[FileNameJoin[{base, "StatusIndex.txt"}], {If[okZeroOne, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okZeroOne, "OK", "FAIL"], "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
