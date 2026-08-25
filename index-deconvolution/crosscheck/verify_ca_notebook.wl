(* verify_ca_notebook.wl

   Faithful headless verification of ca_to_network_demo.nb: extract the input
   cells and evaluate them in order, overriding only NotebookDirectory[], then
   check that the rule-90 walkthrough, the full demonstration, and the detailed
   rule-30 comparison all report exact recovery with no messages, and export the
   original-versus-reconstructed comparison to a PDF as evidence.

   Environment: CB_NB, CB_EXPDIR, CB_PDF.
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

okSingle = TrueQ[ver90["global_map_exact"]];
okAll = TrueQ[allPass];
okCompare = TrueQ[cmp30["match"]];
Export[pdfPath, Row[{cmp30["original"], cmp30["reconstructed"], cmp30["difference"]}]];
pdfOk = FileExistsQ[pdfPath];

Print["-------------------------------------------------------------------"];
Print["messages raised during evaluation : ", errorCount];
Print["rule 90 walkthrough exact          : ", okSingle];
Print["all example rules exact            : ", okAll];
Print["rule 30 evolution reproduced exact : ", okCompare];
Print["comparison PDF exported            : ", pdfOk];
Print["NOTEBOOK VERIFICATION PASS         : ",
  (errorCount == 0) && okSingle && okAll && okCompare && pdfOk];
