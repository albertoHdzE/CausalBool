(* BioDetailLibrary.wl

   Detailed comparison helpers for the biological notebook: compare the original
   output repertoire with the reconstructed one, and locate a node's one-set (the
   input states in which it fires) in the repertoire.  The recovered network and
   its index-set pivot/sumandos rules are rendered by CADetailLibrary
   (CBNetworkTable, CBPrintRule).

   Depends on CausalBoolCore.wl, Deconvolution.wl, CADeconvolution.wl and
   CADetailLibrary.wl.
*)

CBCompareRepertoire[dec_, rep_] := Module[{rep2, match, n, R},
  rep2 = CBNetworkRepertoire[dec];
  match = (rep2 === rep);
  R = Length[rep]; n = Length[rep[[1]]];
  <|"match" -> match,
    "original" -> ArrayPlot[rep, PlotLabel -> "original repertoire",
      FrameLabel -> {"node", "input state"}, Frame -> True, ImageSize -> 190],
    "reconstructed" -> ArrayPlot[rep2, PlotLabel -> "reconstructed repertoire",
      Frame -> True, ImageSize -> 190],
    "difference" -> ArrayPlot[
      Table[BitXor[rep[[i, j]], rep2[[i, j]]], {i, R}, {j, n}],
      ColorRules -> {0 -> White, 1 -> Red},
      PlotLabel -> "difference (all white = identical)", Frame -> True,
      ImageSize -> 190]|>];

(* 1-based input-state indices in which node k fires (its one-set). *)
CBOneSetIndices[rep_, k_] := Flatten[Position[rep[[All, k]], 1]];

(* Tint node k's column across the repertoire: red where it fires, light red
   where it does not, so the one-set stands out. *)
CBHighlightNodeOneSet[rep_, k_] := Module[{marked},
  marked = Map[ReplacePart[#, k -> (#[[k]] /. {0 -> 2, 1 -> 3})] &, rep];
  ArrayPlot[marked, ColorRules -> {0 -> White, 1 -> Black, 2 -> LightRed, 3 -> Red},
    PlotLabel -> "one-set of node " <> ToString[k] <> " highlighted (red)",
    FrameLabel -> {"node", "input state"}, Frame -> True, ImageSize -> 210]];
