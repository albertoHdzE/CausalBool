Get["src/Packages/Integration/Experiments.m"];
patternSymbol[col_List] := Module[{z, o}, z = Count[col, 0]; o = Count[col, 1]; If[z == Length[col], 0, If[o == Length[col], 1, "*"]]];
base = FileNameJoin[{"results", "tests", "pattern001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
cmX = {{0,1},{1,0}};
dynX = {"XOR","XOR"};
repX = Integration`Experiments`CreateRepertoiresDispatch[cmX, dynX]["RepertoireOutputs"];
patX = patternSymbol /@ Transpose[repX];
okX = (patX === {"*","*"});
cmK = {{1,1},{1,1}};
dynK = {"KOFN","KOFN"};
paramsK = <|1 -> <|"k" -> 0|>, 2 -> <|"k" -> 3|>|>;
repK = Integration`Experiments`CreateRepertoiresDispatch[cmK, dynK, paramsK]["RepertoireOutputs"];
patK = patternSymbol /@ Transpose[repK];
okK = (patK === {1,0});
status = If[okX && okK, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "Patterns.json"}], <|"XOR"->patX, "KOFN"->patK|>, "JSON"];
Association["Status"->status, "ResultsPath"->base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
