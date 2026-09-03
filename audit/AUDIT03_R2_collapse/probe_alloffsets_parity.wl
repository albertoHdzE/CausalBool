weights[n_Integer] := 2^Range[0, n - 1];
guarded[n_, connected_] := Module[{free = Complement[Range[n], connected], ws},
  ws = weights[n][[free]];
  If[Length[ws] == 0, {0}, Sort[(# . ws) & /@ Tuples[{0, 1}, Length[ws]]]]];
unguarded[n_, connected_] := Module[{free = Complement[Range[n], connected], ws},
  ws = weights[n][[free]];
  Sort[(# . ws) & /@ Tuples[{0, 1}, Length[ws]]]];
Print["all coordinates connected (free = {}):"];
Print["  guarded   -> ", guarded[3, {1,2,3}]];
Print["  unguarded -> ", unguarded[3, {1,2,3}]];
Print["  equal     -> ", guarded[3,{1,2,3}] === unguarded[3,{1,2,3}]];
Print[""];
Print["exhaustive comparison, n=1..6, every connected subset:"];
diffs = 0; total = 0;
Do[Do[ total++;
   If[guarded[n, s] =!= unguarded[n, s], diffs++;
      If[diffs <= 3, Print["  DIFFERS n=", n, " connected=", s,
         "  guarded=", guarded[n,s], "  unguarded=", unguarded[n,s]]]],
   {s, Subsets[Range[n]]}], {n, 1, 6}];
Print["  ", total, " cases, ", diffs, " differ"];
