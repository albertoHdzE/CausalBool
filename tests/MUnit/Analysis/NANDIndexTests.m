inputs = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
Ic = {2, 3};
(* Empirical zero-set: connected bits all 1 *)
empZero = Flatten@Position[Map[And @@ Map[# == 1 &, #[[Ic]]] &, inputs], True, 1];
(* Empirical one-set is the complement *)
allIdx = Range[Length[inputs]];
empOne = Complement[allIdx, empZero];
base = FileNameJoin[{"results", "tests", "analysis_nand"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
okZeroOne = Sort[empZero] === {4, 8} && Sort[empOne] === {1, 2, 3, 5, 6, 7};
Export[FileNameJoin[{base, "NANDZeroIndices.json"}], empZero, "JSON"];
Export[FileNameJoin[{base, "NANDOneIndices.json"}], empOne, "JSON"];
Export[FileNameJoin[{base, "StatusIndex.txt"}], {If[okZeroOne, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okZeroOne, "OK", "FAIL"], "ResultsPath" -> base]