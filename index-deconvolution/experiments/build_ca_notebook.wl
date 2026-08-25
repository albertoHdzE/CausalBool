(* build_ca_notebook.wl

   Generate ca_to_network_demo.nb.  Code cells call the CA demonstration and
   detail libraries, so the notebook and its headless verification run identical
   code.  Output path passed via environment variable CB_NB_OUT.
*)

outPath = Environment["CB_NB_OUT"];

setupCode = StringRiffle[{
  "(* Load the forward method, the deconvolution, the cellular-automaton",
  "   deconvolution and the demonstration and detail libraries. *)",
  "nbDir = NotebookDirectory[];",
  "idDir = ParentDirectory[nbDir];",
  "root  = ParentDirectory[idDir];",
  "Get[FileNameJoin[{root, \"papers\", \"method\", \"code\", \"lib\", \"CausalBoolCore.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"Deconvolution.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"CADeconvolution.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"CADemoLibrary.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"CADetailLibrary.wl\"}]];"
  }, "\n"];

codeSingle = StringRiffle[{
  "diagrams90 = CAMakeEnsemble[90, 12, 10, 80, 1];",
  "dec90 = DeconvolveCA[diagrams90, 3];",
  "ver90 = VerifyCA[diagrams90, dec90, 90];",
  "Print[\"recovered interior gate     : \", dec90[\"reports\"][[6]][\"canonical\"][[1]]];",
  "Print[\"recovered interior support  : \", dec90[\"reports\"][[6]][\"support\"]];",
  "Print[\"global map exact            : \", ver90[\"global_map_exact\"]];"
  }, "\n"];

codeAll = StringRiffle[{
  "allPass = RunCADemo[];"
  }, "\n"];

codeNetwork = StringRiffle[{
  "(* The recovered model is a network: a connectivity matrix and a gate per",
  "   cell.  We take rule 30, one of the most complex, and show the network. *)",
  "diagrams30 = CAMakeEnsemble[30, 12, 10, 80, 1];",
  "dec30 = DeconvolveCA[diagrams30, 3];",
  "Print[\"the recovered network is C (connectivity) plus one gate per cell\"];",
  "Print[\"gates: \", dec30[\"gates\"]];",
  "CBNetworkTable[dec30]"
  }, "\n"];

codeRule = StringRiffle[{
  "(* Each cell's rule as index-set pivots and sumandos: a union of cosets, one",
  "   pivot (decimal) per clause, shifted over the free cells. *)",
  "CBPrintRule[dec30, 6];",
  "CBPrintRule[dec30, 7];"
  }, "\n"];

codeCompare = StringRiffle[{
  "(* Original cellular automaton versus the reconstructed network evolution,",
  "   with the difference (all white means identical). *)",
  "cmp30 = CBCompareEvolution[dec30, diagrams30[[1]]];",
  "Print[\"evolution reproduced exactly: \", cmp30[\"match\"]];",
  "Row[{cmp30[\"original\"], cmp30[\"reconstructed\"], cmp30[\"difference\"]}]"
  }, "\n"];

codeHighlight = StringRiffle[{
  "(* Locate a chosen spatial pattern in time using the index framework, and",
  "   highlight the matching rows in red with their time indices. *)",
  "hl30 = CBHighlightPattern[diagrams30[[1]], diagrams30[[1, 5]]];",
  "Print[\"target pattern occurs at time steps: \", hl30[\"matching_time_indices\"]];",
  "hl30[\"plot\"]"
  }, "\n"];

introText = StringJoin[
  "An elementary cellular automaton is a synchronous Boolean network: each cell ",
  "is a node connected to its neighbourhood, and the rule is the shared local ",
  "gate. A space-time diagram gives only a trajectory, in which each row is the ",
  "input to the next, not the exhaustive input repertoire. This notebook recovers ",
  "the network from such observations, shows the recovered model in full (its ",
  "connectivity matrix, its gates, and each cell's index-set rule in pivot and ",
  "sumandos form), and compares the original pattern with the reconstructed ",
  "evolution row by row."];

textSingle = StringJoin[
  "Rule 90 is the clearest case: its next value is the exclusive-or of the two ",
  "outer cells, so the deconvolution drops the irrelevant centre and names the ",
  "gate XOR over a support of size two."];

textAll = StringJoin[
  "Across the example rules the recovered networks realise the exact global map. ",
  "Rule 254 is recovered as OR, rule 232 as MAJORITY, rule 150 as three-input ",
  "XOR, and the complex rules 30 and 110 as unions of regulatory clauses."];

textNetwork = StringJoin[
  "The recovered model is defined exactly like the forward model: a connectivity ",
  "matrix C, with C[[k]] listing the cells feeding cell k, and one gate per cell. ",
  "The table lists, for every cell, its gate, its inputs, the size of its one-set ",
  "(the number of global states in which it fires), and the number of clauses in ",
  "its index-set rule."];

textRule = StringJoin[
  "Each cell's rule is a short index-set expression: a union of pivot-shifted ",
  "cosets. Each clause has a pivot, the decimal value of its activator cells, and ",
  "ranges freely (the sumandos) over the cells it does not fix. Rule 30 at an ",
  "interior cell is three clauses over its three neighbours; a named gate such as ",
  "XOR is the same structure with a fixed clause pattern."];

textCompare = StringJoin[
  "The reconstructed network, run forward from the same initial row, reproduces ",
  "the original space-time diagram exactly; the difference panel is entirely ",
  "white."];

textHighlight = StringJoin[
  "Finally we pick a spatial pattern (one row of the diagram) and use the index ",
  "framework to find every time step at which it recurs, highlighting those rows ",
  "in red and reporting their indices."];

cells = {
  Cell["Cellular Automaton to Network by Deconvolution", "Title"],
  Cell["Recovering, describing and verifying the generating network", "Subtitle"],
  Cell[introText, "Text"],
  Cell["Setup", "Section"],
  Cell[setupCode, "Input"],
  Cell["Walkthrough: rule 90", "Section"],
  Cell[textSingle, "Text"],
  Cell[codeSingle, "Input"],
  Cell["All example rules", "Section"],
  Cell[textAll, "Text"],
  Cell[codeAll, "Input"],
  Cell["The recovered network (connectivity and gates)", "Section"],
  Cell[textNetwork, "Text"],
  Cell[codeNetwork, "Input"],
  Cell["The index-set rules (pivots and sumandos)", "Section"],
  Cell[textRule, "Text"],
  Cell[codeRule, "Input"],
  Cell["Original versus reconstructed pattern", "Section"],
  Cell[textCompare, "Text"],
  Cell[codeCompare, "Input"],
  Cell["Locating a pattern in time", "Section"],
  Cell[textHighlight, "Text"],
  Cell[codeHighlight, "Input"]
};

Export[outPath, Notebook[cells], "NB"];
Print["wrote notebook: ", outPath];
Print["cell count: ", Length[cells]];
