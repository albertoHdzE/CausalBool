Get["src/Packages/Integration/Experiments.m"];
patternSymbol[col_List] := Module[{z, o}, z = Count[col, 0]; o = Count[col, 1]; If[z == Length[col], 0, If[o == Length[col], 1, "*"]]];
base = FileNameJoin[{"results", "tests", "pattern001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
cmX = {{0,1},{1,0}};
dynX = {"XOR","XOR"};
repX = Integration`Experiments`CreateRepertoiresDispatch[cmX, dynX]["RepertoireOutputs"];
patX = patternSymbol /@ Transpose[repX];
okX = (patX === {"*","*"});
cmK = {{1,1},{1,1}};
dynK = {"KOFN","KOFN"};
paramsK = <|1 -> <|"k" -> 0|>, 2 -> <|"k" -> 3|>|>;
repK = Integration`Experiments`CreateRepertoiresDispatch[cmK, dynK, paramsK]["RepertoireOutputs"];
patK = patternSymbol /@ Transpose[repK];
okK = (patK === {1,0});
status = If[okX && okK, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "Patterns.json"}], <|"XOR"->patX, "KOFN"->patK|>, "JSON"];
Association["Status"->status, "ResultsPath"->base]
