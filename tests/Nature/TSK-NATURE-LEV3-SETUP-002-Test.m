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

(* AUDIT04-E. THE DEGENERACY DOCUMENTED ABOVE IS GONE, AND THIS CHECK IS
   INVERTED TO PIN THAT.

   Everything above describes the RETIRED Shannon block encoder, whose smallest
   block was 4x4 -- so at n=4 there was exactly one block, unique/total = 1/1,
   and the cost was log2(1) = 0 for a complete graph, an empty graph and a line
   graph alike. The old assertion required that zero. It was honest about a real
   blind spot, and it also meant the suite would have gone RED if the blind spot
   were ever fixed.

   D_v2 now forwards to the index-set program length (author directive
   2026-09-07: no Shannon quantity may be one of our complexity measures). A
   program length is never zero for a graph with edges -- writing the graph down
   costs bits at every size -- so n=4 now returns 30.1851 rather than 0.

   The check therefore becomes the OPPOSITE and is strictly stronger: n=4 must
   be POSITIVE, and the three 4-node graphs the old measure could not tell apart
   must now receive THREE DIFFERENT lengths. A measure that cannot discriminate
   at its own smallest size is not measuring at that size. *)

adjSmall = {{0, 1, 0, 0}, {1, 0, 1, 0}, {0, 1, 0, 1}, {0, 0, 1, 0}};   (* n=4 line *)
adjFull  = {{0, 1, 1, 1}, {1, 0, 1, 1}, {1, 1, 0, 1}, {1, 1, 1, 0}};   (* n=4 complete *)
adjEmpty = {{0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}};   (* n=4 empty *)

resSmall = Integration`BioBridgeV2`UniversalDv2[adjSmall];
resFull  = Integration`BioBridgeV2`UniversalDv2[adjFull];
resEmpty = Integration`BioBridgeV2`UniversalDv2[adjEmpty];

n4Positive = AssociationQ[resSmall] && KeyExistsQ[resSmall, "dv2"] &&
             NumericQ[resSmall["dv2"]] && TrueQ[resSmall["dv2"] > 0];

n4Discriminates = NumericQ[resFull["dv2"]] && NumericQ[resEmpty["dv2"]] &&
                  Length[DeleteDuplicates[
                    {resSmall["dv2"], resFull["dv2"], resEmpty["dv2"]}]] == 3;

floorOK = n4Positive && n4Discriminates;

Print[">> n=4 is POSITIVE (was structurally 0 under the retired encoder): ",
      If[n4Positive, "PASSED -- D_v2 = " <> ToString[resSmall["dv2"]],
                     "FAILED -- D_v2 = " <> ToString[resSmall["dv2"]]]];
Print[">> n=4 DISCRIMINATES line/complete/empty (all 0 under the retired one): ",
      If[n4Discriminates, "PASSED", "FAILED"],
      " -- ", ToString[{resSmall["dv2"], resFull["dv2"], resEmpty["dv2"]}]];

adj = {{0, 1, 0, 0, 0, 1}, {1, 0, 1, 0, 0, 0}, {0, 1, 0, 1, 0, 0},
       {0, 0, 1, 0, 1, 0}, {0, 0, 0, 1, 0, 1}, {1, 0, 0, 0, 1, 0}};  (* n=6 ring *)
res = Integration`BioBridgeV2`UniversalDv2[adj];

(* n=6 must produce a POSITIVE length. A key check alone would pass on 0. *)
lineGraphOK = AssociationQ[res] && KeyExistsQ[res, "dv2"] &&
              NumericQ[res["dv2"]] && TrueQ[res["dv2"] > 0] && floorOK;
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

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{statusBase, "Done.txt"}], DateString[], "Text"];
