(* TSK-BIO-METRICS-002 — an ABSOLUTE description length for KOFN.

   AUDIT04 Phase A. The mutant `cformula-kofn` reverts the KOFN branch of the
   node cost from `log2Int[d + 1] + 1` to the drifted `1 + d` form that two
   copies carried before the AUDIT03 collapse. It SURVIVED the whole
   verification set, and the prediction registered in advance named the reason:

       "nothing in the MUnit suite pins an exact D for an arbitrary network;
        only RELATIVE Wolfram-Python agreement is checked, never an absolute
        value."

   Its registered pair `dl-binomial-off` was killed, so the split localises the
   gap precisely -- it is not general to description length, it is the KOFN
   branch specifically.

   WHY A PLAUSIBLE TEST WOULD HAVE MISSED IT. `log2Int[x] = N@Log[2, x]`, an
   exact real logarithm rather than a ceiling, so the owner and the mutant
   evaluate to:

       d = 1   Log2[2] + 1 = 2      vs   1 + 1 = 2      IDENTICAL
       d = 2   Log2[3] + 1 = 2.585  vs   1 + 2 = 3      differ
       d = 3   Log2[4] + 1 = 3      vs   1 + 3 = 4      differ

   A KOFN node of in-degree ONE is therefore blind to this defect, and a small
   hand-built fixture is exactly where an in-degree-1 node would appear. The
   d = 1 case is asserted below as a DOCUMENTED BLIND SPOT, so the reason the
   gap existed is recorded in the suite rather than only in an audit file.

   INDEPENDENT DERIVATION. The expected values are computed here from the node
   language declared in BioMetrics.m -- gate selector, in-degree field,
   wiring field, parameter field -- and never by calling the owner and recording
   what it returned. *)

base = FileNameJoin[{"results", "tests", "biometrics002"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
AppendTo[$Path, "src/Packages"];
Needs["Integration`BioMetrics`"];

(* ---- the cost model, written out here, independent of the owner -----------
   Per BioMetrics.m encodeNodeCost, a node costs:
       log2(k)                gate selector, k = 12 declared labels
     + log2(n + 1)            in-degree field, the one that makes D decodable
     + log2(max(1, C(n, d)))  which d of n inputs
     + parameter field        gate-specific
   and the KOFN parameter field is log2(d + 1) + 1: log2(d+1) for the threshold
   k in 0..d, plus one bit for the strict/non-strict policy. *)
expectedNodeBits[n_, d_, param_] := Log[2, 12.] + Log[2, n + 1.] +
                                    Log[2, Max[1., Binomial[n, d]]] + param;
kofnParam[d_] := Log[2, d + 1.] + 1;
andParam = 1.;

(* ---- case 1: KOFN at in-degree 2 -- the mutant differs here ---------------
   n = 3. Nodes 1 and 2 are sources; node 3 is KOFN over both. *)
cm2 = {{0, 0, 0}, {0, 0, 0}, {1, 1, 0}};
dyn2 = {"AND", "AND", "KOFN"};
res2 = Integration`BioMetrics`ComputeDescriptionLength[cm2, dyn2];

want2Node3 = expectedNodeBits[3, 2, kofnParam[2]];
want2Total = expectedNodeBits[3, 0, andParam] * 2 + want2Node3;

okNode2 = Abs[res2["perNode"][[3]] - want2Node3] < 10.^-9;
okTotal2 = Abs[res2["D"] - want2Total] < 10.^-9;

(* The mutant's value, computed explicitly. Asserting that the owner does NOT
   equal it turns "this test would catch the mutant" from a claim into a check. *)
mutant2Node3 = expectedNodeBits[3, 2, 1. + 2];
okRejects2 = Abs[res2["perNode"][[3]] - mutant2Node3] > 0.1;

(* ---- case 2: KOFN at in-degree 3 ------------------------------------------ *)
cm3 = {{0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}, {1, 1, 1, 0}};
dyn3 = {"AND", "AND", "AND", "KOFN"};
res3 = Integration`BioMetrics`ComputeDescriptionLength[cm3, dyn3];

want3Node4 = expectedNodeBits[4, 3, kofnParam[3]];
okNode3 = Abs[res3["perNode"][[4]] - want3Node4] < 10.^-9;
mutant3Node4 = expectedNodeBits[4, 3, 1. + 3];
okRejects3 = Abs[res3["perNode"][[4]] - mutant3Node4] > 0.1;

(* ---- case 3: the DOCUMENTED BLIND SPOT, in-degree 1 -----------------------
   Here log2(d+1) + 1 and 1 + d are both exactly 2, so owner and mutant agree.
   Asserted so that the limit of this defence is visible in the suite: a KOFN
   test built only on an in-degree-1 node proves nothing about this branch. *)
cm1 = {{0, 0}, {1, 0}};
dyn1 = {"AND", "KOFN"};
res1 = Integration`BioMetrics`ComputeDescriptionLength[cm1, dyn1];
want1Node2 = expectedNodeBits[2, 1, kofnParam[1]];
okNode1 = Abs[res1["perNode"][[2]] - want1Node2] < 10.^-9;
blindSpotIsReal = Abs[kofnParam[1] - (1. + 1)] < 10.^-12;

(* ---- case 4: C_formula for KOFN is a COUNT, not a length ------------------
   FormulaComponentWeight is a different quantity in different units, and
   C_formula = 23 on the flagship is published. Pinned here so the two are not
   conflated by a later edit. *)
okComponents =
  Integration`BioMetrics`FormulaComponentWeight["KOFN", {1, 2}] === 2 &&
  Integration`BioMetrics`FormulaComponentWeight["KOFN", {1, 2, 3}] === 2 &&
  Integration`BioMetrics`ComputeFormulaComponents[cm2, dyn2] === 1 + 1 + 2;

allOK = okNode2 && okTotal2 && okRejects2 && okNode3 && okRejects3 &&
        okNode1 && blindSpotIsReal && okComponents;

status = If[TrueQ[allOK], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];

Association[
  "Status" -> status,
  "KOFNd2Node" -> okNode2, "KOFNd2Total" -> okTotal2,
  "RejectsMutantAtD2" -> okRejects2,
  "KOFNd3Node" -> okNode3, "RejectsMutantAtD3" -> okRejects3,
  "KOFNd1Node" -> okNode1, "BlindSpotAtD1IsReal" -> blindSpotIsReal,
  "FormulaComponents" -> okComponents,
  "D_d2" -> res2["D"], "D_d3" -> res3["D"],
  "ResultsPath" -> base
]
