base = FileNameJoin[{"results", "tests", "arch3"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
AppendTo[$Path, "src/Packages"];
Needs["Integration`Alpha`"];
Needs["Integration`Gates`"];
Needs["Integration`Experiments`"];
symsAlpha = Names["Integration`Alpha`*"];
symsGates = Names["Integration`Gates`*"];
symsExper = Names["Integration`Experiments`*"];
cm = {{0, 1}, {1, 0}};
dyn = {"AND", "XOR"};
rep = Integration`Alpha`CreateRepertoires[cm, dyn];
okCreate = KeyExistsQ[rep, "RepertoireOutputs"];
okApply = Integration`Gates`ApplyGate["AND", {1, 1}] === 1 && Integration`Gates`ApplyGate["OR", {0, 0}] === 0;
rd = Integration`Experiments`RunDynamic[cm, dyn];
okRun = KeyExistsQ[rd, "RepertoireOutputs"];
existsPublic = Length[symsAlpha] > 0 && Length[symsGates] > 0 && Length[symsExper] > 0;
status = If[okCreate && okApply && okRun && existsPublic, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Association["Status" -> status, "PublicSymbols" -> {Length[symsAlpha], Length[symsGates], Length[symsExper]}, "CreateOK" -> okCreate, "ApplyOK" -> okApply, "RunOK" -> okRun, "ResultsPath" -> base]