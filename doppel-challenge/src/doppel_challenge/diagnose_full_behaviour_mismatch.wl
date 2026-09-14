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
maxExamples = Lookup[payload, "max_examples", 5];
maxPositions = Lookup[payload, "max_positions", 20];

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

compressed = calculatingPattsInDivisionsOfCM[cm, dyn, divisionSize];
reconstructed = calculatingAttractors[
  compressed["Locations"],
  compressed["Sumandos"]
]["BinAttractorsByPosition"];

expectedSorted = KeySort[Association @ KeyValueMap[#1 -> Sort[#2] &, expected]];
reconstructedSorted = KeySort[Association @ KeyValueMap[#1 -> Sort[#2] &, reconstructed]];

allPatterns = SortBy[
  Union[Keys[expectedSorted], Keys[reconstructedSorted]],
  ToString[InputForm[#]] &
];

getPositions[assoc_Association, key_] := If[KeyExistsQ[assoc, key], assoc[key], {}];

mismatchPatterns = Select[
  allPatterns,
  getPositions[expectedSorted, #] =!= getPositions[reconstructedSorted, #] &
];

toJsonAssociation[assoc_Association] := Association @ KeyValueMap[
  ToString[InputForm[#1]] -> #2 &,
  assoc
];

chunkPattern[pattern_List] := Table[
  Take[pattern, {i, Min[i + divisionSize - 1, Length[pattern]]}],
  {i, 1, Length[pattern], divisionSize}
];

perDivisionDiagnostics[pattern_List] := Module[
  {chunks},
  chunks = chunkPattern[pattern];
  Table[
    Module[
      {
        key = chunks[[i]],
        locationAssoc = compressed["Locations"][[i]],
        sumandosAssoc = compressed["Sumandos"][[i]],
        decimalRep,
        sumandos
      },
      decimalRep = If[KeyExistsQ[locationAssoc, key], locationAssoc[key], Missing["KeyAbsent"]];
      sumandos = If[KeyExistsQ[sumandosAssoc, key], sumandosAssoc[key], Missing["KeyAbsent"]];
      <|
        "division_index" -> i,
        "pattern_chunk" -> key,
        "chunk_string" -> ToString[InputForm[key]],
        "location_key_exists" -> KeyExistsQ[locationAssoc, key],
        "sumandos_key_exists" -> KeyExistsQ[sumandosAssoc, key],
        "decimal_repertoire" -> Replace[decimalRep, _Missing -> Null],
        "sumandos" -> Replace[sumandos, _Missing -> Null]
      |>
    ],
    {i, Length[chunks]}
  ]
];

examples = Table[
  Module[
    {
      pattern = mismatchPatterns[[i]],
      expectedPositions,
      reconstructedPositions
    },
    expectedPositions = getPositions[expectedSorted, pattern];
    reconstructedPositions = getPositions[reconstructedSorted, pattern];
    <|
      "pattern" -> pattern,
      "pattern_string" -> ToString[InputForm[pattern]],
      "expected_count" -> Length[expectedPositions],
      "reconstructed_count" -> Length[reconstructedPositions],
      "expected_positions_prefix" -> Take[expectedPositions, UpTo[maxPositions]],
      "reconstructed_positions_prefix" -> Take[reconstructedPositions, UpTo[maxPositions]],
      "per_division" -> perDivisionDiagnostics[pattern]
    |>
  ],
  {i, Min[maxExamples, Length[mismatchPatterns]]}
];

Print[ExportString[
  <|
    "network" -> <|
      "n" -> Length[cm],
      "cm" -> cm,
      "dyn" -> dyn,
      "division_size" -> divisionSize
    |>,
    "dispatch_rows" -> Length[outputs],
    "unique_output_patterns_dispatch" -> Length[Keys[expectedSorted]],
    "reconstructed_patterns" -> Length[Keys[reconstructedSorted]],
    "exact_match" -> (expectedSorted === reconstructedSorted),
    "mismatch_pattern_count" -> Length[mismatchPatterns],
    "expected_only_count" -> Length[Complement[Keys[expectedSorted], Keys[reconstructedSorted]]],
    "reconstructed_only_count" -> Length[Complement[Keys[reconstructedSorted], Keys[expectedSorted]]],
    "expected_patterns" -> Length[Keys[expectedSorted]],
    "reconstructed_pattern_keys" -> Length[Keys[reconstructedSorted]],
    "examples" -> examples,
    "division_decimal_keys" -> (Length[Keys[#]] & /@ compressed["Locations"]),
    "division_sumandos_keys" -> (Length[Keys[#]] & /@ compressed["Sumandos"])
  |>,
  "RawJSON"
]];
