baseDir = DirectoryName[$InputFileName];
(* AUDIT03/R2a.2 — weights, allOffsets and givePlaces now come from the single
   owner CausalBoolCore.wl. This script previously defined them locally, and its
   allOffsets lacked the empty-ws guard the other two copies carried; the three
   were verified functionally identical before the collapse (126/126 cases,
   audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl). *)
Get[FileNameJoin[{baseDir, "..", "lib", "CausalBoolCore.wl"}]];

cm06 = {
  {1, 0, 0, 0, 0, 0},
  {0, 1, 0, 0, 0, 0},
  {0, 0, 1, 0, 0, 0},
  {1, 0, 0, 1, 0, 0},
  {0, 1, 0, 1, 0, 0},
  {1, 0, 1, 0, 1, 0}
};

dyn06 = {"OR", "NOT", "OR", "IMPLIES", "AND", "XOR"};

onPossibleBehaviour[mechanism_List, substate_List, dynVector_List, cm_List] := Module[
  {target, desired, n, connected, decimalAnchor, sumandos},
  target = First[mechanism];
  desired = First[substate];
  n = Length[dynVector];
  connected = Flatten@Position[cm[[target]], 1];
  Which[
    dynVector[[target]] === "AND" && desired === 1,
      decimalAnchor = {1 + Total[2^(connected - 1)]};
      sumandos = allOffsets[n, connected];
      <|"DecimalRepertoire" -> decimalAnchor, "Sumandos" -> sumandos|>,
    True,
      $Failed
  ]
];

