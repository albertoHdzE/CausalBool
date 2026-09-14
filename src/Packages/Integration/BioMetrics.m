BeginPackage["Integration`BioMetrics`"]
ComputeDescriptionLength::usage = "ComputeDescriptionLength[net] or [cm, dyn, params] returns description length D for a Boolean network";
ComputeFormulaComponents::usage = "ComputeFormulaComponents[cm, dyn, params] returns C_formula, the count of symbolic pieces in the closed-form index-set description of a network; FormulaComponentWeight[gate, Ic, params] is the per-node count";
FormulaComponentWeight::usage = "FormulaComponentWeight[gate, Ic, params] counts the symbolic pieces in one node's closed-form index-set formula";
ComputeDescriptionLengthV2::usage = "ComputeDescriptionLengthV2[net] returns structural description length D_v2 (requires motifs/hierarchy data)";
Begin["`Private`"]

(* AUDIT03 — C_formula, the symbolic component count.

   This had FIVE definition sites, all in tests/, and they had DRIFTED. Four
   were identical; TSK-EXPER-004-SubsystemSearch.m carried an older form with
   no KOFN and no CANALISING branch and a two-argument signature, so those
   gates fell through to the "1 + d" default. Measured in the kernel over the
   twelve families at d = 1..6: 20 of 72 cells disagree -- IMPLIES and NIMPLIES
   at every d except 2, KOFN and CANALISING at every d except 1.

   The drift went unnoticed because TSK-EXPER-004 is one of 23 MUnit files that
   the runner never executes: it globs "*Tests.m", and that name does not match.

   C_formula = 23 on the flagship is a PUBLISHED number, so this is the owner
   and everything else calls it. *)

FormulaComponentWeight[gate_String, Ic_List, params_Association : <||>] :=
  Module[{d = Length[Ic]},
    Switch[gate,
      "AND" | "OR" | "NAND" | "NOR", 1 + d,
      "XOR" | "XNOR", 1 + 1,
      "NOT", 1,
      "IMPLIES" | "NIMPLIES", 1 + 2,
      "MAJORITY", 1 + 1,
      "KOFN", 1 + 1,
      "CANALISING", 1 + If[KeyExistsQ[params, "canalisedOutput"], 0, 1],
      _, 1 + d
    ]];

ComputeFormulaComponents[cm_List, dynamic_List, params_Association : <||>] :=
  Module[{n = Length[dynamic], ics},
    ics = Table[Flatten@Position[cm[[i]], 1], {i, n}];
    Total@Table[
      FormulaComponentWeight[dynamic[[i]], ics[[i]], Lookup[params, i, <||>]],
      {i, n}]];
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

(* AUDIT03-B — the IMPLIES/NIMPLIES field, and why it is NOT being changed.

   log2(d(d-1)) charges for an ORDERED pair. The engine cannot express one:
   every caller hands ApplyGate the connected inputs already SORTED
   (input[[Sort[Flatten[Position[cm[[node]], 1]]]]]) and the semantics read
   inputs[[1]] -> inputs[[2]], so the antecedent is ALWAYS the lower-indexed
   node. Measured at n = 4: 6 wirings, 6 distinct behaviours, 12 ordered pairs
   priced, and all 6 swapped behaviours unreachable. Half the messages the code
   prices name behaviours the engine cannot produce.

   The cost consequence is ZERO, everywhere, and this was measured rather than
   assumed. IMPLIES is binary, so d = 2 always and log2(d(d-1)) = log2 2 = 1 --
   identical to the default branch every other gate pays. The 10-node flagship
   is 135.66005 bits with the field and 135.66005 without; the Kraft sum over
   expressible node-codes is 0.2815 either way; and the bio corpus contains
   ZERO IMPLIES/NIMPLIES nodes (2,486 CUSTOM, 762 IDENTITY, 538 CANALISING,
   327 AND, 280 OR, 151 INPUT, 53 NOT, 26 NOR, 3 NAND).

   So the expression stays as published. What is added is the assertion that
   makes the unreachable case loud instead of silently paying a phantom field:
   an IMPLIES node with d != 2 is a wiring error, not a costing question. *)

ComputeDescriptionLength::impliesarity = "AUDIT03-B: `1` node has in-degree `2`, but IMPLIES/NIMPLIES are binary and the engine reads inputs[[1]] -> inputs[[2]] over the SORTED connected set. Refusing to price a gate the dispatcher cannot evaluate.";

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
    "IMPLIES" | "NIMPLIES",
      (If[d =!= 2, Message[ComputeDescriptionLength::impliesarity, gate, d]];
       log2Int[Max[1, d (d - 1)]]),
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
    "IMPLIES" | "NIMPLIES",
      (If[d =!= 2, Message[ComputeDescriptionLength::impliesarity, gate, d]];
       log2Int[Max[1, d (d - 1)]]),
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

