AppendTo[$Path, "src/Packages"];

base2 = FileNameJoin[{"results","tests","compare002"}];
base3 = FileNameJoin[{"results","tests","compare003"}];

rows2 = Import[FileNameJoin[{base2,"Summary.json"}],"JSON"];
rows3 = Import[FileNameJoin[{base3,"Summary.json"}],"JSON"];

fmt[x_] := ToString@NumberForm[N@x, {4,3}];

labels2 = rows2[[All, "gate"]];
val2[name_] := rows2[[All, name]];

coords[labels_, vals_] := StringRiffle[MapThread["("<>#1<>","<>fmt[#2]<>")"&, {labels, vals}], " "]; 

pidChart = StringJoin[
  "\\begin{figure}[h]\n",
  "\\centering\n",
  "\\begin{tikzpicture}\n",
  "\\begin{axis}[ybar, symbolic x coords={", StringRiffle[labels2, ","], "}, xtick=data, ymin=0, ylabel={bits}, legend pos=north west]\n",
  "\\addplot coordinates {", coords[labels2, val2["Ix1y"]], "};\\addlegendentry{$I(x_1;y)$}\n",
  "\\addplot coordinates {", coords[labels2, val2["Ix2y"]], "};\\addlegendentry{$I(x_2;y)$}\n",
  "\\addplot coordinates {", coords[labels2, val2["Ix12y"]], "};\\addlegendentry{$I(x_1,x_2;y)$}\n",
  "\\addplot coordinates {", coords[labels2, val2["Synergy"]], "};\\addlegendentry{$\\text{Synergy}$}\n",
  "\\end{axis}\n",
  "\\end{tikzpicture}\n",
  "\\caption{PID components per gate under unbiased inputs.}\n",
  "\\end{figure}\n"
];

Export[FileNameJoin[{base2,"Charts.tex"}], pidChart, "Text"];

labels3 = rows3[[All, "gate"]];
val3[name_] := rows3[[All, name]];

teChart = StringJoin[
  "\\begin{figure}[h]\n",
  "\\centering\n",
  "\\begin{tikzpicture}\n",
  "\\begin{axis}[ybar, symbolic x coords={", StringRiffle[labels3, ","], "}, xtick=data, ymin=0, ylabel={bits}, legend pos=north west]\n",
  "\\addplot coordinates {", coords[labels3, val3["TE_X_to_Y"]], "};\\addlegendentry{$TE_{X\\to Y}$}\n",
  "\\addplot coordinates {", coords[labels3, val3["TE_Y_to_Y"]], "};\\addlegendentry{$TE_{Y\\to Y}$}\n",
  "\\addplot coordinates {", coords[labels3, val3["TC_XY_Y1"]], "};\\addlegendentry{$TC(X,Y,Y_{t+1})$}\n",
  "\\end{axis}\n",
  "\\end{tikzpicture}\n",
  "\\caption{Transfer entropy and total correlation per gate under unbiased inputs.}\n",
  "\\end{figure}\n"
];

Export[FileNameJoin[{base3,"Charts.tex"}], teChart, "Text"];

Association["Compare002Charts"->FileNameJoin[{base2,"Charts.tex"}], "Compare003Charts"->FileNameJoin[{base3,"Charts.tex"}]]

