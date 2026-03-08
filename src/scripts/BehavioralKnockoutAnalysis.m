(* src/scripts/BehavioralKnockoutAnalysis.m *)

(* 1. Environment Setup *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

(* 2. Helper Functions *)

(* Helper to load network with gate fix *)
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

(* Fix for symbolic DeltaD *)
Integration`BioMetrics`Private`encodeNodeCost[_, "Input", _, _] := 0;

(* Robust ApplyGate *)
MyApplyGate[gate_String, inputs_List, params_: <||>] := Module[{padded, maxIdx},
  padded = inputs;
  Switch[gate,
    "NOT", If[Length[inputs] < 1, padded = {0}],
    "IMPLIES" | "NIMPLIES", If[Length[inputs] < 2, padded = PadRight[inputs, 2, 0]],
    "CANALISING", 
      maxIdx = Lookup[params, "canalisingIndex", 1];
      If[Length[inputs] < maxIdx, padded = PadRight[inputs, maxIdx, 0]]
  ];
  
  If[gate === "Input" || gate === "INPUT", Return[0]];
  
  Integration`Gates`ApplyGate[gate, padded, params]
];

(* Custom ComputeNextState *)
MyComputeNextState[state_, cm_, dynamic_, params_] := Module[{n, nextState, inputs, gate, p, res},
    n = Length[state];
    nextState = Table[0, {n}];
    Do[
        inputs = state[[ Flatten[Position[cm[[i]], 1]] ]];
        gate = dynamic[[i]];
        p = Lookup[params, i, <||>];
        res = MyApplyGate[gate, inputs, p];
        nextState[[i]] = res;
    , {i, n}];
    nextState
];

(* Robust Attractor Computation (Handles self-loops/fixed points) *)
ComputeAttractorsRobust[net_Association] := Module[
  {n, cm, dynamic, params, states, nextStates, edges, g, cycles, selfLoops, allAttractors},
  n = Lookup[net, "n", Length[net["dynamic"]]];
  If[n > 15, Return[$Failed]];
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  states = Tuples[{0, 1}, n];
  nextStates = Map[MyComputeNextState[#, cm, dynamic, params]&, states];
  edges = MapThread[DirectedEdge, {states, nextStates}];
  g = Graph[states, edges];
  
  cycles = FindCycle[g, Infinity, All];
  selfLoops = List /@ Select[EdgeList[g], First[#] === Last[#] &];
  allAttractors = Join[cycles, selfLoops];
  
  Map[
    Function[cycle,
      Map[First, cycle]
    ],
    allAttractors
  ]
];

(* Stuck-at-0 Knockout Simulation for Behavior *)
ComputeAttractorsKnockout[net_Association, kIdx_Integer] := Module[
  {n, cm, dynamic, params, states, nextStates, edges, g, cycles, selfLoops, allAttractors},
  n = Lookup[net, "n", Length[net["dynamic"]]];
  If[n > 15, Return[$Failed]];
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  
  states = Tuples[{0, 1}, n];
  
  (* Compute next state but force knockout node to 0 *)
  nextStates = Map[
    Function[s,
      Module[{ns},
        ns = MyComputeNextState[s, cm, dynamic, params];
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
  
  Map[
    Function[cycle,
      Map[First, cycle]
    ],
    allAttractors
  ]
];


(* Helper to stack attractors into a single matrix *)
StackAttractors[attractors_] := Module[{},
    If[attractors === {} || attractors === $Failed, Return[{}]];
    Flatten[attractors, 1]
];

(* 3. Load Data *)
essPath = FileNameJoin[{currentDir, "data", "bio", "validation", "essentiality_data.csv"}];
allEss = Integration`BioExperiments`LoadEssentialityData[essPath];
networks = {"lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"};

batchBDMRequest = <||>;
analysisData = {};

Print["\n=== Phase 5: Behavioral DeltaBDM Analysis ==="];
Print["Preparing attractor data for external BDM computation..."];

(* 4. Data Collection Loop *)
Do[
  netName = net;
  netPath = FileNameJoin[{currentDir, "data", "bio", "processed", netName <> ".json"}];
  loadedNet = LoadJSONNetwork[netPath];
  
  If[loadedNet =!= $Failed && KeyExistsQ[allEss, netName],
    Print["Processing: ", netName];
    
    (* A. Compute Structural DeltaD (using original Structural Knockout) *)
    critData = Integration`BioExperiments`ComputeKnockoutDeltas[loadedNet];
    deltaDMap = critData["criticality"];
    
    (* B. Compute Original Behavior *)
    origAttrs = ComputeAttractorsRobust[loadedNet];
    origMatrix = StackAttractors[origAttrs];
    
    (* Check if matrix is empty *)
    If[Length[origMatrix] == 0, Print["Warning: No attractors found for ", netName]];
    
    (* Add to batch *)
    batchBDMRequest[netName <> "_ORIGINAL"] = origMatrix;
    
    (* C. Compute Knockout Behaviors (using Stuck-at-0) *)
    n = loadedNet["n"];
    nodeNames = loadedNet["nodeNames"];
    ess = allEss[netName];
    
    Do[
        gene = nodeNames[[i]];
        If[KeyExistsQ[ess, gene],
            (* Use Stuck-at-0 Simulation *)
            kAttrs = ComputeAttractorsKnockout[loadedNet, i];
            kMatrix = StackAttractors[kAttrs];
            
            batchBDMRequest[netName <> "_" <> gene] = kMatrix;
            
            AppendTo[analysisData, <|
                "Network" -> netName,
                "Gene" -> gene,
                "Essentiality" -> ess[gene],
                "DeltaD" -> deltaDMap[gene],
                "RequestKey_Orig" -> netName <> "_ORIGINAL",
                "RequestKey_KO" -> netName <> "_" <> gene
            |>];
        ];
    , {i, n}];
  ];
, {net, networks}];

(* 5. External BDM Computation *)
Print["\nComputing BDM for ", Length[batchBDMRequest], " matrices..."];
tempReqFile = FileNameJoin[{currentDir, "temp_bdm_request.json"}];
Export[tempReqFile, batchBDMRequest, "JSON"];

scriptPath = FileNameJoin[{srcDir, "scripts", "compute_bdm_batch.py"}];
cmd = "python3 " <> scriptPath <> " " <> tempReqFile;
process = RunProcess[{"sh", "-c", cmd}, All];

If[!AssociationQ[process],
    Print["Error: RunProcess failed to execute."];
    Print["Command: ", cmd];
    Print["Result: ", process];
    Exit[];
];

jsonOutput = process["StandardOutput"];
errOutput = process["StandardError"];
exitCode = process["ExitCode"];

If[exitCode =!= 0 || StringLength[StringTrim[errOutput]] > 0,
    Print["Python Process Info (Exit Code: ", exitCode, "):"];
    If[StringLength[StringTrim[errOutput]] > 0, Print["Stderr:\n", errOutput]];
];

bdmResults = ImportString[jsonOutput, "RawJSON"];

DeleteFile[tempReqFile];

If[bdmResults === $Failed || !AssociationQ[bdmResults],
    Print["Error: Failed to parse BDM results."];
    Print["Raw Stdout: ", jsonOutput];
    Exit[];
];

(* 6. Compute DeltaBDM and Consolidate *)
finalResults = {};
Do[
    item = analysisData[[i]];
    keyOrig = item["RequestKey_Orig"];
    keyKO = item["RequestKey_KO"];
    
    valOrig = Lookup[bdmResults, keyOrig, 0.0];
    valKO = Lookup[bdmResults, keyKO, 0.0];
    
    deltaBDM = valOrig - valKO;
    
    res = <|
        "Network" -> item["Network"],
        "Gene" -> item["Gene"],
        "Essentiality" -> item["Essentiality"],
        "DeltaD" -> item["DeltaD"],
        "BDM_Orig" -> valOrig,
        "BDM_KO" -> valKO,
        "DeltaBDM" -> deltaBDM
    |>;
    AppendTo[finalResults, res];
, {i, Length[analysisData]}];

(* 7. Save Results *)
resultsDir = FileNameJoin[{currentDir, "results", "bio", "knockouts"}];
If[!DirectoryQ[resultsDir], CreateDirectory[resultsDir, CreateIntermediateDirectories->True]];
outFile = FileNameJoin[{resultsDir, "bdm_knockouts.json"}];
Export[outFile, finalResults, "JSON"];
Print["Results saved to: ", outFile];

(* 8. Statistical Summary *)
Print["\n=== Statistical Summary ==="];
essential = Select[finalResults, #["Essentiality"] == 1 &];
nonEssential = Select[finalResults, #["Essentiality"] == 0 &];

meanDEss = Mean[#["DeltaD"]& /@ essential];
meanDNon = Mean[#["DeltaD"]& /@ nonEssential];
meanBEss = Mean[#["DeltaBDM"]& /@ essential];
meanBNon = Mean[#["DeltaBDM"]& /@ nonEssential];

Print["Mean DeltaD (Ess):      ", NumberForm[meanDEss, {5,2}]];
Print["Mean DeltaD (Non-Ess):  ", NumberForm[meanDNon, {5,2}]];
If[meanDNon != 0,
    Print["Ratio DeltaD:           ", NumberForm[meanDEss/meanDNon, {3,1}], "x"];
];

Print["\nMean DeltaBDM (Ess):    ", NumberForm[meanBEss, {5,2}]];
Print["Mean DeltaBDM (Non-Ess):", NumberForm[meanBNon, {5,2}]];
If[meanBNon != 0,
    Print["Ratio DeltaBDM:         ", NumberForm[meanBEss/meanBNon, {3,1}], "x"];
];

dVals = #["DeltaD"]& /@ finalResults;
bVals = #["DeltaBDM"]& /@ finalResults;
corr = Correlation[dVals, bVals];
Print["\nCorrelation (DeltaD vs DeltaBDM): ", NumberForm[corr, {3,2}]];

Print["\nTop 5 Genes by DeltaBDM:"];
sorted = SortBy[finalResults, -Abs[#["DeltaBDM"]] &];
Do[
    row = sorted[[k]];
    Print[row["Network"], "-", row["Gene"], 
          "\t Ess:", row["Essentiality"], 
          "\t dBDM:", NumberForm[row["DeltaBDM"], {5,2}],
          "\t dD:", NumberForm[row["DeltaD"], {5,2}]];
, {k, Min[5, Length[sorted]]}];
