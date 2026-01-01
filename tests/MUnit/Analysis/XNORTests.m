Get["src/Packages/Integration/Gates.m"];
Get["src/Packages/Integration/Experiments.m"];
avgSensitivityXNOR[d_Integer] := Module[{inputs, changeCount = 0}, inputs = Table[IntegerDigits[x, 2, d], {x, 0, 2^d - 1}]; Do[With[{y = Integration`Gates`ApplyGate["XNOR", v]}, Do[With[{yf = Integration`Gates`ApplyGate["XNOR", ReplacePart[v, j -> 1 - v[[j]]]]}, If[yf != y, changeCount++]], {j, 1, d}]], {v, inputs}]; N[changeCount/(2^d)]];
base = FileNameJoin[{"results", "tests", "analysis_xnor"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
emp = Table[avgSensitivityXNOR[d], {d, 1, 4}];
th = Table[d, {d, 1, 4}];
okSens = Max[Abs[emp - th]] < 10^-12;
cm = {{1, 1}, {1, 1}};
dyn = {"XNOR", "XNOR"};
rep = Integration`Experiments`CreateRepertoiresDispatch[cm, dyn]["RepertoireOutputs"];
patternSymbol[col_List] := Module[{z, o}, z = Count[col, 0]; o = Count[col, 1]; If[z == Length[col], 0, If[o == Length[col], 1, "*"]]];
pat = patternSymbol /@ Transpose[rep];
okPat = (pat === {"*", "*"});
status = If[okSens && okPat, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], status, "Text"];
Export[FileNameJoin[{base, "AverageSensitivity.json"}], <|"empirical" -> emp, "theory" -> th|>, "JSON"];
Export[FileNameJoin[{base, "Patterns.json"}], <|"XNOR_XNOR" -> pat|>, "JSON"];
Association["Status" -> status, "ResultsPath" -> base]
