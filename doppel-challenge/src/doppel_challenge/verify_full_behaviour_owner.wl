repo = If[StringLength[Environment["CB_REPO"]] > 0, Environment["CB_REPO"], Directory[]];
SetDirectory[repo];

Get["src/integration/Alpha.m"];
Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/Experiments.m"];

cm = {
  {0, 1, 0},
  {1, 0, 1},
  {0, 1, 0}
};
dyn = {"AND", "OR", "XOR"};

dispatch = Integration`Experiments`CreateRepertoiresDispatch[cm, dyn];
outputs = dispatch["RepertoireOutputs"];

expected = GroupBy[
  MapIndexed[
    <|"Pattern" -> #1, "Position" -> First[#2] - 1|> &,
    outputs
  ],
  #Pattern &,
  Sort[#[[All, "Position"]]] &
];

compressed = calculatingPattsInDivisionsOfCM[cm, dyn, 2];
reconstructed = calculatingAttractors[
  compressed["Locations"],
  compressed["Sumandos"]
]["BinAttractorsByPosition"];

expectedSorted = Association @ KeyValueMap[#1 -> Sort[#2] &, expected];
reconstructedSorted = Association @ KeyValueMap[#1 -> Sort[#2] &, reconstructed];

toJsonAssociation[assoc_Association] := Association @ KeyValueMap[
  ToString[InputForm[#1]] -> #2 &,
  assoc
];

Print[ExportString[
  <|
    "network" -> <|"n" -> Length[cm], "cm" -> cm, "dyn" -> dyn|>,
    "dispatch_rows" -> Length[outputs],
    "unique_output_patterns_dispatch" -> Length[Keys[expectedSorted]],
    "division_count" -> Length[compressed["Locations"]],
    "division_decimal_keys" -> (Length[Keys[#]] & /@ compressed["Locations"]),
    "division_sumandos_keys" -> (Length[Keys[#]] & /@ compressed["Sumandos"]),
    "reconstructed_patterns" -> Length[Keys[reconstructedSorted]],
    "exact_match" -> (expectedSorted === reconstructedSorted),
    "expected" -> toJsonAssociation[expectedSorted],
    "reconstructed" -> toJsonAssociation[reconstructedSorted]
  |>,
  "RawJSON"
]];
