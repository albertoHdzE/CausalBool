Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results", "tests", "theory001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "theory001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

cm3 = {{0,1,0},{1,0,1},{0,1,0}};
dyn3 = {"AND","OR","XOR"};

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
