(* build_ca_notebook.wl

   Generate ca_to_network_demo.nb.  Code cells call the CA demonstration library,
   so the notebook and its headless verification run identical code.
   Output path passed via environment variable CB_NB_OUT.
*)

outPath = Environment["CB_NB_OUT"];

setupCode = StringRiffle[{
  "(* Load the forward method, the deconvolution, the cellular-automaton",
  "   deconvolution and the demonstration library, relative to this notebook. *)",
  "nbDir = NotebookDirectory[];",
  "idDir = ParentDirectory[nbDir];",
  "root  = ParentDirectory[idDir];",
  "Get[FileNameJoin[{root, \"papers\", \"method\", \"code\", \"lib\", \"CausalBoolCore.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"Deconvolution.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"CADeconvolution.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"CADemoLibrary.wl\"}]];"
  }, "\n"];

codeSingle = StringRiffle[{
  "(* Walkthrough for rule 90.  Observe the automaton from 80 random initial",
  "   conditions, deconvolve to a network, and read off the recovered local",
  "   rule.  Rule 90 depends only on the two outer cells, so the centre is",
  "   dropped and the gate is XOR. *)",
  "diagrams90 = CAMakeEnsemble[90, 12, 10, 80, 1];",
  "dec90 = DeconvolveCA[diagrams90, 3];",
  "ver90 = VerifyCA[diagrams90, dec90, 90];",
  "Print[\"recovered interior gate     : \", dec90[\"reports\"][[6]][\"canonical\"][[1]]];",
  "Print[\"recovered interior support  : \", dec90[\"reports\"][[6]][\"support\"]];",
  "Print[\"global map exact            : \", ver90[\"global_map_exact\"]];"
  }, "\n"];

codeAll = StringRiffle[{
  "(* Recover every example rule and confirm the network realises the exact",
  "   global map of the automaton, not merely the observed trajectory. *)",
  "allPass = RunCADemo[];"
  }, "\n"];

introText = StringJoin[
  "An elementary cellular automaton is a synchronous Boolean network: each cell ",
  "is a node connected to its neighbourhood, and the rule is the shared local ",
  "gate. A space-time diagram, however, gives only a trajectory, in which each ",
  "row is the input to the next, not the exhaustive input repertoire. This ",
  "notebook recovers the network from such observations. For each rule it pools ",
  "observations from several initial conditions until every local neighbourhood ",
  "has been seen, deconvolves each cell into its minimal functional support and ",
  "local gate, and verifies that the recovered network reproduces the exact ",
  "global map of the automaton over all states, not merely the observed rows."];

textSingle = StringJoin[
  "Rule 90 is the clearest case: its next value is the exclusive-or of the two ",
  "outer cells, so the deconvolution drops the irrelevant centre and names the ",
  "gate XOR over a support of size two."];

textAll = StringJoin[
  "Across the example rules the recovered networks realise the exact global ",
  "map. Rule 254 is recovered as OR over the three cells, rule 232 as MAJORITY, ",
  "rule 150 as three-input XOR, and the rules with no canonical name (30 and ",
  "110) as explicit look-up tables. In every case the reconstructed network is ",
  "the automaton, expressed in the CausalBool formalism."];

cells = {
  Cell["Cellular Automaton to Network by Deconvolution", "Title"],
  Cell["Recovering the generating network from an observed space-time diagram", "Subtitle"],
  Cell[introText, "Text"],
  Cell["Setup", "Section"],
  Cell[setupCode, "Input"],
  Cell["Walkthrough: rule 90", "Section"],
  Cell[textSingle, "Text"],
  Cell[codeSingle, "Input"],
  Cell["All example rules", "Section"],
  Cell[textAll, "Text"],
  Cell[codeAll, "Input"]
};

Export[outPath, Notebook[cells], "NB"];
Print["wrote notebook: ", outPath];
Print["cell count: ", Length[cells]];
