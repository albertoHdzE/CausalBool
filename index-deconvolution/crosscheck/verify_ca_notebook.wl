(* verify_ca_notebook.wl

   Faithful headless verification of ca_to_network_demo.nb: extract the input
   cells and evaluate them in order, overriding only NotebookDirectory[], then
   check that the rule-90 walkthrough and the full demonstration both report
   exact recovery with no messages raised.

   Environment variables: CB_NB (notebook path), CB_EXPDIR (experiments dir).
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

okSingle = TrueQ[ver90["global_map_exact"]];
okAll = TrueQ[allPass];

Print["-------------------------------------------------------------------"];
Print["messages raised during evaluation : ", errorCount];
Print["rule 90 walkthrough exact          : ", okSingle];
Print["all example rules exact            : ", okAll];
Print["NOTEBOOK VERIFICATION PASS         : ", (errorCount == 0) && okSingle && okAll];
