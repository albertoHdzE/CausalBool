AppendTo[$Path, "src/Packages"];

EnsureDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "exper002"}];
EnsureDir[base];

andBias[p_] := p^2;
orBias[p_] := 2 p - p^2;
xorBias[p_] := 2 p (1 - p);
nandBias[p_] := 1 - p^2;
norBias[p_] := (1 - p)^2;
xnorBias[p_] := p^2 + (1 - p)^2;
notBias[p_] := 1 - p;

andSlope[p_] := 2 p;
orSlope[p_] := 2 - 2 p;
xorSlope[p_] := 2 - 4 p;
nandSlope[p_] := -2 p;
norSlope[p_] := -2 (1 - p);
xnorSlope[p_] := 4 p - 2;
notSlope[p_] := -1;

gateBias["AND"][p_] := andBias[p];
gateBias["OR"][p_] := orBias[p];
gateBias["XOR"][p_] := xorBias[p];
gateBias["NAND"][p_] := nandBias[p];
gateBias["NOR"][p_] := norBias[p];
gateBias["XNOR"][p_] := xnorBias[p];
gateBias["NOT"][p_] := notBias[p];

gateSlope["AND"][p_] := andSlope[p];
gateSlope["OR"][p_] := orSlope[p];
gateSlope["XOR"][p_] := xorSlope[p];
gateSlope["NAND"][p_] := nandSlope[p];
gateSlope["NOR"][p_] := norSlope[p];
gateSlope["XNOR"][p_] := xnorSlope[p];
gateSlope["NOT"][p_] := notSlope[p];

mixturePairs = {{"AND", "OR"}, {"XOR", "OR"}, {"AND", "XOR"}, {"NAND", "NOR"}, {"XNOR", "XOR"}};
wGrid = N@Range[0, 1, 0.25];
pGrid = N@Range[0, 1, 0.1];

mixBias[p_, pair_, w_] := Module[{g1 = pair[[1]], g2 = pair[[2]]}, w gateBias[g1][p] + (1 - w) gateBias[g2][p]];
mixSlope[p_, pair_, w_] := Module[{g1 = pair[[1]], g2 = pair[[2]]}, w gateSlope[g1][p] + (1 - w) gateSlope[g2][p]];

rowEnd = FromCharacterCode[{92, 92}];
texRow[list_List] := StringJoin[Riffle[ToString /@ list, " & "], " ", rowEnd];

summaryRows = Flatten@Table[
  Module[{pair = mixturePairs[[i]], w = wGrid[[j]], b = mixBias[0.5, mixturePairs[[i]], wGrid[[j]]], s = mixSlope[0.5, mixturePairs[[i]], wGrid[[j]]]},
    texRow[{pair[[1]] <> "/" <> pair[[2]], NumberForm[w, {3, 2}], NumberForm[b, {5, 3}], NumberForm[s, {5, 3}]}]
  ],
  {i, Length@mixturePairs}, {j, Length@wGrid}];
summaryTex = StringJoin[
  "\\begin{tabular}{lccc}\n",
  "\\toprule\n",
  "Pair & w & Bias~at~$p=0.5$ & Slope~at~$p=0.5$ \\\\ \n",
  "\\midrule\n",
  StringRiffle[summaryRows, "\n"], "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "Summary.tex"}], summaryTex, "Text"];

wCols = {0., 0.5, 1.};
Do[
  pair = mixturePairs[[i]];
  rows = Table[
    texRow[{NumberForm[p, {3, 2}], NumberForm[mixBias[p, pair, wCols[[1]]], {5, 3}], NumberForm[mixBias[p, pair, wCols[[2]]], {5, 3}], NumberForm[mixBias[p, pair, wCols[[3]]], {5, 3}]}]
    , {p, pGrid}];
  table = StringJoin[
    "\\begin{tabular}{lccc}\n",
    "\\toprule\n",
    "$p$ & $w=0$ & $w=0.5$ & $w=1$ \\\\ \n",
    "\\midrule\n",
    StringRiffle[rows, "\n"], "\n",
    "\\bottomrule\n\\end{tabular}\n"
  ];
  Export[FileNameJoin[{base, StringJoin["Sweep_", pair[[1]], "_", pair[[2]], ".tex"]}], table, "Text"]
  , {i, Length@mixturePairs}];

Export[FileNameJoin[{base, "Status.txt"}], "OK", "Text"];

Association["Status" -> "OK", "ResultsPath" -> base]

