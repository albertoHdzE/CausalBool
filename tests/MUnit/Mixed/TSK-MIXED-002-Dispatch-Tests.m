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
