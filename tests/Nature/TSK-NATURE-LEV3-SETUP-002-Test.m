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

If[AssociationQ[res] && KeyExistsQ[res, "dv2"],
    Print[">> Compute Line Graph: PASSED. D_v2 = ", res["dv2"]],
    Print[">> Compute Line Graph: FAILED."];
    Exit[1];
];

Print["------------------------------------------------"];
Print["   ALL TESTS PASSED"];
Print["------------------------------------------------"];
