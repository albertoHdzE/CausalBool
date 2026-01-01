AppendTo[$Path, "src/Packages"];
Needs["Integration`Experiments`"];
base = FileNameJoin[{"results", "tests", "mixed001FormulaVsExhaustive"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
inputsFor[n_Integer] := IntegerDigits[Range[0, 2^n - 1], 2, n];
vectorPredict[cm_List, dyn_List, inputs_List, params_Association:<||>] := Module[{n = Length[dyn], packedInputs, ics, out},
  packedInputs = Developer`ToPackedArray[inputs];
  ics = Table[Flatten@Position[cm[[k]], 1], {k, n}];
  out = ConstantArray[0, {Length[packedInputs], n}];
  Do[
    Module[{Ic = ics[[k]], bits, p = Lookup[params, k, <||>], d = dyn[[k]], a, b, ci, vcan, cout, kthr, strict, t},
      bits = packedInputs[[All, Ic]];
      Switch[d,
        "OR", out[[All, k]] = Boole[Total[bits, {2}] >= 1],
        "AND", out[[All, k]] = Boole[Total[bits, {2}] == Length[Ic]],
        "XOR", out[[All, k]] = Mod[Total[bits, {2}], 2],
        "XNOR", out[[All, k]] = 1 - Mod[Total[bits, {2}], 2],
        "NAND", out[[All, k]] = 1 - Boole[Total[bits, {2}] == Length[Ic]],
        "NOR", out[[All, k]] = Boole[Total[bits, {2}] == 0],
        "NOT", (ci = Lookup[p, "i", If[Length[Ic] >= 1, Ic[[1]], Ic[[1]]]]; out[[All, k]] = 1 - packedInputs[[All, ci]]),
        "IMPLIES" | "NIMPLIES", ( {a, b} = Lookup[p, "pair", If[Length[Ic] >= 2, {Ic[[1]], Ic[[2]]}, {Ic[[1]], Ic[[1]]}]]; If[d === "IMPLIES", out[[All, k]] = Boole[(1 - packedInputs[[All, a]]) + packedInputs[[All, b]] >= 1], out[[All, k]] = Boole[packedInputs[[All, a]] * (1 - packedInputs[[All, b]])]] ),
        "MAJORITY", (t = Ceiling[Max[1, Length[Ic]]/2]; out[[All, k]] = Boole[Total[bits, {2}] >= t]),
        "KOFN", (kthr = Lookup[p, "k", 1]; strict = TrueQ[Lookup[p, "strict", False]]; out[[All, k]] = If[strict, Boole[Total[bits, {2}] > kthr], Boole[Total[bits, {2}] >= kthr]]),
        "CANALISING",
          (
            ci = Lookup[p, "canalisingIndex", If[Length[Ic] >= 1, Ic[[1]], Ic[[1]]]];
            vcan = Lookup[p, "canalisingValue", 1];
            cout = Lookup[p, "canalisedOutput", 0];
            Module[{fallback = Boole[Total[bits, {2}] >= 1], mask = Boole[packedInputs[[All, ci]] == vcan]},
              out[[All, k]] = mask*cout + (1 - mask)*fallback
            ]
          ),
        _, out[[All, k]] = 0
      ]
    ],
    {k, 1, n}
  ];
  Developer`ToPackedArray[out]
];

libPredict[cm_List, dyn_List, inputs_List, params_Association:<||>] := Module[{n = Length[dyn], ics, out},
  ics = Table[Flatten@Position[cm[[k]], 1], {k, n}];
  out = Table[
    With[{Ic = ics[[k]], d = dyn[[k]], p = Lookup[params, k, <||>]},
      Integration`Gates`ApplyGate[d, inputs[[j, Ic]], p]
    ],
    {j, Length[inputs]}, {k, n}
  ];
  Developer`ToPackedArray[out]
];

indexSetPredict[inputs_List, cm_List, dyn_List, params_Association:<||>] := Module[{n = Length[dyn], ics, onesSets, out},
  ics = Table[Flatten@Position[cm[[k]], 1], {k, n}];
  onesSets = Table[
    With[{Ic = ics[[k]], d = dyn[[k]], p = Lookup[params, k, <||>]},
      Integration`Gates`IndexSetNetwork[d, n, Ic, p]
    ],
    {k, n}
  ];
  out = ConstantArray[0, {Length[inputs], n}];
  Do[
    If[Length[onesSets[[k]]] > 0,
      Module[{mapped = 1 + FromDigits[Reverse[IntegerDigits[# - 1, 2, n]], 2] & /@ onesSets[[k]]},
        out[[mapped, k]] = 1
      ]
    ],
    {k, n}
  ];
  Developer`ToPackedArray[out]
];

indexSetAnalytic[n_Integer, Ic_List, gate_String, params_Association:<||>] := Module[{free, pow, d, indexFromPos, subsFree, subsIc, k, strict, pair, a, b, ii, ciAbs, vcan, cout, icRest},
  free = Complement[Range[n], Ic];
  pow = Table[2^(i - 1), {i, 1, n}];
  d = Length[Ic];
  indexFromPos[pos_List] := 1 + Total[pow[[pos]]];
  subsFree = Subsets[free];
  subsIc = Subsets[Ic];
  Which[
    gate === "AND",
    indexFromPos[Join[Ic, #]] & /@ subsFree,
    gate === "OR",
    Complement[Range[1, 2^n], indexFromPos /@ subsFree],
    gate === "XOR",
    Module[{assigns}, assigns = Select[Tuples[{0, 1}, d], Mod[Total[#], 2] == 1 &]; Flatten[Table[indexFromPos[Join[Pick[Ic, assigns[[t]], 1], s]], {t, Length[assigns]}, {s, subsFree}]]],
    gate === "XNOR",
    Module[{assigns}, assigns = Select[Tuples[{0, 1}, d], Mod[Total[#], 2] == 0 &]; Flatten[Table[indexFromPos[Join[Pick[Ic, assigns[[t]], 1], s]], {t, Length[assigns]}, {s, subsFree}]]],
    gate === "NAND",
    Complement[Range[1, 2^n], indexFromPos[Join[Ic, #]] & /@ subsFree],
    gate === "NOR",
    indexFromPos /@ subsFree,
    gate === "NOT",
    ii = Lookup[params, "i", If[Length[Ic] == 1, Ic[[1]], Ic[[1]]]]; indexFromPos /@ Subsets[Complement[Range[n], {ii}]],
    gate === "IMPLIES",
    pair = Lookup[params, "pair", If[Length[Ic] == 2, Ic, Ic[[;; Min[2, d]]]]]; a = pair[[1]]; b = pair[[2]]; Complement[Range[1, 2^n], indexFromPos /@ (Join[{a}, #] & /@ Subsets[Complement[Range[n], {a, b}]] )],
    gate === "NIMPLIES",
    pair = Lookup[params, "pair", If[Length[Ic] == 2, Ic, Ic[[;; Min[2, d]]]]]; a = pair[[1]]; b = pair[[2]]; indexFromPos /@ (Join[{a}, #] & /@ Subsets[Complement[Range[n], {a, b}]] ),
    gate === "MAJORITY",
    Module[{t, assigns}, t = Floor[d/2] + 1; assigns = Select[Tuples[{0, 1}, d], Total[#] >= t &]; Flatten[Table[indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]], {u, Length[assigns]}, {s, subsFree}]]],
    gate === "KOFN",
    Module[{assigns}, k = Lookup[params, "k", 1]; strict = TrueQ[Lookup[params, "strict", False]]; assigns = Select[Tuples[{0, 1}, d], If[strict, Total[#] > k, Total[#] >= k] &]; Flatten[Table[indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]], {u, Length[assigns]}, {s, subsFree}]]],
    gate === "CANALISING",
    ciAbs = Lookup[params, "canalisingIndex", If[Length[Ic] >= 1, Ic[[1]], 1]]; vcan = Lookup[params, "canalisingValue", 1]; cout = Lookup[params, "canalisedOutput", 0]; icRest = Complement[Ic, {ciAbs}]; Module[{band = indexFromPos /@ (Join[If[vcan == 1, {ciAbs}, {}], #] & /@ Subsets[Complement[Range[n], {ciAbs}]]) , offBase = If[vcan == 1, {}, {ciAbs}], restFree = Complement[Range[n], Join[{ciAbs}, icRest]], offFallback}, offFallback = Union @@ Table[indexFromPos /@ (Join[offBase, t, s] & /@ Subsets[restFree]), {t, Subsets[icRest], If[Length[t] == 0, Sequence @@ {}, Sequence @@ {t}]}]; If[cout == 1, Union[band, offFallback], offFallback]],
    True, {}
  ]
];

indexSetPredictAnalytic[n_Integer, cm_List, dyn_List, params_Association:<||>] := Module[{ics, onesSets, out},
  ics = Table[Flatten@Position[cm[[k]], 1], {k, n}];
  onesSets = Table[indexSetAnalytic[n, ics[[k]], dyn[[k]], Lookup[params, k, <||>]], {k, 1, n}];
  out = ConstantArray[0, {2^n, n}];
  Do[If[Length[onesSets[[k]]] > 0, out[[onesSets[[k]], k]] = 1], {k, n}];
  Developer`ToPackedArray[out]
];

(* Define a fixed 10-node network and dynamics using all gates *)
cm10 = {
  {0,1,1,0,0,0,0,0,0,0},
  {1,0,1,0,0,0,0,0,0,0},
  {0,0,0,1,1,0,0,0,0,0},
  {0,1,1,0,1,0,0,0,0,0},
  {0,0,0,0,0,1,0,0,0,0},
  {0,0,0,0,1,0,1,0,0,0},
  {0,0,0,0,0,1,0,0,0,0},
  {1,0,0,0,0,0,0,0,1,0},
  {0,1,0,0,0,0,0,0,0,1},
  {0,0,1,1,0,0,1,1,0,0}
};
dyn10 = {"AND","OR","XOR","KOFN","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY"};
params10 = <|4 -> <|"k" -> 2|>|>; (* Node 4 threshold *)

(* Baseline exhaustive via dispatch *)
{tBase, res} = AbsoluteTiming[Integration`Experiments`CreateRepertoiresDispatch[cm10, dyn10, params10]];
inputs10 = res["RepertoireInputs"];
outputsBase = Normal@res["RepertoireOutputs"]; Export[FileNameJoin[{base, "Inputs.csv"}], Developer`ToPackedArray@inputs10, "CSV"]; Export[FileNameJoin[{base, "OutputsBaseline.csv"}], Developer`ToPackedArray@outputsBase, "CSV"];

(* Predictive vectorised using formulae-induced rules *)
{tPred, outputsPred} = AbsoluteTiming[vectorPredict[cm10, dyn10, inputs10, params10]];
outputsPredNum = Developer`ToPackedArray@Map[If[TrueQ[#], 1, If[NumericQ[#], #, 0]] &, outputsPred, {2}];
Export[FileNameJoin[{base, "OutputsPredictive.csv"}], outputsPredNum, "CSV"];

{tPredLib, outputsPredLib} = AbsoluteTiming[libPredict[cm10, dyn10, inputs10, params10]];
outputsPredLibNum = Developer`ToPackedArray@outputsPredLib;
Export[FileNameJoin[{base, "OutputsPredictiveLib.csv"}], outputsPredLibNum, "CSV"];

{tPredIndex, outputsPredIndex} = AbsoluteTiming[indexSetPredict[inputs10, cm10, dyn10, params10]];
Export[FileNameJoin[{base, "OutputsPredictiveIndex.csv"}], Developer`ToPackedArray@outputsPredIndex, "CSV"];

{tPredAna, outputsPredAna} = AbsoluteTiming[indexSetPredictAnalytic[Length[dyn10], cm10, dyn10, params10]];
Export[FileNameJoin[{base, "OutputsPredictiveAnalytic.csv"}], Developer`ToPackedArray@outputsPredAna, "CSV"];

(* Comparison and reporting *)
eqNum = Developer`ToPackedArray@Boole[MapThread[Equal, {outputsBase, outputsPredNum}, 2]];
diffCount = Total[Flatten[1 - eqNum]];
acc = N[Total[Flatten[eqNum]] / Length[Flatten[eqNum]]];
eqLib = Developer`ToPackedArray@Boole[MapThread[Equal, {outputsBase, outputsPredLibNum}, 2]];
accLib = N[Total[Flatten[eqLib]] / Length[Flatten[eqLib]]];
eqIndex = Developer`ToPackedArray@Boole[MapThread[Equal, {outputsBase, outputsPredIndex}, 2]];
accIndex = N[Total[Flatten[eqIndex]] / Length[Flatten[eqIndex]]];
eqAna = Developer`ToPackedArray@Boole[MapThread[Equal, {outputsBase, outputsPredAna}, 2]];
accAna = N[Total[Flatten[eqAna]] / Length[Flatten[eqAna]]];
Export[FileNameJoin[{base, "Summary.json"}], <|"accuracy" -> acc, "baselineTime" -> tBase, "predictiveTime" -> tPred, "diffCount" -> diffCount, "accuracyLib" -> accLib, "predictiveLibTime" -> tPredLib, "accuracyIndex" -> accIndex, "predictiveIndexTime" -> tPredIndex, "accuracyAnalytic" -> accAna, "predictiveAnalyticTime" -> tPredAna|>, "JSON"];
Print["Accuracy=", acc, " BaselineTime=", tBase, " PredictiveTime=", tPred, " DiffCount=", diffCount, " | AccuracyLib=", accLib, " PredictiveLibTime=", tPredLib, " | AccuracyIndex=", accIndex, " PredictiveIndexTime=", tPredIndex, " | AccuracyAnalytic=", accAna, " PredictiveAnalyticTime=", tPredAna];
Export[FileNameJoin[{base, "Status.txt"}], {If[diffCount == 0, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[diffCount == 0, "OK", "FAIL"], "ResultsPath" -> base]

(* Step samples for documentation *)
sampleCount = Min[16, Length[outputsBase]];
fmtRow[row_List] := StringJoin["[", StringRiffle[ToString /@ row, ", "], "]"];
sampleTextBaseline = StringRiffle[fmtRow /@ outputsBase[[1 ;; sampleCount]], "\n"];
sampleTextAnalytic = StringRiffle[fmtRow /@ outputsPredAna[[1 ;; sampleCount]], "\n"];
Export[FileNameJoin[{base, "OutputsBaselineSample.txt"}], sampleTextBaseline, "Text"];
Export[FileNameJoin[{base, "OutputsAnalyticSample.txt"}], sampleTextAnalytic, "Text"];

(* OnPossibleBehaviour for one node *)
nodeSingle = 7;
IcSingle = Flatten@Position[cm10[[nodeSingle]], 1];
onesSingleAna = indexSetAnalytic[Length[dyn10], IcSingle, dyn10[[nodeSingle]], Lookup[params10, nodeSingle, <||>]];
zerosSingleAna = Complement[Range[1, 2^Length[dyn10]], onesSingleAna];
onesSingleBase = Flatten@Position[outputsBase[[All, nodeSingle]], 1, 1];
zerosSingleBase = Flatten@Position[outputsBase[[All, nodeSingle]], 0, 1];
okSingle = Sort[onesSingleAna] === Sort[onesSingleBase] && Sort[zerosSingleAna] === Sort[zerosSingleBase];
Export[FileNameJoin[{base, "OPB_Node7_Ones.csv"}], Sort[onesSingleAna], "CSV"];
Export[FileNameJoin[{base, "OPB_Node7_Zeros.csv"}], Sort[zerosSingleAna], "CSV"];
Export[FileNameJoin[{base, "OPB_Node7_Summary.json"}], <|"ok" -> okSingle, "countOnes" -> Length[onesSingleAna], "countZeros" -> Length[zerosSingleAna]|>, "JSON"];

(* Pattern indices for subsets *)
subset4 = {1, 3, 5, 7}; pattern4 = {0, 0, 0, 0};
subset7 = {1, 2, 4, 5, 6, 8, 10}; pattern7 = Table[0, {Length[subset7]}];
onesSetsAll = Table[indexSetAnalytic[Length[dyn10], Flatten@Position[cm10[[k]], 1], dyn10[[k]], Lookup[params10, k, <||>]], {k, 1, Length[dyn10]}];
allIdx = Range[1, 2^Length[dyn10]];
condIdx[node_, bit_] := If[bit == 1, onesSetsAll[[node]], Complement[allIdx, onesSetsAll[[node]]]];
idx4Ana = Fold[Intersection, allIdx, MapThread[condIdx, {subset4, pattern4}]];
idx7Ana = Fold[Intersection, allIdx, MapThread[condIdx, {subset7, pattern7}]];
rows4 = outputsBase[[All, subset4]]; rows7 = outputsBase[[All, subset7]];
idx4Base = Flatten@Position[rows4, pattern4, 1];
idx7Base = Flatten@Position[rows7, pattern7, 1];
ok4 = Sort[idx4Ana] === Sort[idx4Base];
ok7 = Sort[idx7Ana] === Sort[idx7Base];
Export[FileNameJoin[{base, "PatternSubset4_IndicesAnalytic.csv"}], Sort[idx4Ana], "CSV"];
Export[FileNameJoin[{base, "PatternSubset4_IndicesBaseline.csv"}], Sort[idx4Base], "CSV"];
Export[FileNameJoin[{base, "PatternSubset7_IndicesAnalytic.csv"}], Sort[idx7Ana], "CSV"];
Export[FileNameJoin[{base, "PatternSubset7_IndicesBaseline.csv"}], Sort[idx7Base], "CSV"];
Export[FileNameJoin[{base, "PatternSubsets_Summary.json"}], <|"ok4" -> ok4, "ok7" -> ok7, "len4" -> Length[idx4Ana], "len7" -> Length[idx7Ana]|>, "JSON"];

(* Complexity metrics: Shannon entropy and ZIP size, optional PyBDM *)
toBits[m_List] := Flatten[m];
Hbin[p_?NumericQ] := If[p==0||p==1, 0.0, -p Log[2, p] - (1-p) Log[2, 1-p]];
pOverall = N@Mean@toBits@outputsBase;
shannonOverall = Hbin[pOverall];
pPerNode = N@(Mean /@ Transpose[outputsBase]);
shannonPerNode = Hbin /@ pPerNode;
(* removed dataset comparison metrics by project policy *)

(* Formula-based compression component count *)
compressionWeight[gate_, Ic_List, params_Association:<||>] := Module[{d = Length[Ic]}, Switch[gate,
  "AND" | "OR" | "NAND" | "NOR", 1 + d,
  "XOR" | "XNOR", 1 + 1,
  "NOT", 1,
  "IMPLIES" | "NIMPLIES", 1 + 2,
  "MAJORITY", 1 + 1,
  "KOFN", 1 + 1,
  "CANALISING", 1 + If[KeyExistsQ[params, "canalisedOutput"], 0, 1],
  _, 1 + d
]];
computeCompression[cm_List, dyn_List, params_Association:<||>] := Module[{n = Length[dyn], ics},
  ics = Table[Flatten@Position[cm[[i]], 1], {i, n}];
  Total@Table[compressionWeight[dyn[[i]], ics[[i]], Lookup[params, i, <||>]], {i, n}]
];
Cformula = computeCompression[cm10, dyn10, params10];

(* LaTeX tables for documentation *)

gateLabels = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN","CANALISING"};
log2Int[x_] := N@Log[2, x];
encodeCostBits[cm_List, dyn_List, params_Association:<||>] := Module[{n = Length[dyn], ics, K = Length[gateLabels]},
  ics = Table[Flatten@Position[cm[[i]], 1], {i, n}];
  Total@Table[
    Module[{d = Length[ics[[i]]], g = dyn[[i]], p = Lookup[params, i, <||>], cost = 0.0},
      cost += log2Int[K];
      cost += log2Int[Max[1, Binomial[n, d]]];
      Switch[g,
        "KOFN", cost += log2Int[d + 1] + 1,
        "CANALISING", cost += log2Int[n] + 1 + 1,
        "IMPLIES" | "NIMPLIES", cost += log2Int[Max[1, d (d - 1)]],
        "NOT", cost += log2Int[Max[1, d]],
        "MAJORITY", cost += 1,
        "XOR" | "XNOR", cost += 1,
        _, cost += 1
      ];
      cost
    ],
    {i, n}
  ]
];

(* Visual sampling and side-by-side comparisons *)
SeedRandom[1234];
sampleIdx = Sort@RandomSample[Range[Length[outputsBase]], Min[10, Length[outputsBase]]];
samplesBase = outputsBase[[sampleIdx]];
samplesAna = outputsPredAna[[sampleIdx]];
samplesLib = outputsPredLibNum[[sampleIdx]];
Export[FileNameJoin[{base, "Samples_Indices.json"}], sampleIdx, "JSON"];
Export[FileNameJoin[{base, "Samples_Base.csv"}], samplesBase, "CSV"];
Export[FileNameJoin[{base, "Samples_Analytic.csv"}], samplesAna, "CSV"];
Export[FileNameJoin[{base, "Samples_Lib.csv"}], samplesLib, "CSV"];
sideBySide = Table[<|"index" -> sampleIdx[[r]], "base" -> samplesBase[[r]], "analytic" -> samplesAna[[r]]|>, {r, Length[sampleIdx]}];
Export[FileNameJoin[{base, "Samples_SideBySide.json"}], sideBySide, "JSON"];

(* Colored subset comparison tables (LaTeX) *)
subsetVis = subset4;
rowLaTeX[row_List, subset_List, color_String] := StringRiffle[Table[If[MemberQ[subset, c], "\\textcolor{"<>color<>"}{"<>ToString[row[[c]]]<>"}", ToString[row[[c]]]], {c, 1, Length[row]}], " & "] <> " \\\\";
tableLaTeX[rows_List, subset_List, color_String] := Module[{spec}, spec = StringJoin @@ Table["c", {Length[rows[[1]]]}]; StringJoin["\\begin{tabular}{", spec, "}\n", StringRiffle[Table[rowLaTeX[rows[[r]], subset, color], {r, Length[rows]}], "\n"], "\n\\end{tabular}"]];
baseColored = tableLaTeX[samplesBase, subsetVis, "red"];
anaColored = tableLaTeX[samplesAna, subsetVis, "blue"];
Export[FileNameJoin[{base, "SubsetComparison_Base.tex"}], baseColored, "Text"];
Export[FileNameJoin[{base, "SubsetComparison_Analytic.tex"}], anaColored, "Text"];