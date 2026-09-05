(* ::Package:: *)

(* Test Script for TSK-NATURE-LEV3-SETUP-002 *)
(* Verifies BioBridge_v2.m and UniversalDv2 function *)

currentDir = DirectoryName[$InputFileName];
projectRoot = FileNameJoin[{currentDir, "..", ".."}];
srcDir = FileNameJoin[{projectRoot, "src", "integration"}];

(* Add src to path if needed or just load by file *)
Get[FileNameJoin[{srcDir, "BioBridge_v2.m"}]];

Print["------------------------------------------------"];
Print["   Test: BioBridge_v2 Integration"];
Print["------------------------------------------------"];

(* 1. Basic Verification *)
If[Integration`BioBridgeV2`VerifyBridge[],
    Print[">> Bridge Self-Test: PASSED"],
    Print[">> Bridge Self-Test: FAILED"];
    Exit[1];
];

(* 2. Test with specific matrix *)
adj = {{0, 1, 0, 0}, {1, 0, 1, 0}, {0, 1, 0, 1}, {0, 0, 1, 0}}; (* Simple Line Graph *)
res = Integration`BioBridgeV2`UniversalDv2[adj];

lineGraphOK = AssociationQ[res] && KeyExistsQ[res, "dv2"];
If[lineGraphOK,
    Print[">> Compute Line Graph: PASSED. D_v2 = ", res["dv2"]],
    Print[">> Compute Line Graph: FAILED."]];

(* AUDIT03-B. This file had a real verdict and NO STATUS EXPORT, so the runner
   could not score it -- and it sits outside tests/MUnit, so the manifest guard
   could not see it either. It has therefore never run in any suite. Both are
   fixed: it exports the verdict it already computes, and it is declared in
   tests/MUnit/MANIFEST.tsv. *)
statusBase = FileNameJoin[{"results", "tests", "nature_lev3_setup"}];
If[!DirectoryQ[statusBase],
   CreateDirectory[statusBase, CreateIntermediateDirectories -> True]];
Export[FileNameJoin[{statusBase, "Status.txt"}],
       {If[TrueQ[lineGraphOK], "OK", "FAIL"], DateString[]}, "Text"];

Print["------------------------------------------------"];
Print[If[TrueQ[lineGraphOK], "   ALL TESTS PASSED", "   FAILED"]];
Print["------------------------------------------------"];
If[!TrueQ[lineGraphOK], Exit[1]];
