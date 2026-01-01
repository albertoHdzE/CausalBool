Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];
patternSymbol[col_List] := Module[{z, o}, z = Count[col, 0]; o = Count[col, 1]; If[z == Length[col], 0, If[o == Length[col], 1, "*"]]];
predictPattern[gate_String, deg_Integer, params_Association: <||>] := Which[
  gate === "AND" || gate === "OR", "*",
  gate === "XOR" || gate === "XNOR", "*",
  gate === "KOFN", Which[Lookup[params, "k", 1] == 0, 1, Lookup[params, "k", 1] > deg, 0, True, "*"],
  True, "*"
];
base = FileNameJoin[{"results", "tests", "pattern003"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
cmFull = {{1,1},{1,1}};
(* Case 1: XOR/XNOR parity and equivalence *)
dyn1 = {"XOR","XNOR"};
rep1 = Integration`Experiments`CreateRepertoiresDispatch[cmFull, dyn1]["RepertoireOutputs"];
pat1 = patternSymbol /@ Transpose[rep1];
pred1 = {predictPattern["XOR", 2], predictPattern["XNOR", 2]};
ok1 = (pat1 === pred1);
(* Case 2: Monotone AND/OR *)
dyn2 = {"AND","OR"};
rep2 = Integration`Experiments`CreateRepertoiresDispatch[cmFull, dyn2]["RepertoireOutputs"];
pat2 = patternSymbol /@ Transpose[rep2];
pred2 = {predictPattern["AND", 2], predictPattern["OR", 2]};
ok2 = (pat2 === pred2);
(* Case 3: Threshold extremes KOFN *)
params3 = <|1 -> <|"k" -> 0|>, 2 -> <|"k" -> 3|>|>;
dyn3 = {"KOFN","KOFN"};
rep3 = Integration`Experiments`CreateRepertoiresDispatch[cmFull, dyn3, params3]["RepertoireOutputs"];
pat3 = patternSymbol /@ Transpose[rep3];
pred3 = {predictPattern["KOFN", 2, <|"k"->0|>], predictPattern["KOFN", 2, <|"k"->3|>]};
ok3 = (pat3 === pred3);
status = If[And@@{ok1, ok2, ok3}, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "Patterns.json"}], <|"parity_equiv"-><|"emp"->pat1, "pred"->pred1|>, "monotone"-><|"emp"->pat2, "pred"->pred2|>, "kofn_ext"-><|"emp"->pat3, "pred"->pred3|>|>, "JSON"];
Association["Status"->status, "ResultsPath"->base]
