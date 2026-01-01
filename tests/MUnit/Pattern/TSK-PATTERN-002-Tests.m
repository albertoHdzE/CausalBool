Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];
patternSymbol[col_List] := Module[{z, o}, z = Count[col, 0]; o = Count[col, 1]; If[z == Length[col], 0, If[o == Length[col], 1, "*"]]];
base = FileNameJoin[{"results", "tests", "pattern002"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
(* Monotone gates over exhaustive inputs typically yield * unless extreme cases *)
cm2 = {{1,1},{1,1}};
dynAND = {"AND","AND"};
dynOR = {"OR","OR"};
repAND = Integration`Experiments`CreateRepertoiresDispatch[cm2, dynAND]["RepertoireOutputs"];
repOR = Integration`Experiments`CreateRepertoiresDispatch[cm2, dynOR]["RepertoireOutputs"];
patAND = patternSymbol /@ Transpose[repAND];
patOR = patternSymbol /@ Transpose[repOR];
okMonotone = (patAND === {"*","*"} && patOR === {"*","*"});
(* XOR/XNOR parity/equivalence produce * across exhaustive inputs *)
dynXOR = {"XOR","XOR"};
dynXNOR = {"XNOR","XNOR"};
repXOR = Integration`Experiments`CreateRepertoiresDispatch[cm2, dynXOR]["RepertoireOutputs"];
repXNOR = Integration`Experiments`CreateRepertoiresDispatch[cm2, dynXNOR]["RepertoireOutputs"];
patXOR = patternSymbol /@ Transpose[repXOR];
patXNOR = patternSymbol /@ Transpose[repXNOR];
okParity = (patXOR === {"*","*"} && patXNOR === {"*","*"});
(* Threshold extremes: k=0 => constant 1; k>deg => constant 0 *)
paramsKext = <|1 -> <|"k" -> 0|>, 2 -> <|"k" -> 3|>|>;
repKext = Integration`Experiments`CreateRepertoiresDispatch[cm2, {"KOFN","KOFN"}, paramsKext]["RepertoireOutputs"];
patKext = patternSymbol /@ Transpose[repKext];
okKext = (patKext === {1,0});
(* Canalising: if canalising value present, output constant; otherwise falls back to OR here *)
paramsCan = <|1 -> <|"canalisingIndex"->1, "canalisingValue"->1, "canalisedOutput"->0|>, 2 -> <|"canalisingIndex"->1, "canalisingValue"->0, "canalisedOutput"->1|>|>;
repCan = Integration`Experiments`CreateRepertoiresDispatch[cm2, {"CANALISING","CANALISING"}, paramsCan]["RepertoireOutputs"];
patCan = patternSymbol /@ Transpose[repCan];
okCan = (MemberQ[patCan, 0] || MemberQ[patCan, 1]);
status = If[And@@{okMonotone, okParity, okKext, okCan}, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "Patterns.json"}], <|"AND"->patAND, "OR"->patOR, "XOR"->patXOR, "XNOR"->patXNOR, "KOFNext"->patKext, "CANALISING"->patCan|>, "JSON"];
Association["Status"->status, "ResultsPath"->base]
