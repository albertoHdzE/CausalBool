(* Exact complete one-step behaviour owner.

   The exhaustive dispatch is used only as a validation owner when requested.
   The compressed owner is the Alpha.m Locations/Sumandos pipeline.  The
   default response contains counts and the canonical additive pairs, but not
   the unfolded position lists.  Position lists are an explicit small-N
   explanatory option because they can be exponentially larger than the pair.
*)
repo = If[StringLength[Environment["CB_REPO"]] > 0, Environment["CB_REPO"], Directory[]];
SetDirectory[repo];
inputPath = Environment["DOPPEL_INPUT_JSON"];
If[StringLength[inputPath] == 0,
  Print[ExportString[<|"error" -> "missing DOPPEL_INPUT_JSON"|>, "RawJSON"]]; Exit[2]
];

payload = Import[inputPath, "RawJSON"];
cm = payload["cm"];
dyn = payload["dyn"];
divisionSize = Lookup[payload, "division_size", 2];
materialize = TrueQ[Lookup[payload, "materialize_positions", False]];
validateExhaustive = TrueQ[Lookup[payload, "validate_exhaustive", True]];
n = Length[cm];
limit = 2^n;

Get["src/integration/Alpha.m"];
Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/Experiments.m"];

(* The existing Alpha owner returns a final pattern -> position map.  Its
   positions are zero-based after converting the exhaustive table positions.
   A small deterministic factorisation exposes the additive pair without
   making the Python caller unfold it. *)
closedMask[positions_List] := Module[{set = DeleteDuplicates[positions], mask = 0, bit},
  If[Length[set] == 0, Return[0]];
  Do[bit = 2^j;
    If[And @@ ((MemberQ[set, BitXor[#, bit]]) & /@ set), mask += bit],
    {j, 0, Max[0, IntegerLength[Max[set], 2] - 1]}];
  mask
];

subsetOffsets[mask_Integer] := Module[{bits, result = {0}},
  bits = Select[2^Range[0, Max[0, IntegerLength[mask, 2] - 1]], BitAnd[mask, #] != 0 &];
  Do[result = Join[result, (# + bit & /@ result)], {bit, bits}];
  Sort[DeleteDuplicates[result]]
];

canonicalPair[positions_List] := Module[
  {set = Sort[DeleteDuplicates[positions]], mask, offsets, decimals, unfolded},
  If[Length[set] == 0, Return[<|"DecimalRepertoire" -> {}, "Sumandos" -> {},
    "pair_is_disjoint" -> True|>]];
  mask = closedMask[set];
  (* Avoid constructing an offset family larger than the explicit protocol
     budget.  The fallback remains exact and is marked as disjoint. *)
  If[DigitCount[mask, 2, 1] > 20,
    Return[<|"DecimalRepertoire" -> set, "Sumandos" -> {0},
      "pair_is_disjoint" -> True|>]
  ];
  offsets = subsetOffsets[mask];
  decimals = Select[set, BitAnd[#, mask] == 0 &];
  unfolded = Sort[DeleteDuplicates[Flatten[Table[d + s, {d, decimals}, {s, offsets}]]]];
  If[unfolded =!= set,
    <|"DecimalRepertoire" -> set, "Sumandos" -> {0}, "pair_is_disjoint" -> True|>,
    <|"DecimalRepertoire" -> decimals, "Sumandos" -> offsets,
      "pair_is_disjoint" -> (Length[decimals] Length[offsets] == Length[set])|>
  ]
];

dispatch = If[validateExhaustive,
  Integration`Experiments`CreateRepertoiresDispatch[cm, dyn], <||>];
outputs = If[validateExhaustive, dispatch["RepertoireOutputs"], {}];

compressed = calculatingPattsInDivisionsOfCM[cm, dyn, divisionSize];
reconstructed = calculatingAttractors[
  compressed["Locations"], compressed["Sumandos"]
]["BinAttractorsByPosition"];

allPatterns = Table[Reverse[IntegerDigits[x, 2, n]], {x, 0, limit - 1}];
rows = Table[
  Module[{pattern = allPatterns[[x + 1]], positions, pair, row},
    positions = If[KeyExistsQ[reconstructed, pattern],
      Sort[DeleteDuplicates[reconstructed[pattern]]], {}];
    pair = canonicalPair[positions];
    row = <|"output_pattern" -> pattern,
      "occurrence_count" -> Length[positions],
      "DecimalRepertoire" -> pair["DecimalRepertoire"],
      "Sumandos" -> pair["Sumandos"],
      "pair_is_disjoint" -> pair["pair_is_disjoint"]|>;
    If[materialize, Append[row, "reconstructed_output_positions" -> positions], row]
  ], {x, 0, limit - 1}];

expected = If[validateExhaustive,
  GroupBy[MapIndexed[<|"Pattern" -> #1, "Position" -> First[#2] - 1|> &, outputs],
    #Pattern &, Sort[#[[All, "Position"]]] &], <||>];
expectedRows = If[validateExhaustive,
  Table[If[KeyExistsQ[expected, allPatterns[[x + 1]]],
    Sort[DeleteDuplicates[expected[allPatterns[[x + 1]]]]], {}],
    {x, 0, limit - 1}], {}];
actualRows = Lookup[#, "reconstructed_output_positions", Missing[]] & /@ rows;
countMatch = If[validateExhaustive,
  And @@ MapThread[Function[{a, b}, TrueQ[Length[a] == b]], {expectedRows,
    Lookup[#, "occurrence_count", 0] & /@ rows}], True];
positionMatch = If[validateExhaustive && materialize,
  And @@ MapThread[Function[{a, b}, TrueQ[Sort[a] == Sort[b]]], {expectedRows, actualRows}], True];
exactMatch = countMatch && positionMatch;

Print[ExportString[<|
  "network" -> <|"n" -> n, "cm" -> cm, "dyn" -> dyn,
    "division_size" -> divisionSize|>,
  "input_enumeration" -> "decimal_0_to_2^N_minus_1",
  "output_bit_order" -> "LSB_first_node_0_to_N_minus_1",
  "position_convention" -> "zero_based",
  "materialize_positions" -> materialize,
  "validate_exhaustive" -> validateExhaustive,
  "dispatch_rows" -> If[validateExhaustive, Length[outputs], Null],
  "reconstructed_output_patterns" -> Length[Keys[reconstructed]],
  "representations" -> rows,
  "validation" -> <|"exact_match" -> exactMatch,
    "count_match" -> countMatch, "position_match" -> positionMatch,
    "count_checks" -> If[validateExhaustive,
      MapThread[Function[{a, b}, Boole[TrueQ[Length[a] == b]]],
        {expectedRows, Lookup[#, "occurrence_count", 0] & /@ rows}], {}],
    "position_checks" -> If[validateExhaustive && materialize,
      MapThread[Function[{a, b}, Boole[TrueQ[Sort[a] == Sort[b]]]],
        {expectedRows, actualRows}], {}],
    "expected_positions_available" -> validateExhaustive,
    "expected_position_count" -> If[validateExhaustive, Total[Length /@ expectedRows], Null],
    "reconstructed_position_count" -> Total[Lookup[rows, "occurrence_count", 0]]|>
|>, "RawJSON"]];
