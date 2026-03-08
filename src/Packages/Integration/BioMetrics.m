BeginPackage["Integration`BioMetrics`"]
ComputeDescriptionLength::usage = "ComputeDescriptionLength[net] or [cm, dyn, params] returns description length D for a Boolean network";
ComputeDescriptionLengthV2::usage = "ComputeDescriptionLengthV2[net] returns structural description length D_v2 (requires motifs/hierarchy data)";
Begin["`Private`"]
gateLabels = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN","CANALISING"};
log2Int[x_] := N@Log[2, x];
encodeNodeCost[cmRow_List, gate_String, nodeParams_Association, n_Integer] := Module[{ic, d, k, cost},
  ic = Flatten@Position[cmRow, 1];
  d = Length[ic];
  k = Length[gateLabels];
  cost = 0.0;
  cost += log2Int[k];
  cost += log2Int[Max[1, Binomial[n, d]]];
  cost += Switch[gate,
    "KOFN", log2Int[d + 1] + 1,
    "CANALISING", log2Int[n] + 1 + 1,
    "IMPLIES" | "NIMPLIES", log2Int[Max[1, d (d - 1)]],
    "NOT", log2Int[Max[1, d]],
    "MAJORITY", 1,
    "XOR" | "XNOR", 1,
    _, 1
  ];
  cost
];
encodeNodeLogicCost[cmRow_List, gate_String, nodeParams_Association, n_Integer] := Module[{ic, d, k, cost},
  ic = Flatten@Position[cmRow, 1];
  d = Length[ic];
  k = Length[gateLabels];
  cost = 0.0;
  (* 1. Gate Type Selection Cost *)
  cost += log2Int[k];
  
  (* 2. Topology Cost (REMOVED in V2 - handled by Motifs/Hierarchy) *)
  (* cost += log2Int[Max[1, Binomial[n, d]]]; *)
  
  (* 3. Parameter Cost (Logic complexity given wiring) *)
  cost += Switch[gate,
    "KOFN", log2Int[d + 1] + 1,
    "CANALISING", log2Int[n] + 1 + 1,
    "IMPLIES" | "NIMPLIES", log2Int[Max[1, d (d - 1)]],
    "NOT", log2Int[Max[1, d]],
    "MAJORITY", 1,
    "XOR" | "XNOR", 1,
    _, 1
  ];
  cost
];

ComputeDescriptionLength[cm_List, dynamic_List, params_Association : <||>] := Module[{n, perNode, totalBits},
  n = Length[dynamic];
  perNode = Table[
    encodeNodeCost[cm[[i]], dynamic[[i]], Lookup[params, i, <||>], n],
    {i, n}
  ];
  totalBits = Total[perNode];
  <|
    "D" -> totalBits,
    "perNode" -> perNode,
    "avgPerNode" -> If[n > 0, totalBits/n, 0.0],
    "components" -> n,
    "totalEdges" -> Total[Flatten[cm]]
  |>
];
ComputeDescriptionLength[net_Association] := ComputeDescriptionLength[
  net["cm"],
  net["dynamic"],
  Lookup[net, "params", <||>]
];

ComputeDescriptionLengthV2[net_Association] := Module[
  {n, cm, dynamic, params, dWiring, dLogic, dMotif, dHierarchy, dSize, motifs, hierarchy, total, perNodeLogic},
  
  motifs = Lookup[net, "motifs", <||>];
  hierarchy = Lookup[net, "hierarchy", <||>];
  
  (* Require V2 data *)
  If[Length[motifs] == 0 || Length[hierarchy] == 0,
    Return[$Failed]
  ];
  
  dMotif = Lookup[motifs, "motif_cost", 0.0];
  dHierarchy = Lookup[hierarchy, "hierarchy_cost", 0.0];
  dWiring = dMotif + dHierarchy;
  
  cm = net["cm"];
  dynamic = net["dynamic"];
  params = Lookup[net, "params", <||>];
  n = Length[dynamic];
  
  perNodeLogic = Table[
    encodeNodeLogicCost[cm[[i]], dynamic[[i]], Lookup[params, i, <||>], n],
    {i, n}
  ];
  dLogic = Total[perNodeLogic];
  
  dSize = N@Log[2, Max[1, n]]; 
  
  total = dSize + dWiring + dLogic;
  
  <|
    "D_v2" -> total,
    "D_wiring" -> dWiring,
    "D_logic" -> dLogic,
    "components" -> <|
       "motif" -> dMotif, 
       "hierarchy" -> dHierarchy, 
       "size" -> dSize,
       "logic_per_node" -> perNodeLogic
    |>
  |>
];
End[]
EndPackage[]

