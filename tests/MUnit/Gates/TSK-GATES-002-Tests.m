AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
Needs["Integration`Alpha`"];
Needs["Integration`Experiments`"];
base = FileNameJoin[{"results", "tests", "gates002"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
cm1 = {{0,1},{1,0}};
dyn1 = {"AND","XOR"};
legacy = Integration`Alpha`RunDynamic[cm1, dyn1]["RepertoireOutputs"];
disp = Integration`Experiments`RunDynamicDispatch[cm1, dyn1]["RepertoireOutputs"];
okLegacy = (legacy === disp);
cm2 = {{1,1},{1,1}};
dyn2 = {"KOFN","KOFN"};
params = <|1 -> <|"k" -> 2|>, 2 -> <|"k" -> 1|>|>;
inputs = Table[IntegerDigits[x,2,2], {x,0,3}];
exp2 = Table[{Integration`Gates`ApplyGate["KOFN", x, <|"k"->2|>], Integration`Gates`ApplyGate["KOFN", x, <|"k"->1|>]}, {x, inputs}];
res2 = Integration`Experiments`CreateRepertoiresDispatch[cm2, dyn2, params]["RepertoireOutputs"];
okParams = (res2 === exp2);
status = If[okLegacy && okParams, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "LegacyVsDispatch.json"}], <|"Equal"->okLegacy|>, "JSON"];
Export[FileNameJoin[{base, "ParamDispatch.json"}], <|"Equal"->okParams|>, "JSON"];
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
