AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "analysis_implies"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
n = 3; pair = {1, 3};
inputs = Table[IntegerDigits[x, 2, n], {x, 0, 2^n - 1}];
(* R4/W0.3: Or/And over integer 0/1 stay symbolic (1||0 does not evaluate), so the
   empirical arm exported {} — predicate comparisons restore it. Analytic arm is
   IndexSetNetwork under the MSB row contract (ORDERING §3), pair network-absolute (§4b). *)
empImp = Flatten@Position[((#[[pair[[1]]]] == 0) || (#[[pair[[2]]]] == 1)) & /@ inputs, True, 1];
empNImp = Flatten@Position[((#[[pair[[1]]]] == 1) && (#[[pair[[2]]]] == 0)) & /@ inputs, True, 1];
anaImp = Integration`Gates`IndexSetNetwork["IMPLIES", n, {}, <|"pair" -> pair|>];
anaNImp = Integration`Gates`IndexSetNetwork["NIMPLIES", n, {}, <|"pair" -> pair|>];
okImp = Sort[empImp] === Sort[anaImp];
okNImp = Sort[empNImp] === Sort[anaNImp];
Export[FileNameJoin[{base, "IndexSetNetwork_IMPLIES_pair1_3.json"}], empImp, "JSON"];
Export[FileNameJoin[{base, "IndexSetNetwork_NIMPLIES_pair1_3.json"}], empNImp, "JSON"];
Export[FileNameJoin[{base, "Status_network_pair.txt"}], {If[okImp && okNImp, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[okImp && okNImp, "OK", "FAIL"], "ResultsPath" -> base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
