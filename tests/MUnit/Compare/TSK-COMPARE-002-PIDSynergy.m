AppendTo[$Path, "src/Packages"];

EnsureDir[path_] := If[!DirectoryQ[path], CreateDirectory[path, CreateIntermediateDirectories -> True]];
base = FileNameJoin[{"results", "tests", "compare002"}];
EnsureDir[base];

gates = {"AND","OR","XOR","XNOR","NAND","NOR"};

apply2[gate_, x1_Integer, x2_Integer] := Switch[gate,
  "AND", If[x1 == 1 && x2 == 1, 1, 0],
  "OR", If[x1 == 1 || x2 == 1, 1, 0],
  "XOR", If[Mod[x1 + x2, 2] == 1, 1, 0],
  "XNOR", If[Mod[x1 + x2, 2] == 0, 1, 0],
  "NAND", If[x1 == 1 && x2 == 1, 0, 1],
  "NOR", If[x1 == 1 || x2 == 1, 0, 1],
  _, 0
];

pairs = Tuples[{0,1}, 2];

pXYZ[gate_] := Module[{assoc = Association[]},
  Scan[(assoc[{#[[1]], #[[2]], apply2[gate, #[[1]], #[[2]]]}] = 1/4.0) &, pairs];
  assoc
];

dist[assoc_] := Module[{px1 = Association[], px2 = Association[], py = Association[], pX1Y = Association[], pX2Y = Association[], pX1X2 = Association[]},
  KeyValueMap[(px1[#1[[1]]] = Lookup[px1, #1[[1]], 0] + #2) &, assoc];
  KeyValueMap[(px2[#1[[2]]] = Lookup[px2, #1[[2]], 0] + #2) &, assoc];
  KeyValueMap[(py[#1[[3]]] = Lookup[py, #1[[3]], 0] + #2) &, assoc];
  Do[pX1Y[{x1, y}] = Total[Table[Lookup[assoc, Key[{x1, x2, y}], 0], {x2, {0,1}}]], {x1, {0,1}}, {y, {0,1}}];
  Do[pX2Y[{x2, y}] = Total[Table[Lookup[assoc, Key[{x1, x2, y}], 0], {x1, {0,1}}]], {x2, {0,1}}, {y, {0,1}}];
  Do[pX1X2[{x1, x2}] = Total[Table[Lookup[assoc, Key[{x1, x2, y}], 0], {y, {0,1}}]], {x1, {0,1}}, {x2, {0,1}}];
  <|"px1" -> px1, "px2" -> px2, "py" -> py, "pX1Y" -> pX1Y, "pX2Y" -> pX2Y, "pX1X2" -> pX1X2|>
];

miX1Y[d_] := Module[{sum = 0.0}, Do[Module[{p = Lookup[d["pX1Y"], Key[{x1, y}], 0], ax = Lookup[d["px1"], x1], ay = Lookup[d["py"], y]}, If[p > 0 && ax > 0 && ay > 0, sum += p*Log[2, p/(ax*ay)]]], {x1, {0,1}}, {y, {0,1}}]; sum];
miX2Y[d_] := Module[{sum = 0.0}, Do[Module[{p = Lookup[d["pX2Y"], Key[{x2, y}], 0], ax = Lookup[d["px2"], x2], ay = Lookup[d["py"], y]}, If[p > 0 && ax > 0 && ay > 0, sum += p*Log[2, p/(ax*ay)]]], {x2, {0,1}}, {y, {0,1}}]; sum];
miX12Y[assoc_, d_] := Module[{sum = 0.0}, Do[Module[{p = Lookup[assoc, Key[{x1, x2, y}], 0], ax = Lookup[d["pX1X2"], Key[{x1, x2}], 0], ay = Lookup[d["py"], y]}, If[p > 0 && ax > 0 && ay > 0, sum += p*Log[2, p/(ax*ay)]]], {x1, {0,1}}, {x2, {0,1}}, {y, {0,1}}]; sum];

specXGivenY[d_, which_] := Module[{py = d["py"], out = Association[]},
  Do[Module[{yprob = Lookup[py, y], s = 0.0},
      Do[Module[{cond = If[which == 1, Lookup[d["pX1Y"], Key[{x, y}], 0], Lookup[d["pX2Y"], Key[{x, y}], 0]], px = If[which == 1, Lookup[d["px1"], x], Lookup[d["px2"], x]], pxGivenY = If[yprob > 0, cond/yprob, 0], pyGivenX = If[px > 0, cond/px, 0]}, If[pxGivenY > 0 && yprob > 0 && pyGivenX > 0, s += pxGivenY*Log[2, pyGivenX/yprob]]], {x, {0,1}}];
      out[y] = s
    ], {y, {0,1}}]; out
];

pidFor[gate_] := Module[{assoc = pXYZ[gate], d, ix1, ix2, ix12, r, u1, u2, s},
  d = dist[assoc];
  ix1 = miX1Y[d];
  ix2 = miX2Y[d];
  ix12 = miX12Y[assoc, d];
  r = Sum[Lookup[d["py"], y]*Min[Lookup[specXGivenY[d, 1], y], Lookup[specXGivenY[d, 2], y]], {y, {0,1}}];
  u1 = ix1 - r; u2 = ix2 - r; s = ix12 - u1 - u2 - r;
  <|"gate" -> gate, "Ix1y" -> ix1, "Ix2y" -> ix2, "Ix12y" -> ix12, "Redundancy" -> r, "Unique1" -> u1, "Unique2" -> u2, "Synergy" -> s|>
];

rows = Map[pidFor, gates];
rowEnd = FromCharacterCode[{92,92}];

fmt[x_] := ToString@NumberForm[N@x, {4, 3}];
rowTex[r_] := StringJoin[r["gate"], " & ", fmt[r["Ix1y"]], " & ", fmt[r["Ix2y"]], " & ", fmt[r["Ix12y"]], " & ", fmt[r["Redundancy"]], " & ", fmt[r["Unique1"]], " & ", fmt[r["Unique2"]], " & ", fmt[r["Synergy"]], " ", rowEnd];
rowsTex = StringRiffle[rowTex /@ rows, "\n"];
tableTex = StringJoin[
  "\\begin{tabular}{lccccccc}\n",
  "\\toprule\n",
  "Gate & $I(x_1;y)$ & $I(x_2;y)$ & $I(x_1,x_2;y)$ & Redund & $\\text{Unique}_1$ & $\\text{Unique}_2$ & Synergy \\\\ \n",
  "\\midrule\n",
  rowsTex, "\n",
  "\\bottomrule\n\\end{tabular}\n"
];
Export[FileNameJoin[{base, "Summary.tex"}], tableTex, "Text"];
Export[FileNameJoin[{base, "Summary.json"}], rows, "JSON"];
ok = Abs[SelectFirst[rows, # ["gate"] == "XOR" &]["Synergy"] - 1.0] < 1.0*^-6;
Export[FileNameJoin[{base, "Status.txt"}], If[ok, "OK", "NOT_OK"], "Text"];
Association["Status" -> If[ok, "OK", "NOT_OK"], "ResultsPath" -> base]
