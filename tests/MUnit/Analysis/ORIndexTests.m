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

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
