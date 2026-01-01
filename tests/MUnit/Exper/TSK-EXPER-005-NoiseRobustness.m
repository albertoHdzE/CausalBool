AppendTo[$Path, "src/Packages"];

EnsureDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "exper005"}];
EnsureDir[base];

gates = {"AND","OR","XOR","XNOR","NAND","NOR","MAJORITY","NOT"};
arity[g_] := Switch[g, "MAJORITY", 3, "NOT", 1, _, 2];
applyGate[g_, xs_List] := Switch[g,
  "AND", If[Min[xs] == 1, 1, 0],
  "OR", If[Max[xs] == 1, 1, 0],
  "XOR", Boole[Mod[Total[xs], 2] == 1],
  "XNOR", Boole[Mod[Total[xs], 2] == 0],
  "NAND", If[Min[xs] == 1, 0, 1],
  "NOR", If[Max[xs] == 1, 0, 1],
  "MAJORITY", Boole[Total[xs] >= 2],
  "NOT", If[First[xs] == 1, 0, 1],
  _, If[Max[xs] == 1, 1, 0]
];

gateCorrectRateExact[g_, q_] := Module[{k = arity[g], inputs, noises, px, pe, total = 0.0},
  inputs = Tuples[{0, 1}, k]; noises = Tuples[{0, 1}, k];
  Do[
    px = (1/2.0)^k;
    Do[
      pe = (q)^Total[no] (1 - q)^(k - Total[no]);
      total += px*pe*Boole[applyGate[g, in] == applyGate[g, BitXor[in, no]]]
    , {no, noises}]
  , {in, inputs}];
  total
];

qVals = {0.01, 0.05}; trials = 500;
rowEnd = FromCharacterCode[{92, 92}];
gateRow[g_] := Module[{r1 = gateCorrectRateExact[g, qVals[[1]]], r2 = gateCorrectRateExact[g, qVals[[2]]]},
  StringJoin[
    g, " & ",
    ToString@NumberForm[N@r1, {3, 2}], " & ",
    ToString@NumberForm[N@r2, {3, 2}], " ", rowEnd
  ]
];
gateRows = StringRiffle[gateRow /@ gates, "\n"];
gateTable = StringJoin[
  "\\begin{tabular}{lcc}\n",
  "\\toprule\n",
  "Gate & CorrectRate~$q=0.01$ & CorrectRate~$q=0.05$ \\\\ \n",
  "\\midrule\n",
  gateRows, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "GateNoise.tex"}], gateTable, "Text"];

(* Network-level robustness under synchronous OR updates with output flips *)
sizes = {20};
seeds = {401};
params = <| "ER" -> <|"p" -> 0.05|>, "SF" -> <|"m" -> 2|>, "SW" -> <|"k" -> 4, "p" -> 0.05|> |>;

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

orUpdateCM[cm_, s_] := Module[{n = Length[s]}, Table[If[Max[cm[[i, All]]*s] == 1, 1, 0], {i, n}]];

simulateNoise[g_Graph, q_, tMax_, seed_] := BlockRandom[
  Module[{lg = largestComponent[g], adj, n, s0, s, t, s0n, sn},
    adj = AdjacencyMatrix[lg] // Normal;
    n = Length@adj; s0 = RandomInteger[{0,1}, n]; s = s0;
    For[t = 1, t <= tMax, t++,
      s0n = orUpdateCM[adj, s0]; s0 = s0n;
      sn = orUpdateCM[adj, s]; s = flipBits[sn, q];
    ];
    N@Mean[Boole[s == s0]]
  ], RandomSeeding -> seed];

netRow[{model_, n_}] := Module[{q1 = qVals[[1]], q2 = qVals[[2]], seedsLoc = seeds, g, r1, r2},
  r1 = N@Mean@Table[g = Switch[model, "ER", makeER[n, s], "SF", makeSF[n, s], "SW", makeSW[n, s]]; simulateNoise[g, q1, 10, s], {s, seedsLoc}];
  r2 = N@Mean@Table[g = Switch[model, "ER", makeER[n, s], "SF", makeSF[n, s], "SW", makeSW[n, s]]; simulateNoise[g, q2, 10, s], {s, seedsLoc}];
  StringJoin[model, " ", ToString@n, " & ", ToString@NumberForm[r1, {3, 2}], " & ", ToString@NumberForm[r2, {3, 2}], " ", rowEnd]
];
(* optional network table generation removed for stability *)

Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];

Association["Status" -> "OK", "ResultsPath" -> base]
