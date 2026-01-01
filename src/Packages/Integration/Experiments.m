BeginPackage["Integration`Experiments`"]
RunDynamic::usage = "Run one-step update over full repertoires for a network";
RunDynamicDispatch::usage = "Run update using gate dispatch and optional params";
CreateRepertoiresDispatch::usage = "Create repertoires using gate dispatch and optional params";
Begin["`Private`"]
Get["src/integration/Alpha.m"]
Get["src/Packages/Integration/Gates.m"]
RunDynamic[cm_, dynamic_] := runDynamic[cm, dynamic]
CreateRepertoiresDispatch[cm_, dynamic_, params_: <||>] := Module[{noNodes, inputs, outputs}, noNodes = Length[dynamic]; inputs = Table[Reverse[IntegerDigits[x, 2, noNodes]], {x, 0, 2^noNodes - 1}]; outputs = Table[Table[Integration`Gates`ApplyGate[dynamic[[n]], Part[input, Sort[Flatten[Position[cm[[n]], 1]]]], Lookup[params, n, <||>]], {n, 1, noNodes}], {input, inputs}]; <|"RepertoireInputs" -> inputs, "RepertoireOutputs" -> outputs|>]
RunDynamicDispatch[cm_, dynamic_, params_: <||>] := Module[{noNodes, inputs, outputs}, noNodes = Length[dynamic]; inputs = Table[Reverse[IntegerDigits[x, 2, noNodes]], {x, 0, 2^noNodes - 1}]; outputs = Table[Table[Integration`Gates`ApplyGate[dynamic[[n]], Part[input, Sort[Flatten[Position[cm[[n]], 1]]]], Lookup[params, n, <||>]], {n, 1, noNodes}], {input, inputs}]; <|"RepertoireOutputs" -> outputs|>]
End[]
EndPackage[]
