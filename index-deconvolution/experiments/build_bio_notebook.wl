(* build_bio_notebook.wl
   Generate biological_deconvolution_demo.nb.  Output path via CB_NB_OUT. *)

outPath = Environment["CB_NB_OUT"];

setupCode = StringRiffle[{
  "(* Load the forward method, the deconvolution and its extensions, and the",
  "   biological demonstration and detail libraries. *)",
  "nbDir = NotebookDirectory[];",
  "idDir = ParentDirectory[nbDir];",
  "root  = ParentDirectory[idDir];",
  "Get[FileNameJoin[{root, \"papers\", \"method\", \"code\", \"lib\", \"CausalBoolCore.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"Deconvolution.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"CADeconvolution.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"BioDemoLibrary.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"CADetailLibrary.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"BioDetailLibrary.wl\"}]];",
  "biocasesPath = FileNameJoin[{idDir, \"crosscheck\", \"bio_cases.json\"}];"
  }, "\n"];

codeRun = StringRiffle[{
  "(* Deconvolve each biological network from its output repertoire alone and",
  "   confirm the recovered network reproduces the repertoire exactly. *)",
  "bioPass = RunBioDemo[biocasesPath];"
  }, "\n"];

codeNetwork = StringRiffle[{
  "(* Take the fission yeast cell cycle and show the recovered model in full:",
  "   a connectivity matrix and a gate per node. *)",
  "cases = Import[biocasesPath, \"RawJSON\"];",
  "yeast = cases[[1]];",
  "decY = DeconvolveRepertoire[yeast[\"repertoire\"], yeast[\"n\"]];",
  "Print[\"model: \", yeast[\"label\"], \"   nodes: \", yeast[\"n\"]];",
  "Print[\"recovered gates: \", decY[\"gates\"]];",
  "CBNetworkTable[decY]"
  }, "\n"];

codeRule = StringRiffle[{
  "(* The activator/inhibitor node, in index-set pivot/sumandos form. *)",
  "regNode = FirstPosition[decY[\"gates\"], \"REGULATORY\"][[1]];",
  "Print[\"regulatory (activator/inhibitor) node index: \", regNode];",
  "CBPrintRule[decY, regNode];"
  }, "\n"];

codeCompare = StringRiffle[{
  "(* Original versus reconstructed repertoire, with the difference. *)",
  "cmpY = CBCompareRepertoire[decY, yeast[\"repertoire\"]];",
  "Print[\"repertoire reproduced exactly: \", cmpY[\"match\"]];",
  "Row[{cmpY[\"original\"], cmpY[\"reconstructed\"], cmpY[\"difference\"]}]"
  }, "\n"];

codeOneSet = StringRiffle[{
  "(* Locate the node's one-set: the input states in which it fires. *)",
  "idxY = CBOneSetIndices[yeast[\"repertoire\"], regNode];",
  "Print[\"node \", regNode, \" fires in \", Length[idxY], \" of \", 2^yeast[\"n\"], \" input states\"];",
  "Print[\"first firing input indices (1-based): \", Take[idxY, UpTo[12]]];",
  "CBHighlightNodeOneSet[yeast[\"repertoire\"], regNode]"
  }, "\n"];

introText = StringJoin[
  "The algorithmic-information causal calculus of Zenil and colleagues applies ",
  "its perturbation analysis to biological networks but reconstructs only ",
  "cellular automata, never the biological networks themselves. Here the ",
  "index-set deconvolution recovers real gene-regulatory Boolean networks ",
  "exactly from their output repertoire, shows the recovered model in full (its ",
  "connectivity matrix, its gates, and each node's index-set rule), and compares ",
  "the original repertoire with the reconstructed one."];

gateText = StringJoin[
  "Real regulatory logic is dominated by conjunctions: a gene is expressed when ",
  "its activators are present and its repressors absent. The single-repressor ",
  "case is NIMPLIES and the all-repressor case is NOR; the mixed case is the ",
  "REGULATORY gate, and unions of clauses are the regulatory disjunctive normal ",
  "form. Each is a union of pivot-shifted cosets in the index set."];

netText = StringJoin[
  "The recovered model is defined exactly like the forward model: a connectivity ",
  "matrix and one gate per node. The table lists each node's gate, its inputs, ",
  "the size of its one-set, and the number of clauses in its index-set rule."];

ruleText = StringJoin[
  "The activator/inhibitor node is shown as its index-set rule: a pivot (the ",
  "decimal value of the activator inputs) and the free inputs (the sumandos) over ",
  "which it ranges."];

compareText = StringJoin[
  "The reconstructed network reproduces the output repertoire exactly; the ",
  "difference panel is entirely white."];

oneSetText = StringJoin[
  "Finally we locate the node's one-set, the set of input states in which it ",
  "fires, and highlight that node's column across the repertoire."];

cells = {
  Cell["Deconvolving Biological Networks", "Title"],
  Cell["Recovering, describing and verifying gene-regulatory networks", "Subtitle"],
  Cell[introText, "Text"],
  Cell["The regulatory gate family", "Section"],
  Cell[gateText, "Text"],
  Cell["Setup", "Section"],
  Cell[setupCode, "Input"],
  Cell["Deconvolve all the biological networks", "Section"],
  Cell[codeRun, "Input"],
  Cell["The recovered network (connectivity and gates)", "Section"],
  Cell[netText, "Text"],
  Cell[codeNetwork, "Input"],
  Cell["An index-set rule (pivots and sumandos)", "Section"],
  Cell[ruleText, "Text"],
  Cell[codeRule, "Input"],
  Cell["Original versus reconstructed repertoire", "Section"],
  Cell[compareText, "Text"],
  Cell[codeCompare, "Input"],
  Cell["Locating a node's one-set", "Section"],
  Cell[oneSetText, "Text"],
  Cell[codeOneSet, "Input"]
};

Export[outPath, Notebook[cells], "NB"];
Print["wrote notebook: ", outPath];
Print["cell count: ", Length[cells]];
