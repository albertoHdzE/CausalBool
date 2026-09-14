Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];
n = 3;
cm = {{0,1,1},{0,0,0},{0,0,0}};
dyn = {"OR","AND","XOR"};
phi[j_, n_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2];
res = Integration`Experiments`CreateRepertoiresDispatch[cm, dyn];
base = res["RepertoireOutputs"];
lsbIndicesOR = Flatten@Position[base[[All, 1]], 1];
mapped = Sort[phi[#, n] & /@ lsbIndicesOR];
set = Integration`Gates`IndexSetNetwork["OR", n, {2,3}, <||>];
analytic = Sort[set];
ok = (mapped === analytic);
CreateDirectory["results/tests/analysis_or", CreateIntermediateDirectories -> True];
Export["results/tests/analysis_or/Patterns.json", <|"n"->n,"Ic"->{2,3},"LSBOnes"->lsbIndicesOR,"MSBMap"->mapped,"Analytic"->analytic,"ok"->ok|>];
Export["results/tests/analysis_or/Status.txt", If[ok, "PASS", "FAIL"]];

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export["results/tests/analysis_or/Done.txt", DateString[], "Text"];
