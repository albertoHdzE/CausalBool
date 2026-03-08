(* src/scripts/RunKnockoutDemo.m *)

(* 1. Set up Environment *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

(* Force reload to ensure latest changes *)
Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

Print["Packages loaded."];

(* 2. Helper to load and format the network from JSON *)
LoadJSONNetwork[path_] := Module[
    {json, rawNodes, rawCM, rawGates, n, nodeNames, cm, dynamic, params, i, name, gData, gType, gParams},
    
    If[!FileExistsQ[path], 
        Print["Error: File not found: ", path]; 
        Return[$Failed]
    ];
    
    json = Import[path, "RawJSON"]; (* Use RawJSON for easier Association handling *)
    
    rawNodes = json["nodes"];
    rawCM = json["cm"];
    rawGates = json["gates"];
    
    n = Length[rawNodes];
    nodeNames = rawNodes;
    cm = rawCM;
    
    (* Extract dynamic (gate types) and params in order of nodes *)
    dynamic = Table["", {n}];
    params = <||>;
    
    Do[
        name = nodeNames[[i]];
        gData = rawGates[name];
        gType = gData["gate"];
        gParams = gData["parameters"];
        
        dynamic[[i]] = gType;
        If[Length[gParams] > 0,
            params[i] = gParams;
        ];
    , {i, n}];
    
    <|
        "name" -> json["name"],
        "cm" -> cm,
        "nodeNames" -> nodeNames,
        "dynamic" -> dynamic,
        "params" -> params,
        "n" -> n,
        "edges" -> Total[Flatten[cm]]
    |>
];

(* 3. Run Demo on Lambda Phage *)
netPath = FileNameJoin[{currentDir, "data", "bio", "processed", "lambda_phage.json"}];
Print["Loading network from: ", netPath];

net = LoadJSONNetwork[netPath];

If[net === $Failed, Exit[]];

Print["Network Loaded: ", net["name"]];
Print["Nodes: ", net["nodeNames"]];
Print["Gates: ", net["dynamic"]];
Print["Baseline Description Length (D): ", Integration`BioMetrics`ComputeDescriptionLength[net]["D"]];

Print["\nComputing Knockout Deltas..."];
result = Integration`BioExperiments`ComputeKnockoutDeltas[net];

(* 4. Display Results *)
Print["\n--- Causal Criticality Profile (Delta D) ---"];
crit = result["criticality"];
nodes = Keys[crit];
Do[
    Print[nodes[[i]], " -> ", crit[nodes[[i]]]];
, {i, Length[nodes]}];

(* 5. Export Results *)
outDir = FileNameJoin[{currentDir, "results", "bio", "knockouts"}];
If[!DirectoryQ[outDir], CreateDirectory[outDir]];
outPath = FileNameJoin[{outDir, "lambda_phage_criticality.json"}];

Export[outPath, result, "JSON"];
Print["\nFull results exported to: ", outPath];
