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
