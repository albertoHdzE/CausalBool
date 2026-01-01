Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/IndexAlgebra.m"];

nVals = {3, 4};
IcSamples[n_] := If[n >= 3, { {2, 3} }, { {1, 2} }];

andNandCheck[n_, Ic_] := Module[{andSet, nandSet, uni, comp},
  andSet = Integration`Gates`IndexSetNetwork["AND", n, Ic, <||>];
  nandSet = Integration`Gates`IndexSetNetwork["NAND", n, Ic, <||>];
  uni = Integration`IndexAlgebra`IndexSetUniverse[n];
  comp = Integration`IndexAlgebra`IndexSetComplement[n, andSet];
  Sort[nandSet] === Sort[comp]
];

orNorCheck[n_, Ic_] := Module[{orSet, norSet, uni, comp},
  orSet = Integration`Gates`IndexSetNetwork["OR", n, Ic, <||>];
  norSet = Integration`Gates`IndexSetNetwork["NOR", n, Ic, <||>];
  uni = Integration`IndexAlgebra`IndexSetUniverse[n];
  comp = Integration`IndexAlgebra`IndexSetComplement[n, orSet];
  Sort[norSet] === Sort[comp]
];

xorXnorCheck[n_, Ic_] := Module[{xorSet, xnorSet, uni, comp},
  xorSet = Integration`Gates`IndexSetNetwork["XOR", n, Ic, <||>];
  xnorSet = Integration`Gates`IndexSetNetwork["XNOR", n, Ic, <||>];
  uni = Integration`IndexAlgebra`IndexSetUniverse[n];
  comp = Integration`IndexAlgebra`IndexSetComplement[n, xorSet];
  Sort[xnorSet] === Sort[comp]
];

orUnionBandsCheck[n_, Ic_] := Module[{orSet, unionBands},
  orSet = Integration`Gates`IndexSetNetwork["OR", n, Ic, <||>];
  unionBands = Integration`IndexAlgebra`IndexSetUnion @@ (Integration`IndexAlgebra`OneBandIndices[n, #] & /@ Ic);
  Sort[orSet] === Sort[unionBands]
];

notZeroBandCheck[n_, i_] := Module[{notSet, zeroBand},
  notSet = Integration`Gates`IndexSetNetwork["NOT", n, {}, <|"i" -> i|>];
  zeroBand = Integration`IndexAlgebra`ZeroBandIndices[n, i];
  Sort[notSet] === Sort[zeroBand]
];

closureCheck[n_, set_] := Module[{uni = Integration`IndexAlgebra`IndexSetUniverse[n]},
  Min[set] >= 1 && Max[set] <= 2^n && DuplicateFreeQ[set] && VectorQ[set, IntegerQ]
];

cases = Table[{n, IcSamples[n][[1]]}, {n, nVals}];

results = Table[
  Module[{n = cases[[k, 1]], Ic = cases[[k, 2]], iSel},
    iSel = Ic[[1]];
    <|
      "n" -> n,
      "Ic" -> Ic,
      "andNand" -> andNandCheck[n, Ic],
      "orNor" -> orNorCheck[n, Ic],
      "xorXnor" -> xorXnorCheck[n, Ic],
      "orUnionBands" -> orUnionBandsCheck[n, Ic],
      "notZeroBand" -> notZeroBandCheck[n, iSel],
      "closureUnion" -> closureCheck[n, Integration`IndexAlgebra`IndexSetUnion @@ (Integration`IndexAlgebra`OneBandIndices[n, #] & /@ Ic)],
      "closureComp" -> closureCheck[n, Integration`IndexAlgebra`IndexSetComplement[n, Integration`Gates`IndexSetNetwork["AND", n, Ic, <||>]]]
    |>
  ],
  {k, Length[cases]}
];

bools = Flatten[results[[All, {"andNand", "orNor", "xorXnor", "orUnionBands", "notZeroBand", "closureUnion", "closureComp"}]]];
allOK = Not[MemberQ[bools, False]];

CreateDirectory["results/tests/theory006", CreateIntermediateDirectories -> True];
Export["results/tests/theory006/Compositionality.json", results];
status = If[allOK, "PASS", "FAIL"];
Export["results/tests/theory006/Status.txt", status];
