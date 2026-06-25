baseDir = DirectoryName[$InputFileName];
Get[FileNameJoin[{baseDir, "..", "lib", "CausalBoolCore.wl"}]];

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

n10 = Length[dyn10];
allIndices10 = Range[1, 2^n10];

weights[n_Integer] := 2^Range[0, n - 1];

allOffsets[n_Integer, connected_List] := Module[
  {free = Complement[Range[n], connected], ws},
  ws = weights[n][[free]];
  If[Length[ws] == 0, {0}, Sort[(# . ws) & /@ Tuples[{0, 1}, Length[ws]]]]
];

givePlaces[locations_List, sumandos_List] := Sort@Flatten[Table[loc + sumandos, {loc, locations}]];

indexSetAnalytic[n_Integer, Ic_List, gate_String, params_Association : <||>] := Module[
  {free, pow, d, indexFromPos, subsFree, k, strict, pair, a, b, ii},
  free = Complement[Range[n], Ic];
  pow = weights[n];
  d = Length[Ic];
  indexFromPos[pos_List] := 1 + Total[pow[[pos]]];
  subsFree = Subsets[free];
  Which[
    gate === "AND",
      indexFromPos[Join[Ic, #]] & /@ subsFree,
    gate === "OR",
      Complement[Range[1, 2^n], indexFromPos /@ subsFree],
    gate === "XOR",
      Module[{assigns},
        assigns = Select[Tuples[{0, 1}, d], Mod[Total[#], 2] == 1 &];
        Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]
      ],
    gate === "XNOR",
      Module[{assigns},
        assigns = Select[Tuples[{0, 1}, d], Mod[Total[#], 2] == 0 &];
        Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]
      ],
    gate === "NAND",
      Complement[Range[1, 2^n], indexFromPos[Join[Ic, #]] & /@ subsFree],
    gate === "NOR",
      indexFromPos /@ subsFree,
    gate === "NOT",
      ii = Lookup[params, "i", First[Ic]];
      indexFromPos /@ Subsets[Complement[Range[n], {ii}]],
    gate === "IMPLIES",
      pair = Lookup[params, "pair", Ic[[;; 2]]];
      a = pair[[1]];
      b = pair[[2]];
      Complement[
        Range[1, 2^n],
        indexFromPos /@ (Join[{a}, #] & /@ Subsets[Complement[Range[n], {a, b}]])
      ],
    gate === "NIMPLIES",
      pair = Lookup[params, "pair", Ic[[;; 2]]];
      a = pair[[1]];
      b = pair[[2]];
      indexFromPos /@ (Join[{a}, #] & /@ Subsets[Complement[Range[n], {a, b}]]),
    gate === "MAJORITY",
      Module[{t, assigns},
        t = Floor[d/2] + 1;
        assigns = Select[Tuples[{0, 1}, d], Total[#] >= t &];
        Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]
      ],
    gate === "KOFN",
      Module[{assigns},
        k = Lookup[params, "k", 1];
        strict = TrueQ[Lookup[params, "strict", False]];
        assigns = Select[Tuples[{0, 1}, d], If[strict, Total[#] > k, Total[#] >= k] &];
        Flatten@Table[
          indexFromPos[Join[Pick[Ic, assigns[[u]], 1], s]],
          {u, Length[assigns]}, {s, subsFree}
        ]
      ],
    True,
      {}
  ]
];

formatVector[vec_List] := StringJoin[ToString /@ vec];
texSet[list_List] := "\\(\\{" <> StringRiffle[ToString /@ list, ", "] <> "\\}\\)";
texVector[list_List] := "\\texttt{" <> formatVector[list] <> "}";
texNodeSet[list_List] := texSet[list];

ics10 = Table[Flatten@Position[cm10[[k]], 1], {k, 1, n10}];
dispatch10 = CreateRepertoiresDispatch[cm10, dyn10, params10];
inputs10 = Normal@dispatch10["RepertoireInputs"];
outputs10 = Normal@dispatch10["RepertoireOutputs"];

oneSets10 = Table[
  Sort@indexSetAnalytic[n10, ics10[[k]], dyn10[[k]], Lookup[params10, k, <||>]],
  {k, 1, n10}
];

baselineOneSets10 = Table[
  Flatten@Position[outputs10[[All, k]], 1],
  {k, 1, n10}
];

nodeVerification10 = Table[
  Sort[oneSets10[[k]]] === Sort[baselineOneSets10[[k]]],
  {k, 1, n10}
];

conditionSet[node_Integer, bit_Integer] := If[
  bit == 1,
  oneSets10[[node]],
  Complement[allIndices10, oneSets10[[node]]]
];

queryIndices[nodes_List, pattern_List] := Sort@Fold[
  Intersection,
  allIndices10,
  MapThread[conditionSet, {nodes, pattern}]
];

queryBaseline[nodes_List, pattern_List] := Flatten@Position[outputs10[[All, nodes]], pattern, 1];

mixedQueryRepresentation[nodes_List, pattern_List] := Module[
  {analytic, unionCoords, sumandos, baseIndices},
  analytic = queryIndices[nodes, pattern];
  unionCoords = Sort@DeleteDuplicates@Flatten[ics10[[nodes]]];
  sumandos = allOffsets[n10, unionCoords];
  baseIndices = Select[
    analytic,
    Function[idx, AllTrue[Complement[Range[n10], unionCoords], inputs10[[idx, #]] == 0 &]]
  ];
  <|"DecimalRepertoire" -> baseIndices, "Sumandos" -> sumandos|>
];

fullCases = {
  <|"Name" -> "F1", "Kind" -> "Full", "Description" -> "All outputs active", "SelectedNodes" -> Range[10], "SelectedPattern" -> {1, 1, 1, 1, 1, 1, 1, 1, 1, 1}|>,
  <|"Name" -> "F2", "Kind" -> "Full", "Description" -> "All active except y10", "SelectedNodes" -> Range[10], "SelectedPattern" -> {1, 1, 1, 1, 1, 1, 1, 1, 1, 0}|>,
  <|"Name" -> "F3", "Kind" -> "Full", "Description" -> "All active except y9", "SelectedNodes" -> Range[10], "SelectedPattern" -> {1, 1, 1, 1, 1, 1, 1, 1, 0, 1}|>,
  <|"Name" -> "F4", "Kind" -> "Full", "Description" -> "All active except y6", "SelectedNodes" -> Range[10], "SelectedPattern" -> {1, 1, 1, 1, 1, 0, 1, 1, 1, 1}|>
};

subsystemCases = {
  <|"Name" -> "S1", "Kind" -> "Subsystem", "Description" -> "Threshold-XNOR-NOT-majority event", "SelectedNodes" -> {4, 6, 7, 10}, "SelectedPattern" -> {0, 1, 1, 1}|>,
  <|"Name" -> "S2", "Kind" -> "Subsystem", "Description" -> "Six-gate mixed interaction event", "SelectedNodes" -> {4, 6, 7, 8, 9, 10}, "SelectedPattern" -> {0, 1, 1, 1, 0, 1}|>
};

enrichCase[case_Association] := Module[
  {nodes, pattern, analytic, baseline, verifiedQ, anchor, offsets, representation},
  nodes = case["SelectedNodes"];
  pattern = case["SelectedPattern"];
  analytic = queryIndices[nodes, pattern];
  baseline = queryBaseline[nodes, pattern];
  verifiedQ = Sort[analytic] === Sort[baseline];
  anchor = First[analytic];
  offsets = analytic - anchor;
  representation = mixedQueryRepresentation[nodes, pattern];
  Join[
    case,
    <|
      "PatternString" -> formatVector[pattern],
      "AnalyticIndices" -> analytic,
      "BaselineIndices" -> baseline,
      "Verified" -> verifiedQ,
      "Count" -> Length[analytic],
      "Anchor" -> anchor,
      "Offsets" -> offsets,
      "DecimalRepertoire" -> representation["DecimalRepertoire"],
      "Sumandos" -> representation["Sumandos"]
    |>
  ]
];

caseStats[result_Association] := Module[
  {nodes, unionCoords, freeCoords, degreeSum, overlapMultiplicity},
  nodes = result["SelectedNodes"];
  unionCoords = Sort@DeleteDuplicates@Flatten[ics10[[nodes]]];
  freeCoords = Complement[Range[n10], unionCoords];
  degreeSum = Total[Length /@ ics10[[nodes]]];
  overlapMultiplicity = degreeSum - Length[unionCoords];
  Join[
    result,
    <|
      "CoordinateUnion" -> unionCoords,
      "FreeCoordinates" -> freeCoords,
      "DegreeSum" -> degreeSum,
      "UnionSize" -> Length[unionCoords],
      "OverlapMultiplicity" -> overlapMultiplicity,
      "ReductionFactor" -> 2^overlapMultiplicity,
      "BaseIndicesZeroFree" -> Select[
        result["AnalyticIndices"],
        Function[idx, AllTrue[freeCoords, inputs10[[idx, #]] == 0 &]]
      ]
    |>
  ]
];

fullResults = enrichCase /@ fullCases;
subsystemResults = enrichCase /@ subsystemCases;
fullResults = caseStats /@ fullResults;
subsystemResults = caseStats /@ subsystemResults;
allCaseResults = Join[fullResults, subsystemResults];

resF110 = mixedQueryRepresentation[fullCases[[1, "SelectedNodes"]], fullCases[[1, "SelectedPattern"]]];
gpF110 = givePlaces[resF110["DecimalRepertoire"], resF110["Sumandos"]];
verifiedF110Q = Sort[gpF110] === Sort[fullResults[[1, "BaselineIndices"]]];

resF210 = mixedQueryRepresentation[fullCases[[2, "SelectedNodes"]], fullCases[[2, "SelectedPattern"]]];
gpF210 = givePlaces[resF210["DecimalRepertoire"], resF210["Sumandos"]];
verifiedF210Q = Sort[gpF210] === Sort[fullResults[[2, "BaselineIndices"]]];

resF310 = mixedQueryRepresentation[fullCases[[3, "SelectedNodes"]], fullCases[[3, "SelectedPattern"]]];
gpF310 = givePlaces[resF310["DecimalRepertoire"], resF310["Sumandos"]];
verifiedF310Q = Sort[gpF310] === Sort[fullResults[[3, "BaselineIndices"]]];

resF410 = mixedQueryRepresentation[fullCases[[4, "SelectedNodes"]], fullCases[[4, "SelectedPattern"]]];
gpF410 = givePlaces[resF410["DecimalRepertoire"], resF410["Sumandos"]];
verifiedF410Q = Sort[gpF410] === Sort[fullResults[[4, "BaselineIndices"]]];

resS110 = mixedQueryRepresentation[subsystemCases[[1, "SelectedNodes"]], subsystemCases[[1, "SelectedPattern"]]];
gpS110 = givePlaces[resS110["DecimalRepertoire"], resS110["Sumandos"]];
verifiedS110Q = Sort[gpS110] === Sort[subsystemResults[[1, "BaselineIndices"]]];

resS210 = mixedQueryRepresentation[subsystemCases[[2, "SelectedNodes"]], subsystemCases[[2, "SelectedPattern"]]];
gpS210 = givePlaces[resS210["DecimalRepertoire"], resS210["Sumandos"]];
verifiedS210Q = Sort[gpS210] === Sort[subsystemResults[[2, "BaselineIndices"]]];

If[!And @@ nodeVerification10 || !And @@ (Lookup[allCaseResults, "Verified"]),
  Print["Verification failed for mixed_interaction_10node.wl"];
  Exit[1];
];

fullSummaryRowsTex = Table[
  Module[{case = fullResults[[k]]},
    case["Name"] <> " & " <>
      "\\texttt{" <> case["PatternString"] <> "} & " <>
      ToString[case["Anchor"]] <> " & " <>
      texSet[case["Offsets"]] <> " & " <>
      texSet[case["AnalyticIndices"]] <> " & " <>
      ToString[case["Count"]] <> " \\\\"
  ],
  {k, Length[fullResults]}
];

subsystemSummaryRowsTex = Table[
  Module[{case = subsystemResults[[k]]},
    case["Name"] <> " & " <>
      texNodeSet[case["SelectedNodes"]] <> " & " <>
      "\\texttt{" <> case["PatternString"] <> "} & " <>
      ToString[case["Anchor"]] <> " & " <>
      texSet[case["Offsets"]] <> " & " <>
      texSet[case["AnalyticIndices"]] <> " & " <>
      ToString[case["Count"]] <> " \\\\"
  ],
  {k, Length[subsystemResults]}
];

fullRowsTex = Flatten@Table[
  Module[{case = fullResults[[k]]},
    Table[
      case["Name"] <> " & " <>
        ToString[i] <> " & " <>
        texVector[inputs10[[i]]] <> " & " <>
        texVector[outputs10[[i]]] <> " \\\\",
      {i, case["AnalyticIndices"]}
    ]
  ],
  {k, Length[fullResults]}
];

subsystemRowsTex = Flatten@Table[
  Module[{case = subsystemResults[[k]], nodes = subsystemResults[[k, "SelectedNodes"]]},
    Table[
      case["Name"] <> " & " <>
        "\\texttt{" <> formatVector[outputs10[[i, nodes]]] <> "} & " <>
        ToString[i] <> " & " <>
        texVector[inputs10[[i]]] <> " & " <>
        texVector[outputs10[[i]]] <> " \\\\",
      {i, case["AnalyticIndices"]}
    ]
  ],
  {k, Length[subsystemResults]}
];

fullRowsCsv = Flatten@Table[
  Module[{case = fullResults[[k]]},
    Table[
      {
        case["Name"],
        case["PatternString"],
        i,
        formatVector[inputs10[[i]]],
        formatVector[outputs10[[i]]]
      },
      {i, case["AnalyticIndices"]}
    ]
  ],
  {k, Length[fullResults]}
];

subsystemRowsCsv = Flatten@Table[
  Module[{case = subsystemResults[[k]], nodes = subsystemResults[[k, "SelectedNodes"]]},
    Table[
      {
        case["Name"],
        formatVector[case["SelectedPattern"]],
        i,
        formatVector[inputs10[[i]]],
        formatVector[outputs10[[i]]],
        formatVector[outputs10[[i, nodes]]]
      },
      {i, case["AnalyticIndices"]}
    ]
  ],
  {k, Length[subsystemResults]}
];

sessionDisplay[result_Association] := <|
  "Name" -> result["Name"],
  "Pattern" -> result["PatternString"],
  "DecimalRepertoire" -> result["DecimalRepertoire"],
  "Sumandos" -> result["Sumandos"],
  "Indices" -> result["AnalyticIndices"],
  "Verified" -> result["Verified"]
|>;

statsDisplay[result_Association] := <|
  "Name" -> result["Name"],
  "Union" -> result["CoordinateUnion"],
  "Free" -> result["FreeCoordinates"],
  "DegreeSum" -> result["DegreeSum"],
  "UnionSize" -> result["UnionSize"],
  "OverlapMultiplicity" -> result["OverlapMultiplicity"],
  "ReductionFactor" -> result["ReductionFactor"]
|>;

caseSessionLines[result_Association, resName_String, gpName_String, resValue_Association, gpValue_List, verifiedQ_] := {
  "(* " <> result["Name"] <> ": " <> result["Description"] <> " *)",
  "In := " <> resName <> " = mixedQueryRepresentation[" <>
    ToString[InputForm[result["SelectedNodes"]]] <> ", " <>
    ToString[InputForm[result["SelectedPattern"]]] <> "]",
  "",
  "(* Unfolding the compressed representation *)",
  "In := " <> gpName <> " = givePlaces[" <> resName <> "[\"DecimalRepertoire\"], " <> resName <> "[\"Sumandos\"]]",
  "",
  "(* Compressed representation of the query *)",
  "Out = " <> ToString[InputForm[resValue]],
  "",
  "(* Exact unfolded repertoire indices *)",
  "Out = " <> ToString[InputForm[gpValue]],
  "",
  "(* Exact corroboration against the exhaustive baseline *)",
  "Out = " <> ToString[InputForm[verifiedQ]]
};

sessionHeaderLines = {
  "In := cm10 = " <> ToString[InputForm[cm10]],
  "In := dyn10 = " <> ToString[InputForm[dyn10]],
  "In := params10 = " <> ToString[InputForm[params10]],
  ""
};

sessionLinesFull = Join[
  sessionHeaderLines,
  Riffle[
    {
      caseSessionLines[fullResults[[1]], "resF110", "gpF110", resF110, gpF110, verifiedF110Q],
      caseSessionLines[fullResults[[2]], "resF210", "gpF210", resF210, gpF210, verifiedF210Q],
      caseSessionLines[fullResults[[3]], "resF310", "gpF310", resF310, gpF310, verifiedF310Q],
      caseSessionLines[fullResults[[4]], "resF410", "gpF410", resF410, gpF410, verifiedF410Q]
    },
    {""}
  ] // Flatten
];

sessionLinesSubsystem = Join[
  sessionHeaderLines,
  Riffle[
    {
      caseSessionLines[subsystemResults[[1]], "resS110", "gpS110", resS110, gpS110, verifiedS110Q],
      caseSessionLines[subsystemResults[[2]], "resS210", "gpS210", resS210, gpS210, verifiedS210Q]
    },
    {""}
  ] // Flatten
];

sessionLines = Join[
  sessionHeaderLines,
  {
    "In := overlapStats10 = " <> ToString[InputForm[statsDisplay /@ allCaseResults]],
    "In := baseS110 = " <> ToString[InputForm[<|"CoordinateUnion" -> subsystemResults[[1, "CoordinateUnion"]], "FreeCoordinates" -> subsystemResults[[1, "FreeCoordinates"]], "BaseIndices" -> subsystemResults[[1, "BaseIndicesZeroFree"]]|>]],
    "",
    "(* Verifying that every local analytic one-set matches the exhaustive baseline *)",
    "In := checks10 = " <> ToString[InputForm[nodeVerification10]],
    "",
    "(* Exact corroboration for all six mixed-query cases *)",
    "Out = " <> ToString[InputForm[And @@ Lookup[allCaseResults, "Verified"]]]
  }
];

summary = <|
  "AdjacencyMatrix" -> cm10,
  "Dynamic" -> dyn10,
  "Parameters" -> KeyValueMap[ToString[#1] -> #2 &, params10],
  "NodeVerification" -> nodeVerification10,
  "FullCases" -> (KeyDrop[#, {"BaselineIndices"}] & /@ fullResults),
  "SubsystemCases" -> (KeyDrop[#, {"BaselineIndices"}] & /@ subsystemResults)
|>;

exportText[file_, lines_List] := Export[file, StringRiffle[lines, "\n"] <> "\n", "Text"];

exportText[FileNameJoin[{baseDir, "session_excerpt.txt"}], sessionLines];
exportText[FileNameJoin[{baseDir, "session_excerpt_full.txt"}], sessionLinesFull];
exportText[FileNameJoin[{baseDir, "session_excerpt_subsystem.txt"}], sessionLinesSubsystem];
exportText[FileNameJoin[{baseDir, "full_case_summary_rows.tex"}], fullSummaryRowsTex];
exportText[FileNameJoin[{baseDir, "subsystem_case_summary_rows.tex"}], subsystemSummaryRowsTex];
exportText[FileNameJoin[{baseDir, "full_case_rows.tex"}], fullRowsTex];
exportText[FileNameJoin[{baseDir, "subsystem_case_rows.tex"}], subsystemRowsTex];

Export[FileNameJoin[{baseDir, "full_case_rows.csv"}],
  Prepend[fullRowsCsv, {"Case", "TargetPattern", "Index", "InputVector", "OutputVector"}],
  "CSV"
];

Export[FileNameJoin[{baseDir, "subsystem_case_rows.csv"}],
  Prepend[subsystemRowsCsv, {"Case", "TargetProjection", "Index", "InputVector", "OutputVector", "Projection"}],
  "CSV"
];

Export[FileNameJoin[{baseDir, "summary.json"}], Normal[summary], "JSON"];

Print[StringRiffle[Join[sessionLinesFull, {""}, sessionLinesSubsystem, {""}, sessionLines], "\n"]];
