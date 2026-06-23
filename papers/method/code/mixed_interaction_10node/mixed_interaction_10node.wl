baseDir = DirectoryName[$InputFileName];
projectRoot = Nest[DirectoryName, baseDir, 4];

AppendTo[$Path, FileNameJoin[{projectRoot, "src", "Packages"}]];
Needs["Integration`Experiments`"];

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

ics10 = Table[Flatten@Position[cm10[[k]], 1], {k, 1, n10}];
dispatch10 = Integration`Experiments`CreateRepertoiresDispatch[cm10, dyn10, params10];
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

selectedNodes = {4, 6, 7, 10};
selectedPattern = {0, 1, 1, 1};

conditionSet[node_Integer, bit_Integer] := If[
  bit == 1,
  oneSets10[[node]],
  Complement[allIndices10, oneSets10[[node]]]
];

selectedIndicesAnalytic = Sort@Fold[
  Intersection,
  allIndices10,
  MapThread[conditionSet, {selectedNodes, selectedPattern}]
];

selectedIndicesBaseline = Flatten@Position[outputs10[[All, selectedNodes]], selectedPattern, 1];
selectedVerifiedQ = Sort[selectedIndicesAnalytic] === Sort[selectedIndicesBaseline];

If[!And @@ nodeVerification10 || !TrueQ[selectedVerifiedQ],
  Print["Verification failed for mixed_interaction_10node.wl"];
  Exit[1];
];

formatVector[vec_List] := StringJoin[ToString /@ vec];

selectedRowsTex = Table[
  Module[{idx = i, inStr, outStr},
    inStr = formatVector[inputs10[[i]]];
    outStr = formatVector[outputs10[[i]]];
    ToString[idx] <>
      " & \\texttt{" <> inStr <> "}" <>
      " & \\texttt{" <> outStr <> "}" <>
      " & \\textbf{" <> ToString[outputs10[[i, 4]]] <> "}" <>
      " & \\textbf{" <> ToString[outputs10[[i, 6]]] <> "}" <>
      " & \\textbf{" <> ToString[outputs10[[i, 7]]] <> "}" <>
      " & \\textbf{" <> ToString[outputs10[[i, 10]]] <> "} \\\\"
  ],
  {i, selectedIndicesAnalytic}
];

sessionLines = {
  "In := cm10 = " <> ToString[InputForm[cm10]],
  "In := dyn10 = " <> ToString[InputForm[dyn10]],
  "In := params10 = " <> ToString[InputForm[params10]],
  "",
  "(* Computing the mixed output condition {y4, y6, y7, y10} = {0, 1, 1, 1} *)",
  "In := selected10 = " <> ToString[InputForm[selectedIndicesAnalytic]],
  "",
  "(* Verifying that every local analytic one-set matches the exhaustive baseline *)",
  "In := checks10 = " <> ToString[InputForm[nodeVerification10]],
  "",
  "(* Exact corroboration for the selected mixed pattern *)",
  "Out = " <> ToString[InputForm[selectedVerifiedQ]]
};

summary = <|
  "AdjacencyMatrix" -> cm10,
  "Dynamic" -> dyn10,
  "Parameters" -> KeyValueMap[ToString[#1] -> #2 &, params10],
  "SelectedNodes" -> selectedNodes,
  "SelectedPattern" -> selectedPattern,
  "NodeVerification" -> nodeVerification10,
  "SelectedIndices" -> selectedIndicesAnalytic,
  "SelectedCount" -> Length[selectedIndicesAnalytic],
  "SelectedVerified" -> selectedVerifiedQ
|>;

Export[FileNameJoin[{baseDir, "session_excerpt.txt"}], StringRiffle[sessionLines, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "selected_rows.tex"}], StringRiffle[selectedRowsTex, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "selected_indices.csv"}], List /@ selectedIndicesAnalytic, "CSV"];
Export[FileNameJoin[{baseDir, "selected_rows.csv"}],
  Prepend[
    Table[
      {
        i,
        formatVector[inputs10[[i]]],
        formatVector[outputs10[[i]]],
        outputs10[[i, 4]],
        outputs10[[i, 6]],
        outputs10[[i, 7]],
        outputs10[[i, 10]]
      },
      {i, selectedIndicesAnalytic}
    ],
    {"Index", "InputVector", "OutputVector", "Y4", "Y6", "Y7", "Y10"}
  ],
  "CSV"
];
Export[FileNameJoin[{baseDir, "summary.json"}], Normal[summary], "JSON"];

Print[StringRiffle[sessionLines, "\n"]];
