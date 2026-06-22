(* debug_symbolic.m *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
PrependTo[$Path, pkgDir];

Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

LoadJSONNetwork[path_] := Module[{json, rawNodes, rawCM, rawGates, n, nodeNames, cm, dynamic, params, i, name, gData, gType, gParams},
    If[!FileExistsQ[path], Return[$Failed]];
    json = Import[path, "RawJSON"];
    rawNodes = json["nodes"];
    rawCM = json["cm"];
    rawGates = json["gates"];
    n = Length[rawNodes];
    nodeNames = rawNodes;
    cm = rawCM;
    dynamic = Table["", {n}];
    params = <||>;
    Do[
        name = nodeNames[[i]];
        If[KeyExistsQ[rawGates, name],
            gData = rawGates[name];
            gType = gData["gate"];
            gParams = gData["parameters"];
        ,
            gType = "Input";
            gParams = <||>;
        ];
        dynamic[[i]] = gType;
        If[Length[gParams] > 0, params[i] = gParams];
    , {i, n}];
    <| "name" -> json["name"], "cm" -> cm, "nodeNames" -> nodeNames, "dynamic" -> dynamic, "params" -> params, "n" -> n |>
];

Integration`BioMetrics`Private`encodeNodeCost[_, "Input", _, _] := 0;

ComputeAttractorsRobust[net_Association] := Module[
  {n, cm, dynamic, params, states, nextStates, edges, g, cycles, selfLoops, allAttractors},
  n = Lookup[net, "n", Length[net["dynamic"]]];
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  states = Tuples[{0, 1}, n];
  nextStates = Map[Integration`BioExperiments`Private`ComputeNextState[#, cm, dynamic, params]&, states];
  edges = MapThread[DirectedEdge, {states, nextStates}];
  g = Graph[states, edges];
  cycles = FindCycle[g, Infinity, All];
  selfLoops = List /@ Select[EdgeList[g], First[#] === Last[#] &];
  allAttractors = Join[cycles, selfLoops];
  Map[Function[cycle, Map[First, cycle]], allAttractors]
];

ComputeAttractorsKnockout[net_Association, kIdx_Integer] := Module[
  {n, cm, dynamic, params, states, nextStates, edges, g, cycles, selfLoops, allAttractors},
  n = Lookup[net, "n", Length[net["dynamic"]]];
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  states = Tuples[{0, 1}, n];
  nextStates = Map[
    Function[s,
      Module[{ns},
        ns = Integration`BioExperiments`Private`ComputeNextState[s, cm, dynamic, params];
        ns[[kIdx]] = 0; 
        ns
      ]
    ],
    states
  ];
  edges = MapThread[DirectedEdge, {states, nextStates}];
  g = Graph[states, edges];
  cycles = FindCycle[g, Infinity, All];
  selfLoops = List /@ Select[EdgeList[g], First[#] === Last[#] &];
  allAttractors = Join[cycles, selfLoops];
  Map[Function[cycle, Map[First, cycle]], allAttractors]
];

networks = {"lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"};

Do[
    netName = net;
    Print["Checking ", netName];
    netPath = FileNameJoin[{currentDir, "data", "bio", "processed", netName <> ".json"}];
    loadedNet = LoadJSONNetwork[netPath];
    
    If[loadedNet === $Failed, Print["Failed load"]; Continue[]];
    
    (* Check Original *)
    attrs = ComputeAttractorsRobust[loadedNet];
    flat = Flatten[attrs];
    If[!AllTrue[flat, IntegerQ], 
        Print["  Original has non-integers!"];
        Print["  Sample: ", Select[flat, !IntegerQ[#]&][[1]]];
    ];
    
    (* Check Knockouts *)
    n = loadedNet["n"];
    Do[
        kAttrs = ComputeAttractorsKnockout[loadedNet, i];
        flatK = Flatten[kAttrs];
        If[!AllTrue[flatK, IntegerQ], 
            Print["  Knockout ", i, " has non-integers!"];
            Print["  Sample: ", Select[flatK, !IntegerQ[#]&][[1]]];
        ];
    , {i, n}];
, {net, networks}];
