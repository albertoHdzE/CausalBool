BeginPackage["Integration`Gates`"]
ApplyGate::usage = "Apply a gate to inputs with optional params";
TruthTable::usage = "Return truth table for gate and arity";
IndexSet::usage = "Return indices (1-based) where gate outputs 1 over ordered exhaustive inputs";
IndexSetNetwork::usage = "Return indices (1-based) where the gate outputs 1 in an n-bit network for connected inputs Ic";
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
myMajority[list_] := If[Count[list, 1] > Count[list, 0], 1, 0]
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
    gate === "MAJORITY", myMajority[inputs],
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
    gate === "KOFN", Module[{k, inputs, cond}, k = Lookup[params, "k", 1]; inputs = Table[IntegerDigits[x, 2, arity], {x, 0, 2^arity - 1}]; cond = If[strict, Count[#, 1] > k &, Count[#, 1] >= k &]; Flatten@Position[cond /@ inputs, True, 1]],
    gate === "CANALISING", Module[{ci, v, out, inputs}, ci = Lookup[params, "canalisingIndex", 1]; v = Lookup[params, "canalisingValue", 1]; out = Lookup[params, "canalisedOutput", 0]; inputs = Table[IntegerDigits[x, 2, arity], {x, 0, 2^arity - 1}]; Flatten@Position[(ApplyGate["CANALISING", #, params] == 1) & /@ inputs, True, 1]],
    True, {}
  ];
  idx
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
    Module[{ci = Lookup[params, "canalisingIndex", If[Length[Ic] >= 1, Ic[[1]], 1]]}, Flatten@Position[(ApplyGate[gate, {#[[ci]]} ~Join~ Part[#, Complement[Ic, {ci}]], params] == 1) & /@ inputs, True, 1]],
    True,
    Flatten@Position[(ApplyGate[gate, Part[#, Ic], params] == 1) & /@ inputs, True, 1]
  ]
]
End[]
EndPackage[]
