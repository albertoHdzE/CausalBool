AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_kofn"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
tt2 = Integration`Gates`TruthTable["KOFN", 3, <|"k" -> 2|>];
idx2 = Integration`Gates`IndexSet["KOFN", 3, <|"k" -> 2|>];
okIdx2 = (idx2 === {4, 6, 7, 8});
tt0 = Integration`Gates`TruthTable["KOFN", 3, <|"k" -> 0|>];
idx0 = Integration`Gates`IndexSet["KOFN", 3, <|"k" -> 0|>];
okIdx0 = (idx0 === Range[8]);
tt4 = Integration`Gates`TruthTable["KOFN", 3, <|"k" -> 4|>];
idx4 = Integration`Gates`IndexSet["KOFN", 3, <|"k" -> 4|>];
okIdx4 = (idx4 === {});
status = If[okIdx2 && okIdx0 && okIdx4, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "IndexSet_k2.json"}], idx2, "JSON"];
Export[FileNameJoin[{base, "IndexSet_k0.json"}], idx0, "JSON"];
Export[FileNameJoin[{base, "IndexSet_k4.json"}], idx4, "JSON"];
Association["Status" -> status, "ResultsPath" -> base]