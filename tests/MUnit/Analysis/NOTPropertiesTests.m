AppendTo[$Path, "src/Packages"];
Get["src/Packages/Integration/Gates.m"];
base = FileNameJoin[{"results", "tests", "analysis_not"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
inputs = {{0},{1}};
out = Integration`Gates`ApplyGate["NOT", #] & /@ inputs;
inv = Integration`Gates`ApplyGate["NOT", {#}] & /@ out;
okInv = inv === Flatten[inputs];
sensPairs = {{{0},{1}}, {{1},{0}}};
okSens = And @@ Table[Integration`Gates`ApplyGate["NOT", sensPairs[[i,1]]] != Integration`Gates`ApplyGate["NOT", sensPairs[[i,2]]], {i, Length[sensPairs]}];
status = If[okInv && okSens, "OK", "FAIL"];
Export[FileNameJoin[{base, "PropertiesStatus.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "ResultsPath" -> base]