Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results", "tests", "theory004"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

canonicalNode[cm_List, dyn_List, params_Association:<||>, i_Integer] := Module[{Ic}, Ic = Flatten@Position[cm[[i]], 1]; <|"gate" -> dyn[[i]], "inputs" -> Ic, "params" -> Lookup[params, i, <||>]|>];
canonicalNetwork[cm_List, dyn_List, params_Association:<||>] := Table[canonicalNode[cm, dyn, params, i], {i, Length[dyn]}];

outputsFromCanonical[canon_List, n_Integer] := Module[{cm, dyn, params, ics, inputs},
  dyn = canon[[All, "gate"]]; ics = canon[[All, "inputs"]]; params = Association@Table[i -> Lookup[canon[[i]], "params", <||>], {i, Length[canon]}];
  inputs = IntegerDigits[Range[0, 2^n - 1], 2, n];
  Table[Integration`Gates`ApplyGate[dyn[[i]], inputs[[j, ics[[i]]]], Lookup[params, i, <||>]], {j, Length[inputs]}, {i, Length[dyn]}]
];

gateLabels = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN","CANALISING"};
log2Int[x_] := N@Log[2, x];
encodeCostBits[cm_List, dyn_List, params_Association:<||>] := Module[{n = Length[dyn], ics, K = Length[gateLabels]},
  ics = Table[Flatten@Position[cm[[i]], 1], {i, n}];
  Total@Table[Module[{d = Length[ics[[i]]], g = dyn[[i]], p = Lookup[params, i, <||>], cost = 0.0}, cost += log2Int[K]; cost += log2Int[Max[1, Binomial[n, d]]]; Switch[g, "KOFN", cost += log2Int[d + 1] + 1, "CANALISING", cost += log2Int[n] + 1 + 1, "IMPLIES" | "NIMPLIES", cost += log2Int[Max[1, d (d - 1)]], "NOT", cost += log2Int[Max[1, d]], "MAJORITY", cost += 1, "XOR" | "XNOR", cost += 1, _, cost += 1]; cost], {i, n}]
];

cm = {{0,1,0,0},{1,0,1,0},{0,1,0,1},{0,0,1,0}};
dyn = {"AND","OR","XOR","KOFN"};
params = <|4 -> <|"k" -> 2|>|>;

canon = canonicalNetwork[cm, dyn, params];
resCanonical = outputsFromCanonical[canon, Length[dyn]];
resBaseline = Table[Integration`Gates`ApplyGate[dyn[[i]], IntegerDigits[j - 1, 2, Length[dyn]][[Flatten@Position[cm[[i]], 1]]], Lookup[params, i, <||>]], {j, 2^Length[dyn]}, {i, Length[dyn]}];
eq = Developer`ToPackedArray@Boole[MapThread[Equal, {resBaseline, resCanonical}, 2]];
acc = N[Total[Flatten[eq]]/Length[Flatten[eq]]];

Dbits = encodeCostBits[cm, dyn, params];
naiveOnes = Total@Table[Length@Flatten@Position[resBaseline[[All, i]], 1, 1], {i, Length[dyn]}];
okMinimal = Dbits < 8*naiveOnes;

perm = {2,3,4,1};
cmP = cm[[perm, perm]]; dynP = dyn[[perm]]; paramsP = Association@Table[i -> Lookup[params, perm[[i]], <||>], {i, Length[dyn]}];
canonP = canonicalNetwork[cmP, dynP, paramsP];
resCanonP = outputsFromCanonical[canonP, Length[dyn]];
resBaselineP = Table[Integration`Gates`ApplyGate[dynP[[i]], IntegerDigits[j - 1, 2, Length[dynP]][[Flatten@Position[cmP[[i]], 1]]], Lookup[paramsP, i, <||>]], {j, 2^Length[dynP]}, {i, Length[dynP]}];
okInvariant = N[Total[Flatten@Boole@MapThread[Equal, {resCanonP, resBaselineP}, 2]]/Length[Flatten@resBaselineP]] == 1.0;

metrics = <|"acc"->N@acc, "Dbits"->N@Dbits, "naiveOnes"->naiveOnes, "okMinimal"->TrueQ[okMinimal], "okInvariant"->TrueQ[okInvariant]|>;
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
status = If[And[acc == 1.0, okMinimal, okInvariant], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status"->status, "ResultsPath"->base]
