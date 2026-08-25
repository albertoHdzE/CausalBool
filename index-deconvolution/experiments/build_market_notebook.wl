(* build_market_notebook.wl
   Generate market_simulation_demo.nb.  Output path via CB_NB_OUT. *)

outPath = Environment["CB_NB_OUT"];

setupCode = StringRiffle[{
  "(* Load the market plotting library and the out-of-sample comparison data",
  "   exported by exp06_market_simulation.py. *)",
  "nbDir = NotebookDirectory[];",
  "idDir = ParentDirectory[nbDir];",
  "Get[FileNameJoin[{nbDir, \"MarketDemoLibrary.wl\"}]];",
  "plotdataPath = FileNameJoin[{idDir, \"finance\", \"market_plotdata.json\"}];",
  "result = MarketComparison[plotdataPath];"
  }, "\n"];

codePath = "result[\"pathPlot\"]";
codeBar = "result[\"barPlot\"]";

introText = StringJoin[
  "This notebook asks how close the deconvolution comes to reproducing the ",
  "market. The deconvolution fits, for each instrument, the best small-support ",
  "deterministic directional rule from the training period; that rule then ",
  "generates a directed price path on a held-out test period, keeping the real ",
  "magnitude of each move but the model's predicted sign. The generated path is ",
  "compared with the real one out of sample, which is the only honest test: any ",
  "in-sample edge is overfitting. The statistics and the per-instrument chart ",
  "quantify the directional skill; the contradiction rates measure how far the ",
  "one-step dynamics are from any deterministic law."];

readText = StringJoin[
  "Out of sample the model does not beat the base rate of always predicting the ",
  "more common direction: the mean edge is slightly negative and no instrument ",
  "is predicted reliably. The real and generated paths track loosely but the ",
  "model carries no exploitable determinism. This is consistent with the ",
  "contradiction rates near one half: binarised daily markets are close to ",
  "random at the one-step scale, unlike the cellular automata and gene networks ",
  "the same method recovers exactly."];

cells = {
  Cell["How Close Is the Deconvolution to the Market?", "Title"],
  Cell["Real versus model-generated paths, out of sample", "Subtitle"],
  Cell[introText, "Text"],
  Cell["Setup and statistics", "Section"],
  Cell[setupCode, "Input"],
  Cell["Real vs model-generated cumulative path", "Section"],
  Cell[codePath, "Input"],
  Cell["Per-instrument accuracy versus base rate", "Section"],
  Cell[codeBar, "Input"],
  Cell["Reading", "Section"],
  Cell[readText, "Text"]
};

Export[outPath, Notebook[cells], "NB"];
Print["wrote notebook: ", outPath];
Print["cell count: ", Length[cells]];
