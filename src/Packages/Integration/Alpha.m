BeginPackage["Integration`Alpha`"]
CreateRepertoires::usage = "Create input and output repertoires for a Boolean network";
RunDynamic::usage = "Run one-step update over full repertoires for a network";
Begin["`Private`"]
Get["src/integration/Alpha.m"]
(* AUDIT02/P4a: createRepertoireByResult now delegates gate semantics to
   Integration`Gates`ApplyGate instead of re-encoding truth tables inline, so
   Gates.m must be present on this path too. Experiments.m already loads it the
   same way (Experiments.m:7); Gates.m carries its own BeginPackage, so its
   symbols land in Integration`Gates` regardless of this Private block. *)
Get["src/Packages/Integration/Gates.m"]
CreateRepertoires[cm_, dynamic_] := createRepertoires[cm, dynamic]
RunDynamic[cm_, dynamic_] := runDynamic[cm, dynamic]
End[]
EndPackage[]