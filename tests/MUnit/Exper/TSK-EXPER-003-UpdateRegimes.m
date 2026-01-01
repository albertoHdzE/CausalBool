AppendTo[$Path, "src/Packages"];

EnsureDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "exper003"}];
EnsureDir[base];

sizes = {50, 100};
seeds = {401, 402};
params = <|
  "ER" -> <|"p" -> 0.05|>,
  "SF" -> <|"m" -> 2|>,
  "SW" -> <|"k" -> 4, "p" -> 0.05|>
|>;

largestComponent[g_] := Module[{cc = ConnectedComponents[g]}, Subgraph[g, First@MaximalBy[cc, Length]]];
inNeighbors[g_, v_] := Select[VertexList[g], EdgeQ[g, UndirectedEdge[#, v]] &];

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

orUpdate[g_, s_List, v_, posAssoc_] := Module[{nsLabels = inNeighbors[g, v], ns = posAssoc /@ nsLabels}, If[Length@ns == 0, 0, Max@s[[ns]]]];
synchronousStep[g_, s_List, posAssoc_] := Module[{vlist = VertexList[g]}, Table[orUpdate[g, s, v, posAssoc], {v, vlist}]];
asynchronousStep[g_, s_List, posAssoc_] := Module[{vlist = VertexList[g], k, v, idx},
  k = RandomInteger[{1, Length[vlist]}]; v = vlist[[k]]; idx = k;
  ReplacePart[s, idx -> orUpdate[g, s, v, posAssoc]]
];

simulate[g_, regime_, tMax_, seed_] := BlockRandom[
  Module[{lg = largestComponent[g], vlist, posAssoc, s, visited = <||>, steps = 0, t = 0, upd, key, cycleLen = 0, conv = False},
    vlist = VertexList[lg]; posAssoc = AssociationThread[vlist, Range[Length[vlist]]];
    s = RandomInteger[{0, 1}, Length[vlist]];
    upd = If[regime === "sync", synchronousStep, asynchronousStep];
    While[t < tMax,
      key = Hash[s]; If[KeyExistsQ[visited, key], cycleLen = t - visited[key]; Break[]]; visited[key] = t;
      s = upd[lg, s, posAssoc]; t++;
      If[s === synchronousStep[lg, s, posAssoc], conv = True; steps = t; Break[]];
    ];
    If[!conv, steps = tMax];
    <|"conv" -> conv, "steps" -> steps, "cycle" -> cycleLen|>
  ], RandomSeeding -> seed];

compareOne[model_, n_, seed_] := Module[{g, resSync, resAsync},
  g = Switch[model, "ER", makeER[n, seed], "SF", makeSF[n, seed], "SW", makeSW[n, seed]];
  resSync = simulate[g, "sync", 200, seed];
  resAsync = simulate[g, "async", 200, seed + 1];
  Association["model" -> model, "n" -> n, "seed" -> seed, "sync" -> resSync, "async" -> resAsync]
];

results = Flatten@Table[compareOne[m, n, s], {m, {"ER", "SF", "SW"}}, {n, sizes}, {s, seeds}];

aggVal[model_, n_, getter_] := Module[{sub = Select[results, # ["model"] === model && # ["n"] === n &]}, NumberForm[Mean[Map[getter, sub]], {5, 3}]];
rateVal[model_, n_, key_] := Module[{sub = Select[results, # ["model"] === model && # ["n"] === n &]}, NumberForm[Mean[Map[If[# [key, "conv"], 1.0, 0.0] &, sub]], {3, 2}]];

rowAgg[{model_, n_}] := StringJoin[
  model, " ", ToString@n, " & ",
  ToString@rateVal[model, n, "sync"], " & ", ToString@aggVal[model, n, Function[r, r["sync", "steps"]]], " & ", ToString@aggVal[model, n, Function[r, r["sync", "cycle"]]], " & ",
  ToString@rateVal[model, n, "async"], " & ", ToString@aggVal[model, n, Function[r, r["async", "steps"]]], " & ", ToString@aggVal[model, n, Function[r, r["async", "cycle"]]], " \\\\"
];
rowsAgg = StringRiffle[Flatten@Table[rowAgg[{model, n}], {model, {"ER", "SF", "SW"}}, {n, sizes}], "\n"];
tableAgg = StringJoin[
  "\\begin{tabular}{lcccccc}\n",
  "\\toprule\n",
  "Model~n & SyncConvRate & SyncSteps & SyncCycle & AsyncConvRate & AsyncSteps & AsyncCycle \\\\ \n",
  "\\midrule\n",
  rowsAgg, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "Summary.tex"}], tableAgg, "Text"];

Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];

Association["Status" -> "OK", "ResultsPath" -> base]
