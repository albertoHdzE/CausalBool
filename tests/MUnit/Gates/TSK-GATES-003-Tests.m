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

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
