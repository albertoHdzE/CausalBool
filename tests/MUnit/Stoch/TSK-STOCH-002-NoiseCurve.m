Get["src/Packages/Integration/Gates.m"];

base = FileNameJoin[{"results", "tests", "stoch002"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

sizes = {20, 50};
seeds = {701, 702};
qGrid = N[Range[0, 10]/100.0];
gates = {"AND","OR","XOR","XNOR","NAND","NOR","MAJORITY","NOT"};

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

degVec[cm_List] := Length /@ Table[Flatten@Position[cm[[k]], 1], {k, Length[cm]}];

(* Analytic XOR flip probability under independent bit-flips with prob q: P(odd flips) = (1 - (1-2 q)^k)/2 *)
xorAnalytic[q_, k_Integer] := (1 - (1 - 2 q)^k)/2.0;

runOne[n_Integer, seed_Integer, m_Integer:1024] := Module[{cm, dyn, dvec, samples, curves = {}},
  SeedRandom[seed];
  cm = ConstantArray[0, {n, n}];
  Do[
    Module[{deg = RandomInteger[{1, Min[5, n - 1]}], choices},
      choices = RandomSample[Complement[Range[n], {i}], deg];
      cm[[i, choices]] = 1;
    ], {i, n}];
  dyn = Table[RandomChoice[gates], {n}];
  dvec = degVec[cm];
  samples = sampleInputsVec[n, m];
  With[{baseOuts = applyOutputs[cm, dyn, #] & /@ samples},
    Do[
      Module[{q = qq, outsNoise, networkChange, xorIdx, empXor, anaXor},
        outsNoise = applyOutputs[cm, dyn, flipNoise[#, q]] & /@ samples;
        networkChange = Mean@Table[Boole[(baseOuts[[t]] =!= outsNoise[[t]])], {t, Length[samples]}];
        xorIdx = Flatten@Position[dyn, "XOR"];
        empXor = If[Length[xorIdx] == 0, Null,
          Mean@Table[Mean@Table[Boole[(baseOuts[[t, i]] =!= outsNoise[[t, i]])], {t, Length[samples]}], {i, xorIdx}]
        ];
        anaXor = If[Length[xorIdx] == 0, Null,
          Mean@Table[xorAnalytic[q, dvec[[i]]], {i, xorIdx}]
        ];
        AppendTo[curves, <|"q" -> q, "networkChange" -> networkChange, "empXor" -> empXor, "anaXor" -> anaXor|>];
      ], {qq, qGrid}]
  ];
  <|"n" -> n, "seed" -> seed, "curves" -> curves|>
];

metrics = Flatten[Table[runOne[n, s], {n, sizes}, {s, seeds}], 1];
Export[FileNameJoin[{base, "NoiseCurves.json"}], metrics, "JSON"];

(* Build LaTeX tables: network curve summary and XOR analytic vs empirical *)
byN = GroupBy[metrics, # ["n"] &];
qList = qGrid;
netRows = StringRiffle[
  Table[
    Module[{q = qList[[j]], v20, v50},
      v20 = Mean[(#["curves"][[j, "networkChange"]]) & /@ byN[20]];
      v50 = Mean[(#["curves"][[j, "networkChange"]]) & /@ byN[50]];
      StringJoin[{ToString@NumberForm[q, {2, 2}], " & ", ToString@NumberForm[v20, {2, 3}], " & ", ToString@NumberForm[v50, {2, 3}], " \\\\ "}]
    ], {j, Length[qList]}], "\n"];
netTex = StringJoin[
  "\\subsection*{Noise Curves (STOCH-002) — Network}\n",
  "\\begin{tabular}{rcc}\n",
  "\\toprule\n",
  "$q$ & $n=20$ & $n=50$ \\\\ \n",
  "\\midrule\n",
  netRows,
  "\n\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "NoiseCurvesNet.tex"}], netTex, "Text"];

xorRows = StringRiffle[
  Table[
    Module[{q = qList[[j]], emp, ana, err},
      emp = Mean[DeleteCases[(#["curves"][[j, "empXor"]]) & /@ metrics, Null]];
      ana = Mean[DeleteCases[(#["curves"][[j, "anaXor"]]) & /@ metrics, Null]];
      err = If[emp === Null || ana === Null, 0.0, Abs[emp - ana]];
      StringJoin[{ToString@NumberForm[q, {2, 2}], " & ", ToString@NumberForm[ana, {2, 3}], " & ", ToString@NumberForm[emp, {2, 3}], " & ", ToString@NumberForm[err, {2, 3}], " \\\\ "}]
    ], {j, Length[qList]}], "\n"];
xorTex = StringJoin[
  "\\subsection*{Noise Curves (STOCH-002) — XOR Analytic vs Empirical}\n",
  "\\begin{tabular}{rccc}\n",
  "\\toprule\n",
  "$q$ & analytic & empirical & $|\\Delta|$ \\\\ \n",
  "\\midrule\n",
  xorRows,
  "\n\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "NoiseCurvesXOR.tex"}], xorTex, "Text"];
Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];
