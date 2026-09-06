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

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
