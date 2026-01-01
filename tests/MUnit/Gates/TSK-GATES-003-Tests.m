AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "gates003"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
inputs2 = {{0,0},{0,1},{1,0},{1,1}};
expXOR = {0,1,1,0};
outNoNoise = Integration`Gates`TruthTable["XOR",2][[All,2]];
okNoNoise = (outNoNoise === expXOR);
SeedRandom[1234]; outNoise = Integration`Gates`TruthTable["XOR",2,<|"noiseFlipProb"->0.5|>][[All,2]];
SeedRandom[1234]; outNoise2 = Integration`Gates`TruthTable["XOR",2,<|"noiseFlipProb"->0.5|>][[All,2]];
okRepro = (outNoise === outNoise2);
okDiff = (outNoise =!= outNoNoise);
status = If[okNoNoise && okRepro && okDiff, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "NoiseOutputs.json"}], <|"NoNoise"->outNoNoise, "Noise"->outNoise|>, "JSON"];
Association["Status"->status, "ResultsPath"->base]