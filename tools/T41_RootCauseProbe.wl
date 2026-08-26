(* ::Package:: *)
(* AUDIT01/T4.1 step-1 instrument: TSK-MIXED-001 IndexSetNetwork+Phi path probe.
   Establishes, by fresh execution (U7/U8):
   (A) current IndexSetNetwork+single-Phi path equals the LSB baseline elementwise
       (per-node symmetric differences, never cardinality alone);
   (B) what wrong bridges look like: Phi omitted / Phi applied twice;
   (C) the dead-path arithmetic identity behind the archived accuracyIndex=0.51875:
       an all-zero prediction matrix scores exactly the baseline zero-cell fraction.
   Output: results/tests/mixed001FormulaVsExhaustive/rootcause/probe_results.json *)

AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
Needs["Integration`Experiments`"];

base = FileNameJoin[{"results", "tests", "mixed001FormulaVsExhaustive", "rootcause"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

phi[j_, nn_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, nn]], 2];
mapPhiSet[set_List, nn_] := Sort[phi[#, nn] & /@ set];

cm10 = {
  {0,1,1,0,0,0,0,0,0,0},{1,0,1,0,0,0,0,0,0,0},{0,0,0,1,1,0,0,0,0,0},
  {0,1,1,0,1,0,0,0,0,0},{0,0,0,0,0,1,0,0,0,0},{0,0,0,0,1,0,1,0,0,0},
  {0,0,0,0,0,1,0,0,0,0},{1,0,0,0,0,0,0,0,1,0},{0,1,0,0,0,0,0,0,0,1},
  {0,0,1,1,0,0,1,1,0,0}};
dyn10 = {"AND","OR","XOR","KOFN","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY"};
params10 = <|4 -> <|"k" -> 2|>|>;
n = Length[dyn10];

res = Integration`Experiments`CreateRepertoiresDispatch[cm10, dyn10, params10];
baseline = Developer`ToPackedArray@Normal@res["RepertoireOutputs"];
ics = Table[Flatten@Position[cm10[[k]], 1], {k, n}];

predictFromSets[sets_List] := Module[{out = ConstantArray[0, {Length[baseline], n}]},
  Do[If[Length[sets[[k]]] > 0, out[[sets[[k]], k]] = 1], {k, n}];
  Developer`ToPackedArray[out]];

networkSets = Table[
  Integration`Gates`IndexSetNetwork[dyn10[[k]], n, ics[[k]], Lookup[params10, k, <||>]], {k, n}];
analyticSets = Table[
  Integration`Gates`IndexSetAnalytic[n, ics[[k]], dyn10[[k]], Lookup[params10, k, <||>]], {k, n}];

setsSinglePhi = Table[mapPhiSet[networkSets[[k]], n], {k, n}];
setsDoublePhi = Table[mapPhiSet[mapPhiSet[networkSets[[k]], n], n], {k, n}];
setsNoPhi = Table[Sort[networkSets[[k]]], {k, n}];

pathSinglePhi = predictFromSets[setsSinglePhi];
pathNoPhi = predictFromSets[setsNoPhi];
pathDoublePhi = predictFromSets[setsDoublePhi];
pathAnalyticLSB = predictFromSets[analyticSets];

symDiffCount[a_List, b_List] := Length[Complement[a, b]] + Length[Complement[b, a]];
perNodeSymDiff[pred_] := Association @@ Table[
  ("node" <> ToString[k]) ->
    symDiffCount[Sort[Flatten@Position[baseline[[All, k]], 1]],
                 Sort[Flatten@Position[pred[[All, k]], 1]]], {k, n}];

cellMismatches[pred_] := Total[Boole[MapThread[Unequal, {baseline, pred}, 2]], 2];
accuracyOf[pred_] := N[1 - cellMismatches[pred]/(Length[baseline]*n)];

zeroCells = Count[Flatten[baseline], 0];
zeroFraction = N[zeroCells/(Length[baseline]*n)];
deadAgreement = accuracyOf[ConstantArray[0, Dimensions[baseline]]];

report = <|
  "executedAt" -> DateString[],
  "network" -> <|"n" -> n, "dyn" -> dyn10|>,
  "A_currentPath_singlePhi" -> <|
     "cellMismatches" -> cellMismatches[pathSinglePhi],
     "accuracy" -> accuracyOf[pathSinglePhi],
     "perNodeSymDiffCounts" -> perNodeSymDiff[pathSinglePhi]|>,
  "B_noPhi_bridge" -> <|"cellMismatches" -> cellMismatches[pathNoPhi],
     "accuracy" -> accuracyOf[pathNoPhi],
     "perNodeSymDiffCounts" -> perNodeSymDiff[pathNoPhi]|>,
  "C_doublePhi_bridge" -> <|"cellMismatches" -> cellMismatches[pathDoublePhi],
     "accuracy" -> accuracyOf[pathDoublePhi]|>,
  "analytic_LSB_native" -> <|"cellMismatches" -> cellMismatches[pathAnalyticLSB],
     "accuracy" -> accuracyOf[pathAnalyticLSB]|>,
  "D_deadPathIdentity" -> <|
     "baselineZeroCells" -> zeroCells,
     "zeroFraction" -> zeroFraction,
     "allZeroMatrixAccuracy" -> deadAgreement,
     "identityHolds" -> deadAgreement == zeroFraction,
     "archivedAccuracyIndex" -> 0.51875,
     "matchesArchived" -> Abs[zeroFraction - 0.51875] < 10^-12|>,
  "phiInvolutionCheck" ->
     (Table[phi[phi[x, n], n], {x, 1, 2^n}] === Range[1, 2^n])
|>;

Export[FileNameJoin[{base, "probe_results.json"}], report, "JSON"];
Print["A current(single-Phi): mismatches=", report["A_currentPath_singlePhi"]["cellMismatches"],
  " acc=", report["A_currentPath_singlePhi"]["accuracy"]];
Print["B no-Phi bridge: mismatches=", report["B_noPhi_bridge"]["cellMismatches"],
  " acc=", report["B_noPhi_bridge"]["accuracy"]];
Print["C double-Phi bridge: mismatches=", report["C_doublePhi_bridge"]["cellMismatches"],
  " acc=", report["C_doublePhi_bridge"]["accuracy"]];
Print["D dead-path identity: zeroFraction=", zeroFraction, " allZeroAcc=", deadAgreement,
  " matchesArchived0.51875=", report["D_deadPathIdentity"]["matchesArchived"]];
If[report["A_currentPath_singlePhi"]["cellMismatches"] =!= 0, Exit[1]];
If[!TrueQ[report["D_deadPathIdentity"]["matchesArchived"]], Exit[1]];
Print["T41 PROBE OK"]
