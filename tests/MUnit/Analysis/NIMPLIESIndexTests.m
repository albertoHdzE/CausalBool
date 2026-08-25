(* AUDIT01/T1.2 — NIMPLIES dedicated coverage (previously none): truth-table parity
   ApplyGate vs hand semantics, plus closed-form one-set vs LUT at n=3. *)

base = FileNameJoin[{"results", "tests", "analysis_nimplies"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

ok = True;
(* arity-2 truth table: NIMPLIES = a AND NOT b -> only (1,0) outputs 1 *)
tt = {{0,0},{0,1},{1,0},{1,1}};
expected = {0,0,1,0};
Scan[
  Function[pair, Module[{row = pair[[1]], exp = pair[[2]], v},
    v = ApplyGate["NIMPLIES", row, <||>];
    If[v =!= exp, ok = False; Print["NIMPLIES mismatch at ", row, ": got ", v, ", expected ", exp]]]],
  Transpose[{tt, expected}]
];
(* literal IndexSet case unchanged *)
If[IndexSet["NIMPLIES", 2] =!= {3}, ok = False; Print["literal set drifted"]];
(* closed form vs LUT at n=3, Ic={1,2}, pair {1,2} *)
lut = Module[{rows, outs},
  rows = Table[Reverse[IntegerDigits[x, 2, 3]], {x, 0, 7}];
  outs = ApplyGate["NIMPLIES", #[[{1, 2}]], <||>] & /@ rows;
  Flatten@Position[outs, 1, 1]
];
ana = IndexSetAnalytic[3, {1, 2}, "NIMPLIES", <|"pair" -> {1, 2}|>];
If[ana =!= lut,
  ok = False;
  Print["NIMPLIES n=3 symDiff: ", Complement[ana, lut] ~Join~ Complement[lut, ana]]];

status = If[ok, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Print["Analysis/NIMPLIES: ", status];
Association["Status" -> status, "ResultsPath" -> base]
