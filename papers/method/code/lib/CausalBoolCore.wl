(* CausalBoolCore.wl
   Standalone gate dispatch and repertoire utilities
   for the CausalBool method paper companion code.

   Compatible with Mathematica 12+ and Wolfram Engine 13+.
   No external packages required. *)

(* ── Gate dispatch ─────────────────────────────────────────────────────────── *)
(*
   ApplyGate[gate, inputs, params] evaluates a Boolean gate on a list of 0/1
   inputs and returns a 0/1 output.  Supported gates:
     AND  OR  XOR  NAND  NOR  XNOR  NOT  IMPLIES  NIMPLIES  MAJORITY  KOFN
   KOFN requires params = <|"k" -> integer|>.
   IMPLIES and NIMPLIES are binary (inputs[[1]] -> inputs[[2]] semantics).
*)

ApplyGate[gate_String, inputs_List, params_: <||>] := Which[
  gate === "AND",      If[Count[inputs, 0] == 0, 1, 0],
  gate === "OR",       If[Count[inputs, 1] > 0, 1, 0],
  gate === "XOR",      Mod[Total[inputs], 2],
  gate === "NAND",     If[Count[inputs, 0] > 0, 1, 0],
  gate === "NOR",      If[Count[inputs, 1] == 0, 1, 0],
  gate === "XNOR",     1 - Mod[Total[inputs], 2],
  gate === "NOT",      1 - First[inputs],
  gate === "IMPLIES",  If[inputs[[1]] == 0 || inputs[[2]] == 1, 1, 0],
  gate === "NIMPLIES", If[inputs[[1]] == 1 && inputs[[2]] == 0, 1, 0],
  gate === "MAJORITY", If[Count[inputs, 1] > Floor[Length[inputs] / 2], 1, 0],
  gate === "KOFN",     If[Count[inputs, 1] >= Lookup[params, "k", 1], 1, 0],
  True, 0
];

(* ── Exhaustive repertoire ─────────────────────────────────────────────────── *)
(*
   CreateRepertoiresDispatch[cm, dynamic, params] builds the full 2^n repertoire
   for a synchronous Boolean network.

   Arguments:
     cm       - n×n adjacency matrix (1-based; cm[[i,j]]=1 iff j -> i)
     dynamic  - length-n list of gate-type strings
     params   - optional Association of node-specific parameters (e.g. KOFN k)

   Returns:
     <|"RepertoireInputs"  -> list of 2^n LSB-first input vectors,
       "RepertoireOutputs" -> corresponding output vectors|>

   Input vectors are enumerated with the convention
   input[[1]] = bit 0 (LSB), input[[n]] = bit n-1 (MSB),
   matching the index-set ordering used throughout the paper.
*)

CreateRepertoiresDispatch[cm_List, dynamic_List, params_: <||>] := Module[
  {n, inputs, outputs},
  n = Length[dynamic];
  inputs = Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, 2^n - 1}];
  outputs = Table[
    Table[
      ApplyGate[
        dynamic[[node]],
        input[[Sort[Flatten[Position[cm[[node]], 1]]]]],
        Lookup[params, node, <||>]
      ],
      {node, 1, n}
    ],
    {input, inputs}
  ];
  <|"RepertoireInputs" -> inputs, "RepertoireOutputs" -> outputs|>
];
