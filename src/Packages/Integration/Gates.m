BeginPackage["Integration`Gates`"]
ApplyGate::usage = "Apply a gate to inputs with optional params";
TruthTable::usage = "Return truth table for gate and arity";
IndexSet::usage = "Return indices (1-based) where gate outputs 1 over ordered exhaustive inputs";
IndexSetNetwork::usage = "Return indices (1-based) where the gate outputs 1 in an n-bit network for connected inputs Ic";
IndexSetAnalytic::usage = "IndexSetAnalytic[n, Ic, gate, params_<||>] returns the closed-form one-set (sorted, 1-based, LSB-position weights w(i)=2^(i-1)) of the named gate family acting on connected inputs Ic within an n-coordinate space. Canonical/LSB convention; transport to MSB row order exclusively via Integration`IndexAlgebra`Phi. Covers all twelve families incl. CANALISING.";
Begin["`Private`"]
myAnd[list_] := If[Count[list, 0] == 0, 1, 0]
myOr[list_] := If[Count[list, 1] > 0, 1, 0]
myXor[list_] := Mod[Total[list], 2]
myNand[list_] := If[Count[list, 0] > 0, 1, 0]
myNor[list_] := If[Count[list, 1] == 0, 1, 0]
myXnor[list_] := Mod[Total[list], 2] /. {0 -> 1, 1 -> 0}
myNot[list_] := 1 - First[list]
myImplies[list_] := myOr[{1 - list[[1]], list[[2]]}]
myNImplies[list_] := myAnd[{list[[1]], 1 - list[[2]]}]
(* AUDIT01/T1.3 (D-3): even-arity tie convention is an explicit, declared parameter.
   "strict" (default) -> ties output 0  (threshold Floor[d/2]+1)
   "atOrAbove"        -> ties output 1  (threshold Ceiling[d/2])
   Odd arity: both coincide. Published mixed-10 tables were produced under "strict". *)
