(* BioDemoLibrary.wl

   Report helpers for the biological deconvolution notebook.  Depends on
   CausalBoolCore.wl, Deconvolution.wl and CADeconvolution.wl.  Reads the
   exported repertoires of biological Boolean networks and deconvolves them.
*)

CBGateHistogram[gates_] := Sort[Counts[gates]];

BioReport[case_] := Module[{rep, dec, rep2, exact, hist, reg},
  rep = case["repertoire"];
  dec = DeconvolveRepertoire[rep, case["n"]];
  rep2 = CBNetworkRepertoire[dec];
  exact = (rep2 === rep);
  hist = CBGateHistogram[dec["gates"]];
  reg = Count[dec["gates"], "REGULATORY"];
  Print[case["label"], ": n=", case["n"], "  exact=", exact,
    "  REGULATORY=", reg, "  gates=", hist];
  exact];

RunBioDemo[casesPath_] := Module[{cases, results},
  cases = Import[casesPath, "RawJSON"];
  results = Table[BioReport[cases[[i]]], {i, 1, Length[cases]}];
  Print["-------------------------------------------------------------------"];
  Print["all models reproduced exactly: ", AllTrue[results, TrueQ]];
  AllTrue[results, TrueQ]];
