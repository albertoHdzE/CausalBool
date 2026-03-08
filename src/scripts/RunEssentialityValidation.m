currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

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
        gData = rawGates[name];
        gType = gData["gate"];
        gParams = gData["parameters"];
        dynamic[[i]] = gType;
        If[Length[gParams] > 0, params[i] = gParams];
    , {i, n}];
    <| "name" -> json["name"], "cm" -> cm, "nodeNames" -> nodeNames, "dynamic" -> dynamic, "params" -> params, "n" -> n |>
];

essPath = FileNameJoin[{currentDir, "data", "bio", "validation", "essentiality_data.csv"}];

allEss = Integration`BioExperiments`LoadEssentialityData[essPath];

networks = {"lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"};

Do[
  netName = net;
  netPath = FileNameJoin[{currentDir, "data", "bio", "processed", netName <> ".json"}];
  Print["\n=== Network: ", netName, " ==="];
  loadedNet = LoadJSONNetwork[netPath];
  If[loadedNet === $Failed,
    Print["Skipping ", netName, ": network file not found."];
    Continue[];
  ];
  res = Integration`BioExperiments`ComputeKnockoutDeltas[loadedNet];
  crit = res["criticality"];
  behRes = Integration`BioExperiments`ComputeKnockoutBehaviorDeltas[loadedNet];
  behCrit = If[AssociationQ[behRes] && KeyExistsQ[behRes, "behavior_criticality"], behRes["behavior_criticality"], <||>];
  If[KeyExistsQ[allEss, netName],
    ess = allEss[netName];
    comparison = If[AssociationQ[behCrit] && behCrit =!= <||>,
      Integration`BioExperiments`CompareCriticalityToEssentiality[crit, ess, behCrit],
      Integration`BioExperiments`CompareCriticalityToEssentiality[crit, ess]
    ];
    If[Length[comparison] == 0,
      Print["No overlapping genes between criticality and essentiality for ", netName, "."],
      Print["Gene\tDeltaD\tDeltaB\tEssential\tPred"];
      Do[
        Print[
          row["Gene"], "\t",
          NumberForm[row["DeltaD"], {4, 2}], "\t",
          If[KeyExistsQ[row, "DeltaBehavior"], NumberForm[row["DeltaBehavior"], {4, 2}], "-"], "\t",
          row["Essentiality"], "\t\t",
          row["Prediction"]
        ],
        {row, comparison}
      ];
      correct = Count[comparison, row_ /; row["Essentiality"] == row["Prediction"]];
      total = Length[comparison];
      Print["Accuracy: ", correct, "/", total, " (", N[correct/total]*100, "%)"];
    ];
    ,
    Print["No essentiality data available for ", netName, "."]
  ];
,
{net, networks}
];
