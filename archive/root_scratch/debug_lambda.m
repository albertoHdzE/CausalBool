(* debug_lambda.m *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
PrependTo[$Path, pkgDir];

Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

(* Definitions from script *)
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

ComputeAttractorsRobust[net_Association] := Module[
  {n, cm, dynamic, params, states, nextStates, edges, g, cycles, selfLoops, allAttractors, res},
  n = Lookup[net, "n", Length[net["dynamic"]]];
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  states = Tuples[{0, 1}, n];
  nextStates = Map[Integration`BioExperiments`Private`ComputeNextState[#, cm, dynamic, params]&, states];
  edges = MapThread[DirectedEdge, {states, nextStates}];
  g = Graph[states, edges];
  
  cycles = FindCycle[g, Infinity, All];
  Print["Cycles found: ", Length[cycles]];
  
  selfLoops = List /@ Select[EdgeList[g], First[#] === Last[#] &];
  Print["SelfLoops found: ", Length[selfLoops]];
  
  allAttractors = Join[cycles, selfLoops];
  
  res = Map[
    Function[cycle,
      Map[First, cycle]
    ],
    allAttractors
  ];
  res
];

Print["=== Debug Lambda Phage ==="];
netName = "lambda_phage";
netPath = FileNameJoin[{currentDir, "data", "bio", "processed", netName <> ".json"}];
loadedNet = LoadJSONNetwork[netPath];

If[loadedNet === $Failed, Print["Failed to load net"]; Exit[]];

Print["Computing Attractors..."];
attrs = ComputeAttractorsRobust[loadedNet];
Print["Attractor Count: ", Length[attrs]];
Print["Sample: ", If[Length[attrs]>0, attrs[[1]], "None"]];

Print["=== Checking for Null/Symbolic ==="];
Print["Head of first state: ", Head[attrs[[1,1]]]];
