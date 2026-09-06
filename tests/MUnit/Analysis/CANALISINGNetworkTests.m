AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_canalising"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 4; Ic = {2, 3}; paramsN = <|"canalisingIndex" -> 2, "canalisingValue" -> 1, "canalisedOutput" -> 1|>;
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
empIdx = Flatten@Position[(Integration`Gates`ApplyGate["CANALISING", {#[[2]], #[[3]]}, paramsN] == 1) & /@ inputs, True, 1];
anaIdx = Integration`Gates`IndexSetNetwork["CANALISING", n, Ic, paramsN];
ok = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "IndexSetNetwork_n4_Ic2_3.csv"}], Normal[anaIdx], "CSV"];
Export[FileNameJoin[{base, "Status_network.txt"}], {If[ok, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[ok, "OK", "FAIL"], "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
