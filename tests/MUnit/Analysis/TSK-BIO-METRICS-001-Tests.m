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
(* AUDIT03/R3.1 (2026-09-03) — INTENDED DELTA, recorded not absorbed.
   Was 2.8509775004326936*^1. BioMetrics encodeNodeCost now charges the
   log2(n+1) in-degree field without which the code is not uniquely decodable
   (Kraft sum was n+1, not 1). At n=4 the correction is exactly 4*Log2[5] =
   9.287712379549449, and 28.509775004326936 + 9.287712379549449 =
   37.79748738387639 — so this expectation moves by the field and by nothing
   else, which is itself the check. Evidence, including the decoder and its
   negative controls: audit/AUDIT03_R3_description_length/FINDING.md. *)
expected = 3.779748738387639*^1;
tol = 10.^-6;
okMatch = Abs[Dbits1 - expected] < tol;
okConsistent = Abs[Dbits1 - Dbits2] < tol;
metrics = <|"Dbits" -> Dbits1, "DbitsAssoc" -> Dbits2, "expected" -> expected, "okMatch" -> okMatch, "okConsistent" -> okConsistent|>;
Export[FileNameJoin[{base, "Metrics.json"}], metrics, "JSON"];
status = If[And[okMatch, okConsistent], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
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
