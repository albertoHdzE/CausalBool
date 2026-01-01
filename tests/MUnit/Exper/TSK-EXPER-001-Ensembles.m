AppendTo[$Path, "src/Packages"];

EnsureDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "exper001"}];
EnsureDir[base];

sizes = {50, 100, 200, 300, 500};
seeds = {401, 402};
params = <|
  "ER" -> <|"p" -> 0.05|>,
  "SF" -> <|"m" -> 2|>,
  "SW" -> <|"k" -> 4, "p" -> 0.05|>
|>;

toMatrix[g_Graph] := Module[{adj = AdjacencyMatrix[g] // Normal}, adj - DiagonalMatrix[Diagonal[adj]] // Normal];
largestComponent[g_] := Module[{cc = ConnectedComponents[g]}, Subgraph[g, First@MaximalBy[cc, Length]]];

metricsFor[g_Graph] := Module[{deg, lg, distMat, dvec, diam, adj, triangles, triples, clust, degAssoc, el, pairs, assort, btw},
  deg = VertexDegree[g];
  lg = largestComponent[g];
  distMat = GraphDistanceMatrix[lg] // Normal;
  dvec = Flatten@distMat;
  diam = GraphDiameter[lg];
  adj = AdjacencyMatrix[g];
  triangles = N[Tr[adj.adj.adj]/6.0];
  triples = N[Total[Binomial[deg, 2]]];
  clust = If[triples > 0, N[(3.0*triangles)/triples], 0.0];
  degAssoc = AssociationThread[VertexList[lg], VertexDegree[lg]];
  el = EdgeList[lg];
  pairs = Map[Function[e, {degAssoc[e[[1]]], degAssoc[e[[2]]]}], el];
  assort = If[Length[pairs] > 1, Correlation[pairs[[All, 1]], pairs[[All, 2]]], 0.0];
  btw = BetweennessCentrality[lg];
  <|
    "avgDegree" -> N@Mean[deg],
    "degVar" -> N@Variance[deg],
    "clustering" -> clust,
    "meanDistance" -> N@Mean[dvec],
    "diameter" -> diam,
    "componentCount" -> Length@ConnectedComponents[g],
    "largestComponentSize" -> VertexCount@lg,
    "assortativity" -> N@assort,
    "betweennessMean" -> N@Mean[btw],
    "betweennessSd" -> N@StandardDeviation[btw]
  |>
];

makeER[n_, seed_] := Module[{p = params["ER", "p"], m},
  m = Round[p*n*(n - 1)/2];
  BlockRandom[RandomGraph[{n, m}], RandomSeeding -> seed]
];
makeSF[n_, seed_] := BlockRandom[
  Module[{m = params["SF", "m"], m0 = Max[params["SF", "m"] + 1, 5], edges, deg, weights, choose},
    edges = Flatten[Table[{i, j}, {i, 1, m0}, {j, i + 1, m0}], 1];
    Do[
      deg = ConstantArray[0, v - 1];
      Scan[(deg[[#[[1]]]]++; deg[[#[[2]]]]++) &, edges];
      weights = If[Total[deg] > 0, deg/Total[deg], ConstantArray[1/(v - 1), v - 1]];
      choose = DeleteDuplicates@RandomChoice[weights -> Range[v - 1], m];
      edges = Join[edges, Thread[{v, choose}]],
      {v, m0 + 1, n}
    ];
    Graph[Range[n], UndirectedEdge @@@ edges]
  ],
  RandomSeeding -> seed
];

makeSW[n_, seed_] := BlockRandom[
  Module[{k = params["SW", "k"], p = params["SW", "p"], edges = {}, half, adj, newt},
    half = Floor[k/2];
    Do[Do[AppendTo[edges, {i, Mod[i + t - 1, n] + 1}], {t, 1, half}], {i, 1, n}];
    edges = Union[Sort /@ edges];
    adj = ConstantArray[False, {n, n}];
    Scan[(adj[[#[[1]], #[[2]]]] = True; adj[[#[[2]], #[[1]]]] = True) &, edges];
    edges = Table[
      Module[{a = edges[[e, 1]], b = edges[[e, 2]]},
        If[RandomReal[] < p,
          newt = RandomChoice[Complement[Range[n], {a}, Pick[Range[n], adj[[a]], True]]];
          adj[[a, b]] = False; adj[[b, a]] = False;
          adj[[a, newt]] = True; adj[[newt, a]] = True;
          {a, newt},
          {a, b}
        ]
      ],
      {e, Length@edges}
    ];
    Graph[Range[n], UndirectedEdge @@@ edges]
  ],
  RandomSeeding -> seed
];

buildOne[model_, n_, seed_] := Module[{g},
  g = Switch[model, "ER", makeER[n, seed], "SF", makeSF[n, seed], "SW", makeSW[n, seed]];
  Association["model" -> model, "n" -> n, "seed" -> seed, "metrics" -> metricsFor[g]]
];

results = Flatten@Table[buildOne[m, n, s], {m, {"ER", "SF", "SW"}}, {n, sizes}, {s, seeds}];

formatRowAssoc[a_Association] := Module[{m = a["metrics"]},
  StringJoin[
    a["model"], " ", ToString@a["n"], " (seed ", ToString@a["seed"], ") & ",
    ToString@NumberForm[m["avgDegree"], {5, 3}], " & ",
    ToString@NumberForm[m["clustering"], {5, 3}], " & ",
    ToString@NumberForm[m["meanDistance"], {5, 3}], " & ",
    ToString@m["diameter"], " \\\\"
  ]
];

rowsTex = StringRiffle[formatRowAssoc /@ results, "\n"];
tableTex = StringJoin[
  "\\begin{tabular}{lcccc}\n",
  "\\toprule\n",
  "Model~n~(seed) & AvgDegree & Clustering & MeanDist & Diameter \\\\ \n",
  "\\midrule\n",
  rowsTex, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "Summary.tex"}], tableTex, "Text"];

getVals[model_, n_, field_] := Map[# ["metrics", field] &, Select[results, # ["model"] === model && # ["n"] === n &]];
formatMedSd[vals_List] := Module[{med = N@Median[vals], sd = N@StandardDeviation[vals]}, StringJoin[ToString@NumberForm[med, {5, 3}], " (", ToString@NumberForm[sd, {4, 3}], ")"]];
rowAgg[{model_, n_}] := StringJoin[
  model, " ", ToString@n, " & ",
  formatMedSd[getVals[model, n, "avgDegree"]], " & ",
  formatMedSd[getVals[model, n, "clustering"]], " & ",
  formatMedSd[getVals[model, n, "meanDistance"]], " & ",
  formatMedSd[getVals[model, n, "diameter"]], " \\\\"
];
rowsAgg = StringRiffle[Table[rowAgg[{model, n}], {model, {"ER", "SF", "SW"}}, {n, sizes}] // Flatten, "\n"];
tableAgg = StringJoin[
  "\\begin{tabular}{lcccc}\n",
  "\\toprule\n",
  "Model~n & AvgDeg~($\\sigma$) & Clust~($\\sigma$) & MeanDist~($\\sigma$) & Diam~($\\sigma$) \\\\ \n",
  "\\midrule\n",
  rowsAgg, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "SummaryAgg.tex"}], tableAgg, "Text"];

(* Extended per-seed metrics table skipped to avoid over-wide layout; using aggregated table below *)

(* Extended aggregated metrics across seeds *)
rowAggExt[{model_, n_}] := StringJoin[
  model, " ", ToString@n, " & ",
  formatMedSd[getVals[model, n, "assortativity"]], " & ",
  formatMedSd[getVals[model, n, "betweennessMean"]], " & ",
  formatMedSd[getVals[model, n, "betweennessSd"]], " \\\\"
];
rowsAggExt = StringRiffle[Table[rowAggExt[{model, n}], {model, {"ER", "SF", "SW"}}, {n, sizes}] // Flatten, "\n"];
tableAggExt = StringJoin[
  "\\begin{tabular}{lccc}\n",
  "\\toprule\n",
  "Model~n & Assort~($\\sigma$) & BetwMean~($\\sigma$) & BetwSd~($\\sigma$) \\\\ \n",
  "\\midrule\n",
  rowsAggExt, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "SummaryAggExt.tex"}], tableAggExt, "Text"];

Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];

Association["Status" -> "OK", "ResultsPath" -> base]
