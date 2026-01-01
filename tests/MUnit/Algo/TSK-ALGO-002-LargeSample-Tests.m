Get["src/Packages/Integration/Gates.m"];

base = FileNameJoin[{"results", "tests", "algo002"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

sizes = {20, 50};
seeds = {201, 202};
gates = {"AND","OR","XOR","NAND","NOR","XNOR","MAJORITY"};

truthOutput[gate_, Ic_List, x_List, params_Association:<||>] := Module[{d = Length[Ic], tt, idx},
  tt = Integration`Gates`TruthTable[gate, d, params];
  idx = FromDigits[x[[Ic]], 2] + 1;
  tt[[idx, 2]]
];

applyOutput[gate_, Ic_List, x_List, params_Association:<||>] := Integration`Gates`ApplyGate[gate, x[[Ic]], params];

runOne[n_Integer, seed_Integer] := Module[{cm, dyn, params = <||>, sampleIdx, okRows = 0, totalRows = 0},
  SeedRandom[seed];
  cm = ConstantArray[0, {n, n}];
  Do[
    Module[{deg = RandomInteger[{1, Min[5, n - 1]}], choices},
      choices = RandomSample[Complement[Range[n], {i}], deg];
      cm[[i, choices]] = 1;
    ],
    {i, n}
  ];
  dyn = Table[RandomChoice[gates], {n}];
  sampleIdx = Join[Range[1, 16], RandomInteger[{0, 2^n - 1}, 16]];
  Do[
    Module[{x = IntegerDigits[j, 2, n], Ics = Table[Flatten@Position[cm[[k]], 1], {k, n}], y1, y2},
      y1 = Table[applyOutput[dyn[[k]], Ics[[k]], x, Lookup[params, k, <||>]], {k, n}];
      y2 = Table[truthOutput[dyn[[k]], Ics[[k]], x, Lookup[params, k, <||>]], {k, n}];
      okRows += Boole[y1 === y2];
      totalRows += 1;
    ],
    {j, sampleIdx}
  ];
  <|"n" -> n, "seed" -> seed, "rowsChecked" -> totalRows, "rowsEqual" -> okRows, "accuracy" -> N[okRows/totalRows]|>
];

metrics = Flatten[Table[runOne[n, s], {n, sizes}, {s, seeds}], 1];
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
status = If[AllTrue[metrics[[All, "accuracy"]], (# == 1.0) &], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], status, "Text"];
