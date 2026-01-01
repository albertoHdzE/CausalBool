AppendTo[$Path, "src/Packages"];

EnsureDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "exper004"}];
EnsureDir[base];

sizes = {50, 100, 200};
seeds = {401, 402, 403};
params = <|
  "ER" -> <|"p" -> 0.05|>,
  "SF" -> <|"m" -> 2|>,
  "SW" -> <|"k" -> 4, "p" -> 0.05|>
|>;

largestComponent[g_] := Module[{cc = ConnectedComponents[g]}, Subgraph[g, First@MaximalBy[cc, Length]]];

makeER[n_, seed_] := Module[{p = params["ER", "p"], m}, m = Round[p*n*(n - 1)/2]; BlockRandom[RandomGraph[{n, m}], RandomSeeding -> seed]];
makeSF[n_, seed_] := BlockRandom[
  Module[{m = params["SF", "m"], m0 = Max[params["SF", "m"] + 1, 5], edges, deg, weights, choose},
    edges = Flatten[Table[{i, j}, {i, 1, m0}, {j, i + 1, m0}], 1];
    Do[
      deg = ConstantArray[0, v - 1]; Scan[(deg[[#[[1]]]]++; deg[[#[[2]]]]++) &, edges];
      weights = If[Total[deg] > 0, deg/Total[deg], ConstantArray[1/(v - 1), v - 1]];
      choose = DeleteDuplicates@RandomChoice[weights -> Range[v - 1], m];
      edges = Join[edges, Thread[{v, choose}]], {v, m0 + 1, n}];
    Graph[Range[n], UndirectedEdge @@@ edges]
  ], RandomSeeding -> seed];
makeSW[n_, seed_] := BlockRandom[
  Module[{k = params["SW", "k"], p = params["SW", "p"], edges = {}, half, adj, newt},
    half = Floor[k/2];
    Do[Do[AppendTo[edges, {i, Mod[i + t - 1, n] + 1}], {t, 1, half}], {i, 1, n}];
    edges = Union[Sort /@ edges]; adj = ConstantArray[False, {n, n}];
    Scan[(adj[[#[[1]], #[[2]]]] = True; adj[[#[[2]], #[[1]]]] = True) &, edges];
    edges = Table[Module[{a = edges[[e, 1]], b = edges[[e, 2]]}, If[RandomReal[] < p,
        newt = RandomChoice[Complement[Range[n], {a}, Pick[Range[n], adj[[a]], True]]];
        adj[[a, b]] = False; adj[[b, a]] = False; adj[[a, newt]] = True; adj[[newt, a]] = True; {a, newt}, {a, b}]], {e, Length@edges}];
    Graph[Range[n], UndirectedEdge @@@ edges]
  ], RandomSeeding -> seed];

compressionWeight[gate_, d_Integer] := Switch[gate,
  "AND" | "OR" | "NAND" | "NOR", 1 + d,
  "XOR" | "XNOR" | "MAJORITY", 1 + 1,
  "NOT", 1,
  _, 1 + d
];
computeCompression[cm_List, dyn_List] := Module[{n = Length[dyn], ics}, ics = Table[Flatten@Position[cm[[i]], 1], {i, n}]; Total@Table[compressionWeight[dyn[[i]], Length[ics[[i]]]], {i, n}]];

proposeBlocks[cm_List] := Module[{n = Length[cm], adjU, visited = ConstantArray[False, Length[cm]], blocks = {}},
  adjU = Unitize[cm + Transpose[cm]]; Do[adjU[[i, i]] = 0, {i, n}];
  Do[
    If[!visited[[i]], Module[{queue = {i}, block = {}}, visited[[i]] = True; While[queue =!= {}, Module[{u = First[queue]}, queue = Rest[queue]; AppendTo[block, u]; Do[If[adjU[[u, v]] == 1 && !visited[[v]], visited[[v]] = True; queue = Append[queue, v]], {v, n}]]]; AppendTo[blocks, Sort@block]]],
    {i, n}
  ];
  blocks
];

gates = {"AND","OR","XOR","NAND","NOR","XNOR","MAJORITY","NOT"};

metricsFor[g_Graph, seed_Integer] := Module[{lg, adj, cm, n, dyn, blocks, cWhole, cSumBlocks, totalEdges, cutEdges, cutFrac},
  lg = largestComponent[g]; adj = AdjacencyMatrix[lg] // Normal; cm = adj; n = Length@cm;
  SeedRandom[seed]; dyn = Table[RandomChoice[gates], {n}];
  blocks = proposeBlocks[cm];
  cWhole = computeCompression[cm, dyn];
  cSumBlocks = Total@Table[computeCompression[cm[[blk, blk]], dyn[[blk]]], {blk, blocks}];
  totalEdges = Total[Flatten[cm]]; cutEdges = Total[Flatten@Table[Total[cm[[i, Complement[Range[n], blk]]]], {blk, blocks}, {i, blk}]];
  cutFrac = If[totalEdges == 0, 0.0, N[cutEdges/totalEdges]];
  Association[
    "blockCount" -> Length@blocks,
    "meanBlockSize" -> If[Length@blocks == 0, 0, N@Mean[Length /@ blocks]],
    "cutFrac" -> N@cutFrac,
    "okFactorise" -> TrueQ[(cutFrac == 0.0) && (cWhole == cSumBlocks)]
  ]
];

buildOne[model_, n_, seed_] := Module[{g}, g = Switch[model, "ER", makeER[n, seed], "SF", makeSF[n, seed], "SW", makeSW[n, seed]]; Association["model" -> model, "n" -> n, "seed" -> seed, "metrics" -> metricsFor[g, seed]]];

results = Flatten@Table[buildOne[m, n, s], {m, {"ER", "SF", "SW"}}, {n, sizes}, {s, seeds}];

getVals[model_, n_, field_] := Map[# ["metrics", field] &, Select[results, # ["model"] === model && # ["n"] === n &]];
formatMedSd[vals_List] := Module[{med = N@Median[vals], sd = N@StandardDeviation[vals]}, StringJoin[ToString@NumberForm[med, {5, 3}], " (", ToString@NumberForm[sd, {4, 3}], ")"]];
rowEnd = FromCharacterCode[{92, 92}];
rowAgg[{model_, n_}] := StringJoin[
  model, " ", ToString@n, " & ",
  formatMedSd[getVals[model, n, "blockCount"]], " & ",
  formatMedSd[getVals[model, n, "meanBlockSize"]], " & ",
  formatMedSd[getVals[model, n, "cutFrac"]], " & ",
  ToString@NumberForm[Mean[Map[If[#, 1.0, 0.0] &, getVals[model, n, "okFactorise"]]], {3, 2}], " ", rowEnd];
rowsAgg = StringRiffle[Flatten@Table[rowAgg[{model, n}], {model, {"ER", "SF", "SW"}}, {n, sizes}], "\n"];
tableAgg = StringJoin[
  "\\begin{tabular}{lcccc}\n",
  "\\toprule\n",
  "Model~n & Blocks~($\\sigma$) & MeanBlk~($\\sigma$) & CutFrac~($\\sigma$) & FactoriseRate \\\\ \n",
  "\\midrule\n",
  rowsAgg, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "Summary.tex"}], tableAgg, "Text"];

Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];

Association["Status" -> "OK", "ResultsPath" -> base]
