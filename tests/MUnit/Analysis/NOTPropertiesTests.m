AppendTo[$Path, "src/Packages"];
Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results", "tests", "analysis_not"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
inputs = {{0},{1}};
out = Integration`Gates`ApplyGate["NOT", #] & /@ inputs;
inv = Integration`Gates`ApplyGate["NOT", {#}] & /@ out;
okInv = inv === Flatten[inputs];
sensPairs = {{{0},{1}}, {{1},{0}}};
okSens = And @@ Table[Integration`Gates`ApplyGate["NOT", sensPairs[[i,1]]] != Integration`Gates`ApplyGate["NOT", sensPairs[[i,2]]], {i, Length[sensPairs]}];
status = If[okInv && okSens, "OK", "FAIL"];
Export[FileNameJoin[{base, "PropertiesStatus.txt"}], {status, DateString[]}, "Text"];
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
