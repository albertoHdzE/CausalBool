(* verify_market_notebook.wl

   Faithful headless verification of market_simulation_demo.nb: evaluate the
   input cells overriding NotebookDirectory[], confirm no messages, that the two
   plots are valid graphics, and export the comparison path plot to a PDF as
   viewable evidence that it renders.

   Environment: CB_NB, CB_EXPDIR, CB_PDF (output PDF path).
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

pathOk = MatchQ[result["pathPlot"], _Graphics | _Legended];
barOk = MatchQ[result["barPlot"], _Graphics | _Legended];
Export[pdfPath, result["pathPlot"]];
pdfOk = FileExistsQ[pdfPath];

Print["-------------------------------------------------------------------"];
Print["messages raised during evaluation : ", errorCount];
Print["path plot is a graphic            : ", pathOk];
Print["bar plot is a graphic             : ", barOk];
Print["comparison PDF exported           : ", pdfOk, "  (", pdfPath, ")"];
Print["NOTEBOOK VERIFICATION PASS        : ", (errorCount == 0) && pathOk && barOk && pdfOk];
