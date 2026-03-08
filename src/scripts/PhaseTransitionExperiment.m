(* src/scripts/PhaseTransitionExperiment.m *)

(* 1. Environment Setup *)
currentDir = Directory[];
srcDir = FileNameJoin[{currentDir, "src"}];
pkgDir = FileNameJoin[{srcDir, "Packages"}];
If[!MemberQ[$Path, pkgDir], PrependTo[$Path, pkgDir]];

Get["Integration`BioMetrics`"];
Get["Integration`BioExperiments`"];

(* 2. Helper Functions *)

(* Robust ApplyGate (adapted from BehavioralKnockoutAnalysis.m) *)
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

(* Robust Attractor Computation *)
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

StackAttractors[attractors_] := Module[{},
    If[attractors === {} || attractors === $Failed, Return[{}]];
    Flatten[attractors, 1]
];

(* Network Generator (from Masterplan) *)
GenerateMixedNetwork[n_, pXOR_, seed_] := Module[
  {cm, dynamic, params, i, j},
  
  SeedRandom[seed];
  
  (* Random connectivity (Erdős-Rényi, p=0.2 approx 2.4 edges per node for n=12) *)
  (* To ensure connected behavior, let's ensure at least 1 input per node *)
  cm = Table[0, {n}, {n}];
  Do[
      (* Ensure at least 1 input *)
      cm[[i, RandomInteger[{1, n}]]] = 1;
      (* Add more edges with prob *)
      Do[
          If[i != j && RandomReal[] < 0.15, cm[[i, j]] = 1], 
      {j, n}];
  , {i, n}];
  
  (* Assign gates *)
  dynamic = Table[
    If[RandomReal[] < pXOR,
      "XOR",
      RandomChoice[{"AND", "OR"}] (* Simple Canalising *)
    ],
    {n}
  ];
  
  (* No special params for standard gates *)
  params = <||>;
  
  <|"n" -> n, "cm" -> cm, "dynamic" -> dynamic, "params" -> params|>
];

(* 3. Experiment Configuration *)
nGenes = 10; (* Small enough for full state space BDM *)
numNetworks = 20; (* Networks per step *)
pXORSteps = Range[0.0, 1.0, 0.05];

batchBDMRequest = <||>;
experimentData = {};

Print["\n=== Phase 6: Universality / Phase Transition Sweep ==="];
Print["Generating networks and computing mechanistic D..."];

(* 4. Generation Loop *)
Do[
    pXOR = p;
    Print["Processing pXOR = ", NumberForm[p, {3, 2}]];
    
    Do[
        seed = Hash[{p, k}]; (* Unique seed *)
        net = GenerateMixedNetwork[nGenes, p, seed];
        
        (* 1. Compute Mechanistic D *)
        (* Need to format net for ComputeDescriptionLength *)
        (* It expects cm, dynamic, params in Association or List form *)
        dResult = Integration`BioMetrics`ComputeDescriptionLength[net];
        valD = dResult["D"];
        
        (* 2. Compute Behavior (Attractors) *)
        attrs = ComputeAttractorsRobust[net];
        matrix = StackAttractors[attrs];
        
        (* Store for BDM batch *)
        reqKey = "p" <> ToString[PaddedForm[p, {2, 2}]] <> "_k" <> ToString[k];
        (* Clean key for JSON *)
        reqKey = StringReplace[reqKey, " " -> "0"]; 
        
        If[Length[matrix] > 0,
            batchBDMRequest[reqKey] = matrix;
            
            AppendTo[experimentData, <|
                "pXOR" -> p,
                "Replica" -> k,
                "D" -> valD,
                "RequestKey" -> reqKey
            |>];
        ];
        
    , {k, numNetworks}];
    
, {p, pXORSteps}];

(* 5. External BDM Computation *)
Print["\nComputing BDM for ", Length[batchBDMRequest], " matrices..."];
tempReqFile = FileNameJoin[{currentDir, "temp_pt_bdm_request.json"}];
Export[tempReqFile, batchBDMRequest, "JSON"];

scriptPath = FileNameJoin[{srcDir, "scripts", "compute_bdm_batch.py"}];
cmd = "python3 " <> scriptPath <> " " <> tempReqFile;
process = RunProcess[{"sh", "-c", cmd}, All];

If[process["ExitCode"] =!= 0,
    Print["Error executing Python BDM script."];
    Print[process["StandardError"]];
    Exit[];
];

bdmResults = ImportString[process["StandardOutput"], "RawJSON"];
DeleteFile[tempReqFile];

(* 6. Consolidate Results *)
finalResults = {};
Do[
    item = experimentData[[i]];
    key = item["RequestKey"];
    valBDM = Lookup[bdmResults, key, 0.0];
    
    res = <|
        "pXOR" -> item["pXOR"],
        "Replica" -> item["Replica"],
        "D" -> item["D"],
        "BDM" -> valBDM
    |>;
    AppendTo[finalResults, res];
, {i, Length[experimentData]}];

(* 7. Save Results *)
resultsDir = FileNameJoin[{currentDir, "results", "bio", "phase_transition"}];
If[!DirectoryQ[resultsDir], CreateDirectory[resultsDir, CreateIntermediateDirectories->True]];
outFile = FileNameJoin[{resultsDir, "phase_transition.json"}];
Export[outFile, finalResults, "JSON"];
Print["Results saved to: ", outFile];

(* 8. Summary Statistics *)
summary = GroupBy[finalResults, #["pXOR"] &];
Print["\nSummary (Mean D vs Mean BDM):"];
keys = Sort[Keys[summary]];
Do[
    k = keys[[i]];
    vals = summary[k];
    meanD = Mean[#["D"] & /@ vals];
    meanBDM = Mean[#["BDM"] & /@ vals];
    Print["pXOR: ", NumberForm[k, {3, 2}], 
          " | D: ", NumberForm[meanD, {5, 2}], 
          " | BDM: ", NumberForm[meanBDM, {5, 2}]];
, {i, Length[keys]}];
