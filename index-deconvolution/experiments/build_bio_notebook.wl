(* build_bio_notebook.wl

   Generate biological_deconvolution_demo.nb.  Output path via CB_NB_OUT.
*)

outPath = Environment["CB_NB_OUT"];

setupCode = StringRiffle[{
  "(* Load the forward method, the deconvolution and its extensions, and the",
  "   biological demonstration library, relative to this notebook. *)",
  "nbDir = NotebookDirectory[];",
  "idDir = ParentDirectory[nbDir];",
  "root  = ParentDirectory[idDir];",
  "Get[FileNameJoin[{root, \"papers\", \"method\", \"code\", \"lib\", \"CausalBoolCore.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"Deconvolution.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"CADeconvolution.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"BioDemoLibrary.wl\"}]];",
  "biocasesPath = FileNameJoin[{idDir, \"crosscheck\", \"bio_cases.json\"}];"
  }, "\n"];

codeRun = StringRiffle[{
  "(* Deconvolve each biological network from its output repertoire alone and",
  "   confirm the recovered network reproduces the repertoire exactly.  The",
  "   REGULATORY column counts the activator/inhibitor conjunctions named by the",
  "   new gate. *)",
  "bioPass = RunBioDemo[biocasesPath];"
  }, "\n"];

introText = StringJoin[
  "The algorithmic-information causal calculus of Zenil and colleagues applies ",
  "its perturbation analysis to biological networks but reconstructs only ",
  "cellular automata, never the biological networks themselves. Here the ",
  "index-set deconvolution recovers real gene-regulatory Boolean networks ",
  "exactly from their output repertoire. The models are the fission yeast cell ",
  "cycle, the IRMA synthetic yeast circuit, the WNT5A melanoma network, myeloid ",
  "differentiation and apoptosis, taken from the PyBoolNet collection."];

gateText = StringJoin[
  "Real regulatory logic is dominated by conjunctions: a gene is expressed when ",
  "its activators are present and its repressors are absent. The single-repressor ",
  "case is the named gate NIMPLIES and the all-repressor case is NOR, but the ",
  "mixed multi-input case has no classical name. We add the REGULATORY gate for ",
  "it, defined as the product of the activator literals and the negated inhibitor ",
  "literals, out = (product over activators of v) times (product over inhibitors ",
  "of (1 - v)). Its index-set signature is a reduced truth table with a single 1, ",
  "whose position encodes the activator and inhibitor split. It generalises AND ",
  "(all activators) and NOR (all inhibitors) and names the mixed conjunctions ",
  "that pervade the models below."];

cells = {
  Cell["Deconvolving Biological Networks", "Title"],
  Cell["Recovering gene-regulatory Boolean networks from their behaviour", "Subtitle"],
  Cell[introText, "Text"],
  Cell["The regulatory (activator/inhibitor) gate", "Section"],
  Cell[gateText, "Text"],
  Cell["Setup", "Section"],
  Cell[setupCode, "Input"],
  Cell["Deconvolve the biological networks", "Section"],
  Cell[codeRun, "Input"]
};

Export[outPath, Notebook[cells], "NB"];
Print["wrote notebook: ", outPath];
Print["cell count: ", Length[cells]];
