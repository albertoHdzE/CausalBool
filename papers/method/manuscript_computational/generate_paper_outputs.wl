(* generate_paper_outputs.wl
   Runs the actual CausalBool code and prints the outputs
   needed for the computational paper's code listings.
   Uses CausalBoolCore.wl — the same library as the companion code. *)

baseDir = DirectoryName[$InputFileName];
Get[FileNameJoin[{baseDir, "..", "code", "lib", "CausalBoolCore.wl"}]];
AppendTo[$Path, FileNameJoin[{baseDir, "..", "..", "..", "src", "Packages"}]];
Needs["Integration`Gates`"];


(* ================================================================== *)
(* SECTION 3.1 — Six-node AND deconvolution                           *)
(* ================================================================== *)

Print["=== SECTION 3.1: Six-node AND deconvolution ==="];

cm06 = {
  {1, 0, 0, 0, 0, 0},
  {0, 1, 0, 0, 0, 0},
  {0, 0, 1, 0, 0, 0},
  {1, 0, 0, 1, 0, 0},
  {0, 1, 0, 1, 0, 0},
  {1, 0, 1, 0, 1, 0}
};
dyn06 = {"OR", "NOT", "OR", "IMPLIES", "AND", "XOR"};

(* Build exhaustive repertoire using real API *)
dispatch06 = CreateRepertoiresDispatch[cm06, dyn06];
inputs06 = dispatch06["RepertoireInputs"];
outputs06 = dispatch06["RepertoireOutputs"];

Print["dispatch06 keys: ", Keys[dispatch06]];
Print["Length[inputs06]: ", Length[inputs06]];
Print["First 3 inputs: ", inputs06[[1;;3]]];
Print["First 3 outputs: ", outputs06[[1;;3]]];

(* Node 5 = AND, connected inputs *)
ic5 = Sort@Flatten@Position[cm06[[5]], 1];
Print["Node 5 connected inputs (ic5): ", ic5];

(* Compute one-set using analytic function from companion code *)



(* AND decimal anchor *)
decimalAnchor5 = 1 + Total[weights[6][[ic5]]];
Print["AND decimal anchor (1 + w(2) + w(4)): ", decimalAnchor5];

offsets5 = allOffsets[6, ic5];
Print["Offset family: ", offsets5];

predicted5 = givePlaces[{decimalAnchor5}, offsets5];
Print["Predicted one-set (AND): ", predicted5];

baseline5 = Flatten@Position[outputs06[[All, 5]], 1];
Print["Baseline one-set (AND):  ", baseline5];

verified5 = Sort[predicted5] === Sort[baseline5];
Print["Exact match: ", verified5];

(* Gate dispatch verification *)
Print["\n--- ApplyGate verification ---"];
Print["ApplyGate[\"AND\", {1,1}]: ", ApplyGate["AND", {1, 1}]];
Print["ApplyGate[\"AND\", {1,0}]: ", ApplyGate["AND", {1, 0}]];
Print["ApplyGate[\"AND\", {0,1}]: ", ApplyGate["AND", {0, 1}]];

(* ================================================================== *)
(* SECTION 3.2 — XOR case, LOCAL semantics: node 6 reads raw coords {1,3,5}. *)
(* ================================================================== *)

Print["\n=== SECTION 3.2: XOR case \(LOCAL semantics, Ic={1,3,5}\) ==="];

(* Node 6 = XOR, connected inputs = {1, 3, 5} from the CM *)
ic6 = Sort@Flatten@Position[cm06[[6]], 1];
Print["Node 6 connected inputs (ic6): ", ic6];

(* Analytic one-set via indexSetAnalytic *)
predictedXOR = Sort@IndexSetAnalytic[6, ic6, "XOR"];
Print["IndexSetAnalytic[6, {1,3,5}, \"XOR\"]: ", predictedXOR];
Print["Length: ", Length[predictedXOR]];

(* Offset decomposition for XOR *)
offsetsXOR = allOffsets[6, ic6];
Print["Free coords: ", Complement[Range[6], ic6]];
Print["Offset family: ", offsetsXOR];