myMajority[list_, params_: <||>] := Module[{d, ones, th},
  d = Length[list]; ones = Count[list, 1];
  th = If[TrueQ[Lookup[params, "tiePolicy", "strict"] === "atOrAbove"], Ceiling[d/2], Floor[d/2] + 1];
  If[ones >= th, 1, 0]
]
myKOfN[list_, k_Integer] := If[Count[list, 1] >= k, 1, 0]
myCanalising[list_, params_Association] := Module[{i, v, out}, i = Lookup[params, "canalisingIndex", 1]; v = Lookup[params, "canalisingValue", 1]; out = Lookup[params, "canalisedOutput", 0]; If[list[[i]] == v, out, myOr[list]]]
ApplyGate[gate_String, inputs_List, params_: <||>] := Module[{res, p},
  res = Which[
    gate === "AND", myAnd[inputs],
    gate === "OR", myOr[inputs],
    gate === "XOR", myXor[inputs],
    gate === "NAND", myNand[inputs],
    gate === "NOR", myNor[inputs],
    gate === "XNOR", myXnor[inputs],
    gate === "NOT", myNot[inputs],
    gate === "IMPLIES", myImplies[inputs],
    gate === "NIMPLIES", myNImplies[inputs],
    gate === "MAJORITY", myMajority[inputs, params],
    gate === "KOFN", myKOfN[inputs, Lookup[params, "k", 1]],
    gate === "CANALISING", myCanalising[inputs, params],
    True, 0
  ];
  p = Lookup[params, "noiseFlipProb", None];
  If[NumericQ[p] && p > 0, If[RandomReal[] < p, 1 - res, res], res]
]
TruthTable[gate_String, arity_Integer, params_: <||>] := Module[{inputs, outputs}, inputs = Table[IntegerDigits[x, 2, arity], {x, 0, 2^arity - 1}]; outputs = ApplyGate[gate, #, params] & /@ inputs; Transpose[{inputs, outputs}]]
IndexSet[gate_String, arity_Integer, params_: <||>] := Module[{idx, strict},
  strict = TrueQ[Lookup[params, "strict", False]];
  idx = Which[
    gate === "NOT" && arity == 1, {1},
    gate === "IMPLIES" && arity == 2, {1, 2, 4},
    gate === "NIMPLIES" && arity == 2, {3},
    (* Back-compat: original MSB branches preserved verbatim (CANALISING is not
       position-symmetric, so blind Phi-transport could flip canalisingIndex coords) *)
    gate === "KOFN", Module[{k, inputs, cond}, k = Lookup[params, "k", 1]; inputs = Table[IntegerDigits[x, 2, arity], {x, 0, 2^arity - 1}]; cond = If[strict, Count[#, 1] > k &, Count[#, 1] >= k &]; Flatten@Position[cond /@ inputs, True, 1]],
    gate === "CANALISING", Module[{ci, v, out, inputs}, ci = Lookup[params, "canalisingIndex", 1]; v = Lookup[params, "canalisingValue", 1]; out = Lookup[params, "canalisedOutput", 0]; inputs = Table[IntegerDigits[x, 2, arity], {x, 0, 2^arity - 1}]; Flatten@Position[(ApplyGate["CANALISING", #, params] == 1) & /@ inputs, True, 1]],
    (* AUDIT01/T1.2: previously these seven families fell through to {}; now served
       by the closed-form engine, transported to this function's MSB convention via Phi *)
    True,
    Module[{lsb},
      lsb = indexSetAnalyticCore[arity, Range[arity], gate, params];
      If[lsb === $Failed || lsb === {}, If[lsb === $Failed, {}, Sort[lsb]],
        Sort[PhiIndex[#, arity] & /@ lsb]]
    ]
  ];
  idx
]
(* Private bit-reversal transport, identical to Integration`IndexAlgebra`Phi *)
PhiIndex[j_Integer, n_Integer] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2]

(* ---- Closed-form one-set engine (AUDIT01/T1.2) ------------------------------- *)
(* Port of the thrice-duplicated script-level indexSetAnalytic (canonical sources:
   papers/method/code/mixed_interaction_10node/mixed_interaction_10node.wl,
   papers/method/manuscript_computational/generate_paper_outputs.wl,
   tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m) plus a closed CANALISING
   family the scripts never had. Convention: LSB-position weights w(i)=2^(i-1),
   index = 1 + Sum over on-positions. MAJORITY threshold t=Floor[d/2]+1 (ties->0),
   matching Gates.m myMajority; T1.3 may parameterise. *)
indexSetAnalyticCore[n_Integer, Ic_List, gate_String, params_Association] := Module[
  {free, pow, d, indexFromPos, subsFree, k, strict, pair, a, b, ii, ci, cv, co, assigns, cond},
  free = Complement[Range[n], Ic];
  pow = 2^Range[0, n - 1];
  d = Length[Ic];
  indexFromPos[pos_List] := 1 + Total[pow[[pos]]];
  subsFree = Subsets[free];
  Which[
    gate === "AND",
      Sort[indexFromPos[Join[Ic, #]] & /@ subsFree],
    gate === "OR",
      Sort[Complement[Range[1, 2^n], indexFromPos /@ subsFree]],
    gate === "XOR",
      Module[{},
        assigns = Select[Tuples[{0, 1}, d], Mod[Total[#], 2] == 1 &];
        Sort[Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]]
      ],
    gate === "XNOR",
      Module[{},
        assigns = Select[Tuples[{0, 1}, d], Mod[Total[#], 2] == 0 &];
        Sort[Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]]
      ],
    gate === "NAND",
      Sort[Complement[Range[1, 2^n], indexFromPos[Join[Ic, #]] & /@ subsFree]],
    gate === "NOR",
      Sort[indexFromPos /@ subsFree],
    gate === "NOT",
      ii = Lookup[params, "i", First[Ic]];
      Sort[indexFromPos /@ Subsets[Complement[Range[n], {ii}]]],
    gate === "IMPLIES",
      pair = Lookup[params, "pair", Ic[[;; 2]]];
      a = pair[[1]]; b = pair[[2]];
      Sort[Complement[
        Range[1, 2^n],
        indexFromPos /@ (Join[{a}, #] & /@ Subsets[Complement[Range[n], {a, b}]])
      ]],
    gate === "NIMPLIES",
      pair = Lookup[params, "pair", Ic[[;; 2]]];
      a = pair[[1]]; b = pair[[2]];
      Sort[indexFromPos /@ (Join[{a}, #] & /@ Subsets[Complement[Range[n], {a, b}]])],
    gate === "MAJORITY",
      Module[{t},
        (* AUDIT01/T1.3 D-3: honor tiePolicy identically to myMajority *)
        t = If[TrueQ[Lookup[params, "tiePolicy", "strict"] === "atOrAbove"], Ceiling[d/2], Floor[d/2] + 1];
        assigns = Select[Tuples[{0, 1}, d], Total[#] >= t &];
        Sort[Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]]
      ],
    gate === "KOFN",
      Module[{},
        k = Lookup[params, "k", 1];
        strict = TrueQ[Lookup[params, "strict", False]];
        assigns = Select[Tuples[{0, 1}, d], If[strict, Total[#] > k, Total[#] >= k] &];
        Sort[Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]]
      ],
    gate === "CANALISING",
      Module[{},
        ci = Lookup[params, "canalisingIndex", 1];
        cv = Lookup[params, "canalisingValue", 1];
        co = Lookup[params, "canalisedOutput", 0];
        cond = (If[#1[[ci]] == cv, co == 1, Count[#1, 1] > 0]) &;
        assigns = Select[Tuples[{0, 1}, d], cond];
        Sort[Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]]
      ],
    True,
      $Failed
  ]
];

IndexSetAnalytic[n_Integer, Ic_List, gate_String, params_: <||>] :=
  Module[{res = indexSetAnalyticCore[n, Ic, gate, params]},
    If[res === $Failed,
      Return[$Failed, Module],
      Sort[res]
    ]
  ]
IndexSetNetwork[gate_String, n_Integer, Ic_List, params_: <||>] := Module[{inputs, pair, i},
  inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
  pair = Lookup[params, "pair", None];
  i = Lookup[params, "i", None];
  Which[
    gate === "IMPLIES" || gate === "NIMPLIES",
    If[pair === None,
      If[Length[Ic] == 2,
        Flatten@Position[(ApplyGate[gate, Part[#, Ic], params] == 1) & /@ inputs, True, 1],
        {}
      ],
      Flatten@Position[(ApplyGate[gate, {#[[pair[[1]]]], #[[pair[[2]]]]}, params] == 1) & /@ inputs, True, 1]
    ],
    gate === "NOT",
    Module[{ii = If[i === None, If[Length[Ic] == 1, Ic[[1]], None], i]}, If[ii === None, {}, Flatten@Position[(ApplyGate[gate, {#[[ii]]}, params] == 1) & /@ inputs, True, 1]]],
    gate === "CANALISING",
    (* AUDIT01/T4.1 (F36 closure): params are Ic-relative here, identical to
       ApplyGate/myCanalising and the closed-form engine (GOVERNANCE/ORDERING.md).
       The previous branch reordered the row to place the canalising bit first while
       passing the original canalisingIndex through - correct only when that value
       happened to be position 1 of Ic. Callers holding network-absolute indices
       translate once at their boundary (First@Position[Ic, ciAbs]). *)
    Flatten@Position[(ApplyGate[gate, Part[#, Ic], params] == 1) & /@ inputs, True, 1],
    True,
    Flatten@Position[(ApplyGate[gate, Part[#, Ic], params] == 1) & /@ inputs, True, 1]
  ]
]
End[]
EndPackage[]
