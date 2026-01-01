AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_kofn"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
idxNonstrict = Integration`Gates`IndexSet["KOFN", 3, <|"k" -> 2|>];
idxStrict = Integration`Gates`IndexSet["KOFN", 3, <|"k" -> 2, "strict" -> True|>];
okStrict = (idxStrict === {8}) && (idxNonstrict === {4, 6, 7, 8});
Export[FileNameJoin[{base, "IndexSet_k2_strict.json"}], idxStrict, "JSON"];
Export[FileNameJoin[{base, "IndexSet_k2_nonstrict.json"}], idxNonstrict, "JSON"];
Export[FileNameJoin[{base, "Status_strict.txt"}], {If[okStrict, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okStrict, "OK", "FAIL"], "ResultsPath" -> base]