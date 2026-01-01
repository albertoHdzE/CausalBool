Get["src/Packages/Integration/Gates.m"];

base = FileNameJoin[{"results", "tests", "stoch001"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

sizes = {20, 50};
seeds = {601, 602};
qs = {0.01, 0.05};
gates = {"AND","OR","XOR","NAND","NOR","XNOR","MAJORITY","NOT"};

hammingStrata[n_Integer] := {0, 1, Floor[n/2], n - 1, n};
sampleInputsVec[n_Integer, m_Integer] := Module[{strata = hammingStrata[n], per = Max[1, Floor[m/Length[hammingStrata[n]]]], pool = {}},
  Do[
    Module[{w = ww},
      AppendTo[pool, Table[Module[{pos = If[w == 0, {}, If[w == n, Range[n], RandomSample[Range[n], w]]], v = ConstantArray[0, n]}, v[[pos]] = 1; v], {per}]]
    ], {ww, strata}];
  Flatten[pool, 1]
];

flipNoise[v_List, q_Real] := Module[{n = Length[v], mask}, mask = Boole[RandomReal[1, n] < q]; Mod[v + mask, 2]];

applyOutputs[cm_List, dyn_List, x_List] := Module[{n = Length[dyn], Ics},
  Ics = Table[Flatten@Position[cm[[k]], 1], {k, n}];
  Table[Integration`Gates`ApplyGate[dyn[[k]], x[[Ics[[k]]]], <||>], {k, n}]
];

avgByGate[dyn_List, values_List] := Module[{gatesU = Union[dyn]}, Association@Table[g -> Mean@Pick[values, dyn, g], {g, gatesU}]];

runOne[n_Integer, seed_Integer, m_Integer:1024] := Module[{cm, dyn, samples, baseOuts, qMetrics = {}, degs},
  SeedRandom[seed];
  cm = ConstantArray[0, {n, n}];
  Do[
    Module[{deg = RandomInteger[{1, Min[5, n - 1]}], choices},
      choices = RandomSample[Complement[Range[n], {i}], deg];
      cm[[i, choices]] = 1;
    ], {i, n}];
  dyn = Table[RandomChoice[gates], {n}];
  samples = sampleInputsVec[n, m];
  baseOuts = applyOutputs[cm, dyn, #] & /@ samples;
  degs = Length /@ Table[Flatten@Position[cm[[k]], 1], {k, n}];
  Do[
    Module[{q = qq, outsNoise, changeRatesNodes, changeRateNetwork, byGate},
      outsNoise = applyOutputs[cm, dyn, flipNoise[#, q]] & /@ samples;
      changeRatesNodes = Table[Mean@Table[Boole[(baseOuts[[t, k]] =!= outsNoise[[t, k]])], {t, Length[samples]}], {k, n}];
      changeRateNetwork = Mean@Table[Boole[(baseOuts[[t]] =!= outsNoise[[t]])], {t, Length[samples]}];
      byGate = avgByGate[dyn, changeRatesNodes];
      AppendTo[qMetrics, <|"q" -> q, "byGate" -> byGate, "networkChangeRate" -> changeRateNetwork|>];
    ], {qq, qs}];
  <|"n" -> n, "seed" -> seed, "qMetrics" -> qMetrics, "gates" -> dyn|>
];

metrics = Flatten[Table[runOne[n, s], {n, sizes}, {s, seeds}], 1];
Export[FileNameJoin[{base, "NoiseMetrics.json"}], metrics, "JSON"];

(* Build LaTeX table summarising network-level change rates for q=0.01 and q=0.05 *)
byN = GroupBy[metrics, # ["n"] &];
rowsPerf = StringRiffle[
  Table[
    Module[{n = nn, mlist = byN[nn], q1vals, q5vals, avg1, avg5},
      q1vals = (#["qMetrics"][[1, "networkChangeRate"]]) & /@ mlist;
      q5vals = (#["qMetrics"][[2, "networkChangeRate"]]) & /@ mlist;
      avg1 = Mean[q1vals]; avg5 = Mean[q5vals];
      StringJoin[{ToString[n], " & ", ToString@NumberForm[avg1, {3, 3}], " & ", ToString@NumberForm[avg5, {3, 3}], " \\ "}]
    ], {nn, Keys[byN]}], "\n"];

perfItems = StringRiffle[
  Table[
    Module[{n = nn, mlist = byN[nn], q1vals, q5vals, avg1, avg5},
      q1vals = (#["qMetrics"][[1, "networkChangeRate"]]) & /@ mlist;
      q5vals = (#["qMetrics"][[2, "networkChangeRate"]]) & /@ mlist;
      avg1 = Mean[q1vals]; avg5 = Mean[q5vals];
      StringJoin["\\item $n=", ToString[n], "$: $q=0.01$=", ToString@NumberForm[avg1, {3, 3}], ", $q=0.05$=", ToString@NumberForm[avg5, {3, 3}]]
    ], {nn, Keys[byN]}], "\n"];

perfTex = StringJoin[
  "\\subsection*{Noise Robustness (STOCH-001)}\n",
  "\\begin{itemize}\n",
  perfItems,
  "\n\\end{itemize}\n"
];

Export[FileNameJoin[{base, "PerfStoch.tex"}], perfTex, "Text"];
Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];

(* Build per-gate itemized summary averaging across seeds *)
gateOrder = {"AND","OR","XOR","XNOR","NAND","NOR","MAJORITY","NOT"};
byN = GroupBy[metrics, # ["n"] &];
avgGateVal[nn_, qIdx_, g_] := Module[{mlist = byN[nn], vals},
  vals = Table[Lookup[mlist[[k, "qMetrics"]][[qIdx, "byGate"]], g, 0.0], {k, Length[mlist]}];
  Mean[vals]
];
gateItems = StringRiffle[
  Table[
    Module[{g = gg, a20q1, a20q5, a50q1, a50q5},
      a20q1 = avgGateVal[20, 1, g]; a20q5 = avgGateVal[20, 2, g];
      a50q1 = avgGateVal[50, 1, g]; a50q5 = avgGateVal[50, 2, g];
      StringJoin["\\item ", g, ": $n=20$ $q=0.01$=", ToString@NumberForm[a20q1, {3, 3}], ", $q=0.05$=", ToString@NumberForm[a20q5, {3, 3}],
                 ", $n=50$ $q=0.01$=", ToString@NumberForm[a50q1, {3, 3}], ", $q=0.05$=", ToString@NumberForm[a50q5, {3, 3}]]
    ], {gg, gateOrder}], "\n"];
gateTex = StringJoin[
  "\\subsection*{Per-Gate Noise Sensitivity (STOCH-001)}\n",
  "\\begin{itemize}\n",
  gateItems,
  "\n\\end{itemize}\n"
];
Export[FileNameJoin[{base, "GateStoch.tex"}], gateTex, "Text"];

(* Compact per-gate tabular *)
gateRowsTab = StringRiffle[
  Table[
    Module[{g = gg, a20q1, a20q5, a50q1, a50q5},
      a20q1 = N@avgGateVal[20, 1, g]; a20q5 = N@avgGateVal[20, 2, g];
      a50q1 = N@avgGateVal[50, 1, g]; a50q5 = N@avgGateVal[50, 2, g];
      StringJoin[{g, " & ", ToString@NumberForm[a20q1, {2, 3}], " & ", ToString@NumberForm[a20q5, {2, 3}], " & ", ToString@NumberForm[a50q1, {2, 3}], " & ", ToString@NumberForm[a50q5, {2, 3}], " \\ "}]
    ], {gg, gateOrder}], "\n"];
gateTabTex = StringJoin[
  "\\subsection*{Per-Gate Noise Sensitivity (STOCH-001) — Tabular}\n",
  "\\begin{tabular}{lcccc}\n",
  "\\toprule\n",
  "Gate & n=20,q=0.01 & n=20,q=0.05 & n=50,q=0.01 & n=50,q=0.05 \\ \n",
  gateRowsTab,
  "\\bottomrule\n",
  "\\end{tabular}\n"
];
Export[FileNameJoin[{base, "GateStochTable.tex"}], gateTabTex, "Text"];
