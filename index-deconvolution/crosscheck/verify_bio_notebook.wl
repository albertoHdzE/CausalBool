(* verify_bio_notebook.wl

   Faithful headless verification of biological_deconvolution_demo.nb.  Extract
   the input cells, evaluate them in order overriding NotebookDirectory[], and
   check that every biological network is reproduced exactly with no messages.

   Environment: CB_NB (notebook path), CB_EXPDIR (experiments dir).
*)

nbPath = Environment["CB_NB"];
expDir = Environment["CB_EXPDIR"];

nbExpr = Get[nbPath];
inputs = Cases[nbExpr, Cell[c_String, "Input", ___] :> c, Infinity];
Print["input cells found: ", Length[inputs]];

Unprotect[NotebookDirectory];
NotebookDirectory[] := expDir;
Protect[NotebookDirectory];

errorCount = 0;
Do[Check[ToExpression[inp], errorCount += 1], {inp, inputs}];

Print["-------------------------------------------------------------------"];
Print["messages raised during evaluation : ", errorCount];
Print["all biological networks exact      : ", TrueQ[bioPass]];
Print["NOTEBOOK VERIFICATION PASS         : ", (errorCount == 0) && TrueQ[bioPass]];
