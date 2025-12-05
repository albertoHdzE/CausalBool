AppendTo[$Path, "src/Packages"];
Needs["Integration`IndexAlgebra`"];
Needs["Integration`Gates`"];

base = FileNameJoin[{"results", "tests", "test002"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

phi[j_, n_] := Integration`IndexAlgebra`Phi[j, n];
mapPhi[set_, n_] := Integration`IndexAlgebra`MapPhi[set, n];
univ[n_] := Integration`IndexAlgebra`IndexSetUniverse[n];
compl[n_, set_] := Integration`IndexAlgebra`IndexSetComplement[n, set];
u[sets__] := Integration`IndexAlgebra`IndexSetUnion[sets];
i[sets__] := Integration`IndexAlgebra`IndexSetIntersection[sets];
oneBand[n_, k_] := Integration`IndexAlgebra`OneBandIndices[n, k];
zeroBand[n_, k_] := Integration`IndexAlgebra`ZeroBandIndices[n, k];

lsbInputs[n_] := Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, 2^n - 1}];
applyGateOnLSB[gate_, n_, Ic_, params_: <||>] := Module[{inputs = lsbInputs[n]},
  Table[If[Integration`Gates`ApplyGate[gate, Part[inputs[[j]], Ic], params] == 1, j, Nothing], {j, 1, Length[inputs]}]
];

phiInvolutionOK[n_] := Module[{vals = Range[1, 2^n]}, And @@ Table[phi[phi[j, n], n] == j, {j, vals}]];
universeSizeOK[n_] := Length[univ[n]] == 2^n;
bandsComplementOK[n_, k_] := Module[{one = oneBand[n, k], zero = zeroBand[n, k]}, Sort[u[one, zero]] === Sort[univ[n]] && i[one, zero] === {}];
deMorganOK[n_, a_, b_] := Module[{A = oneBand[n, a], B = oneBand[n, b]}, Sort[compl[n, u[A, B]]] === Sort[i[compl[n, A], compl[n, B]]]];

orderingInvarianceOK[gate_, n_, Ic_, params_: <||>] := Module[{lsbSet, msbSet},
  lsbSet = applyGateOnLSB[gate, n, Ic, params];
  msbSet = Integration`Gates`IndexSetNetwork[gate, n, Ic, params];
  Sort[mapPhi[lsbSet, n]] === Sort[msbSet]
];

kofnStrictOK[n_, k_] := Module[{idxLoose, idxStrict},
  idxLoose = Integration`Gates`IndexSet["KOFN", n, <|"k" -> k, "strict" -> False|>];
  idxStrict = Integration`Gates`IndexSet["KOFN", n, <|"k" -> k, "strict" -> True|>];
  SubsetQ[idxLoose, idxStrict] && Length[idxLoose] >= Length[idxStrict]
];

cases = {
  <|"name" -> "phiInvolution", "ok" -> And @@ (phiInvolutionOK /@ {3, 4, 5})|>,
  <|"name" -> "universeSize", "ok" -> And @@ (universeSizeOK /@ {3, 4, 5})|>,
  <|"name" -> "bandsComplement", "ok" -> And @@ Table[bandsComplementOK[4, k], {k, 1, 4}]|>,
  <|"name" -> "deMorgan", "ok" -> And @@ Table[deMorganOK[4, a, b], {a, 1, 4}, {b, 1, 4}]|>,
  <|"name" -> "orderingInvariance_AND", "ok" -> orderingInvarianceOK["AND", 3, {2, 3}]|>,
  <|"name" -> "orderingInvariance_OR", "ok" -> orderingInvarianceOK["OR", 3, {2, 3}]|>,
  <|"name" -> "orderingInvariance_XOR", "ok" -> orderingInvarianceOK["XOR", 3, {2, 3}]|>,
  <|"name" -> "kofnStrict", "ok" -> kofnStrictOK[3, 2]|>
};

timed = Table[Module[{t, r}, {t, r} = AbsoluteTiming[cases[[i]]]; Append[r, "timeSec" -> t]], {i, Length[cases]}];
allOK = And @@ (timed[[All, "ok"]]);

Export[FileNameJoin[{base, "PropertyTests.json"}], timed, "JSON"];
Export[FileNameJoin[{base, "Status.txt"}], If[allOK, "OK", "FAIL"], "Text"];
Export[FileNameJoin[{base, "Report.txt"}], StringRiffle[Map[Function[r, r["name"] <> ": " <> If[r["ok"], "PASS", "FAIL"] <> " (" <> ToString[NumberForm[r["timeSec"], {4, 3}]] <> "s)"], timed], "\n"], "Text"];

Association["Status" -> If[allOK, "OK", "FAIL"], "ResultsPath" -> base]

