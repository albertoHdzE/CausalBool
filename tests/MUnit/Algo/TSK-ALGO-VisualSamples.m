Get["src/Packages/Integration/Gates.m"];

base = FileNameJoin[{"results","tests","algo001"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

formatVec[v_List] := StringJoin[ToString /@ v];
oneStepOutputs[cm_List, dyn_List, v_List, params_Association:<||>] := Table[
  Integration`Gates`ApplyGate[dyn[[k]], v[[Flatten@Position[cm[[k]], 1]]], Lookup[params, k, <||>]],
  {k, Length[dyn]}
];

makeTeXTable[n_Integer, seed_Integer] := Module[{cm, dyn, params = <||>, sampleIdx, rows, tex},
  SeedRandom[seed];
  cm = Table[If[i == j, 0, RandomInteger[{0, 1}]], {i, 1, n}, {j, 1, n}];
  dyn = Table[RandomChoice[{"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN"}], {n}];
  sampleIdx = Join[Range[1, 8], RandomInteger[{0, 2^n - 1}, 8]];
  rows = Table[Module[{x = IntegerDigits[j, 2, n], y = oneStepOutputs[cm, dyn, IntegerDigits[j, 2, n], params]},
      {j, formatVec[x], formatVec[y]}], {j, sampleIdx}];
  tex = StringJoin[
    "\\begin{tabular}{r|l|l}\n",
    "\\toprule\n$j$ & $x$ & $F(x)$ \\\\\n\\midrule\n",
    StringRiffle[Table[ToString[row[[1]]] <> " & " <> row[[2]] <> " & " <> row[[3]] <> " \\\\", {row, rows}], "\n"],
    "\n\\bottomrule\n\\end{tabular}\n"
  ];
  (* sanitize accidental leading '+' if present *)
  lines = StringSplit[tex, "\n"];
  lines2 = StringReplace[lines, StartOfString ~~ "+" -> ""];
  tex2 = StringRiffle[lines2, "\n"];
  Export[FileNameJoin[{base, "Samples_n" <> ToString[n] <> ".tex"}], tex2, "Text"];
  <|"n"->n, "seed"->seed, "rows"->Length[rows]|>
];

reports = {makeTeXTable[10, 111], makeTeXTable[20, 121], makeTeXTable[50, 131]};
Export[FileNameJoin[{base, "SamplesReport.json"}], reports, "JSON"];
Export[FileNameJoin[{base, "Status_samples.txt"}], "OK", "Text"];
