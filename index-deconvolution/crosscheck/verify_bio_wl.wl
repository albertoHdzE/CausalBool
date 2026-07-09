(* verify_bio_wl.wl

   Wolfram-side biological deconvolution.  Reads the exported repertoires of
   biological Boolean networks, deconvolves each with DeconvolveRepertoire,
   verifies the recovered network reproduces the repertoire exactly (using the
   extended forward evaluator that understands LUT and REGULATORY gates), counts
   the REGULATORY nodes, and checks agreement with the Python classification.

   Environment: CB_CORE, CB_DECON, CB_CADECON, CB_BIO (bio_cases.json).
*)

Get[Environment["CB_CORE"]];
Get[Environment["CB_DECON"]];
Get[Environment["CB_CADECON"]];

cases = Import[Environment["CB_BIO"], "RawJSON"];

allExact = True; allAgree = True;
Do[
  Module[{case, rep, dec, rep2, exact, wlReg, pyReg},
   case = cases[[c]];
   rep = case["repertoire"];
   dec = DeconvolveRepertoire[rep, case["n"]];
   rep2 = CBNetworkRepertoire[dec];
   exact = (rep2 === rep);
   wlReg = Count[dec["gates"], "REGULATORY"];
   pyReg = case["py_regulatory"];
   If[! exact, allExact = False];
   If[wlReg =!= pyReg, allAgree = False];
   Print[case["label"], ": exact=", exact,
     "  REGULATORY wl=", wlReg, " py=", pyReg,
     "  agree=", wlReg === pyReg]],
  {c, 1, Length[cases]}];

Print["-------------------------------------------------------------------"];
Print["all exact                 : ", allExact];
Print["all agree with Python     : ", allAgree];
Print["BIO WOLFRAM VERIFICATION  : ", allExact && allAgree];
