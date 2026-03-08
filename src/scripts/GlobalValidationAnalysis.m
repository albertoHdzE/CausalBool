(* src/scripts/GlobalValidationAnalysis.m *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

(* Helper to load network *)
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
        (* FIX: Handle missing gates (inputs) *)
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

(* FIX: Overload cost for Input *)
Integration`BioMetrics`Private`encodeNodeCost[_, "Input", _, _] := 0;

essPath = FileNameJoin[{currentDir, "data", "bio", "validation", "essentiality_data.csv"}];
allEss = Integration`BioExperiments`LoadEssentialityData[essPath];
networks = {"lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"};

globalData = {};

Print["\nCollecting data from all networks..."];

Do[
  netName = net;
  netPath = FileNameJoin[{currentDir, "data", "bio", "processed", netName <> ".json"}];
  loadedNet = LoadJSONNetwork[netPath];
  
  If[loadedNet =!= $Failed && KeyExistsQ[allEss, netName],
    crit = Integration`BioExperiments`ComputeKnockoutDeltas[loadedNet]["criticality"];
    ess = allEss[netName];
    commonNodes = Intersection[Keys[crit], Keys[ess]];
    
    Do[
      AppendTo[globalData, <|
        "Network" -> netName,
        "Gene" -> node,
        "DeltaD" -> crit[node],
        "Essentiality" -> ess[node]
      |>],
      {node, commonNodes}
    ];
  ];
, {net, networks}];

Print["\nTotal Genes Analyzed: ", Length[globalData]];

(* Analyze separation *)
essentialGenes = Select[globalData, #["Essentiality"] == 1 &];
nonEssentialGenes = Select[globalData, #["Essentiality"] == 0 &];

meanEss = Mean[#["DeltaD"] & /@ essentialGenes];
meanNonEss = Mean[#["DeltaD"] & /@ nonEssentialGenes];

Print["\n=== Global Algorithmic Analysis ==="];
Print["Average DeltaD (Information Loss) for ESSENTIAL genes:      ", NumberForm[meanEss, {5, 2}]];
Print["Average DeltaD (Information Loss) for NON-ESSENTIAL genes:  ", NumberForm[meanNonEss, {5, 2}]];

Print["\nRatio (Signal Strength): ", NumberForm[meanEss / meanNonEss, {3, 1}], "x"];
Print["(Essential genes carry " <> ToString[NumberForm[meanEss / meanNonEss, {3, 1}]] <> "x more algorithmic information on average)"];

(* Simple ASCII Plot *)
Print["\n=== Distribution of DeltaD ==="];
Print["Essential (1) vs Non-Essential (0)"];
Print["Gene\t\tEss\tDeltaD\tBar"];
sortedData = SortBy[globalData, -#["DeltaD"] &];
Do[
  bar = StringJoin[ConstantArray["|", Round[row["DeltaD"] / 2]]];
  Print[
    StringPadRight[row["Network"] <> "-" <> row["Gene"], 20], "\t",
    row["Essentiality"], "\t",
    NumberForm[row["DeltaD"], {4, 1}], "\t",
    bar
  ],
  {row, sortedData}
];

(* Simple classification *)
Print["\n=== Global Classification Performance ==="];
bestAcc = 0;
bestThr = 0;
If[Length[globalData] > 0,
    vals = #["DeltaD"] & /@ globalData;
    minVal = Min[vals];
    maxVal = Max[vals];
    step = (maxVal - minVal) / 50;
    If[step == 0, step = 1];
    labels = #["Essentiality"] & /@ globalData;

    Do[
      preds = If[# > thr, 1, 0] & /@ vals;
      matches = Count[preds - labels, 0];
      acc = N[matches / Length[labels]];
      If[acc > bestAcc, bestAcc = acc; bestThr = thr],
      {thr, minVal, maxVal, step}
    ];

    Print["Best Global Accuracy using ONLY DeltaD: ", NumberForm[bestAcc * 100, {5, 2}], "%"];
    Print["(Threshold: DeltaD > ", NumberForm[bestThr, {5, 2}], ")"];
  ];
