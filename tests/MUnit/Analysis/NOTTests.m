AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_not"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
tt = Integration`Gates`TruthTable["NOT", 1];
expectedTT = {{{0}, 1}, {{1}, 0}};
okTT = tt === expectedTT;
idx = Integration`Gates`IndexSet["NOT", 1];
expectedIdx = {1};
okIdx = idx === expectedIdx;
status = If[okTT && okIdx, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "TruthTable.json"}], tt, "JSON"];
Export[FileNameJoin[{base, "IndexSet.json"}], idx, "JSON"];
Association["Status" -> status, "ResultsPath" -> base]