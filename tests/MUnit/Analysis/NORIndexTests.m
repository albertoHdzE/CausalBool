inputs = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
Ic = {2, 3};
(* Empirical one-set: connected bits all 0 *)
empOne = Flatten@Position[Map[And @@ Map[# == 0 &, #[[Ic]]] &, inputs], True, 1];
(* Empirical zero-set is the complement *)
allIdx = Range[Length[inputs]];
empZero = Complement[allIdx, empOne];
base = FileNameJoin[{"results", "tests", "analysis_nor"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
okZeroOne = Sort[empOne] === {1, 5} && Sort[empZero] === {2, 3, 4, 6, 7, 8};
Export[FileNameJoin[{base, "NOROneIndices.json"}], empOne, "JSON"];
Export[FileNameJoin[{base, "NORZeroIndices.json"}], empZero, "JSON"];
Export[FileNameJoin[{base, "StatusIndex.txt"}], {If[okZeroOne, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okZeroOne, "OK", "FAIL"], "ResultsPath" -> base]