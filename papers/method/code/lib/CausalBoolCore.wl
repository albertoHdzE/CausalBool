(* CausalBoolCore.wl
   Standalone gate dispatch and repertoire utilities
   for the CausalBool method paper companion code.

   Compatible with Mathematica 12+ and Wolfram Engine 13+.
   No external packages required. *)

(* ── Index-set utilities ───────────────────────────────────────────────────────

   AUDIT03/R2a.2 (2026-09-04). weights, allOffsets and givePlaces were defined
   independently in THREE producer scripts. They were functionally identical --
   verified in the kernel over n = 1..6 with every connected subset, 126 of 126
   cases agreeing (audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl) -- but
   textually divergent: corroboration_6node.wl lacked the empty-ws guard the
   other two carried. Wolfram's Dot[{},{}] is 0, so that guard is cosmetic.
   Collapsed here to one owner and guarded by tools/check_single_engine.sh, so a
   second definition site cannot reappear silently.

   CAUTION -- allOffsets computes the SPECIAL CASE, not the definition of Omega.
   It returns the subset sums of the DISCONNECTED coordinates' bit weights.
   Those are the don't-cares free in EVERY schema of a node, so they are always
   present -- but Omega is NOT defined by them. Sumandos are the fillings of a
   SCHEMA'S OWN don't-care positions, wherever they fall, INCLUDING on connected
   inputs. Rule 110 is the witness: three inputs, all connected, yet it
   decomposes as 01*, 10*, *10. See GOVERNANCE/GLOSSARY.md section 1d. Reading
   this function as the definition is how that error was re-adopted four times. *)

weights[n_Integer] := 2^Range[0, n - 1];

allOffsets[n_Integer, connected_List] := Module[
  {free = Complement[Range[n], connected], ws},
  ws = weights[n][[free]];
  If[Length[ws] == 0, {0}, Sort[(# . ws) & /@ Tuples[{0, 1}, Length[ws]]]]
];

givePlaces[locations_List, sumandos_List] :=
  Sort@Flatten[Table[loc + sumandos, {loc, locations}]];

(* ── The 6-node flagship's COMPOSED update ─────────────────────────────────────

   AUDIT03. This was defined identically in two producer scripts
   (corroboration_6node.wl and ordering_invariance_6node.wl) and could drift
   between them, so it gets one owner. It is named for what it is.

   CAUTION -- THIS IS NOT THE SYNCHRONOUS UPDATE AND MUST NOT BE REPLACED BY
   CreateRepertoiresDispatch. Node 6 is XOR over its connected inputs {1,3,5},
   and this function feeds it the NEWLY COMPUTED y5 rather than the input x5.
   That is the declared composed reading (convention D-2d), and it is the
   quantity the flagship's "6-node flagship XOR (composed)" check verifies.

   Measured, so the difference is on record rather than rediscovered: against
   CreateRepertoiresDispatch[cm06, dyn06] on the same network, nodes 1-5 agree
   on all 64 rows and node 6 differs on exactly 32 of 64 -- and the hand form
   equals Mod[x1 + x3 + y5, 2] while the dispatch equals Mod[x1 + x3 + x5, 2].
   Collapsing the two would silently change the flagship by half its rows. *)

composedUpdate6Node[input_List] := Module[
  {y1, y2, y3, y4, y5, y6},
  y1 = input[[1]];
  y2 = Boole[input[[2]] == 0];
  y3 = input[[3]];
  y4 = Boole[input[[1]] == 0 || input[[4]] == 1];
  y5 = Boole[input[[2]] == 1 && input[[4]] == 1];
  y6 = Mod[input[[1]] + input[[3]] + y5, 2];   (* NEW y5, not input[[5]] *)
  {y1, y2, y3, y4, y5, y6}
];

(* ── Gate dispatch ─────────────────────────────────────────────────────────── *)
(*
   ApplyGate[gate, inputs, params] evaluates a Boolean gate on a list of 0/1
   inputs and returns a 0/1 output.  Supported gates (all TWELVE families of
   Integration`Gates`ApplyGate):
     AND  OR  XOR  NAND  NOR  XNOR  NOT  IMPLIES  NIMPLIES  MAJORITY  KOFN
     CANALISING
   KOFN requires params = <|"k" -> integer|>, and honours <|"strict" -> True|>
   (Count > k) as the engine does; the default False keeps the historical
   >= behaviour of every existing caller.
   MAJORITY honours <|"tiePolicy" -> "strict" | "atOrAbove"|>; the default
   "strict" is declared convention D-3 (ties -> 0).
   CANALISING requires canalisingIndex / canalisingValue / canalisedOutput; note
   the NON-canalised branch is Or over the inputs, NOT a constant default.
   IMPLIES and NIMPLIES are binary (inputs[[1]] -> inputs[[2]] semantics).

   AUDIT02/P1: before this revision the file implemented ELEVEN families --
   CANALISING was absent and fell through to the "True, 0" default, so a
   CANALISING node evaluated SILENTLY to 0 rather than erroring, and KOFN/
   MAJORITY ignored their parameters (the pre-T4.7 behaviour). Readers
   reproducing the paper from this file therefore reproduced a reduced engine.
   Semantics below are transcribed from src/Packages/Integration/Gates.m:8-35.
*)

ApplyGate::unsupportedgate = "AUDIT02/P1: gate `1` is not one of the twelve supported families; returning Failure[\"UnsupportedGate\"] rather than a silent 0.";

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
  (* AUDIT01/T1.3: ties->0 (strict) is declared convention D-3; AUDIT02/P1 adds
     the "atOrAbove" policy the engine already honours (Gates.m:21-27). *)
  gate === "MAJORITY",
    With[{d = Length[inputs],
          atOrAbove = TrueQ[Lookup[params, "tiePolicy", "strict"] === "atOrAbove"]},
      If[Count[inputs, 1] >= If[atOrAbove, Ceiling[d/2], Floor[d/2] + 1], 1, 0]],
  (* AUDIT02/P1: KOFN now honours "strict" exactly as Gates.m:31-34 does after
     T4.7 (DEV-T4.7-1). Default False preserves the historical >= behaviour. *)
  gate === "KOFN",
    If[TrueQ[Lookup[params, "strict", False]],
      Boole[Count[inputs, 1] > Lookup[params, "k", 1]],
      Boole[Count[inputs, 1] >= Lookup[params, "k", 1]]],
  (* AUDIT02/P1: CANALISING, transcribed from Gates.m:35 (myCanalising). The
     non-canalised branch is Or over the inputs, not a constant default. *)
  gate === "CANALISING",
    With[{i = Lookup[params, "canalisingIndex", 1],
          v = Lookup[params, "canalisingValue", 1],
          out = Lookup[params, "canalisedOutput", 0]},
      If[inputs[[i]] == v, out, If[Count[inputs, 1] > 0, 1, 0]]],
  (* AUDIT02/P1: fail loudly. A silent 0 for an unknown gate is the pattern that
     let CANALISING evaluate to 0 unnoticed; mirrors the T4.1/F24 hardening. *)
  True,
    (Message[ApplyGate::unsupportedgate, gate];
     Failure["UnsupportedGate", <|"Gate" -> gate|>])
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
