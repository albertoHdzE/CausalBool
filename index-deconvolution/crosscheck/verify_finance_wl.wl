(* verify_finance_wl.wl

   Wolfram-side determinism analysis of the binarised market states and the
   deterministic control, confirming the Python metrics (mean contradiction rate
   over the full support, and the count of nodes reproduced exactly by a small
   functional support).

   Environment: CB_FIN (finance_cases.json).
*)

bundle = Import[Environment["CB_FIN"], "RawJSON"];

patternOf[state_, support_] :=
  Sum[If[state[[support[[j]] + 1]] == 1, 2^(j - 1), 0], {j, 1, Length[support]}];

contradictionRate[states_, node_, support_] := Module[
  {outs = <||>, t, p, recurring, contradictory},
  Do[
   p = patternOf[states[[t]], support];
   outs[p] = Append[Lookup[outs, p, {}], states[[t + 1, node + 1]]],
   {t, 1, Length[states] - 1}];
  recurring = Select[Values[outs], Length[#] >= 2 &];
  If[recurring === {}, Return[0.0]];
  contradictory = Count[recurring, v_ /; (MemberQ[v, 0] && MemberQ[v, 1])];
  N[contradictory/Length[recurring]]];

bestAccuracy[states_, node_, n_, maxK_] := Module[
  {total = Length[states] - 1, best = 0.0, k, support, counts, t, p, correct},
  Do[
   Do[
    counts = <||>;
    Do[
     p = patternOf[states[[t]], support];
     counts[p] = Lookup[counts, p, {0, 0}] + If[states[[t + 1, node + 1]] == 1, {0, 1}, {1, 0}],
     {t, 1, total}];
    correct = Total[Max /@ Values[counts]];
    If[N[correct/total] > best, best = N[correct/total]],
    {support, Subsets[Range[0, n - 1], {k}]}],
   {k, 1, maxK}];
  best];

analyse[states_, maxK_] := Module[{n = Length[states[[1]]], full, cr, exactCount},
  full = Range[0, n - 1];
  cr = Mean[Table[contradictionRate[states, i, full], {i, 0, n - 1}]];
  exactCount = Count[Table[bestAccuracy[states, i, n, maxK], {i, 0, n - 1}], a_ /; a >= 0.999];
  <|"mean_contradiction" -> N[cr], "exact_nodes" -> exactCount, "n" -> n|>];

Do[
  Module[{key = k, case, res, pyCr, pyEx, agree},
   case = bundle[key];
   res = analyse[case["states"], case["max_k"]];
   pyCr = case["py_mean_contradiction"]; pyEx = case["py_exact_nodes"];
   agree = (Abs[res["mean_contradiction"] - pyCr] < 0.001) && (res["exact_nodes"] == pyEx);
   Print[key, ": wl_contradiction=", res["mean_contradiction"],
     " py=", pyCr, "  wl_exact=", res["exact_nodes"], "/", res["n"],
     " py_exact=", pyEx, "  agree=", agree]],
  {k, {"market", "control"}}];
