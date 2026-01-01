Get["experiments/topologies/Topologies.m"];
AppendTo[$Path, "src/Packages"];
Needs["Integration`Experiments`"];
base = FileNameJoin[{"results", "exper", "topologies"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
logFile = FileNameJoin[{base, "RunLog.txt"}];
stream = OpenWrite[logFile];
log[s_String] := (WriteString[$Output, s <> "\n"]; WriteString[stream, s <> "\n"]);
gates = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN"};
pairs = Cases[Rest@$CommandLine, s_String :> StringSplit[s, "=", 2]];
opts = Association@Cases[pairs, {k_, v_} :> Rule[k, v]];
mode = Lookup[opts, "mode", "smoke"];
conf = Which[
  mode === "smoke", <|"sizes" -> {6}, "seeds" -> {101}, "timeLimit" -> 120, "topos" -> {"ER"}|>,
  mode === "medium", <|"sizes" -> {8}, "seeds" -> Range[301, 303], "timeLimit" -> 240, "topos" -> {"ER","BA","WS"}|>,
  True, <|"sizes" -> {10}, "seeds" -> Range[401, 404], "timeLimit" -> 600, "topos" -> {"ER","BA","WS"}|>
];
progressBar[prog_Integer, total_Integer, width_Integer:30] := Module[{ratio, filled, empty}, ratio = N[prog/total]; filled = Floor[ratio*width]; empty = width - filled; "[" <> StringRepeat["#", filled] <> StringRepeat[".", empty] <> "]"]];
validateOnce[gen_, args_List, seed_] := Module[{top, cm, dyn, params, rep, run, diffs, err, indeg, n, steps},
  top = gen @@ Append[args, seed]; cm = top["cm"]; n = Length[cm]; steps = n*2^n;
  log["Test type=" <> mode <> " | topo=" <> top["meta"]["type"] <> " | n=" <> ToString[n] <> " | est steps=" <> ToString[steps]];
  dyn = Table[RandomChoice[gates], {n}];
  params = Association@Table[i -> If[dyn[[i]]=="KOFN", (indeg = Count[cm[[i]], 1]; <|"k"->RandomInteger[{1, Max[1, indeg]}]|>), <||>], {i,1,n}];
  TimeConstrained[
    rep = Integration`Experiments`CreateRepertoiresDispatch[cm, dyn, params]["RepertoireOutputs"];
    run = Integration`Experiments`RunDynamicDispatch[cm, dyn, params]["RepertoireOutputs"];
    diffs = MapThread[Boole[#1 != #2] &, {rep, run}];
    err = N[Total[Flatten[diffs]]/Length[Flatten[diffs]]];,
    conf["timeLimit"],
    err = Indeterminate
  ];
  <|"type"->top["meta"]["type"], "args"->args, "seed"->seed, "error"->err|>
];
sizes = conf["sizes"];
seeds = conf["seeds"];
totalRuns = Length[sizes]*Length[seeds]*3;
runsPerSize = If[MemberQ[conf["topos"], "ER"] && !MemberQ[conf["topos"], "BA"] && !MemberQ[conf["topos"], "WS"], 1, 3];
totalRuns = Length[sizes]*Length[seeds]*runsPerSize;
log["Planned runs=" <> ToString[totalRuns] <> " | mode=" <> mode <> " | limit=" <> ToString[conf["timeLimit"]] <> "s"];
runs = {};
progress = 0;
startTime = AbsoluteTime[];
Do[
  If[MemberQ[conf["topos"], "ER"], AppendTo[runs, validateOnce[ERConnectivity, {sizes[[i]], 0.2}, s]]];
  If[MemberQ[conf["topos"], "BA"], AppendTo[runs, validateOnce[BAConnectivity, {sizes[[i]], 2}, s]]];
  If[MemberQ[conf["topos"], "WS"], AppendTo[runs, validateOnce[WSConnectivity, {sizes[[i]], 4, 0.2}, s]]];
  progress++;
  elapsed = AbsoluteTime[] - startTime;
  eta = If[progress>0, elapsed* (totalRuns - progress)/progress, Indeterminate];
  log[progressBar[progress, totalRuns] <> " " <> ToString[Round[100.0*progress/totalRuns, 0.1]] <> "% | run=" <> ToString[progress] <> "/" <> ToString[totalRuns] <> " | elapsed=" <> ToString[Round[elapsed, 0.1]] <> "s | ETA=" <> ToString[If[NumberQ[eta], Round[eta, 0.1], "-"]] <> "s"];
, {i, 1, Length[sizes]}, {s, seeds}];
Export[FileNameJoin[{base, "TopologiesMixedDispatchMetrics.json"}], runs, "JSON"];
errs = DeleteCases[runs[[All, "error"]], Indeterminate];
maxErr = If[Length[errs] > 0, Max[errs], Indeterminate];
status = If[maxErr === 0., "OK", If[maxErr === Indeterminate, "TIMEOUT", "FAIL"]];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Close[stream];
Association["Status" -> status, "ResultsPath" -> base]