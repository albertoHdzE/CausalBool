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
(* AUDIT03-C. This test used a 4-NODE line graph and asserted only that the
   result had a "dv2" key. Measured: D_v2 is structurally ZERO for every graph
   with n <= 4, because its smallest block is 4x4, so a 4x4 matrix yields
   exactly one block (unique/total = 1/1) and the cost is log2(1) = 0. The test
   was passing on the single degenerate size at which the measure cannot
   discriminate anything -- it reported "SUCCESS. D_v2 = 0" for a complete graph,
   an empty graph and a line graph alike.

   From n = 6 the measure does vary sensibly (measured over random graphs:
   n=6 gives 21.1 / 26.3 / 26.3 bits at densities 0.15 / 0.5 / 0.85, rising to
   89.7 / 156.7 / 162.6 at n=16). So the 4-node case is kept as an explicit
   FLOOR check, and a 6-node case is added that the measure can actually fail. *)

adjSmall = {{0, 1, 0, 0}, {1, 0, 1, 0}, {0, 1, 0, 1}, {0, 0, 1, 0}}; (* n=4: the degenerate floor *)
resSmall = Integration`BioBridgeV2`UniversalDv2[adjSmall];
floorIsZero = AssociationQ[resSmall] && KeyExistsQ[resSmall, "dv2"] &&
              TrueQ[resSmall["dv2"] == 0];
Print[">> n=4 floor (D_v2 must be 0, one 4x4 block): ",
      If[floorIsZero, "PASSED", "FAILED -- D_v2 = " <> ToString[resSmall["dv2"]]]];

adj = {{0, 1, 0, 0, 0, 1}, {1, 0, 1, 0, 0, 0}, {0, 1, 0, 1, 0, 0},
       {0, 0, 1, 0, 1, 0}, {0, 0, 0, 1, 0, 1}, {1, 0, 0, 0, 1, 0}};  (* n=6 ring *)
res = Integration`BioBridgeV2`UniversalDv2[adj];

(* n=6 must produce a POSITIVE length. A key check alone would pass on 0. *)
lineGraphOK = AssociationQ[res] && KeyExistsQ[res, "dv2"] &&
              NumericQ[res["dv2"]] && TrueQ[res["dv2"] > 0] && floorIsZero;
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
