(* AUDIT01/T4.1 - F36 closure pinning test: CANALISING canalisingIndex coordinate
   convention is Ic-relative everywhere. Three independent paths must agree
   ELEMENTWISE (sorted SameQ; symmetric difference printed on failure):
     G1 ground truth : ApplyGate over Part[row, Ic] of LSB rows (Reverse digits)
     G2 network path : IndexSetNetwork (MSB rows) transported via Phi exactly once
     G3 closed form  : IndexSetAnalytic (LSB-canonical native)
   Grid deliberately includes canalising coordinates that are NOT position 1 of Ic -
   the case the pre-T4.1 IndexSetNetwork branch got wrong. *)

base = FileNameJoin[{"results", "tests", "gates014canalisingcoord"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

phi[j_, nn_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, nn]], 2];
lsbRows[nn_] := Table[Reverse[IntegerDigits[x, 2, nn]], {x, 0, 2^nn - 1}];
msbToLsbRowIdx[set_List, nn_] := Sort[phi[#, nn] & /@ set];

n = 4;
ics = {{1, 3}, {2, 3}, {1, 2, 4}, {2, 3, 4}};
cases = Flatten[Table[
   <|"Ic" -> ic, "ci" -> p, "v" -> v, "co" -> co|>,
   {ic, ics}, {p, Length[ic]}, {v, {0, 1}}, {co, {0, 1}}], 3];

runCase[c_Association] := Module[{params, truth, g2, g3, ok},
   params = <|"canalisingIndex" -> c["ci"], "canalisingValue" -> c["v"], "canalisedOutput" -> c["co"]|>;
   truth = Sort@Flatten@Position[(Integration`Gates`ApplyGate["CANALISING", #[[c["Ic"]]], params] == 1) & /@ lsbRows[n], True, 1];
   g2 = msbToLsbRowIdx[Integration`Gates`IndexSetNetwork["CANALISING", n, c["Ic"], params], n];
   g3 = Sort@Integration`Gates`IndexSetAnalytic[n, c["Ic"], "CANALISING", params];
   ok = SameQ[truth, g2, g3];
   <|"case" -> c, "ok" -> ok,
     "symDiffTruthG2" -> If[ok, 0, Length[Complement[truth, g2]] + Length[Complement[g2, truth]]],
     "symDiffTruthG3" -> If[ok, 0, Length[Complement[truth, g3]] + Length[Complement[g3, truth]]]|>];

results = runCase /@ cases;
failed = Select[results, Not[TrueQ[#["ok"]]] &];
Scan[Print["GATES-014 MISMATCH: ", #["case"], " truth-vs-G2 symdiff=", #["symDiffTruthG2"], " truth-vs-G3 symdiff=", #["symDiffTruthG3"]] &, failed];
Export[FileNameJoin[{base, "Summary.json"}],
  <|"executedAt" -> DateString[], "n" -> n, "cases" -> Length[cases],
    "failedCount" -> Length[failed],
    "convention" -> "canalisingIndex is Ic-relative (GOVERNANCE/ORDERING.md)"|>, "JSON"];
Export[FileNameJoin[{base, "Status.txt"}], {If[Length[failed] == 0, "OK", "FAIL"], DateString[]}, "Text"];
If[Length[failed] == 0, Print["GATES-014 OK: ", Length[cases], " cases, all three paths elementwise-equal"], Exit[1]]
