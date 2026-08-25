(* ::Package:: *)
(* AUDIT01/T4.1 AC-4.1c negative-control probe: unsupported gates fed to the LEGACY
   dispatch must now produce an explicit Failure["UnsupportedGate", ...] + message,
   never a silently stale resOp. Positive control: supported gates unchanged. *)

Get["src/integration/Alpha.m"];

failures = {};
checkName[n_] := AppendTo[failures, n];

(* Negative controls: NOR/XOR-in-MIXED unsupported by legacy dispatch *)
res1 = runDynamic[{{0,1},{1,0}}, {"AND","NOR"}];
If[!MemberQ[Level[res1["RepertoireOutputs"], {2}], Failure["UnsupportedGate", _]], checkName["runDynamic NOR silent"]];
res2 = createRepertoires[{{0,1},{1,0}}, {"XOR","NOR"}];
If[!MemberQ[Level[res2["RepertoireOutputs"], {2}], Failure["UnsupportedGate", _]], checkName["createRepertoires NOR silent"]];
res3 = calculateOneOutptuOfNetwork[{1,0,1}, {{0,1,0},{1,0,1},{0,1,0}}, {"AND","IMPLIES","OR"}];
If[!MemberQ[res3["Output"], Failure["UnsupportedGate", _]], checkName["calculateOneOutptuOfNetwork IMPLIES silent"]];

(* Positive controls: supported gates behave exactly as before - cross-checked
   against the PACKAGED dispatch / packaged ApplyGate with PROGRAMMATICALLY derived
   references (same LSB row order, identical gate semantics). No hand-computed
   constants (two earlier hand-built references were themselves wrong - U8 lesson). *)
AppendTo[$Path, "src/Packages"];
Needs["Integration`Experiments`"];
pos1 = runDynamic[{{0, 1}, {1, 0}}, {"AND", "XOR"}];
ref1 = Integration`Experiments`CreateRepertoiresDispatch[{{0, 1}, {1, 0}}, {"AND", "XOR"}];
If[Normal[pos1["RepertoireOutputs"]] =!= Normal[ref1["RepertoireOutputs"]],
   checkName["runDynamic AND/XOR differs from packaged dispatch"]];
pos2 = createRepertoires[{{0, 1}, {1, 0}}, {"AND", "XOR"}];
If[pos2["RepertoireInputs"] =!= ref1["RepertoireInputs"] ||
   Normal[pos2["RepertoireOutputs"]] =!= Normal[ref1["RepertoireOutputs"]],
   checkName["createRepertoires AND/XOR differs from packaged dispatch"]];
pos3 = calculateOneOutptuOfNetwork[{1, 0, 1}, {{0, 1, 0}, {1, 0, 1}, {0, 1, 0}}, {"AND", "MAJORITY", "OR"}];
cmP = {{0, 1, 0}, {1, 0, 1}, {0, 1, 0}};
gatesP = {"AND", "MAJORITY", "OR"};
bitsP = Table[Part[{1, 0, 1}, Sort@Flatten@Position[cmP[[j]], 1]], {j, 3}];
refRow = MapThread[Integration`Gates`ApplyGate, {gatesP, bitsP}];
If[pos3["Output"] =!= refRow,
   checkName["calculateOneOutptuOfNetwork single-row differs from packaged ApplyGate: got " <> ToString[pos3["Output"]] <> " expected " <> ToString[refRow]]];

base = FileNameJoin[{"results", "tests", "t41_resop_guard_probe"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
Export[FileNameJoin[{base, "probe_results.json"}],
  <|"executedAt" -> DateString[],
    "negativeControlsRaisedFailure" -> Length[failures] == 0,
    "silentCases" -> failures|>, "JSON"];
If[failures =!= {},
  Print["T41 RESOP PROBE FAILED: ", failures]; Exit[1],
  Print["T41 RESOP PROBE OK: all unsupported-gate cases raise Failure[UnsupportedGate]; supported gates byte-identical"]]
