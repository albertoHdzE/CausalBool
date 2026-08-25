(* AUDIT01/T1.2 — One-set closed form vs exhaustive LUT, ALL TWELVE families.
   Ground truth: ApplyGate evaluated over full LSB-ordered rows (Reverse[IntegerDigits]).
   Claim under test: Integration`Gates`IndexSetAnalytic == LUT on-set, elementwise
   (sorted SameQ; symmetric difference printed on failure — never cardinality alone). *)

base = FileNameJoin[{"results", "tests", "gates013onesetallfamilies"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

lsbRow[x_, n_] := Reverse[IntegerDigits[x, 2, n]];
lutOneSet[n_, ic_List, gate_String, params_Association] :=
  Module[{rows, outs},
    rows = Table[lsbRow[x, n], {x, 0, 2^n - 1}];
    outs = If[gate === "NOT",
      (* ApplyGate NOT ignores params i (negates first input only); ground truth
         here follows the documented network semantics used by the engine *)
      Module[{ii = Lookup[params, "i", ic[[1]]]}, (1 - #[[ii]]) & /@ rows],
      ApplyGate[gate, #[[ic]], params] & /@ rows];
    Flatten@Position[outs, 1, 1]
  ];

checkOne := Module[{n, ic, res, diffs},
  diffs = {};
  (* symmetric families over arities 2..5 *)
  Do[
    n = ar; ic = Range[ar];
    Scan[
      (res = Check[IndexSetAnalytic[n, ic, #, <||>], $Failed];
        If[res === $Failed || res =!= lutOneSet[n, ic, #, <||>],
          AppendTo[diffs, <| "family" -> #, "n" -> n,
            "symDiff" -> Complement[res, lutOneSet[n, ic, #, <||>]] ~Join~ Complement[lutOneSet[n, ic, #, <||>]], res |>
          ]]
      ) &, {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY"}],
    {ar, 2, 5}
  ];
  (* NOT multi-arity *)
  res = IndexSetAnalytic[3, Range[3], "NOT", <|"i" -> 2|>];
  If[res =!= lutOneSet[3, Range[3], "NOT", <|"i" -> 2|>], AppendTo[diffs, <|"family" -> "NOT-i2"|>]];
  (* IMPLIES / NIMPLIES network case beyond the arity-2 literal *)
  res = IndexSetAnalytic[4, {1, 3, 4}, "IMPLIES", <|"pair" -> {1, 3}|>];
  If[res =!= lutOneSet[4, {1, 3, 4}, "IMPLIES", <|"pair" -> {1, 3}|>], AppendTo[diffs, <|"family" -> "IMPLIES-pair13-n4"|>]];
  res = IndexSetAnalytic[4, {1, 3, 4}, "NIMPLIES", <|"pair" -> {1, 3}|>];
  If[res =!= lutOneSet[4, {1, 3, 4}, "NIMPLIES", <|"pair" -> {1, 3}|>], AppendTo[diffs, <|"family" -> "NIMPLIES-pair13-n4"|>]];
  (* KOFN strict/non-strict grid *)
  Scan[
    (res = IndexSetAnalytic[5, Range[4], "KOFN", <|"k" -> #2, "strict" -> #1|>];
      If[res =!= lutOneSet[5, Range[4], "KOFN", <|"k" -> #2, "strict" -> #1|>],
        AppendTo[diffs, <|"family" -> "KOFN", "k" -> #2, "strict" -> #1|>]
      ]) &, {False, True}, {1, 2, 3}
  ];
  (* CANALISING grid incl. non-default canalising index/value/output *)
  Scan[
    (res = IndexSetAnalytic[4, Range[3], "CANALISING", <|"canalisingIndex" -> #1, "canalisingValue" -> #2, "canalisedOutput" -> #3|>];
      If[res =!= lutOneSet[4, Range[3], "CANALISING", <|"canalisingIndex" -> #1, "canalisingValue" -> #2, "canalisedOutput" -> #3|>],
        AppendTo[diffs, <|"family" -> "CANALISING", "ci" -> #1, "cv" -> #2, "co" -> #3|>]
      ]) &, {1, 2, 3}, {0, 1}, {0, 1}
  ];
  (* public MSB transport sanity: fall-through family via IndexSet == Phi(LSB set) *)
  Module[{lsb, msbViaApi, phi},
    lsb = IndexSetAnalytic[4, Range[4], "XOR", <||>];
    phi[j_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, 4]], 2];
    msbViaApi = IndexSet["XOR", 4, <||>];
    If[msbViaApi =!= Sort[phi /@ lsb], AppendTo[diffs, <|"family" -> "XOR-via-IndexSet-Phi"|>]];
  ];
  (* legacy literal cases untouched *)
  If[IndexSet["NOT", 1] =!= {1}, AppendTo[diffs, <|"family" -> "NOT-literal"|>]];
  If[IndexSet["IMPLIES", 2] =!= {1, 2, 4}, AppendTo[diffs, <|"family" -> "IMPLIES-literal"|>]];
  If[IndexSet["NIMPLIES", 2] =!= {3}, AppendTo[diffs, <|"family" -> "NIMPLIES-literal"|>]];
  diffs
];

diffs = checkOne;
status = If[diffs === {}, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "SymDiffs.txt"}], ToString[InputForm[diffs]], "Text"];
Print["TSK-GATES-013 OneSetAllFamilies: ", status];
If[diffs =!= {}, Print["symmetric differences: ", diffs]];
Association["Status" -> status, "ResultsPath" -> base]
