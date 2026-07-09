(* CADemoLibrary.wl

   Report helpers for the cellular-automaton deconvolution notebook.  Depends on
   CausalBoolCore.wl, Deconvolution.wl and CADeconvolution.wl being loaded first.
*)

CAExampleRules = {254, 90, 232, 150, 30, 110};

(* Named-gate identity where one exists, for commentary. *)
CAKnownIdentity = <|
  254 -> "OR over the three cells",
  90 -> "XOR of left and right; centre irrelevant",
  232 -> "MAJORITY of the three cells",
  150 -> "XOR of the three cells",
  30 -> "no canonical name (look-up table)",
  110 -> "no canonical name (look-up table)"|>;

CAMakeEnsemble[rule_, width_, steps_, nIC_, seed_] := (
  SeedRandom[seed + rule];
  Table[EvolveECA[rule, RandomInteger[1, width], steps], {nIC}]);

CARuleReport[rule_, width_, steps_, nIC_] := Module[
  {diagrams, dec, ver, interior},
  diagrams = CAMakeEnsemble[rule, width, steps, nIC, 1];
  dec = DeconvolveCA[diagrams, 3];
  ver = VerifyCA[diagrams, dec, rule];
  interior = dec["reports"][[Ceiling[width/2]]];
  Print["rule ", rule,
    ": global_map_exact=", ver["global_map_exact"],
    "  trajectory_exact=", ver["trajectory_exact"],
    "  interior support=", Length[interior["support"]],
    "  gate=", interior["canonical"][[1]],
    "   [", CAKnownIdentity[rule], "]"];
  ver["global_map_exact"]];

RunCADemo[] := Module[{results},
  results = Table[CARuleReport[rule, 12, 10, 80], {rule, CAExampleRules}];
  Print["-------------------------------------------------------------------"];
  Print["global map exact: ", Count[results, True], "/", Length[results], " rules"];
  AllTrue[results, TrueQ]];
