BeginPackage["Integration`BioMetrics`"]
ComputeDescriptionLength::usage = "ComputeDescriptionLength[net] or [cm, dyn, params] returns description length D for a Boolean network";
ComputeDescriptionLengthV2::usage = "ComputeDescriptionLengthV2[net] returns structural description length D_v2 (requires motifs/hierarchy data)";
Begin["`Private`"]
gateLabels = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN","CANALISING"};
log2Int[x_] := N@Log[2, x];
(* Per-node description length in the declared node language

     (gate type, in-degree, input set, gate parameters)

   read in that order. Each field is a uniform index into an alphabet whose size
   is fixed by the fields already read, so the code is sequentially decodable and
   its Kraft sum over the whole description space is exactly 1.

   AUDIT03/R3.1 (2026-09-03): the in-degree field log2(n+1) was absent. Without
   it the decoder cannot know the width of the input-set field, nor read it as an
   index into the d-subsets of [n]; the Kraft sum is then n+1, so D was not a
   description length and every knockout DeltaD was a difference of two invalid
   lengths. Restored to match complexity_analysis.py (the field that superseded
   D_formula = 101.07 by 135.66) and TSK-MIXED-001's encodeCostBits.
   Proof: audit/AUDIT03_R3_description_length/verify_description_length.py. *)
encodeNodeCost[cmRow_List, gate_String, nodeParams_Association, n_Integer] := Module[{ic, d, k, cost},
  ic = Flatten@Position[cmRow, 1];
  d = Length[ic];
  k = Length[gateLabels];
  cost = 0.0;
  cost += log2Int[k];
  cost += log2Int[n + 1];
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
(* AUDIT03/R3.1 — DELIBERATELY NOT GIVEN THE IN-DEGREE FIELD, and flagged.
   V2 drops the topology field on the claim that the motif and hierarchy fields
   already determine the wiring, hence d. If that claim holds, d is known to the
   decoder before this field is read and charging log2(n+1) again would be
   double-counting. It is NOT verified here, and it cannot be: dMotif and
   dHierarchy below are numbers LOOKED UP from the network association, not
   lengths emitted by any codec in this repository, so D_v2 has no decodability
   proof at all. Raised as AUDIT03/R3.3 blast-radius item; do not quote D_v2 as a
   description length until a codec exists for those two fields. *)
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

