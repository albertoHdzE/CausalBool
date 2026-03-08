BeginPackage["Integration`BioExperiments`"]
RandomizeNetworkDegreePreserving::usage = "RandomizeNetworkDegreePreserving[cm, nSwaps] returns a degree-preserving randomized copy of cm";
RandomizeGateAssignments::usage = "RandomizeGateAssignments[dynamic] shuffles gate assignments while preserving counts";
VerifyRandomization::usage = "VerifyRandomization[cmBio, cmRand, dynBio, dynRand] returns checks for degree and gate-preservation";
KnockoutNetworkByIndex::usage = "KnockoutNetworkByIndex[net, i] returns network with node i removed";
ComputeKnockoutDeltas::usage = "ComputeKnockoutDeltas[net] returns per-node \[CapitalDelta]D criticality values";
ComputeAttractors::usage = "ComputeAttractors[net] returns the list of attractors (cycles) for the synchronous STG";
LoadEssentialityData::usage = "LoadEssentialityData[path] returns nested association Network -> Gene -> Essentiality(0/1)";
CompareCriticalityToEssentiality::usage = "CompareCriticalityToEssentiality[crit, ess] returns a dataset of predictions vs ground truth";
ComputeKnockoutBehaviorDeltas::usage = "ComputeKnockoutBehaviorDeltas[net] returns per-node attractor-based behavioural deltas";

Begin["`Private`"]

Needs["Integration`BioMetrics`"];
Needs["Integration`Gates`"];