xor06Representation[] := Module[
  {baseLocations, sumandos},
  baseLocations = Sort@Cases[
    Table[
      If[
        Mod[x1 + x3 + Boole[x2 == 1 && x4 == 1], 2] == 1,
        1 + x1 + 2 x2 + 4 x3 + 8 x4,
        Nothing
      ],
      {x4, 0, 1}, {x3, 0, 1}, {x2, 0, 1}, {x1, 0, 1}
    ],
    _Integer,
    Infinity
  ];
  sumandos = Sort[(# . {16, 32}) & /@ Tuples[{0, 1}, 2]];
  <|"DecimalRepertoire" -> baseLocations, "Sumandos" -> sumandos|>
];

inputs06 = Reverse /@ IntegerDigits[Range[0, 2^6 - 1], 2, 6];

networkUpdate[input_List] := Module[
  {y1, y2, y3, y4, y5, y6},
  y1 = input[[1]];
  y2 = Boole[input[[2]] == 0];
  y3 = input[[3]];
  y4 = Boole[input[[1]] == 0 || input[[4]] == 1];
  y5 = Boole[input[[2]] == 1 && input[[4]] == 1];
  y6 = Mod[input[[1]] + input[[3]] + y5, 2];
  {y1, y2, y3, y4, y5, y6}
];

outputs06 = networkUpdate /@ inputs06;

res061 = onPossibleBehaviour[{5}, {1}, dyn06, cm06];
places061 = givePlaces[res061["DecimalRepertoire"], res061["Sumandos"]];
baseline061 = Flatten@Position[outputs06[[All, 5]], 1];
verified061Q = Sort[places061] === Sort[baseline061];

res062 = xor06Representation[];
places062 = givePlaces[res062["DecimalRepertoire"], res062["Sumandos"]];
baseline062 = Flatten@Position[outputs06[[All, 6]], 1];
verified062Q = Sort[places062] === Sort[baseline062];

If[!TrueQ[verified061Q && verified062Q],
  Print["Verification failed for corroboration_6node.wl"];
  Exit[1];
];

formatVector[vec_List] := StringJoin[ToString /@ vec];

rowsTex = Table[
  Module[{idx = i, inStr, outStr, highlightAndQ, highlightXorQ, y5Cell, y6Cell},
    inStr = formatVector[inputs06[[i]]];
    outStr = formatVector[outputs06[[i]]];
    highlightAndQ = MemberQ[places061, i];
    highlightXorQ = MemberQ[places062, i];
    y5Cell = If[
      highlightAndQ,
      "\\textbf{\\textcolor{red}{" <> ToString[outputs06[[i, 5]]] <> "}}",
      ToString[outputs06[[i, 5]]]
    ];
    y6Cell = If[
      highlightXorQ,
      "\\textbf{\\textcolor{blue}{" <> ToString[outputs06[[i, 6]]] <> "}}",
      ToString[outputs06[[i, 6]]]
    ];
    ToString[idx] <> " & \\texttt{" <> inStr <> "} & \\texttt{" <> outStr <> "} & " <> y5Cell <> " & " <> y6Cell <> " \\\\"
  ],
  {i, 1, Length[inputs06]}
];

sessionLinesAnd = {
  "In := cm06 = " <> ToString[InputForm[cm06]],
  "In := dyn06 = " <> ToString[InputForm[dyn06]],
  "",
  "(* Computing places in output repertoire where node 5 = 1 *)",
  "In := res061 = onPossibleBehaviour[{5}, {1}, dyn06, cm06]",
  "",
  "(* Summarized representation of analytic behaviour *)",
  "In := gp06 = givePlaces[res061[\"DecimalRepertoire\"], res061[\"Sumandos\"]]",
  "",
  "(* Compressed representation of analytic behaviour *)",
  "Out = " <> ToString[InputForm[res061]],
  "",
  "(* Unfolded representation of analytic behaviour *)",
  "Out = " <> ToString[InputForm[places061]],
  "",
  "(* Exact corroboration against exhaustive outputs of node 5 *)",
  "Out = " <> ToString[InputForm[verified061Q]]
};

sessionLinesXor = {
  "In := cm06 = " <> ToString[InputForm[cm06]],
  "In := dyn06 = " <> ToString[InputForm[dyn06]],
  "",
  "(* Computing places in output repertoire where node 6 = 1 *)",
  "In := res062 = xor06Representation[]",
  "",
  "(* Summarized representation of analytic behaviour *)",
  "In := gp06xor = givePlaces[res062[\"DecimalRepertoire\"], res062[\"Sumandos\"]]",
  "",
  "(* Compressed representation of analytic behaviour *)",
  "Out = " <> ToString[InputForm[res062]],
  "",
  "(* Unfolded representation of analytic behaviour *)",
  "Out = " <> ToString[InputForm[places062]],
  "",
  "(* Exact corroboration against exhaustive outputs of node 6 *)",
  "Out = " <> ToString[InputForm[verified062Q]]
};

summary = <|
  "AdjacencyMatrix" -> cm06,
  "Dynamic" -> dyn06,
  "AND" -> <|
    "DecimalRepertoire" -> res061["DecimalRepertoire"],
    "Sumandos" -> res061["Sumandos"],
    "PredictedIndices" -> places061,
    "BaselineIndices" -> baseline061,
    "Verified" -> verified061Q
  |>,
  "XOR" -> <|
    "DecimalRepertoire" -> res062["DecimalRepertoire"],
    "Sumandos" -> res062["Sumandos"],
    "PredictedIndices" -> places062,
    "BaselineIndices" -> baseline062,
    "Verified" -> verified062Q
  |>
|>;

Export[FileNameJoin[{baseDir, "session_excerpt.txt"}], StringRiffle[sessionLinesAnd, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "session_excerpt_and.txt"}], StringRiffle[sessionLinesAnd, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "session_excerpt_xor.txt"}], StringRiffle[sessionLinesXor, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "exhaustive_rows.tex"}], StringRiffle[rowsTex, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "exhaustive_rows_part1.tex"}], StringRiffle[Take[rowsTex, 32], "\n"], "Text"];
Export[FileNameJoin[{baseDir, "exhaustive_rows_part2.tex"}], StringRiffle[Take[rowsTex, -32], "\n"], "Text"];
Export[FileNameJoin[{baseDir, "summary.json"}], Normal[summary], "JSON"];
Export[FileNameJoin[{baseDir, "inputs_outputs.csv"}],
  Prepend[
    Table[
      {
        i,
        formatVector[inputs06[[i]]],
        formatVector[outputs06[[i]]],
        outputs06[[i, 5]],
        outputs06[[i, 6]],
        If[MemberQ[places061, i], 1, 0],
        If[MemberQ[places062, i], 1, 0]
      },
      {i, 1, Length[inputs06]}
    ],
    {"Index", "InputVector", "OutputVector", "TargetY5", "TargetY6", "HighlightedY5", "HighlightedY6"}
  ],
  "CSV"
];

Print[StringRiffle[Join[sessionLinesAnd, {""}, sessionLinesXor], "\n"]];
