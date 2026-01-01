Get["src/Packages/Integration/Experiments.m"];
base = FileNameJoin[{"results", "tests", "mixed001"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
ok = True;
(* Simple level: 3-node mixed AND/OR/XOR; compare dispatch repertoires vs one-step dispatch run *)
cm1 = {{0,1,0},{1,0,1},{0,1,0}};
dyn1 = {"AND","OR","XOR"};
rep1 = Integration`Experiments`CreateRepertoiresDispatch[cm1, dyn1]["RepertoireOutputs"];
run1 = Integration`Experiments`RunDynamicDispatch[cm1, dyn1]["RepertoireOutputs"];
ok1 = (rep1 === run1);
Export[FileNameJoin[{base, "Example1.json"}], <|"cm"->cm1, "dynamic"->dyn1, "repEqRun"->ok1|>, "JSON"];
ok = ok && ok1;
(* Medium level: 3-node NAND/MAJORITY/OR; compare dispatch repertoires vs one-step dispatch run *)
cm2 = {{0,1,1},{1,0,0},{0,1,0}};
dyn2 = {"NAND","MAJORITY","OR"};
rep2 = Integration`Experiments`CreateRepertoiresDispatch[cm2, dyn2]["RepertoireOutputs"];
run2 = Integration`Experiments`RunDynamicDispatch[cm2, dyn2]["RepertoireOutputs"];
ok2 = (rep2 === run2);
Export[FileNameJoin[{base, "Example2.json"}], <|"cm"->cm2, "dynamic"->dyn2, "repEqRun"->ok2|>, "JSON"];
ok = ok && ok2;
(* Complex level: full catalogue mix IMPLIES/KOFN/CANALISING/NOT over 4 nodes; verify dispatch equals RunDynamicDispatch *)
cm3 = {{0,1,1,0},{1,0,1,1},{1,1,0,0},{1,0,0,0}}; (* Node1: inputs {2,3}; Node2: {1,3,4}; Node3: {1,2}; Node4: {1} *)
dyn3 = {"IMPLIES","KOFN","CANALISING","NOT"};
params3 = <|2 -> <|"k"->2|>, 3 -> <|"canalisingIndex" -> 1, "canalisingValue" -> 1, "canalisedOutput" -> 1|>|>;
rep3 = Integration`Experiments`CreateRepertoiresDispatch[cm3, dyn3, params3]["RepertoireOutputs"];
run3 = Integration`Experiments`RunDynamicDispatch[cm3, dyn3, params3]["RepertoireOutputs"];
ok3 = (rep3 === run3);
Export[FileNameJoin[{base, "Example3.json"}], <|"cm"->cm3, "dynamic"->dyn3, "params"-> Association@KeyValueMap[ToString[#1]->#2&, params3], "repEqRun"->ok3|>, "JSON"];
ok = ok && ok3;

(* Extended coverage: 5-node mix including NOR, XNOR, NIMPLIES, MAJORITY, KOFN *)
cm4 = {{0,1,1,0,0},{1,0,0,1,0},{0,1,0,1,1},{1,0,1,0,0},{0,0,1,1,0}};
dyn4 = {"NOR","XNOR","NIMPLIES","MAJORITY","KOFN"};
params4 = <|5 -> <|"k"->2|>|>;
rep4 = Integration`Experiments`CreateRepertoiresDispatch[cm4, dyn4, params4]["RepertoireOutputs"];
run4 = Integration`Experiments`RunDynamicDispatch[cm4, dyn4, params4]["RepertoireOutputs"];
ok4 = (rep4 === run4);
Export[FileNameJoin[{base, "Example4.json"}], <|"cm"->cm4, "dynamic"->dyn4, "params"-> Association@KeyValueMap[ToString[#1]->#2&, params4], "repEqRun"->ok4|>, "JSON"];
ok = ok && ok4;

(* Complex+ level: 10-node mixed set with distinct gates (AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES, KOFN) *)
cm5 = {
  {0,1,1,1,0,0,0,0,0,0}, (* 1 <- {2,3,4} *)
  {1,0,1,0,0,0,0,0,0,0}, (* 2 <- {1,3} *)
  {0,0,0,1,1,0,0,0,0,0}, (* 3 <- {4,5} *)
  {0,1,1,0,1,0,0,0,0,0}, (* 4 <- {2,3,5} *)
  {0,0,0,0,0,1,0,0,0,0}, (* 5 <- {6} *)
  {0,0,0,0,1,0,1,0,0,0}, (* 6 <- {5,7} *)
  {0,0,0,0,0,1,0,0,0,0}, (* 7 <- {6} *)
  {1,0,0,0,0,0,0,0,1,0}, (* 8 <- {1,9} *)
  {0,1,0,0,0,0,0,0,0,1}, (* 9 <- {2,10} *)
  {0,0,1,1,0,0,1,1,0,0}  (* 10 <- {3,4,7,8} *)
};
dyn5 = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","KOFN"};
params5 = <|10 -> <|"k"->2|>|>;
rep5 = Integration`Experiments`CreateRepertoiresDispatch[cm5, dyn5, params5]["RepertoireOutputs"];
run5 = Integration`Experiments`RunDynamicDispatch[cm5, dyn5, params5]["RepertoireOutputs"];
ok5 = (rep5 === run5);
Export[FileNameJoin[{base, "Example5.json"}], <|"cm"->cm5, "dynamic"->dyn5, "params"-> Association@KeyValueMap[ToString[#1]->#2&, params5], "repEqRun"->ok5|>, "JSON"];
ok = ok && ok5;

(* Comprehensive variant: 10-node mixed including MAJORITY and CANALISING among catalogue *)
cm6 = {
  {0,1,0,1,0,0,0,0,0,0}, (* 1 <- {2,4} AND *)
  {1,0,1,0,0,0,0,0,0,0}, (* 2 <- {1,3} OR *)
  {0,0,0,1,1,0,0,0,0,0}, (* 3 <- {4,5} XOR *)
  {0,1,1,0,1,0,0,0,0,0}, (* 4 <- {2,3,5} NAND *)
  {0,0,0,0,0,1,0,0,0,0}, (* 5 <- {6} NOR *)
  {0,0,0,0,1,0,1,0,0,0}, (* 6 <- {5,7} XNOR *)
  {0,0,0,0,0,1,0,0,0,0}, (* 7 <- {6} NOT *)
  {1,0,0,0,0,0,0,0,1,0}, (* 8 <- {1,9} IMPLIES *)
  {0,1,0,0,0,0,0,0,0,1}, (* 9 <- {2,10} NIMPLIES *)
  {0,0,1,1,0,0,1,1,0,0}  (* 10 <- {3,4,7,8} MAJORITY *)
};
dyn6 = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY"};
params6 = <||>;
rep6 = Integration`Experiments`CreateRepertoiresDispatch[cm6, dyn6, params6]["RepertoireOutputs"];
run6 = Integration`Experiments`RunDynamicDispatch[cm6, dyn6, params6]["RepertoireOutputs"];
ok6 = (rep6 === run6);
Export[FileNameJoin[{base, "Example6.json"}], <|"cm"->cm6, "dynamic"->dyn6, "repEqRun"->ok6|>, "JSON"];
ok = ok && ok6;
status = If[ok, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "ResultsPath" -> base]
