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
states10 = Reverse /@ IntegerDigits[Range[0, 2^n10 - 1], 2, n10];
stateToIndex10 = AssociationThread[states10, Range[Length[states10]]];

formatVector[vec_List] := StringJoin[ToString /@ vec];
texSet[list_List] := "\\(\\{" <> StringRiffle[ToString /@ list, ", "] <> "\\}\\)";

nextState10[state_List] := Module[{inputs, gate, p},
  Table[
    inputs = state[[Flatten@Position[cm10[[i]], 1]]];
    gate = dyn10[[i]];
    p = Lookup[params10, i, <||>];
    Which[
      gate === "IMPLIES" || gate === "NIMPLIES",
        ApplyGate[gate, {state[[p["pair"][[1]]]], state[[p["pair"][[2]]]]}, p],
      gate === "NOT",
        ApplyGate[gate, {First[inputs]}, p],
      True,
        ApplyGate[gate, inputs, p]
    ],
    {i, 1, n10}
  ]
];

nextStates10 = nextState10 /@ states10;
imageStates10 = DeleteDuplicates[nextStates10];
imageIndices10 = Sort[stateToIndex10 /@ imageStates10];

nextIndices10 = stateToIndex10 /@ nextStates10;

findCyclesFunctional[nextIdx_List] := Module[
  {n, status, cycles, start, current, path, pos, cycle},
  n = Length[nextIdx];
  status = ConstantArray[0, n];
  cycles = {};
  Do[
    If[status[[start]] =!= 0, Continue[]];
    path = {};
    pos = <||>;
    current = start;
    While[status[[current]] == 0 && !KeyExistsQ[pos, current],
      pos[current] = Length[path] + 1;
      AppendTo[path, current];
      current = nextIdx[[current]];
    ];
    If[KeyExistsQ[pos, current],
      cycle = path[[pos[current]] ;;];
      AppendTo[cycles, cycle];
    ];
    Scan[(status[[#]] = 1) &, path];
    ,
    {start, 1, n}
  ];
  cycles
];

cycleIndexLists10 = findCyclesFunctional[nextIndices10];
cycles10 = states10[[#]] & /@ cycleIndexLists10;

cycleIdByState10 = Association@Flatten@Table[
  state -> k,
  {k, 1, Length[cycles10]},
  {state, cycles10[[k]]}
];

eventualCycleId10[state_List] := Module[{seen = <||>, current = state, step = 0},
  While[!KeyExistsQ[cycleIdByState10, current],
    If[KeyExistsQ[seen, current], Return[Missing["NoCycleFound"]]];
    seen[current] = step;
    current = nextState10[current];
    step++
  ];
  cycleIdByState10[current]
];

transientLength10[state_List] := Module[{current = state, step = 0},
  While[!KeyExistsQ[cycleIdByState10, current],
    current = nextState10[current];
    step++
  ];
  step
];

basinCounts10 = Counts[eventualCycleId10 /@ states10];

cycleSummary10 = Table[
  <|
    "CycleID" -> k,
    "Period" -> Length[cycles10[[k]]],
    "States" -> cycles10[[k]],
    "StateStrings" -> (formatVector /@ cycles10[[k]]),
    "BasinSize" -> Lookup[basinCounts10, k, 0]
  |>,
  {k, 1, Length[cycles10]}
];

fullCases10 = {
  <|"Name" -> "F1", "Pattern" -> {1, 1, 1, 1, 1, 1, 1, 1, 1, 1}|>,
  <|"Name" -> "F2", "Pattern" -> {1, 1, 1, 1, 1, 1, 1, 1, 1, 0}|>,
  <|"Name" -> "F3", "Pattern" -> {1, 1, 1, 1, 1, 1, 1, 1, 0, 1}|>,
  <|"Name" -> "F4", "Pattern" -> {1, 1, 1, 1, 1, 0, 1, 1, 1, 1}|>
};

subsystemCases10 = {
  <|"Name" -> "S1", "Nodes" -> {4, 6, 7, 10}, "Projection" -> {0, 1, 1, 1}|>,
  <|"Name" -> "S2", "Nodes" -> {4, 6, 7, 8, 9, 10}, "Projection" -> {0, 1, 1, 1, 0, 1}|>
};

fullCaseStatus10 = Table[
  Module[{pattern, idx, recurrentQ, cycleId, next},
    pattern = fullCases10[[k, "Pattern"]];
    idx = Lookup[stateToIndex10, pattern];
    recurrentQ = KeyExistsQ[cycleIdByState10, pattern];
    cycleId = If[recurrentQ, cycleIdByState10[pattern], eventualCycleId10[pattern]];
    next = nextState10[pattern];
    Join[
      fullCases10[[k]],
      <|
        "StateIndex" -> idx,
        "ReachableQ" -> MemberQ[imageStates10, pattern],
        "RecurrentQ" -> recurrentQ,
        "CycleID" -> cycleId,
        "TransientLength" -> transientLength10[pattern],
        "NextState" -> next
      |>
    ]
  ],
  {k, Length[fullCases10]}
];

subsystemCaseStatus10 = Table[
  Module[{nodes, projection, matchingRows, distinctOutputs, recurrentOutputs, cycleIds},
    nodes = subsystemCases10[[k, "Nodes"]];
    projection = subsystemCases10[[k, "Projection"]];
    matchingRows = Select[
      Range[Length[nextStates10]],
      nextStates10[[#, nodes]] == projection &
    ];
    distinctOutputs = DeleteDuplicates[nextStates10[[matchingRows]]];
    recurrentOutputs = Select[distinctOutputs, KeyExistsQ[cycleIdByState10, #] &];
    cycleIds = DeleteDuplicates[eventualCycleId10 /@ distinctOutputs];
    Join[
      subsystemCases10[[k]],
      <|
        "MatchingRowIndices" -> matchingRows,
        "RowCount" -> Length[matchingRows],
        "DistinctOutputs" -> distinctOutputs,
        "DistinctOutputStrings" -> (formatVector /@ distinctOutputs),
        "DistinctOutputCount" -> Length[distinctOutputs],
        "RecurrentOutputs" -> recurrentOutputs,
        "RecurrentOutputStrings" -> (formatVector /@ recurrentOutputs),
        "RecurrentCount" -> Length[recurrentOutputs],
        "CycleIDs" -> cycleIds
      |>
    ]
  ],
  {k, Length[subsystemCases10]}
];

sampleRows10 = Join[
  Table[
    With[{case = fullCaseStatus10[[k]], pattern = fullCaseStatus10[[k, "Pattern"]]},
      <|
        "Case" -> case["Name"],
        "Kind" -> "Full",
        "Pattern" -> formatVector[pattern],
        "StateIndex" -> case["StateIndex"],
        "NextState" -> formatVector[case["NextState"]],
        "RecurrentQ" -> case["RecurrentQ"],
        "CycleID" -> case["CycleID"],
        "TransientLength" -> case["TransientLength"]
      |>
    ],
    {k, Length[fullCaseStatus10]}
  ],
  Flatten@Table[
    With[{case = subsystemCaseStatus10[[k]], out = subsystemCaseStatus10[[k, "DistinctOutputs", j]]},
      <|
        "Case" -> case["Name"],
        "Kind" -> "Subsystem",
        "Pattern" -> formatVector[out],
        "StateIndex" -> stateToIndex10[out],
        "NextState" -> formatVector[nextState10[out]],
        "RecurrentQ" -> KeyExistsQ[cycleIdByState10, out],
        "CycleID" -> eventualCycleId10[out],
        "TransientLength" -> transientLength10[out]
      |>
    ],
    {k, Length[subsystemCaseStatus10]},
    {j, Length[subsystemCaseStatus10[[k, "DistinctOutputs"]]]}
  ]
];

cycleRowsTex = Table[
  Module[{cyc = cycleSummary10[[k]]},
    ToString[cyc["CycleID"]] <> " & " <>
      ToString[cyc["Period"]] <> " & " <>
      ToString[cyc["BasinSize"]] <> " & " <>
      texSet[cyc["StateStrings"]] <> " \\\\"
  ],
  {k, Length[cycleSummary10]}
];

caseRowsTex = Join[
  Table[
    Module[{case = fullCaseStatus10[[k]]},
      case["Name"] <> " & full & \\texttt{" <> formatVector[case["Pattern"]] <> "} & " <>
        ToString[case["StateIndex"]] <> " & " <>
        If[TrueQ[case["ReachableQ"]], "yes", "no"] <> " & " <>
        If[TrueQ[case["RecurrentQ"]], "yes", "no"] <> " & " <>
        "A_" <> ToString[case["CycleID"]] <> " & " <>
        ToString[case["TransientLength"]] <> " \\\\"
    ],
    {k, Length[fullCaseStatus10]}
  ],
  Table[
    Module[{case = subsystemCaseStatus10[[k]]},
      case["Name"] <> " & subsystem & \\texttt{" <> formatVector[case["Projection"]] <> "} & " <>
        ToString[case["RowCount"]] <> " rows / " <> ToString[case["DistinctOutputCount"]] <> " outputs & " <>
        "yes & " <>
        If[case["RecurrentCount"] > 0, ToString[case["RecurrentCount"]] <> " outputs", "no"] <> " & " <>
        texSet[("A_" <> ToString[#]) & /@ case["CycleIDs"]] <> " & --- \\\\"
    ],
    {k, Length[subsystemCaseStatus10]}
  ]
];

sampleRowsTex = Table[
  Module[{row = sampleRows10[[k]]},
    row["Case"] <> " & " <>
      "\\texttt{" <> row["Pattern"] <> "} & " <>
      ToString[row["StateIndex"]] <> " & " <>
      "\\texttt{" <> row["NextState"] <> "} & " <>
      If[TrueQ[row["RecurrentQ"]], "yes", "no"] <> " & " <>
      "A_" <> ToString[row["CycleID"]] <> " & " <>
      ToString[row["TransientLength"]] <> " \\\\"
  ],
  {k, Length[sampleRows10]}
];

sessionLines = {
  "In := cm10 = " <> ToString[InputForm[cm10]],
  "In := dyn10 = " <> ToString[InputForm[dyn10]],
  "In := params10 = " <> ToString[InputForm[params10]],
  "",
  "(* Distinct reachable outputs after one synchronous update *)",
  "In := imageStates10 = " <> ToString[InputForm[imageStates10]],
  "Out = " <> ToString[InputForm[Length[imageStates10]]],
  "",
  "(* Genuine recurrent attractors of the 10-node transition graph *)",
  "In := attractors10 = " <> ToString[InputForm[cycleSummary10[[All, \"StateStrings\"]]]],
  "Out = " <> ToString[InputForm[<|\"Periods\" -> cycleSummary10[[All, \"Period\"]], \"Basins\" -> cycleSummary10[[All, \"BasinSize\"]]|>]],
  "",
  "(* Dynamical status of the four full-output cases *)",
  "In := fullStatus10 = " <> ToString[InputForm[Table[<|\"Name\" -> c[\"Name\"], \"Reachable\" -> c[\"ReachableQ\"], \"Recurrent\" -> c[\"RecurrentQ\"], \"CycleID\" -> c[\"CycleID\"], \"TransientLength\" -> c[\"TransientLength\"]|>, {c, fullCaseStatus10}]]],
  "",
  "(* Dynamical status of the subsystem families *)",
  "In := subsystemStatus10 = " <> ToString[InputForm[Table[<|\"Name\" -> c[\"Name\"], \"Rows\" -> c[\"RowCount\"], \"DistinctOutputs\" -> c[\"DistinctOutputStrings\"], \"RecurrentOutputs\" -> c[\"RecurrentOutputStrings\"], \"CycleIDs\" -> c[\"CycleIDs\"]|>, {c, subsystemCaseStatus10}]]],
  "",
  "Out = True"
};

summary = <|
  "ImageSize" -> Length[imageStates10],
  "ImageStateStrings" -> (formatVector /@ imageStates10),
  "CycleSummary" -> cycleSummary10,
  "FullCases" -> fullCaseStatus10,
  "SubsystemCases" -> subsystemCaseStatus10,
  "SampleRows" -> sampleRows10
|>;

exportText[file_, lines_List] := Export[file, StringRiffle[lines, "\n"] <> "\n", "Text"];

exportText[FileNameJoin[{baseDir, "dynamical_session_excerpt.txt"}], sessionLines];
exportText[FileNameJoin[{baseDir, "dynamical_cycle_rows.tex"}], cycleRowsTex];
exportText[FileNameJoin[{baseDir, "dynamical_case_rows.tex"}], caseRowsTex];
exportText[FileNameJoin[{baseDir, "dynamical_sample_rows.tex"}], sampleRowsTex];
Export[FileNameJoin[{baseDir, "dynamical_summary.json"}], Normal[summary], "JSON"];

Print[StringRiffle[sessionLines, "\n"]];
