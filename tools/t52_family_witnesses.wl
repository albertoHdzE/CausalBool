(* ::Package:: *)
(* AUDIT01/T5.2 (D-6 closed: ALL TWELVE families) - mechanical proof witnesses.
   For every gate family, at every supported arity 2..6 (NOT/IMPLIES/NIMPLIES
   from their minimal arities), compare:
     analytic  : Integration`Gates`IndexSetAnalytic[n, Ic, gate, params]  (LSB-native)
     exhaustive: rows of ApplyGate evaluated over the full LSB repertoire,
                 projected onto Ic -> acceptance vector -> one-set rows
   Elementwise (sorted SameQ); symmetric-difference size recorded - never
   cardinality alone (U8). Output: papers/method/derivations/verification/. *)

AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

outDir = FileNameJoin[{"papers", "method", "derivations", "verification"}];
If[!DirectoryQ[outDir], CreateDirectory[outDir, CreateIntermediateDirectories -> True]];

lsbRow[x_, nn_] := Reverse[IntegerDigits[x, 2, nn]];
lutOneSet[nn_, ic_List, gate_String, pr_Association] :=
 Module[{rows, outs},
  rows = Table[lsbRow[x, nn], {x, 0, 2^nn - 1}];
  outs = Which[
   gate === "NOT",
    Module[{ii = Lookup[pr, "i", ic[[1]]]}, (1 - #[[ii]]) & /@ rows],
   (* AUDIT01/T5.2: pair/i params are ABSOLUTE network coordinates (engine +
      vectorPredict convention, ORDERING.md §4b); ApplyGate's positional slice
      reading cannot express them, so ground truth evaluates the connective
      directly on the named coordinates - mirroring the established
      FormulaVsExhaustiveTests fast path verbatim. *)
   gate === "IMPLIES" || gate === "NIMPLIES",
    Module[{pair = Lookup[pr, "pair", ic[[;; 2]]], a, b},
      {a, b} = pair;
      If[gate === "IMPLIES",
         Boole[(1 - #[[a]]) + #[[b]] >= 1] &,
         Boole[#[[a]]*(1 - #[[b]]) == 1] &] /@ rows],
   True, ApplyGate[gate, #[[ic]], pr] & /@ rows];
  Sort@Flatten@Position[outs, 1, 1]];

paramGrid[gate_String, d_Integer] :=
  Which[
   gate === "KOFN",
     Join[<|"k" -> #, "strict" -> False|> & /@ Range[1, d],
          <|"k" -> #, "strict" -> True|> & /@ Range[1, d]],
   gate === "CANALISING",
     <|"canalisingIndex" -> #1, "canalisingValue" -> #2, "canalisedOutput" -> #3|> & @@@
       Tuples[{Range[1, d], {0, 1}, {0, 1}}],
   gate === "IMPLIES" || gate === "NIMPLIES",
     <|"pair" -> #|> & /@ Select[Permutations[Range[d], {2}], #[[1]] < #[[2]] &],
   True, {<||>}];

families = {"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN","CANALISING"};

witness[gate_String, nn_Integer, ic_List, pr_Association] := Module[{ana, lut},
  ana = Integration`Gates`IndexSetAnalytic[nn, ic, gate, pr];
  If[ana === $Failed, <|"ok" -> False, "error" -> "$Failed"|>,
   lut = lutOneSet[nn, ic, gate, pr];
   <|"n" -> nn, "Ic" -> ic, "params" -> pr,
     "onesAnalytic" -> Length[ana], "onesExhaustive" -> Length[lut],
     "symDiffSize" -> Length[Complement[ana, lut]] + Length[Complement[lut, ana]],
     "equal" -> Sort[ana] === Sort[lut]|>]];

results = Association @@
  Table[gate ->
    Module[{arities, cases},
      arities = Which[gate === "NOT" || gate === "IMPLIES" || gate === "NIMPLIES", Range[2, 6],
        True, Range[2, 6]];
      cases = Flatten[Table[
        Module[{d = ar, ic = Range[ar]},
         witness[gate, ar, ic, #] & /@ paramGrid[gate, d]],
        {ar, arities}], 1];
      <|"cases" -> cases,
        "totalCases" -> Length[cases],
        "failedCases" -> Select[cases, ! TrueQ[#["equal"]] &]|>],
   {gate, families}];

Do[Export[FileNameJoin[{outDir, gate <> ".json"}], results[gate], "JSON"], {gate, families}];
Export[FileNameJoin[{outDir, "witnesses_summary.json"}],
  <|"executedAt" -> DateString[], "arityMax" -> 6,
    "totals" -> Association @@ Table[g -> results[g]["totalCases"], {g, families}],
    "failures" -> Association @@ Table[g -> Length[results[g]["failedCases"]], {g, families}]|>,
  "JSON"];

Do[Print[g, ": ", results[g]["totalCases"], " cases, failures=",
  Length[results[g]["failedCases"]]], {g, families}];
If[AnyTrue[Table[Length[results[g]["failedCases"]], {g, families}], # > 0 &], Exit[1]];
Print["T52 WITNESSES OK: all twelve families, arities 2..6, elementwise equal"]
