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

(* AUDIT03 — delegated to the single owner, Integration`BioMetrics`.

   THIS COPY WAS THE DRIFTED ONE. It had no KOFN and no CANALISING branch, so
   both fell through to the "1 + d" default, and it took the in-degree instead
   of the connected-input list, so it could not see parameters at all. Measured
   in the kernel over the twelve families at d = 1..6: 20 of 72 cells disagreed
   with the four other copies -- IMPLIES and NIMPLIES at every d except 2, KOFN
   and CANALISING at every d except 1.

   ITS NUMBERS THEREFORE MOVE, and that is the intended correction rather than
   a regression. Nothing downstream notices today, for a reason worth recording:
   this file is one of 23 under tests/MUnit that the runner NEVER EXECUTES --
   run-tests.sh globs "*Tests.m" and this name does not match. It also exports
   Status "OK" unconditionally, so it could not have failed in any case. Both
   are recorded in BASELINE.md as separate open items. *)
Get["src/Packages/Integration/BioMetrics.m"];
compressionWeight[gate_, d_Integer] :=
  Integration`BioMetrics`FormulaComponentWeight[gate, Range[d], <||>];
computeCompression[cm_List, dyn_List] :=
  Integration`BioMetrics`ComputeFormulaComponents[cm, dyn, <||>];

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
