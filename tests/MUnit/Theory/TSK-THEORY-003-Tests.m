Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results","tests","theory003"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories->True]];

(* AUDIT03 — delegated to the single owner, Integration`BioMetrics`.
   C_formula had FIVE definition sites, all local to tests/, and they had
   drifted: TSK-EXPER-004's copy lacked KOFN and CANALISING branches, so 20 of
   72 (gate, d) cells disagreed with the other four. C_formula = 23 on the
   flagship is a published number, so it gets one home. *)
(* AUDIT03 fix: the C_formula delegation added here in 019ff70 had no Get for
   BioMetrics.m, so Integration`BioMetrics`ComputeFormulaComponents stayed
   unevaluated and this file exported no status at all. The suite still
   reported it green because the runner read a STALE Status.txt from an
   earlier run -- fixed in run-tests.sh, which now clears the status first. *)
Get["src/Packages/Integration/BioMetrics.m"];
compressionWeight[gate_, Ic_List, params_Association:<||>] :=
  Integration`BioMetrics`FormulaComponentWeight[gate, Ic, params];
computeCompression[cm_List, dyn_List, params_Association:<||>] :=
  Integration`BioMetrics`ComputeFormulaComponents[cm, dyn, params];

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
