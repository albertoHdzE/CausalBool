(* archived by AUDIT03/R2a.2 from papers/method/manuscript_computational/generate_paper_outputs.wl *)
weights[n_Integer] := 2^Range[0, n - 1];
allOffsets[n_Integer, connected_List] := Module[
  {free = Complement[Range[n], connected], ws},
  ws = weights[n][[free]];
  If[Length[ws] == 0, {0}, Sort[(# . ws) & /@ Tuples[{0, 1}, Length[ws]]]]
];
givePlaces[locations_List, sumandos_List] :=
  Sort@Flatten[Table[loc + sumandos, {loc, locations}]];
];
];
];
];
];
];