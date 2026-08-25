(* verify_notebook.wl

   Faithful headless verification of full_pipeline_demo.nb.  It extracts the
   input cells from the notebook file and evaluates them in order, exactly as a
   user pressing "Evaluate Notebook" would, overriding only NotebookDirectory[]
   (the single value the front end would otherwise supply).  It then checks that
   both examples achieve exact repertoire reproduction and exact functional
   connectivity, and that no evaluation raised a message.

   Environment variables: CB_NB (notebook path), CB_EXPDIR (experiments dir with
   trailing slash).
*)

nbPath = Environment["CB_NB"];
expDir = Environment["CB_EXPDIR"];

nbExpr = Get[nbPath];
inputs = Cases[nbExpr, Cell[c_String, "Input", ___] :> c, Infinity];
Print["input cells found: ", Length[inputs]];

(* Supply NotebookDirectory[] as the front end would. *)
Unprotect[NotebookDirectory];
NotebookDirectory[] := expDir;
Protect[NotebookDirectory];

errorCount = 0;
Do[
  Check[ToExpression[inp], errorCount += 1],
  {inp, inputs}];

okA = TrueQ[resultA[[1]]] && TrueQ[resultA[[2]]];
okB = TrueQ[resultB[[1]]] && TrueQ[resultB[[2]]];

Print["-------------------------------------------------------------------"];
Print["messages raised during evaluation : ", errorCount];
Print["example A exact + connectivity     : ", okA];
Print["example B exact + connectivity     : ", okB];
Print["NOTEBOOK VERIFICATION PASS         : ", (errorCount == 0) && okA && okB];
