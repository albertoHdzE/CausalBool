(* src/scripts/GlobalStatsPipeline.m *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

(* Helper to load network - reused from GlobalValidationAnalysis.m *)
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

(* --- Statistical Analysis --- *)

If[Length[globalData] > 0,
    essentialGenes = Select[globalData, #["Essentiality"] == 1 &];
    nonEssentialGenes = Select[globalData, #["Essentiality"] == 0 &];
    
    valsEss = #["DeltaD"] & /@ essentialGenes;
    valsNonEss = #["DeltaD"] & /@ nonEssentialGenes;
    
    nEss = Length[valsEss];
    nNonEss = Length[valsNonEss];
    
    meanEss = Mean[valsEss];
    meanNonEss = Mean[valsNonEss];
    sdEss = StandardDeviation[valsEss];
    sdNonEss = StandardDeviation[valsNonEss];
    
    (* Cohen's d *)
    sPooled = Sqrt[((nEss - 1) * sdEss^2 + (nNonEss - 1) * sdNonEss^2) / (nEss + nNonEss - 2)];
    cohensD = (meanEss - meanNonEss) / sPooled;
    
    (* Mann-Whitney U Test *)
    (* Null: Distributions are equal. Alt: Essential > NonEssential *)
    mwTest = MannWhitneyTest[{valsEss, valsNonEss}, AlternativeHypothesis -> "Greater"];
    pVal = mwTest; (* By default returns p-value *)
    
    (* ROC / AUC *)
    (* We need to compute TPR and FPR for varying thresholds *)
    (* Sort all data by DeltaD descending *)
    sortedData = SortBy[globalData, -#["DeltaD"] &];
    totalPos = nEss;
    totalNeg = nNonEss;
    
    auc = 0;
    prevFPR = 0;
    prevTPR = 0;
    curTP = 0;
    curFP = 0;
    
    (* Iterate through sorted unique values as thresholds *)
    uniqueVals = Reverse[Sort[Union[#["DeltaD"] & /@ globalData]]];
    
    (* We can also just iterate through the sorted list, but need to handle ties *)
    (* Simplest robust way: trapezoidal rule over unique thresholds *)
    rocPoints = {};
    
    Do[
        thr = val;
        (* Predicted positive if >= thr *)
        (* Note: standard ROC sweeps threshold from Inf down to -Inf *)
        (* Here we take strictly greater than threshold, or greater-equal. *)
        (* Let's stick to standard definition: score > threshold -> Positive *)
        
        tp = Count[essentialGenes, g_ /; g["DeltaD"] >= thr];
        fp = Count[nonEssentialGenes, g_ /; g["DeltaD"] >= thr];
        
        tpr = tp / totalPos;
        fpr = fp / totalNeg;
        
        AppendTo[rocPoints, {fpr, tpr}];
    , {val, uniqueVals}];
    
    (* Add (0,0) and (1,1) if not present, though (1,1) comes from threshold < min *)
    PrependTo[rocPoints, {0, 0}]; (* Threshold > max *)
    AppendTo[rocPoints, {1, 1}]; (* Threshold < min *)
    
    (* Integrate trapezoidal *)
    (* Sort by FPR *)
    rocPoints = Sort[rocPoints];
    Do[
        x1 = rocPoints[[i, 1]];
        y1 = rocPoints[[i, 2]];
        x2 = rocPoints[[i+1, 1]];
        y2 = rocPoints[[i+1, 2]];
        auc = auc + (x2 - x1) * (y1 + y2) / 2;
    , {i, Length[rocPoints] - 1}];
    
    Print["\n=== Statistical Results ==="];
    Print["Cohen's d: ", NumberForm[cohensD, {5, 3}]];
    Print["Mann-Whitney p-value: ", NumberForm[pVal, {5, 5}]];
    Print["AUC: ", NumberForm[auc, {5, 3}]];
    
    results = <|
        "CohensD" -> cohensD,
        "MannWhitneyP" -> pVal,
        "AUC" -> auc,
        "MeanEssential" -> meanEss,
        "MeanNonEssential" -> meanNonEss,
        "Ratio" -> meanEss / meanNonEss
    |>;
    
    outPath = FileNameJoin[{currentDir, "results", "bio", "validation", "global_stats.json"}];
    Export[outPath, results, "JSON"];
    Print["Results saved to: ", outPath];
];
