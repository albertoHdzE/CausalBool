Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];

base = FileNameJoin[{"results", "tests", "algo001"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

sizes = {10, 13};
seeds = {101, 102};
gates = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN"};

runOne[n_Integer, seed_Integer] := Module[{cm, dyn, params = <||>, res, inputs, baseline, tBase, memBase, pred, tPred, memPred, acc},
  SeedRandom[seed];
  cm = Table[If[i == j, 0, RandomInteger[{0, 1}]], {i, 1, n}, {j, 1, n}];
  dyn = Table[RandomChoice[gates], {n}];
  memBase = MemoryInUse[];
  {tBase, res} = AbsoluteTiming[Integration`Experiments`CreateRepertoiresDispatch[cm, dyn, params]];
  inputs = res["RepertoireInputs"]; baseline = res["RepertoireOutputs"];
  memBase = MemoryInUse[] - memBase;
  memPred = MemoryInUse[];
  {tPred, pred} = AbsoluteTiming[Table[
      Integration`Gates`ApplyGate[dyn[[k]], inputs[[j, Flatten@Position[cm[[k]], 1]]], Lookup[params, k, <||>]],
      {j, Length[inputs]}, {k, n}
    ]];
  memPred = MemoryInUse[] - memPred;
  acc = N[Total[Flatten@Boole@MapThread[Equal, {baseline, pred}, 2]]/Length[Flatten@baseline]];
  <|"n" -> n, "seed" -> seed, "accuracy" -> acc, "baselineTime" -> tBase, "predictiveTime" -> tPred, "baselineMem" -> memBase, "predictiveMem" -> memPred|>
];

metrics = Flatten[Table[runOne[n, s], {n, sizes}, {s, seeds}], 1];
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
statusOK = AllTrue[metrics[[All, "accuracy"]], (# == 1.0) &];
Export[FileNameJoin[{base, "Status.txt"}], If[TrueQ[statusOK], "OK", "FAIL"], "Text"];

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
