Get["src/Packages/Integration/Gates.m"];

base1 = FileNameJoin[{"results","tests","algo001"}];
perfOut = FileNameJoin[{base1, "Performance.tex"}];
If[!DirectoryQ[base1], CreateDirectory[base1, CreateIntermediateDirectories -> True]];

metrics1 = Import[FileNameJoin[{base1, "Metrics.json"}], "JSON"];
timesByN = GroupBy[metrics1, # ["n"] &];
rows = Table[{n, N[Median[Map[# ["baselineTime"] &, timesByN[n]]], 6], N[Median[Map[# ["predictiveTime"] &, timesByN[n]]], 6]}, {n, Keys[timesByN]}];
maxTime = Max[rows[[All, 2 ;; 3]]];
scale[t_] := 5.0 (t/maxTime);

(* Build LaTeX table *)
tableRows = StringRiffle[
  Table[
    StringJoin[{ToString[r[[1]]], " & ", ToString[r[[2]]], " & ", ToString[r[[3]]], " \\ "}],
    {r, rows}
  ], "\n"
];
table = StringJoin[
 "\\begin{tabular}{rcc}\n",
 "\\toprule\n",
 "$n$ & Baseline~time~(s) & Predictive~time~(s) \\\\ \\midrule\n",
 tableRows,
 "\n\\bottomrule\n\\end{tabular}\n"
];

(* Build LaTeX timing plot with TikZ bars *)
bars = StringRiffle[
 Table[
   Module[{n = rows[[k, 1]], b = scale[rows[[k, 2]]], p = scale[rows[[k, 3]]], y = 1.5 k},
     StringJoin[
       "\\draw[fill=blue!40] (0,", ToString[y], ") rectangle (", ToString[b], ",", ToString[y+0.5], "); % baseline\n",
       "\\draw[fill=green!40] (0,", ToString[y+0.6], ") rectangle (", ToString[p], ",", ToString[y+1.1], "); % predictive\n",
       "\\node[anchor=west] at (", ToString[Max[b,p]+0.1], ",", ToString[y+0.25], ") {$n=", ToString[n], "}$;\n"
     ]
   ],
   {k, Length[rows]}
 ], "\n"];

plot = StringJoin[
 "\\begin{tikzpicture}[x=1cm,y=1cm]\n",
 bars,
 "\\end{tikzpicture}\n"
];

tex = StringJoin[
 "\\subsection*{Performance Summary (ALGO-001)}\n",
 table,
 "\\medskip\n",
 plot
];

Export[perfOut, tex, "Text"];
