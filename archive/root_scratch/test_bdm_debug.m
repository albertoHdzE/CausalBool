(* test_bdm_debug.m *)
Print["=== Robust Attractor Test ==="];
g2 = Graph[{1->2, 2->1, 3->3}];
cycles = FindCycle[g2, Infinity, All];
selfLoops = List /@ Select[EdgeList[g2], First[#] === Last[#] &];
allAttrs = Join[cycles, selfLoops];
Print["All Attractors (Edges): ", allAttrs];
Print["States: ", Map[First, #, {2}]& /@ allAttrs];
