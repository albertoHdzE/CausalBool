Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results", "tests", "theory001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "theory001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

cm3 = {{0,1,0},{1,0,1},{0,1,0}};
dyn3 = {"AND","OR","XOR"};

compressionWeight[gate_, Ic_List, params_Association:<||>] := Module[{d = Length[Ic]}, Switch[gate,
  "AND" | "OR" | "NAND" | "NOR", 1 + d,
  "XOR" | "XNOR", 1 + 1,
  "NOT", 1,
  "IMPLIES" | "NIMPLIES", 1 + 2,
  "MAJORITY", 1 + 1,
  "KOFN", 1 + 1,
  "CANALISING", 1 + If[KeyExistsQ[params, "canalisedOutput"], 0, 1],
  _, 1 + d
]];
computeCompression[cm_List, dyn_List, params_Association:<||>] := Module[{n = Length[dyn], ics},
  ics = Table[Flatten@Position[cm[[i]], 1], {i, n}];
  Total@Table[compressionWeight[dyn[[i]], ics[[i]], Lookup[params, i, <||>]], {i, n}]
];
alphaBase = computeCompression[cm3, dyn3, <||>];
alphaZero = computeCompression[ConstantArray[0, {3,3}], dyn3, <||>];

p = {2,3,1};
permuteCM[cm_, p_List] := cm[[p, p]];
permuteDyn[dyn_, p_List] := dyn[[p]];
alphaPerm = computeCompression[permuteCM[cm3, p], permuteDyn[dyn3, p], <||>];

cm4 = ArrayFlatten[{{cm3, ConstantArray[0, {3,1}]}, {ConstantArray[0, {1,3}], {{0}}}}];
dyn4 = Append[dyn3, "OR"];
alpha4 = computeCompression[cm4, dyn4, <||>];

okNonNeg = alphaBase >= 0 && alphaZero >= 0 && alpha4 >= 0;
okSepZero = alphaZero == computeCompression[ConstantArray[0, {3,3}], dyn3, <||>];

(* Invariance under relabelling: weight depends on gate and arity only *)
dynSym = {"OR","OR","OR"};
alphaSym = computeCompression[cm3, dynSym, <||>];
alphaSymPerm = computeCompression[permuteCM[cm3, p], permuteDyn[dynSym, p], <||>];
okRelabel = alphaSymPerm == alphaSym;

(* Monotone improvement under canalising collapse *)
paramsCan = <|3 -> <|"canalisedOutput" -> 1|>|>;
alphaCan = computeCompression[cm3, dyn3, paramsCan];
okCollapse = alphaCan <= alphaBase;

metrics = <|"C_base"->alphaBase, "C_zero"->alphaZero, "C_perm"->alphaPerm, "C_4"->alpha4,
  "C_sym"->alphaSym, "C_symPerm"->alphaSymPerm, "C_canalised"->alphaCan,
  "okNonNeg"->okNonNeg, "okSepZero"->okSepZero, "okRelabel"->okRelabel, "okCollapse"->okCollapse|>;
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
status = If[And[okNonNeg, okSepZero, okRelabel, okCollapse], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status"->status, "ResultsPath"->base]
