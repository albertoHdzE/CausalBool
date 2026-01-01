Get["src/Packages/Integration/Gates.m"];

base = FileNameJoin[{"results", "tests", "algo002"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

sizes = {20, 50};
seeds = {301, 302};
gates = {"AND","OR","XOR","NAND","NOR","XNOR","MAJORITY"};

hammingStrata[n_Integer] := {0, 1, Floor[n/2], n - 1, n};
sampleInputsVec[n_Integer, m_Integer] := Module[{strata = hammingStrata[n], per = Max[1, Floor[m/Length[hammingStrata[n]]]], pool = {}},
  Do[
    Module[{w = ww},
      AppendTo[pool, Table[Module[{pos = If[w == 0, {}, If[w == n, Range[n], RandomSample[Range[n], w]]], v = ConstantArray[0, n]}, v[[pos]] = 1; v], {per}]]
    ], {ww, strata}];
  Flatten[pool, 1]
];

truthOutput[gate_, Ic_List, x_List] := Module[{d = Length[Ic], tt, idx}, tt = Integration`Gates`TruthTable[gate, d, <||>]; idx = FromDigits[x[[Ic]], 2] + 1; tt[[idx, 2]]];
applyOutput[gate_, Ic_List, x_List] := Integration`Gates`ApplyGate[gate, x[[Ic]], <||>];

runOne[n_Integer, seed_Integer, m_Integer:512] := Module[{cm, dyn, rows = 0, ok = 0, samples, tApply = 0., tTruth = 0.},
  SeedRandom[seed];
  cm = ConstantArray[0, {n, n}];
  Do[
    Module[{deg = RandomInteger[{1, Min[5, n - 1]}], choices},
      choices = RandomSample[Complement[Range[n], {i}], deg];
      cm[[i, choices]] = 1;
    ], {i, n}
  ];
  dyn = Table[RandomChoice[gates], {n}];
  samples = sampleInputsVec[n, m];
  Do[
    Module[{x = samples[[t]], Ics = Table[Flatten@Position[cm[[k]], 1], {k, n}], y1, y2, ta, tt},
      {ta, y1} = AbsoluteTiming[Table[applyOutput[dyn[[k]], Ics[[k]], x], {k, n}]];
      {tt, y2} = AbsoluteTiming[Table[truthOutput[dyn[[k]], Ics[[k]], x], {k, n}]];
      tApply += ta; tTruth += tt;
      ok += Boole[y1 === y2]; rows += 1;
    ], {t, Length[samples]}
  ];
  <|"n"->n, "seed"->seed, "samples"->rows, "rowsEqual"->ok, "accuracy"->N[ok/rows], "timeApply"->N[tApply,6], "timeTruth"->N[tTruth,6]|>
];

metrics = Flatten[Table[runOne[n, s, 1024], {n, sizes}, {s, seeds}], 1];
Export[FileNameJoin[{base, "Importance.json"}], metrics, "JSON"];
Export[FileNameJoin[{base, "Status_importance.txt"}], If[AllTrue[metrics[[All, "accuracy"]], (# == 1.0) &], "OK", "FAIL"], "Text"];

(* Build LaTeX performance table for sampling runs *)
perfRows = Table[
  Module[{n = mm["n"], sa = mm["samples"], ta = mm["timeApply"], tt = mm["timeTruth"]},
    StringJoin[{ToString[n], " & ", ToString[sa], " & ", ToString[ta], " & ", ToString[tt], " \\"}]
  ], {mm, metrics}];
perfTex = StringJoin[
  "\\subsection*{Sampling Performance (ALGO-002)}\n",
  "\\begin{tabular}{rccc}\n",
  "\\toprule\n",
  "$n$ & samples & Predictive~time~(s) & TruthTable~time~(s) \\ \\midrule\n",
  StringRiffle[perfRows, "\n"],
  "\n\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "Perf.tex"}], perfTex, "Text"];
