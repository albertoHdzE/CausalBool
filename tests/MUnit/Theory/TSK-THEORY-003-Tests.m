Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results","tests","theory003"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories->True]];

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

(* Decomposition across cuts: block diagonal cm *)
cmA = {{0,1,0,0},{1,0,0,0},{0,0,0,1},{0,0,1,0}};
dynA = {"AND","OR","XOR","NAND"};
paramsA = <||>;
Ca = computeCompression[cmA, dynA, paramsA];
(* Split into blocks *)
cm1 = {{0,1},{1,0}}; dyn1 = {"AND","OR"};
cm2 = {{0,1},{1,0}}; dyn2 = {"XOR","NAND"};
C1 = computeCompression[cm1, dyn1, <||>];
C2 = computeCompression[cm2, dyn2, <||>];
okFactorise = (Ca == C1 + C2);

(* Canalising collapse effect *)
cmB = {{0,1,0},{1,0,1},{0,1,0}}; dynB = {"AND","CANALISING","OR"};
paramsB = <|2 -> <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 1|>|>;
Cb = computeCompression[cmB, dynB, <||>];
CbCan = computeCompression[cmB, dynB, paramsB];
okCollapse = (CbCan <= Cb);

metrics = <|"C_all"->Ca, "C_block1"->C1, "C_block2"->C2, "okFactorise"->okFactorise, "C_b"->Cb, "C_bCan"->CbCan, "okCollapse"->okCollapse|>;
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
status = If[And[okFactorise, okCollapse], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], status, "Text"];
