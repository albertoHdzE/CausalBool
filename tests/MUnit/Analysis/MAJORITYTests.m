(* AUDIT01/T1.2+T1.3 — MAJORITY dedicated coverage (previously none).
   Convention under test (TIE POLICY): ties -> 0 for even arity
   (strict majority; threshold t=Floor[d/2]+1), matching Gates.m myMajority.
   This test pins the convention so D-3 cannot drift silently. *)

base = FileNameJoin[{"results", "tests", "analysis_majority"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

ok = True;
(* odd arity 3: exhaustive *)
tt3 = Tuples[{0, 1}, 3];
exp3 = If[Total[#] >= 2, 1, 0] & /@ tt3;
Scan[
  Function[pair, Module[{row = pair[[1]], exp = pair[[2]], v},
    v = ApplyGate["MAJORITY", row, <||>];
    If[v =!= exp, ok = False; Print["MAJORITY mismatch at ", row, ": got ", v, ", expected ", exp]]]],
  Transpose[{tt3, exp3}]
];
(* even arity 4 INCLUDING the tie rows {two ones}: pins ties->0 *)
tieRows = Select[Tuples[{0, 1}, 4], Total[#] == 2 &];
Scan[
  (v = ApplyGate["MAJORITY", #, <||>];
    If[v =!= 0, ok = False; Print["MAJORITY tie row ", #, " must output 0 (ties->0)"]]) &,
  tieRows
];
(* AUDIT01/T1.3: pin the declared alternative policy explicitly *)
Scan[
  (v = ApplyGate["MAJORITY", #, <|"tiePolicy" -> "atOrAbove"|>];
    If[v =!= 1, ok = False; Print["MAJORITY atOrAbove tie row ", #, " must output 1"]]) &,
  tieRows
];
(* closed form vs LUT at n=5 over Ic=Range[4] *)
lut = Module[{rows, outs},
  rows = Table[Reverse[IntegerDigits[x, 2, 5]], {x, 0, 31}];
  outs = ApplyGate["MAJORITY", #[[;; 4]], <||>] & /@ rows;
  Flatten@Position[outs, 1, 1]
];
ana = IndexSetAnalytic[5, Range[4], "MAJORITY", <||>];
If[ana =!= lut,
  ok = False;
  Print["MAJORITY n=5 symDiff: ", Complement[ana, lut] ~Join~ Complement[lut, ana]]];

status = If[ok, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Print["Analysis/MAJORITY: ", status];
Association["Status" -> status, "ResultsPath" -> base]
