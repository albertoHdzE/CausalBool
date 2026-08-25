(* verify_bio_notebook.wl

   Faithful headless verification of biological_deconvolution_demo.nb.  Extract
   the input cells, evaluate them in order overriding NotebookDirectory[], and
   check that every biological network is reproduced exactly, the detailed yeast
   repertoire comparison matches, with no messages, and export that comparison to
   a PDF.

   Environment: CB_NB (notebook path), CB_EXPDIR (experiments dir), CB_PDF.
*)

nbPath = Environment["CB_NB"];
expDir = Environment["CB_EXPDIR"];
pdfPath = Environment["CB_PDF"];

nbExpr = Get[nbPath];
inputs = Cases[nbExpr, Cell[c_String, "Input", ___] :> c, Infinity];
Print["input cells found: ", Length[inputs]];

Unprotect[NotebookDirectory];
NotebookDirectory[] := expDir;
Protect[NotebookDirectory];

errorCount = 0;
Do[Check[ToExpression[inp], errorCount += 1], {inp, inputs}];

okAll = TrueQ[bioPass];
okCompare = TrueQ[cmpY["match"]];
Export[pdfPath, GraphicsRow[{cmpY["original"], cmpY["reconstructed"], cmpY["difference"]}]];
pdfOk = FileExistsQ[pdfPath];

Print["-------------------------------------------------------------------"];
Print["messages raised during evaluation : ", errorCount];
Print["all biological networks exact      : ", okAll];
Print["yeast repertoire reproduced exact  : ", okCompare];
Print["comparison PDF exported            : ", pdfOk];
Print["NOTEBOOK VERIFICATION PASS         : ",
  (errorCount == 0) && okAll && okCompare && pdfOk];
