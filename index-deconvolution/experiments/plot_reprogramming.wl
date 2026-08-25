(* plot_reprogramming.wl

   Render the exact reprogrammability spectrum and the face-to-face comparison
   with Zenil's BDM spectrum, exporting a figure.  Environment: CB_REPROG (the
   exp07_reprogramming.json path), CB_PDF (output figure).
*)

d = Import[Environment["CB_REPROG"], "RawJSON"];
records = d["records"];
comparisons = d["comparisons"];

apop = SelectFirst[records, #["label"] == "Apoptosis" &];
spectrumPlot = BarChart[apop["info_image"],
  ChartLabels -> Placed[apop["names"], Axis, Rotate[#, Pi/2] &],
  PlotLabel -> "Exact reprogrammability spectrum (Apoptosis): image-size change per knockout",
  FrameLabel -> {"gene", "information value"}, Frame -> True, ImageSize -> 560];

labels = #["label"] & /@ comparisons;
rhos = #["spearman_image_vs_bdm"] & /@ comparisons;
comparePlot = BarChart[rhos,
  ChartLabels -> Placed[labels, Axis, Rotate[#, Pi/6] &],
  PlotLabel -> "Rank correlation: our exact dynamical info vs Zenil BDM topological info",
  FrameLabel -> {"network", "Spearman"}, Frame -> True, ImageSize -> 560,
  PlotRange -> {-1, 1}];

Export[Environment["CB_PDF"], Column[{spectrumPlot, comparePlot}]];
Print["wrote figure: ", Environment["CB_PDF"]];
Print["apoptosis top gene: ", apop["names"][[First[Ordering[apop["info_image"], -1]]]]];
