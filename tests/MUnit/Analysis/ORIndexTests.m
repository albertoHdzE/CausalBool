(* Analytic OR index set via union of bands, with IntegerDigits ordering *)
analyticIndicesOR[n_Integer, Ic_List] := Module[{weights, allPositions, bands, Ssets},
  weights = Table[2^(n - i), {i, 1, n}];
  allPositions = Range[n];
  bands = Table[
    Ssets = Subsets[Complement[allPositions, {i}]];
    Table[1 + weights[[i]] + Total[weights[[#]] & /@ s], {s, Ssets}]
    , {i, Ic}];
  Sort@DeleteDuplicates@Flatten[bands]
];
base = FileNameJoin[{"results", "tests", "analysis_or"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
(* Case: n=3, Ic={2,3} under IntegerDigits ordering *)
inputs = Table[IntegerDigits[x, 2, 3], {x, 0, 7}];
Ic = {2, 3};
empIdx = Flatten@Position[Map[Or @@ Map[# == 1 &, #[[Ic]]] &, inputs], True, 1];
anaIdx = analyticIndicesOR[3, Ic];
okIdx = Sort[empIdx] === Sort[anaIdx];
Export[FileNameJoin[{base, "ORIndexEmpirical.json"}], empIdx, "JSON"];
Export[FileNameJoin[{base, "ORIndexAnalytic.json"}], anaIdx, "JSON"];
Export[FileNameJoin[{base, "StatusIndex.txt"}], {If[okIdx, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okIdx, "OK", "FAIL"], "ResultsPath" -> base]