(* ========================================================================
   GRN ANALYSIS FOR NATURE PAPER
   Deterministic Causal Boolean Integration
   
   This notebook integrates biological GRN data with your existing
   deterministic framework to compute D (description length) and
   compare biological vs randomized networks.
   
   Author: Alberto Hernández & Oxford Collaboration
   Date: January 2026
   ======================================================================== *)

Needs["Integration`Experiments`"];
Needs["Integration`Gates`"];
Needs["Integration`BioMetrics`"];
Needs["Integration`BioExperiments`"];

(* ========================================================================
   SECTION 1: DATA LOADING
   ======================================================================== *)

SetDirectory[NotebookDirectory[]];
dataDir = FileNameJoin[{Directory[], "data", "grn_datasets", "processed"}];

LoadBiologicalNetwork[networkName_String] := Module[
  {file, data, cm, nodeNames, dynamic, params},
  
  file = FileNameJoin[{dataDir, networkName <> "_network.m"}];
  
  If[!FileExistsQ[file],
    Print["ERROR: Network file not found: ", file];
    Return[$Failed]
  ];
  
  (* Load network definition *)
  Get[file];
  
  (* Return association *)
  <|
    "name" -> networkName,
    "cm" -> cm,
    "nodeNames" -> nodeNames,
    "dynamic" -> dynamic,
    "params" -> params,
    "n" -> Length[nodeNames],
    "edges" -> Total[Flatten[cm]]
  |>
];

LoadRandomizedNetworks[networkName_String] := Module[
  {file, data, randomCMs},
  
  file = FileNameJoin[{dataDir, networkName <> "_random.npz"}];
  
  If[!FileExistsQ[file],
    Print["ERROR: Randomized networks not found: ", file];
    Return[$Failed]
  ];
  
  (* Load NPZ file - use Python interop or pre-convert *)
  (* For now, return placeholder *)
  Print["Loading randomized networks from: ", file];
  
  (* PLACEHOLDER: In real implementation, use Python interop *)
  (* randomCMs = Import[file, "NPZ"]; *)
  
  Return[$Failed]  (* Update when Python bridge ready *)
];

(* ========================================================================
   SECTION 2: DESCRIPTION LENGTH (D) COMPUTATION
   ======================================================================== *)

ComputeDescriptionLength[cm_List, dynamic_List, params_Association : <||>] := Integration`BioMetrics`ComputeDescriptionLength[cm, dynamic, params];

(* ========================================================================
   SECTION 3: STATISTICAL COMPARISON
   ======================================================================== *)

CompareDescriptionLengths[bioNetwork_Association, randomCMs_List] := Module[
  {bioCm, bioDynamic, bioParams, bioD, randomDs, meanRandom, stdRandom,
   zScore, pValue, foldReduction},
  
  bioCm = bioNetwork["cm"];
  bioDynamic = bioNetwork["dynamic"];
  bioParams = bioNetwork["params"];
  
  (* Compute D for biological network *)
  bioD = ComputeDescriptionLength[bioCm, bioDynamic, bioParams]["D"];
  
  (* Compute D for each randomized network *)
  randomDs = Table[
    ComputeDescriptionLength[randomCm, bioDynamic, bioParams]["D"],
    {randomCm, randomCMs}
  ];
  
  (* Statistical measures *)
  meanRandom = Mean[randomDs];
  stdRandom = StandardDeviation[randomDs];
  zScore = (bioD - meanRandom) / stdRandom;
  
  (* One-tailed t-test: is biological D significantly lower? *)
  pValue = If[stdRandom > 0,
    1 - CDF[StudentTDistribution[Length[randomDs] - 1], zScore],
    1.0
  ];
  
  foldReduction = meanRandom / bioD;
  
  <|
    "biological_D" -> bioD,
    "random_mean_D" -> meanRandom,
    "random_std_D" -> stdRandom,
    "z_score" -> zScore,
    "p_value" -> pValue,
    "fold_reduction" -> foldReduction,
    "n_randomizations" -> Length[randomDs],
    "significant" -> pValue < 0.001
  |>
];

(* ========================================================================
   SECTION 4: VISUALIZATION
   ======================================================================== *)

PlotDComparison[results_Association, networkName_String] := Module[
  {bioD, randomMean, randomStd, plot},
  
  bioD = results["biological_D"];
  randomMean = results["random_mean_D"];
  randomStd = results["random_std_D"];
  
  plot = BarChart[
    {bioD, randomMean},
    ChartLabels -> {"Biological\n" <> networkName, "Random\n(mean ± SD)"},
    ChartStyle -> {RGBColor[0.2, 0.6, 0.8], Gray},
    PlotLabel -> Style[
      "Description Length (D): Biological vs Random\n" <>
      "Fold reduction: " <> ToString[NumberForm[results["fold_reduction"], 2]] <>
      "×, p = " <> ToString[ScientificForm[results["p_value"], 2]],
      14, Bold
    ],
    FrameLabel -> {None, "Description Length (bits)"},
    Frame -> True,
    ImageSize -> 500,
    ErrorBars -> {None, {randomStd, randomStd}}
  ];
  
  plot
];

