repo = If[StringLength[Environment["CB_REPO"]] > 0, Environment["CB_REPO"], Directory[]];
SetDirectory[repo];

inputPath = Environment["DOPPEL_INPUT_JSON"];
If[StringLength[inputPath] == 0,
  Print[ExportString[<|"error" -> "missing DOPPEL_INPUT_JSON"|>, "RawJSON"]];
  Exit[2];
];

payload = Import[inputPath, "RawJSON"];
cm = payload["cm"];
dyn = payload["dyn"];
divisionSize = Lookup[payload, "division_size", 2];
requestedPattern = Lookup[payload, "pattern", Missing["NotAvailable"]];

Get["src/integration/Alpha.m"];
Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/Experiments.m"];

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

expectedSorted = KeySort[Association @ KeyValueMap[#1 -> Sort[#2] &, expected]];

choosePattern[assoc_Association] := Module[
  {keys},
  keys = Keys[assoc];
  First @ SortBy[keys, {-Length[assoc[#]], ToString[InputForm[#]]} &]
];

pattern = If[MissingQ[requestedPattern], choosePattern[expectedSorted], requestedPattern];

compressed = calculatingPattsInDivisionsOfCM[cm, dyn, divisionSize];
reconstructed = calculatingAttractors[
  compressed["Locations"],
  compressed["Sumandos"]
]["BinAttractorsByPosition"];
reconstructedSorted = KeySort[Association @ KeyValueMap[#1 -> Sort[#2] &, reconstructed]];

chunks = Table[
  Take[pattern, {i, Min[i + divisionSize - 1, Length[pattern]]}],
  {i, 1, Length[pattern], divisionSize}
];

perDivision = Table[
  Module[
    {
      key = chunks[[i]],
      decimalRep,
      sumandos,
      unfolded
    },
    decimalRep = If[
      KeyExistsQ[compressed["Locations"][[i]], key],
      compressed["Locations"][[i]][key],
      Missing["KeyAbsent"]
    ];
    sumandos = If[
      KeyExistsQ[compressed["Sumandos"][[i]], key],
      compressed["Sumandos"][[i]][key],
      Missing["KeyAbsent"]
    ];
    unfolded = If[
      MissingQ[decimalRep] || MissingQ[sumandos],
      Missing["KeyAbsent"],
      givePlaces[decimalRep, sumandos]
    ];
    <|
      "division_index" -> i,
      "pattern_chunk" -> key,
      "decimal_repertoire" -> decimalRep,
      "sumandos" -> sumandos,
      "unfolded_local_positions" -> unfolded
    |>
  ],
  {i, Length[chunks]}
];

safeJson[expr_] := expr /. _Missing -> Null;

Print[ExportString[
  <|
    "network" -> <|
      "n" -> Length[cm],
      "division_size" -> divisionSize
    |>,
    "pattern" -> pattern,
    "pattern_string" -> ToString[InputForm[pattern]],
    "expected_positions" -> safeJson[
      If[KeyExistsQ[expectedSorted, pattern], expectedSorted[pattern], {}]
    ],
    "reconstructed_positions" -> safeJson[
      If[KeyExistsQ[reconstructedSorted, pattern], reconstructedSorted[pattern], {}]
    ],
    "final_exact_match" -> (
      If[KeyExistsQ[expectedSorted, pattern], expectedSorted[pattern], {}] ===
      If[KeyExistsQ[reconstructedSorted, pattern], reconstructedSorted[pattern], {}]
    ),
    "per_division" -> safeJson[perDivision]
  |>,
  "RawJSON"
]];
