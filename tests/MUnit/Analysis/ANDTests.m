Get["src/Packages/Integration/Experiments.m"];
Get["src/Packages/Integration/Gates.m"];
n = 3;
cm = {{0,1,1},{0,0,0},{0,0,0}};
dyn = {"AND","OR","XOR"};
phi[j_, n_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2];
res = Integration`Experiments`CreateRepertoiresDispatch[cm, dyn];
base = res["RepertoireOutputs"];
lsbIndicesAND = Flatten@Position[base[[All, 1]], 1];
mapped = Sort[phi[#, n] & /@ lsbIndicesAND];
set = Integration`Gates`IndexSetNetwork["AND", n, {2,3}, <||>];
analytic = Sort[set];
ok = (mapped === analytic);
CreateDirectory["results/tests/analysis_and", CreateIntermediateDirectories -> True];
Export["results/tests/analysis_and/Patterns.json", <|"n"->n,"Ic"->{2,3},"LSBOnes"->lsbIndicesAND,"MSBMap"->mapped,"Analytic"->analytic,"ok"->ok|>];
Export["results/tests/analysis_and/Status.txt", If[ok, "PASS", "FAIL"]];
Export["results/tests/analysis_and/Debug.txt", StringJoin[
  "LSBOnes=", ToString[lsbIndicesAND], "\n",
  "Mapped=", ToString[mapped], "\n",
  "Analytic=", ToString[analytic]
]];

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export["results/tests/analysis_and/Done.txt", DateString[], "Text"];
