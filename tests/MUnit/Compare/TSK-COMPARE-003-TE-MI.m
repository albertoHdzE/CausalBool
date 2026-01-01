AppendTo[$Path, "src/Packages"];

EnsureDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "compare003"}];
EnsureDir[base];

gates = {"AND","OR","XOR","XNOR","NAND","NOR"};

apply2[gate_, x_, y_] := Switch[gate,
  "AND", If[x == 1 && y == 1, 1, 0],
  "OR", If[x == 1 || y == 1, 1, 0],
  "XOR", If[Mod[x + y, 2] == 1, 1, 0],
  "XNOR", If[Mod[x + y, 2] == 0, 1, 0],
  "NAND", If[x == 1 && y == 1, 0, 1],
  "NOR", If[x == 1 || y == 1, 0, 1],
  _, 0
];

triples = Tuples[{0, 1}, 2];

pXYZ[gate_] := Module[{assoc = Association[]},
  Scan[(assoc[{#[[1]], #[[2]], apply2[gate, #[[1]], #[[2]]]}] = 1/4.0) &, triples];
  assoc
];

H[dist_Association] := Module[{s = 0.0}, KeyValueMap[(If[#2 > 0, s += -#2*Log[2, #2]]) &, dist]; s];

distAll[assoc_] := Module[{px = Association[], py = Association[], py1 = Association[], pXY = Association[], pYy1 = Association[], pXy1 = Association[]},
  KeyValueMap[(px[#1[[1]]] = Lookup[px, #1[[1]], 0] + #2) &, assoc];
  KeyValueMap[(py[#1[[2]]] = Lookup[py, #1[[2]], 0] + #2) &, assoc];
  KeyValueMap[(py1[#1[[3]]] = Lookup[py1, #1[[3]], 0] + #2) &, assoc];
  Do[pXY[{x, y}] = Total[Table[Lookup[assoc, {x, y, y1}, 0], {y1, {0, 1}}]], {x, {0, 1}}, {y, {0, 1}}];
  Do[pYy1[{y, y1}] = Total[Table[Lookup[assoc, {x, y, y1}, 0], {x, {0, 1}}]], {y, {0, 1}}, {y1, {0, 1}}];
  Do[pXy1[{x, y1}] = Total[Table[Lookup[assoc, {x, y, y1}, 0], {y, {0, 1}}]], {x, {0, 1}}, {y1, {0, 1}}];
  <|"px" -> px, "py" -> py, "py1" -> py1, "pXY" -> pXY, "pYy1" -> pYy1, "pXy1" -> pXy1|>
];

teXtoYClosed[g_] := Switch[g, "XOR" | "XNOR", 1.0, "AND" | "OR" | "NAND" | "NOR", 0.5, _, 0.0];
teYtoYClosed[g_] := teXtoYClosed[g];

tcXYZ[assoc_, d_] := Module[{HX = H[d["px"]], HY = H[d["py"]], HY1 = H[d["py1"]], HXYZ},
  HXYZ = H[assoc];
  HX + HY + HY1 - HXYZ
];

oneGate[g_] := Module[{assoc = pXYZ[g], d = distAll[pXYZ[g]], teXY, teYY, tc},
  teXY = teXtoYClosed[g]; teYY = teYtoYClosed[g]; tc = tcXYZ[assoc, d];
  <|"gate" -> g, "TE_X_to_Y" -> teXY, "TE_Y_to_Y" -> teYY, "TC_XY_Y1" -> tc|>
];

rows = Map[oneGate, gates];

fmt[x_] := ToString@NumberForm[N@x, {4, 3}];
rowEnd = FromCharacterCode[{92, 92}];
rowTex[r_] := StringJoin[r["gate"], " & ", fmt[r["TE_X_to_Y"]], " & ", fmt[r["TE_Y_to_Y"]], " & ", fmt[r["TC_XY_Y1"]], " ", rowEnd];
rowsTex = StringRiffle[rowTex /@ rows, "\n"];
tableTex = StringJoin[
  "\\begin{tabular}{lccc}\n",
  "\\toprule\n",
  "Gate & $TE_{X\\to Y}$ & $TE_{Y\\to Y}$ & $TC(X,Y,Y_{t+1})$ \\\\ \n",
  "\\midrule\n",
  rowsTex, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "Summary.tex"}], tableTex, "Text"];
Export[FileNameJoin[{base, "Summary.json"}], rows, "JSON"];
ok = Abs[SelectFirst[rows, # ["gate"] == "XOR" &]["TE_X_to_Y"] - 1.0] < 1.0*^-6 && Abs[SelectFirst[rows, # ["gate"] == "XOR" &]["TC_XY_Y1"] - 1.0] < 1.0*^-6;
Export[FileNameJoin[{base, "Status.txt"}], If[ok, "OK", "NOT_OK"], "Text"];
Association["Status" -> If[ok, "OK", "NOT_OK"], "ResultsPath" -> base]
