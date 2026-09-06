AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_not"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 3; i = 2;
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
empIdx = Flatten@Position[(Integration`Gates`ApplyGate["NOT", {#[[i]]}] == 1) & /@ inputs, True, 1];
anaIdx = Integration`Gates`IndexSetNetwork["NOT", n, {}, <|"i" -> i|>];
ok = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "IndexSetNetwork_NOT_i2.json"}], empIdx, "JSON"];
Export[FileNameJoin[{base, "Status_network_not.txt"}], {If[ok, "OK", "FAIL"], DateString[]}, "Text"];
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
