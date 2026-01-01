AppendTo[$Path, "src/Packages"];
Needs["Integration`Experiments`"];

base = FileNameJoin[{"results", "tests", "test004"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

readStatus[path_] := If[FileExistsQ[path], StringTrim@Import[path, "Text"], "MISSING"];
status001 = readStatus[FileNameJoin[{"results", "tests", "tests001", "Status.txt"}]];
status002 = readStatus[FileNameJoin[{"results", "tests", "test002", "Status.txt"}]];
status003 = readStatus[FileNameJoin[{"results", "tests", "test003", "Status.txt"}]];

metrics003 = If[FileExistsQ[FileNameJoin[{"results", "tests", "test003", "Metrics.json"}]], Import[FileNameJoin[{"results", "tests", "test003", "Metrics.json"}], "JSON"], {}];
byN = GroupBy[metrics003, # ["n"] &];
smallNs = Select[Keys[byN], # <= 13 &];
largeNs = Select[Keys[byN], # > 13 &];
smallRows = Table[{n, N[Median[Map[# ["baselineTime"] &, Select[byN[n], KeyExistsQ[#, "baselineTime"] &]]], 6]}, {n, smallNs}];
largeRows = Table[{n, N[Median[Map[# ["predictiveSampleTime"] &, Select[byN[n], KeyExistsQ[#, "predictiveSampleTime"] &]]], 6], Max[Map[# ["sampleCount"] &, Select[byN[n], KeyExistsQ[#, "sampleCount"] &]]]}, {n, largeNs}];

tableAccept = StringJoin[
  "\\begin{tabular}{lc}\\toprule\\n",
  "Ticket & Status \\\\midrule\\n",
  "TEST-001 & ", status001, " \\\n",
  "TEST-002 & ", status002, " \\\n",
  "TEST-003 & ", status003, " \\\n",
  "\\bottomrule\\n\\end{tabular}\\n"
];

tableSmall = StringJoin[
  "\\begin{tabular}{rc}\\toprule\\n",
  "$n$ & Median~baseline~time~(s) \\\\midrule\\n",
  StringRiffle[Table[ToString[r[[1]]] <> " & " <> ToString[r[[2]]] <> " \\\n", {r, smallRows}], ""],
  "\\bottomrule\\n\\end{tabular}\\n"
];

tableLarge = StringJoin[
  "\\begin{tabular}{rcc}\\toprule\\n",
  "$n$ & Predictive~sampling~time~(s) & Samples \\\\midrule\\n",
  StringRiffle[Table[ToString[r[[1]]] <> " & " <> ToString[r[[2]]] <> " & " <> ToString[r[[3]]] <> " \\\n", {r, largeRows}], ""],
  "\\bottomrule\\n\\end{tabular}\\n"
];

figTex = StringJoin[
  "\\subsection*{Acceptance Summary (TEST-004)}\\n",
  tableAccept,
  "\\medskip\\n",
  "\\subsubsection*{Reproduction Tables (Performance)}\\n",
  tableSmall,
  "\\medskip\\n",
  tableLarge
];

Export[FileNameJoin[{base, "Figures.tex"}], figTex, "Text"];
Export[FileNameJoin[{base, "Acceptance.json"}], <|"TEST-001" -> status001, "TEST-002" -> status002, "TEST-003" -> status003, "small" -> smallRows, "large" -> largeRows|>, "JSON"];
allOK = And[status001 === "OK", status002 === "OK", status003 === "OK"];
Export[FileNameJoin[{base, "Status.txt"}], If[allOK, "OK", "FAIL"], "Text"];

Association["Status" -> If[allOK, "OK", "FAIL"], "ResultsPath" -> base]

