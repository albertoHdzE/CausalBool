BeginPackage["Integration`Alpha`"]
CreateRepertoires::usage = "Create input and output repertoires for a Boolean network";
RunDynamic::usage = "Run one-step update over full repertoires for a network";
Begin["`Private`"]
Get["src/integration/Alpha.m"]
CreateRepertoires[cm_, dynamic_] := createRepertoires[cm, dynamic]
RunDynamic[cm_, dynamic_] := runDynamic[cm, dynamic]
End[]
EndPackage[]