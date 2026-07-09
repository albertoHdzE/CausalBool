(* build_notebook.wl

   Generate full_pipeline_demo.nb from verified code blocks.  The code cells call
   the DemoLibrary functions, which are the same functions exercised by the
   headless verification, so the notebook and its verification run identical code.

   Output path passed via environment variable CB_NB_OUT.
*)

outPath = Environment["CB_NB_OUT"];

setupCode = StringRiffle[{
  "(* Locate the project files relative to this notebook, then load the",
  "   forward method (CausalBoolCore.wl), the inverse method (Deconvolution.wl)",
  "   and the demonstration library. *)",
  "nbDir = NotebookDirectory[];",
  "idDir = ParentDirectory[nbDir];",
  "root  = ParentDirectory[idDir];",
  "Get[FileNameJoin[{root, \"papers\", \"method\", \"code\", \"lib\", \"CausalBoolCore.wl\"}]];",
  "Get[FileNameJoin[{idDir, \"src\", \"Deconvolution.wl\"}]];",
  "Get[FileNameJoin[{nbDir, \"DemoLibrary.wl\"}]];"
  }, "\n"];

codeA = StringRiffle[{
  "(* Stage 1: build the network and compute its full behaviour the naive way. *)",
  "netA = ExampleNetworkA[];",
  "repA = NaiveRepertoire[netA];",
  "(* Stage 2: replace the exhaustive repertoire by the compact causal model. *)",
  "IndexReductionReport[netA, repA];",
  "(* Stage 3: hide the original and recover it from the repertoire alone. *)",
  "resultA = DeconvolutionReport[netA, repA];"
  }, "\n"];

codeB = StringRiffle[{
  "netB = ExampleNetworkB[];",
  "repB = NaiveRepertoire[netB];",
  "IndexReductionReport[netB, repB];",
  "resultB = DeconvolutionReport[netB, repB];"
  }, "\n"];

introText = StringJoin[
  "This notebook runs the complete index-set pipeline on two ten-node Boolean ",
  "networks. For each network it (1) computes the full dynamics the naive way ",
  "by exhaustive enumeration of all 2^10 inputs, (2) reduces that behaviour to ",
  "the compact causal index-set model and confirms the model regenerates the ",
  "full behaviour exactly, and (3) hides the original network and recovers it ",
  "from the output repertoire alone by deconvolution, verifying that the ",
  "recovered network reproduces the repertoire byte for byte. The naive ",
  "exhaustive calculation is thus shown to be replaceable by the causal method, ",
  "and the causal method is shown to be invertible."];

textA = StringJoin[
  "Example A uses AND and OR gates only, so the closed-form pivot-and-sumandos ",
  "index sets of the derivations apply: the one-set of each node is constructed ",
  "directly, without scanning all inputs."];

textB = StringJoin[
  "Example B spans the core gate family (XOR, NAND, MAJORITY, KOFN, NOT, ",
  "IMPLIES, NOR, XNOR, OR, AND). The deconvolution recovers the functional ",
  "connectivity and a gate whose function matches the original on every node."];

interpText = StringJoin[
  "In both examples the recovered network reproduces the output repertoire ",
  "exactly and the functional connectivity matches the original. Gate naming ",
  "may differ where several canonical gates realise the same Boolean function ",
  "(for instance a single-input NAND, NOR, XNOR and NOT all compute logical ",
  "negation); every such choice reproduces the behaviour. This is the index-set ",
  "analogue of the algorithmic-information deconvolution of cellular automata, ",
  "but exact rather than approximate."];

cells = {
  Cell["Index-Set Deconvolution: Full Pipeline Demonstration", "Title"],
  Cell["From naive exhaustive dynamics to a compressed causal model and back", "Subtitle"],
  Cell[introText, "Text"],
  Cell["Setup", "Section"],
  Cell[setupCode, "Input"],
  Cell["Example A - AND / OR structured network", "Section"],
  Cell[textA, "Text"],
  Cell[codeA, "Input"],
  Cell["Example B - mixed gate family", "Section"],
  Cell[textB, "Text"],
  Cell[codeB, "Input"],
  Cell["Interpretation", "Section"],
  Cell[interpText, "Text"]
};

Export[outPath, Notebook[cells], "NB"];
Print["wrote notebook: ", outPath];
Print["cell count: ", Length[cells]];