(* ========================================================================
   SECTION 5: BATCH ANALYSIS
   ======================================================================== *)

AnalyzeAllNetworks[] := Module[
  {networks, results, summary},
  
  networks = {"lambda_phage", "yeast_cell_cycle", "tcell_activation"};
  
  results = Association[];
  
  Print["============================================================="];
  Print["BATCH ANALYSIS: Biological vs Random Networks"];
  Print["=============================================================\n"];
  
  Do[
    Module[{net, bioD, randomCMs, comparison},
      
      Print["Analyzing: ", netName];
      
      (* Load biological network *)
      net = LoadBiologicalNetwork[netName];
      
      If[net === $Failed,
        Print["  → SKIPPED (loading failed)\n"];
        Continue[];
      ];
      
      Print["  Nodes: ", net["n"], ", Edges: ", net["edges"]];
      
      (* Compute biological D *)
      bioD = ComputeDescriptionLength[
        net["cm"], 
        net["dynamic"], 
        net["params"]
      ];
      
      Print["  Biological D: ", bioD["D"], " bits"];
      
      randomCMs = Table[
        Integration`BioExperiments`RandomizeNetworkDegreePreserving[
          net["cm"],
          net["n"]*net["n"]*10
        ],
        {100}
      ];
      
      (* Compare *)
      comparison = CompareDescriptionLengths[net, randomCMs];
      
      Print["  Random mean D: ", 
        NumberForm[comparison["random_mean_D"], {5, 2}], " bits"];
      Print["  Fold reduction: ", 
        NumberForm[comparison["fold_reduction"], {4, 2}], "×"];
      Print["  p-value: ", 
        ScientificForm[comparison["p_value"], 3]];
      Print["  Significant: ", comparison["significant"], "\n"];
      
      (* Store results *)
      results[netName] = comparison;
    ],
    {netName, networks}
  ];
  
  Print["============================================================="];
  Print["SUMMARY"];
  Print["============================================================="];
  Print["Networks analyzed: ", Length[results]];
  Print["All significant (p < 0.001): ", 
    AllTrue[Values[results], #["significant"]&]];
  Print["Mean fold reduction: ", 
    NumberForm[Mean[#["fold_reduction"]& /@ Values[results]], {4, 2}], "×"];
  
  results
];

(* Helper: Randomize network preserving degree *)
RandomizeNetwork[cm_List] := Module[
  {n, edges, cmRandom, nSwaps, i, j, i1, j1, i2, j2},
  
  n = Length[cm];
  cmRandom = cm;
  edges = Position[cm, 1];
  nSwaps = n * n * 10;
  
  Do[
    If[Length[edges] < 2, Break[]];
    
    {i1, j1} = RandomChoice[edges];
    {i2, j2} = RandomChoice[edges];
    
    (* Swap if valid *)
    If[i1 != j2 && i2 != j1 && cmRandom[[i1, j2]] == 0 && cmRandom[[i2, j1]] == 0,
      cmRandom[[i1, j1]] = 0;
      cmRandom[[i2, j2]] = 0;
      cmRandom[[i1, j2]] = 1;
      cmRandom[[i2, j1]] = 1;
    ],
    {nSwaps}
  ];
  
  cmRandom
];

(* ========================================================================
   SECTION 6: MAIN EXECUTION
   ======================================================================== *)

(* Run analysis *)
Print["\n*** STARTING GRN ANALYSIS ***\n"];

(* Example: Single network *)
lambdaPhage = LoadBiologicalNetwork["lambda_phage"];

If[lambdaPhage =!= $Failed,
  bioResult = ComputeDescriptionLength[
    lambdaPhage["cm"],
    lambdaPhage["dynamic"],
    lambdaPhage["params"]
  ];
  
  Print["Lambda Phage Network:"];
  Print["  Nodes: ", lambdaPhage["n"]];
  Print["  Edges: ", lambdaPhage["edges"]];
  Print["  Description Length D: ", bioResult["D"], " bits"];
  Print["  Average per node: ", NumberForm[bioResult["avgPerNode"], 3], " bits"];
];

(* Batch analysis (when randomized networks available) *)
(* allResults = AnalyzeAllNetworks[]; *)

Print["\n*** ANALYSIS READY FOR WEEK 2 ***"];
Print["Next: Compute knockout predictions and ROC curves"];
