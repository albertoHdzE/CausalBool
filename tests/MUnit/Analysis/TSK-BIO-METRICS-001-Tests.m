Get["src/Packages/Integration/BioMetrics.m"];
base = FileNameJoin[{"results", "tests", "biometrics001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
cm = {{0, 1, 0, 0}, {1, 0, 1, 0}, {0, 1, 0, 1}, {0, 0, 1, 0}};
dyn = {"AND", "OR", "XOR", "KOFN"};
params = <|4 -> <|"k" -> 2|>|>;
net = <|"cm" -> cm, "dynamic" -> dyn, "params" -> params|>;
res1 = Integration`BioMetrics`ComputeDescriptionLength[cm, dyn, params];
res2 = Integration`BioMetrics`ComputeDescriptionLength[net];
Dbits1 = res1["D"];
Dbits2 = res2["D"];
expected = 2.8509775004326936*^1;
tol = 10.^-6;
okMatch = Abs[Dbits1 - expected] < tol;
okConsistent = Abs[Dbits1 - Dbits2] < tol;
metrics = <|"Dbits" -> Dbits1, "DbitsAssoc" -> Dbits2, "expected" -> expected, "okMatch" -> okMatch, "okConsistent" -> okConsistent|>;
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
status = If[And[okMatch, okConsistent], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "ResultsPath" -> base]

