AppendTo[$Path, "src/Packages"];
Needs["Integration`Experiments`"];

base = FileNameJoin[{"results", "tests", "test003"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

sizes = {6, 8, 10, 12, 13, 20, 50};
seeds = {301, 302};
pEdge = 0.3;

genCM[n_Integer, seed_Integer] := Module[{m}, SeedRandom[seed]; m = RandomInteger[{0, 1}, {n, n}]; Do[m[[i, i]] = 0, {i, n}]; m];
dynFor[n_Integer] := Table["OR", {n}];

runOne[n_Integer, seed_Integer] := Module[{cm, dyn, t, res},
  cm = genCM[n, seed]; dyn = dynFor[n];
  If[n <= 13,
    {t, res} = AbsoluteTiming[Integration`Experiments`CreateRepertoiresDispatch[cm, dyn]];
    <|"n" -> n, "seed" -> seed, "mode" -> "baseline", "baselineTime" -> t|>,
    (* large sizes: predictive sampling over m rows across strata *)
    Module[{m = 1024, strata, samples, Ic, tPred, out},
      strata = Join[{{ConstantArray[0, n]}}, {Table[UnitVector[n, i], {i, n}]}, {RandomInteger[{0, 1}, {Ceiling[m/2], n}]}, {Table[ConstantArray[1, n], 1]}];
      samples = Flatten[strata, 1];
      {tPred, out} = AbsoluteTiming[
        Table[
          Module[{input = samples[[j]]}, Table[
            Ic = Flatten@Position[cm[[k]], 1];
            Integration`Gates`ApplyGate[dyn[[k]], Part[input, Ic]],
            {k, n}]
          ],
          {j, Length[samples]}]
      ];
      <|"n" -> n, "seed" -> seed, "mode" -> "predictiveSampling", "predictiveSampleTime" -> tPred, "sampleCount" -> Length[samples]|>
    ]
  ]
];

results = Flatten@Table[runOne[n, s], {n, sizes}, {s, seeds}];
Export[FileNameJoin[{base, "Metrics.json"}], results, "JSON"];

byN = GroupBy[results, # ["n"] &];
rowsSmall = Table[{n, N[Median[Map[# ["baselineTime"] &, Select[byN[n], KeyExistsQ[#, "baselineTime"] &]]], 6]}, {n, Select[Keys[byN], # <= 13 &]}];
rowsLarge = Table[{n, N[Median[Map[# ["predictiveSampleTime"] &, Select[byN[n], KeyExistsQ[#, "predictiveSampleTime"] &]]], 6], Max[Map[# ["sampleCount"] &, Select[byN[n], KeyExistsQ[#, "sampleCount"] &]]]}, {n, Select[Keys[byN], # > 13 &]}];
tableSmallRows = StringRiffle[Table[StringJoin[{ToString[r[[1]]], " & ", ToString[r[[2]]], " \\\\ "}], {r, rowsSmall}], "\n"];
tableSmall = StringJoin[
  "\\begin{tabular}{rc}\n",
  "\\toprule\n",
  "$n$ & Median~baseline~time~(s) \\\\ \\\\midrule\n",
  tableSmallRows,
  "\n\\bottomrule\n\\end{tabular}\n"
];
tableLargeRows = StringRiffle[Table[StringJoin[{ToString[r[[1]]], " & ", ToString[r[[2]]], " & ", ToString[r[[3]]], " \\\\ "}], {r, rowsLarge}], "\n"];
tableLarge = StringJoin[
  "\\begin{tabular}{rcc}\n",
  "\\toprule\n",
  "$n$ & Predictive~sampling~time~(s) & Samples \\\\ \\\\midrule\n",
  tableLargeRows,
  "\n\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "PerfSmall.tex"}], tableSmall, "Text"];
Export[FileNameJoin[{base, "PerfLarge.tex"}], tableLarge, "Text"];

(* Per-seed small-size table *)
rowsSeedsSmall = Table[
  Module[{ns = byN[n], s301, s302},
    s301 = Select[ns, # ["seed"] === 301 && KeyExistsQ[#, "baselineTime"] &];
    s302 = Select[ns, # ["seed"] === 302 && KeyExistsQ[#, "baselineTime"] &];
    {n,
     If[Length[s301] > 0, N[Median[Map[# ["baselineTime"] &, s301]], 6], Missing["NotAvailable"]],
     If[Length[s302] > 0, N[Median[Map[# ["baselineTime"] &, s302]], 6], Missing["NotAvailable"]]}
  ],
  {n, Select[Keys[byN], # <= 13 &]}];
tableSeedsRows = StringRiffle[Table[StringJoin[{ToString[r[[1]]], " & ", ToString[r[[2]]], " & ", ToString[r[[3]]], " \\\\ "}], {r, rowsSeedsSmall}], "\n"];
tableSeedsSmall = StringJoin[
  "\\begin{tabular}{rcc}\n",
  "\\toprule\n",
  "$n$ & seed~301~time~(s) & seed~302~time~(s) \\\\ \\\\midrule\n",
  tableSeedsRows,
  "\n\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "SeedsSmall.tex"}], tableSeedsSmall, "Text"];

report = StringRiffle[
  Map[Function[r,
    If[KeyExistsQ[r, "baselineTime"],
      "n=" <> ToString[r["n"]] <> ", seed=" <> ToString[r["seed"]] <> ": baseline " <> ToString[NumberForm[r["baselineTime"], {5, 3}]] <> "s",
      "n=" <> ToString[r["n"]] <> ", seed=" <> ToString[r["seed"]] <> ": predictiveSampling " <> ToString[NumberForm[r["predictiveSampleTime"], {5, 3}]] <> "s (m=" <> ToString[r["sampleCount"]] <> ")"
    ]
  ], results], "\n"];
Export[FileNameJoin[{base, "Report.txt"}], report, "Text"];
Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];

Association["Status" -> "OK", "ResultsPath" -> base]