LoadEssentialityData[path_String] := Module[{data, assoc},
  If[!FileExistsQ[path], Return[$Failed]];
  data = Import[path, "CSV", HeaderLines -> 1];
  assoc = GroupBy[data, #[[2]]&, 
    Function[rows, 
      Association[#[[1]] -> ToExpression[#[[3]]]& /@ rows]
    ]
  ];
  assoc
];

CompareCriticalityToEssentiality[crit_Association, ess_Association] := Module[
  {nodes, commonNodes, vals, labels, thrCandidates, allThr, bestThr, bestAcc, preds, acc, result},
  nodes = Keys[crit];
  commonNodes = Intersection[nodes, Keys[ess]];
  If[Length[commonNodes] == 0, Return[{}]];
  vals = crit /@ commonNodes;
  labels = ess /@ commonNodes;
  thrCandidates = DeleteDuplicates[vals];
  allThr = Join[thrCandidates, {Min[vals] - 1, Max[vals] + 1}];
  bestThr = First[allThr];
  bestAcc = -Infinity;
  Do[
    preds = Boole[vals > thr];
    acc = Mean[Boole[preds == labels]];
    If[acc > bestAcc,
      bestAcc = acc;
      bestThr = thr
    ],
    {thr, allThr}
  ];
  result = Table[
    <|
      "Gene" -> node,
      "DeltaD" -> crit[node],
      "Essentiality" -> ess[node],
      "Prediction" -> If[crit[node] > bestThr, 1, 0],
      "Threshold" -> bestThr
    |>,
    {node, commonNodes}
  ];
  result
];

CompareCriticalityToEssentiality[crit_Association, ess_Association, beh_Association] := Module[
  {nodes, commonNodes, valsD, valsB, labels, normD, normB, scores, thrCandidates, allThr, bestThr, bestAcc, preds, acc, result},
  nodes = Intersection[Keys[crit], Keys[ess], Keys[beh]];
  commonNodes = nodes;
  If[Length[commonNodes] == 0, Return[{}]];
  valsD = crit /@ commonNodes;
  valsB = beh /@ commonNodes;
  labels = ess /@ commonNodes;
  normD = If[Max[valsD] == Min[valsD], ConstantArray[0., Length[valsD]], N[(valsD - Min[valsD])/(Max[valsD] - Min[valsD])]];
  normB = If[Max[valsB] == Min[valsB], ConstantArray[0., Length[valsB]], N[(valsB - Min[valsB])/(Max[valsB] - Min[valsB])]];
  scores = 0.5 normD + 0.5 normB;
  thrCandidates = DeleteDuplicates[scores];
  allThr = Join[thrCandidates, {Min[scores] - 1, Max[scores] + 1}];
  bestThr = First[allThr];
  bestAcc = -Infinity;
  Do[
    preds = Boole[scores > thr];
    acc = Mean[Boole[preds == labels]];
    If[acc > bestAcc,
      bestAcc = acc;
      bestThr = thr
    ],
    {thr, allThr}
  ];
  result = Table[
    Module[{score},
      score = scores[[i]];
      <|
        "Gene" -> commonNodes[[i]],
        "DeltaD" -> valsD[[i]],
        "DeltaBehavior" -> valsB[[i]],
        "Score" -> score,
        "Essentiality" -> labels[[i]],
        "Prediction" -> If[score > bestThr, 1, 0],
        "Threshold" -> bestThr
      |>
    ],
    {i, Length[commonNodes]}
  ];
  result
];

ComputeNextState[state_List, cm_List, dynamic_List, params_Association] := Module[
  {n, nextState, inputs, gate, p},
  n = Length[state];
  nextState = Table[
    inputs = state[[ Flatten[Position[cm[[i]], 1]] ]];
    gate = dynamic[[i]];
    p = Lookup[params, i, <||>];
    Integration`Gates`ApplyGate[gate, inputs, p],
    {i, n}
  ];
  nextState
];

ComputeAttractors[net_Association] := Module[
  {n, cm, dynamic, params, states, nextStates, edges, g, attractors},
  n = Lookup[net, "n", Length[net["dynamic"]]];
  If[n > 15, 
    Print["Warning: Network too large for brute-force attractor analysis (N > 15)."];
    Return[$Failed]
  ];
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  states = Tuples[{0, 1}, n];
  nextStates = Map[ComputeNextState[#, cm, dynamic, params]&, states];
  edges = MapThread[DirectedEdge, {states, nextStates}];
  g = Graph[states, edges];
  attractors = FindCycle[g, Infinity, All];
  Map[
    Function[cycle,
      If[Length[cycle] === 0, {},
        Map[First, cycle]
      ]
    ],
    attractors
  ]
];

ComputeKnockoutBehaviorDeltas[net_Association] := Module[
  {baseAttr, baseMetric, n, nodeNames, deltas, kNet, attrKO, metricKO},
  baseAttr = ComputeAttractors[net];
  If[baseAttr === $Failed, Return[<||>]];
  baseMetric = Total[Length /@ baseAttr];
  n = Lookup[net, "n", Length[net["dynamic"]]];
  nodeNames = Lookup[net, "nodeNames", Range[n]];
  deltas = Table[
    kNet = KnockoutNetworkByIndex[net, i];
    attrKO = ComputeAttractors[kNet];
    If[attrKO === $Failed,
      0,
      metricKO = Total[Length /@ attrKO];
      baseMetric - metricKO
    ],
    {i, n}
  ];
  <|
    "metric_full" -> baseMetric,
    "deltaBehavior" -> deltas,
    "nodeNames" -> nodeNames,
    "behavior_criticality" -> AssociationThread[nodeNames, deltas]
  |>
];
RandomizeNetworkDegreePreserving[cm_List, nSwaps_Integer] := Module[
  {n, cmRand, edges, swap, i1, j1, i2, j2, validSwap},
  n = Length[cm];
  cmRand = cm;
  edges = Position[cm, 1];
  Do[
    If[Length[edges] < 2, Break[]];
    {{i1, j1}, {i2, j2}} = RandomSample[edges, 2];
    validSwap = And[
      i1 =!= j2,
      i2 =!= j1,
      i1 =!= i2,
      j1 =!= j2,
      cmRand[[i1, j2]] == 0,
      cmRand[[i2, j1]] == 0
    ];
    If[validSwap,
      cmRand[[i1, j1]] = 0;
      cmRand[[i2, j2]] = 0;
      cmRand[[i1, j2]] = 1;
      cmRand[[i2, j1]] = 1;
      edges = DeleteCases[edges, {i1, j1} | {i2, j2}];
      edges = Append[edges, {i1, j2}];
      edges = Append[edges, {i2, j1}];
    ],
    {swap, nSwaps}
  ];
  cmRand
];
RandomizeGateAssignments[dynamic_List] := RandomSample[dynamic];
VerifyRandomization[cmBio_List, cmRand_List, dynBio_List, dynRand_List] := Module[
  {n, inDegreeBio, inDegreeRand, outDegreeBio, outDegreeRand,
   gateCountsBio, gateCountsRand, checks},
  n = Length[cmBio];
  inDegreeBio = Total /@ cmBio;
  inDegreeRand = Total /@ cmRand;
  outDegreeBio = Total /@ Transpose[cmBio];
  outDegreeRand = Total /@ Transpose[cmRand];
  gateCountsBio = Counts[dynBio];
  gateCountsRand = Counts[dynRand];
  checks = <|
    "size_preserved" -> (Length[cmBio] == Length[cmRand]),
    "in_degree_preserved" -> (inDegreeBio == inDegreeRand),
    "out_degree_preserved" -> (outDegreeBio == outDegreeRand),
    "gate_distribution_preserved" -> (gateCountsBio == gateCountsRand),
    "structure_changed" -> (cmBio =!= cmRand)
  |>;
  checks["all_valid"] = And @@ Values[checks];
  checks
];
KnockoutNetworkByIndex[net_Association, idx_Integer] := Module[
  {cm, dynamic, params, nodeNames, n, valid, keep, cmKO, dynamicKO, paramsKO, nodeNamesKO, name},
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  nodeNames = Lookup[net, "nodeNames", Range[Length[dynamic]]];
  n = Length[dynamic];
  valid = 1 <= idx <= n;
  If[!valid,
    Return[net]
  ];
  keep = Delete[Range[n], idx];
  cmKO = cm[[keep, keep]];
  dynamicKO = dynamic[[keep]];
  paramsKO = Association[
    Table[
      i -> Lookup[params, keep[[i]], <||>],
      {i, Length[keep]}
    ]
  ];
  nodeNamesKO = nodeNames[[keep]];
  name = Lookup[net, "name", "knockout"];
  <|
    "name" -> name,
    "cm" -> cmKO,
    "nodeNames" -> nodeNamesKO,
    "dynamic" -> dynamicKO,
    "params" -> paramsKO,
    "n" -> Length[nodeNamesKO],
    "edges" -> Total[Flatten[cmKO]]
  |>
];
ComputeKnockoutDeltas[net_Association] := Module[
  {base, dFull, n, nodeNames, deltas, kNet, dKO},
  base = Integration`BioMetrics`ComputeDescriptionLength[net];
  dFull = base["D"];
  n = Lookup[net, "n", Length[net["dynamic"]]];
  nodeNames = Lookup[net, "nodeNames", Range[n]];
  deltas = Table[
    kNet = KnockoutNetworkByIndex[net, i];
    dKO = Integration`BioMetrics`ComputeDescriptionLength[kNet]["D"];
    dFull - dKO,
    {i, n}
  ];
  <|
    "D_full" -> dFull,
    "deltaD" -> deltas,
    "nodeNames" -> nodeNames,
    "criticality" -> AssociationThread[nodeNames, deltas]
  |>
];
End[]
EndPackage[]
