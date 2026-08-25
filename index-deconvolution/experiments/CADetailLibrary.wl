(* CADetailLibrary.wl

   Detailed comparison helpers for the cellular-automaton notebook: render the
   recovered network (connectivity matrix and gates), express each cell's rule in
   index-set pivot/sumandos form, and compare the original space-time pattern with
   the reconstructed evolution, highlighting matching rows and their indices.

   Depends on CausalBoolCore.wl, Deconvolution.wl, CADeconvolution.wl and
   CADemoLibrary.wl.
*)

(* One cell's rule as a union of pivot-shifted cosets (activator/inhibitor
   clauses).  For each clause: pivot = decimal of the activator cells; the free
   cells (sumandos) are all cells the clause does not fix. *)
CBRuleDescription[dec_, k_] := Module[
  {rep, support, m, n, reduced, clauses, descs},
  rep = dec["reports"][[k]];
  support = Lookup[rep, "connected", Lookup[rep, "support", {}]];
  m = Length[support];
  n = dec["n"]; reduced = rep["reduced"];
  clauses = If[m == 0, {}, CBRegulatoryDNFClauses[reduced, m]];
  descs = Function[cl,
     Module[{actCells, inhCells, fixed, free, pivot},
      actCells = support[[# + 1]] & /@ cl["activators"];
      inhCells = support[[# + 1]] & /@ cl["inhibitors"];
      fixed = Join[actCells, inhCells];
      free = Complement[Range[n], fixed];
      pivot = Total[2^(# - 1) & /@ actCells];
      <|"activators" -> actCells, "inhibitors" -> inhCells, "pivot" -> pivot,
        "free" -> free, "cosetSize" -> 2^Length[free]|>]] /@ clauses;
  <|"node" -> k, "gate" -> rep["canonical"][[1]], "support" -> support,
    "oneSetSize" -> Total[reduced]*2^(n - m), "clauses" -> descs|>];

(* A compact table of the whole recovered network. *)
CBNetworkTable[dec_] := Module[{rows},
  rows = Table[
    Module[{d = CBRuleDescription[dec, k]},
     {k, d["gate"], d["support"], d["oneSetSize"], Length[d["clauses"]]}],
    {k, 1, dec["n"]}];
  Grid[Prepend[rows,
    Style[#, Bold] & /@ {"cell", "gate", "inputs", "|one-set|", "clauses"}],
   Frame -> All, Alignment -> Left]];

(* Print the index-set rule of one cell in pivot/sumandos language. *)
CBPrintRule[dec_, k_] := Module[{d = CBRuleDescription[dec, k]},
  Print["cell ", k, ": gate ", d["gate"], ", inputs ", d["support"],
    ", one-set size ", d["oneSetSize"]];
  Do[Print["   clause: pivot = ", cl["pivot"],
     " (activators ", cl["activators"], ", inhibitors ", cl["inhibitors"],
     "), sumandos over free cells ", cl["free"],
     " -> coset size ", cl["cosetSize"]],
   {cl, d["clauses"]}]];

(* Compare the original diagram with the reconstructed network's evolution. *)
CBCompareEvolution[dec_, diagram_] := Module[{recon, diff, match},
  recon = CBEvolveNetwork[dec, diagram[[1]], Length[diagram]];
  match = (recon === diagram);
  diff = Table[BitXor[diagram[[i, j]], recon[[i, j]]],
    {i, 1, Length[diagram]}, {j, 1, Length[diagram[[1]]]}];
  <|"match" -> match,
    "original" -> ArrayPlot[diagram, ColorRules -> {0 -> White, 1 -> Black},
      PlotLabel -> "original cellular automaton", ImageSize -> 240, Frame -> True],
    "reconstructed" -> ArrayPlot[recon, ColorRules -> {0 -> White, 1 -> Black},
      PlotLabel -> "reconstructed network evolution", ImageSize -> 240, Frame -> True],
    "difference" -> ArrayPlot[diff, ColorRules -> {0 -> White, 1 -> Red},
      PlotLabel -> "difference (all white = identical)", ImageSize -> 240, Frame -> True]|>];

(* Highlight, in red, every time step whose spatial pattern equals targetRow;
   the pattern within highlighted rows is preserved (light red 0, red 1). *)
CBHighlightPattern[diagram_, targetRow_] := Module[{matches, marked, plot},
  matches = Flatten[Position[diagram, targetRow]];
  marked = MapIndexed[
    If[MemberQ[matches, First[#2]], #1 /. {0 -> 2, 1 -> 3}, #1] &, diagram];
  plot = ArrayPlot[marked,
    ColorRules -> {0 -> White, 1 -> Black, 2 -> LightRed, 3 -> Red},
    PlotLabel -> "target pattern located in time (red rows)",
    ImageSize -> 260, Frame -> True];
  <|"plot" -> plot, "matching_time_indices" -> matches|>];