(* Base set: XOR parity-1 assignments to {1,3,5} with free coords {2,4,6} = 0 *)
baseXOR = Select[predictedXOR,
  Function[idx, AllTrue[Complement[Range[6], ic6],
    inputs06[[idx, #]] == 0 &]]];
Print["Base set (zero-free): ", baseXOR];

(* Verify deconvolution *)
deconvXOR = givePlaces[baseXOR, offsetsXOR];
Print["Dec(L, Omega): ", deconvXOR];
Print["Dec matches analytic: ", Sort[deconvXOR] === Sort[predictedXOR]];

(* Baseline from CreateRepertoiresDispatch *)
baselineXOR = Flatten@Position[outputs06[[All, 6]], 1];
Print["Baseline one-set:  ", baselineXOR];

verifiedXOR = Sort[predictedXOR] === Sort[baselineXOR];
Print["Exact match (LOCAL): ", verifiedXOR];
verifiedXORLocal = verifiedXOR;

(* ================================================================== *)
(* SECTION 3.2b — COMPOSED semantics (paper flagship):                *)
(*   y6 = x1 XOR x3 XOR AND(x2, x4).                                   *)
(* AUDIT01/T1.1 D-2(d): node 6 is an in-degree-4 composite gate OUTSIDE *)
(* the twelve-family catalogue; its one-set is obtained by COMPOSING    *)
(* index sets (indicator arithmetic over constituents), not by the      *)
(* XOR closed form over raw coordinates. Composition lemma is verified  *)
(* here empirically, elementwise, against an exhaustive LUT.            *)
(* ================================================================== *)
Print["\n=== SECTION 3.2b: COMPOSED flagship node \(y6 = x1+x3+AND(x2,x4) mod 2\) ==="];

exhaustiveComposed = Table[
  With[{r = Reverse@IntegerDigits[x, 2, 6]},   (* LSB row: r[[k]] = coordinate k, matching IndexSetAnalytic convention *)
    Mod[r[[1]] + r[[3]] + Boole[r[[2]] == 1 && r[[4]] == 1], 2]],
  {x, 0, 63}];
indicatorsOf[set_List] := Module[{v = ConstantArray[0, 64]}, v[[set]] = 1; v];
constituentXORone = Sort@IndexSetAnalytic[6, {1}, "XOR"];
constituentXORthree = Sort@IndexSetAnalytic[6, {3}, "XOR"];
constituentAND = Sort@IndexSetAnalytic[6, {2, 4}, "AND"];
composedOneSet = Pick[Range[64],
  Mod[indicatorsOf[constituentXORone] + indicatorsOf[constituentXORthree] + indicatorsOf[constituentAND], 2], 1];
lutComposedOnes = Flatten@Position[exhaustiveComposed, 1];
symDiffComposed = Sort@Join[Complement[composedOneSet, lutComposedOnes], Complement[lutComposedOnes, composedOneSet]];
verifiedComposedXOR = symDiffComposed == {};
Print["Composed one-set |J|: ", Length[composedOneSet]];
Print["LUT on-set |J|:       ", Length[lutComposedOnes]];
Print["Symmetric difference: ", If[symDiffComposed == {}, "∅ (elementwise equal)", symDiffComposed]];
Print["Exact match (COMPOSED, composition lemma): ", verifiedComposedXOR];

(* ================================================================== *)
(* SECTION 3.3 — All gate families via indexSetAnalytic                *)
(* ================================================================== *)

Print["\n=== SECTION 3.3: All gate families (indexSetAnalytic) ==="];

(* Quick demo: AND on {2,4} in 6-node *)
demo = Sort@IndexSetAnalytic[6, {2, 4}, "AND"];
Print["IndexSetAnalytic[6, {2,4}, \"AND\"]: ", demo];
Print["Matches predicted5: ", demo === Sort[predicted5]];

(* ================================================================== *)
(* SECTION 4.1 — 10-node benchmark                                    *)
(* ================================================================== *)

Print["\n=== SECTION 4.1: 10-node benchmark ==="];

cm10 = {
  {0, 1, 1, 0, 0, 0, 0, 0, 0, 0},
  {1, 0, 1, 0, 0, 0, 0, 0, 0, 0},
  {0, 0, 0, 1, 1, 0, 0, 0, 0, 0},
  {0, 1, 1, 0, 1, 0, 0, 0, 0, 0},
  {0, 0, 0, 0, 0, 1, 0, 0, 0, 0},
  {0, 0, 0, 0, 1, 0, 1, 0, 0, 0},
  {0, 0, 0, 0, 0, 1, 0, 0, 0, 0},
  {1, 0, 0, 0, 0, 0, 0, 0, 1, 0},
  {0, 1, 0, 0, 0, 0, 0, 0, 0, 1},
  {0, 0, 1, 1, 0, 0, 1, 1, 0, 0}
};
dyn10 = {"AND", "OR", "XOR", "KOFN", "NOR", "XNOR", "NOT", "IMPLIES", "NIMPLIES", "MAJORITY"};
params10 = <|
  4 -> <|"k" -> 2|>,
  8 -> <|"pair" -> {1, 9}|>,
  9 -> <|"pair" -> {2, 10}|>
|>;

n10 = 10;
dispatch10 = CreateRepertoiresDispatch[cm10, dyn10, params10];
inputs10 = dispatch10["RepertoireInputs"];
outputs10 = dispatch10["RepertoireOutputs"];

Print["dispatch10 built. Length: ", Length[outputs10]];

ics10 = Table[Sort@Flatten@Position[cm10[[k]], 1], {k, 1, n10}];
Print["Connected input sets:"];
Do[Print["  Node ", k, " (", dyn10[[k]], "): N_", k, " = ", ics10[[k]]], {k, 1, n10}];

(* Analytic one-sets *)
oneSets10 = Table[
  Sort@IndexSetAnalytic[n10, ics10[[k]], dyn10[[k]], Lookup[params10, k, <||>]],
  {k, 1, n10}];

(* Baseline one-sets *)
baselineOneSets10 = Table[
  Flatten@Position[outputs10[[All, k]], 1],
  {k, 1, n10}];

(* Per-node verification *)
nodeVerification10 = Table[
  Sort[oneSets10[[k]]] === Sort[baselineOneSets10[[k]]],
  {k, 1, n10}];

Print["Per-node verification: ", nodeVerification10];
Print["All nodes verified: ", And @@ nodeVerification10];

(* ================================================================== *)
(* SECTION 4.1 — Mixed queries                                        *)
(* ================================================================== *)

Print["\n=== SECTION 4.1: Mixed queries ==="];

allIndices10 = Range[1, 2^n10];

conditionSet[node_Integer, bit_Integer] := If[
  bit == 1,
  oneSets10[[node]],
  Complement[allIndices10, oneSets10[[node]]]
];

queryIndices[nodes_List, pattern_List] := Sort@Fold[
  Intersection, allIndices10,
  MapThread[conditionSet, {nodes, pattern}]
];

queryBaseline[nodes_List, pattern_List] :=
  Flatten@Position[outputs10[[All, nodes]], pattern, 1];

mixedQueryRepresentation[nodes_List, pattern_List] := Module[
  {analytic, unionCoords, sumandos, baseIndices},
  analytic = queryIndices[nodes, pattern];
  unionCoords = Sort@DeleteDuplicates@Flatten[ics10[[nodes]]];
  sumandos = allOffsets[n10, unionCoords];
  baseIndices = Select[analytic,
    Function[idx, AllTrue[
      Complement[Range[n10], unionCoords],
      inputs10[[idx, #]] == 0 &]]];
  <|"DecimalRepertoire" -> baseIndices, "Sumandos" -> sumandos|>
];

(* --- F1 --- *)
resF1 = mixedQueryRepresentation[Range[10], {1,1,1,1,1,1,1,1,1,1}];
gpF1 = givePlaces[resF1["DecimalRepertoire"], resF1["Sumandos"]];
blF1 = queryBaseline[Range[10], {1,1,1,1,1,1,1,1,1,1}];
vF1 = Sort[gpF1] === Sort[blF1];
Print["\nF1:"];
Print["  DecimalRepertoire: ", resF1["DecimalRepertoire"]];
Print["  Sumandos: ", resF1["Sumandos"]];
Print["  Unfolded: ", gpF1];
Print["  Baseline: ", blF1];
Print["  Verified: ", vF1];

(* --- F2 --- *)
resF2 = mixedQueryRepresentation[Range[10], {1,1,1,1,1,1,1,1,1,0}];
gpF2 = givePlaces[resF2["DecimalRepertoire"], resF2["Sumandos"]];
blF2 = queryBaseline[Range[10], {1,1,1,1,1,1,1,1,1,0}];
vF2 = Sort[gpF2] === Sort[blF2];
Print["\nF2:"];
Print["  DecimalRepertoire: ", resF2["DecimalRepertoire"]];
Print["  Sumandos: ", resF2["Sumandos"]];
Print["  Unfolded: ", gpF2];
Print["  Verified: ", vF2];

(* --- F3 --- *)
resF3 = mixedQueryRepresentation[Range[10], {1,1,1,1,1,1,1,1,0,1}];
gpF3 = givePlaces[resF3["DecimalRepertoire"], resF3["Sumandos"]];
blF3 = queryBaseline[Range[10], {1,1,1,1,1,1,1,1,0,1}];
vF3 = Sort[gpF3] === Sort[blF3];
Print["\nF3:"];
Print["  DecimalRepertoire: ", resF3["DecimalRepertoire"]];
Print["  Sumandos: ", resF3["Sumandos"]];
Print["  Unfolded: ", gpF3];
Print["  Verified: ", vF3];

(* --- F4 --- *)
resF4 = mixedQueryRepresentation[Range[10], {1,1,1,1,1,0,1,1,1,1}];
gpF4 = givePlaces[resF4["DecimalRepertoire"], resF4["Sumandos"]];
blF4 = queryBaseline[Range[10], {1,1,1,1,1,0,1,1,1,1}];
vF4 = Sort[gpF4] === Sort[blF4];
Print["\nF4:"];
Print["  DecimalRepertoire: ", resF4["DecimalRepertoire"]];
Print["  Sumandos: ", resF4["Sumandos"]];
Print["  Unfolded: ", gpF4];
Print["  Verified: ", vF4];

(* --- S1 --- *)
resS1 = mixedQueryRepresentation[{4,6,7,10}, {0,1,1,1}];
gpS1 = givePlaces[resS1["DecimalRepertoire"], resS1["Sumandos"]];
blS1 = queryBaseline[{4,6,7,10}, {0,1,1,1}];
vS1 = Sort[gpS1] === Sort[blS1];
Print["\nS1:"];
Print["  DecimalRepertoire: ", resS1["DecimalRepertoire"]];
Print["  Sumandos: ", resS1["Sumandos"]];
Print["  Unfolded: ", gpS1];
Print["  Baseline: ", blS1];
Print["  Verified: ", vS1];

(* --- S2 --- *)
resS2 = mixedQueryRepresentation[{4,6,7,8,9,10}, {0,1,1,1,0,1}];
gpS2 = givePlaces[resS2["DecimalRepertoire"], resS2["Sumandos"]];
blS2 = queryBaseline[{4,6,7,8,9,10}, {0,1,1,1,0,1}];
vS2 = Sort[gpS2] === Sort[blS2];
Print["\nS2:"];
Print["  DecimalRepertoire: ", resS2["DecimalRepertoire"]];
Print["  Sumandos: ", resS2["Sumandos"]];
Print["  Unfolded: ", gpS2];
Print["  Baseline: ", blS2];
Print["  Verified: ", vS2];

(* ================================================================== *)
(* SECTION 4.2 — Overlap statistics                                   *)
(* ================================================================== *)

Print["\n=== SECTION 4.2: Overlap statistics ==="];

overlapStats[nodes_List] := Module[
  {unionCoords, degreeSum, cq, muq},
  unionCoords = Sort@DeleteDuplicates@Flatten[ics10[[nodes]]];
  degreeSum = Total[Length /@ ics10[[nodes]]];
  cq = Length[unionCoords];
  muq = degreeSum - cq;
  <|"d_q" -> degreeSum, "c_q" -> cq, "mu_q" -> muq,
    "R_q" -> 2^muq, "C_q" -> unionCoords,
    "F_q" -> Complement[Range[n10], unionCoords]|>
];

Print["Full (F1-F4): ", overlapStats[Range[10]]];
Print["S1:           ", overlapStats[{4, 6, 7, 10}]];
Print["S2:           ", overlapStats[{4, 6, 7, 8, 9, 10}]];

(* S1 deconvolution detail *)
Print["\nS1 deconvolution detail:"];
s1stats = overlapStats[{4, 6, 7, 10}];
Print["  C_S1 = ", s1stats["C_q"]];
Print["  F_S1 = ", s1stats["F_q"]];
s1offsets = allOffsets[n10, s1stats["C_q"]];
Print["  Offset family Omega(F_S1) = ", s1offsets];
Print["  Base set L_S1 = ", resS1["DecimalRepertoire"]];

(* ================================================================== *)
(* SECTION 6 — Dynamical landscape                                    *)
(* ================================================================== *)

Print["\n=== SECTION 6: Dynamical landscape ==="];

(* Forward update function using ApplyGate *)
networkUpdate10[input_List] := Table[
  ApplyGate[dyn10[[k]],
    input[[Sort@Flatten@Position[cm10[[k]], 1]]],
    Lookup[params10, k, <||>]],
  {k, 1, n10}];

allStates10 = Table[Reverse[IntegerDigits[x, 2, n10]], {x, 0, 2^n10 - 1}];
allOutputs10 = networkUpdate10 /@ allStates10;
imageStates = DeleteDuplicates[allOutputs10];
Print["|Im(F)| = ", Length[imageStates]];
Print["|U \\ Im(F)| = ", 2^n10 - Length[imageStates]];

(* Attractor detection *)
stateToInt[s_List] := FromDigits[Reverse[s], 2];
successorOf = Association@Table[
  stateToInt[allStates10[[i]]] -> stateToInt[allOutputs10[[i]]],
  {i, Length[allStates10]}];

trajectory[start_Integer] := Module[{visited = {}, current = start},
  While[!MemberQ[visited, current],
    AppendTo[visited, current];
    current = successorOf[current]];
  visited];

allTrajectories = Association@Table[
  s -> trajectory[s], {s, Range[0, 2^n10 - 1]}];

cycleOf[traj_List] := Module[{last, pos},
  last = successorOf[Last[traj]];
  pos = Position[traj, last][[1, 1]];
  traj[[pos ;;]]];

cycles = DeleteDuplicates[Sort /@ (cycleOf /@ Values[allTrajectories])];
Print["Number of attractors: ", Length[cycles]];

Do[
  Module[{cyc = cycles[[i]], period, basinSize},
    period = Length[cyc];
    basinSize = Count[Values[allTrajectories],
      t_ /; ContainsAny[t, cyc]];
    Print["A", i, ": period=", period,
      ", basin=", basinSize,
      ", states=", (StringJoin[ToString /@ Reverse[IntegerDigits[#, 2, n10]]]) & /@ Sort[cyc]];
  ],
  {i, Length[cycles]}
];

(* AUDIT02/W0.5: the dynamical-landscape statistics were computed and PRINTED
   but never exported, so the manuscript's |Im(F)|, attractor count and basin
   sizes had no machine-checkable producer output to be reconciled against and
   the artefact group stayed PENDING for want of a file, not for want of a
   computation. Emitting them here closes that gap; tools/verify_paper_artefacts.py
   ties each table cell to a field below. Basin sizes are sorted descending so
   the order is a property of the run, not of cycle-discovery order. *)
Module[{basins},
  basins = Reverse[Sort[Table[
    Count[Values[allTrajectories], t_ /; ContainsAny[t, cycles[[i]]]],
    {i, Length[cycles]}]]];
  Export[FileNameJoin[{DirectoryName[$InputFileName], "dynamical_landscape.json"}],
    <|"n" -> n10,
      "StateSpaceSize" -> 2^n10,
      "ImageSize" -> Length[imageStates],
      "UnreachableCount" -> 2^n10 - Length[imageStates],
      "AttractorCount" -> Length[cycles],
      "AttractorPeriods" -> Sort[Length /@ cycles],
      "BasinSizesDescending" -> basins,
      "BasinSizeTotal" -> Total[basins]|>,
    "JSON"]];

(* AUDIT01/T1.1: banner replaced by a REAL gate — exits non-zero on any failure *)
verificationList = <|
  "6-node AND" -> verified5,
  "6-node XOR (local)" -> TrueQ[verifiedXORLocal],
  "6-node flagship XOR (composed, D-2d)" -> TrueQ[verifiedComposedXOR],
  "10-node per-node" -> And @@ nodeVerification10,
  "F1" -> vF1, "F2" -> vF2, "F3" -> vF3, "F4" -> vF4,
  "S1" -> vS1, "S2" -> vS2|>;
failedChecks = Keys@Select[verificationList, Not[#] &] /. Not[x_] :> x;
Scan[Print["  ", #, ": ", verificationList[[#]]] &, Keys[verificationList]];
If[failedChecks == {},
  Print["\n=== ALL VERIFICATIONS PASSED ==="],
  Print["\n=== VERIFICATION FAILED: ", failedChecks, " ==="]; Exit[1]
];
