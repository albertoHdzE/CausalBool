Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results", "tests", "mixed002"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
gates = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY"};
runOne[n_, seed_] := Module[{cm, dyn, params, inputs, rep, run, diffs, err},
  SeedRandom[seed];
  cm = Table[If[i==j,0,RandomInteger[{0,1}]], {i,1,n},{j,1,n}];
  dyn = Table[RandomChoice[gates], {n}];
  params = <||>;
  rep = Integration`Experiments`CreateRepertoiresDispatch[cm, dyn, params]["RepertoireOutputs"];
  run = Integration`Experiments`RunDynamicDispatch[cm, dyn, params]["RepertoireOutputs"];
  diffs = MapThread[Boole[#1 != #2] &, {rep, run}];
  err = N[Total[Flatten[diffs]]/Length[Flatten[diffs]]];
  <|"n"->n, "seed"->seed, "error"->err|>
];
sizes = {3,4};
seeds = Range[41, 50];
metrics = Flatten[Table[runOne[n, s], {n, sizes}, {s, seeds}]];
errVec = metrics[[All, "error"]];
summary = <|"sizes"->sizes, "seeds"->seeds, "errors"->errVec, "maxError"->Max[errVec], "meanError"->Mean[errVec]|>;
Export[FileNameJoin[{base, "DispatchMetrics.json"}], summary, "JSON"];
Export[FileNameJoin[{base, "Status_dispatch.txt"}], {If[summary["maxError"]==0., "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[summary["maxError"]==0., "OK", "FAIL"], "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
