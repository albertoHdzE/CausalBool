(* DemoLibrary.wl

   Stage functions and example networks for the full-pipeline demonstration
   notebook.  Depends on CausalBoolCore.wl (forward method) and Deconvolution.wl
   (inverse method) being loaded first.  Defines plain global symbols so all
   three files share a context.

   The notebook and the headless verification both call these functions, so the
   demonstration and its verification run identical code.
*)

(* Build an n-node network from a list of connected-input sets (1-based). *)
CBBuildNetwork[n_, inputsList_, gates_, params_] := Module[{cm},
  cm = Table[0, {n}, {n}];
  Do[Do[cm[[k, i]] = 1, {i, inputsList[[k]]}], {k, 1, n}];
  <|"n" -> n, "C" -> cm, "gates" -> gates, "params" -> params,
    "inputs" -> inputsList|>];

(* Example A: AND / OR-structured ten-node network. *)
ExampleNetworkA[] := CBBuildNetwork[10,
  Table[Sort[{k, Mod[k, 10] + 1}], {k, 1, 10}],
  Table[If[OddQ[k], "AND", "OR"], {k, 1, 10}],
  Table[<||>, {10}]];

(* Example B: mixed-gate ten-node network spanning the core family. *)
ExampleNetworkB[] := CBBuildNetwork[10,
  {{1, 2, 3}, {2, 4}, {1, 3, 5}, {4, 6, 8}, {5},
   {6, 7}, {7, 8}, {8, 9}, {9, 10}, {1, 10}},
  {"XOR", "NAND", "MAJORITY", "KOFN", "NOT",
   "IMPLIES", "NOR", "XNOR", "OR", "AND"},
  {<||>, <||>, <||>, <|"k" -> 2|>, <||>, <||>, <||>, <||>, <||>, <||>}];

(* Stage 1: the naive exhaustive calculation. *)
NaiveRepertoire[net_] := Module[{paramsAssoc, timing, rep, n},
  n = net["n"];
  paramsAssoc = Association[Table[node -> net["params"][[node]], {node, 1, n}]];
  {timing, rep} = AbsoluteTiming[
    CreateRepertoiresDispatch[net["C"], net["gates"], paramsAssoc]["RepertoireOutputs"]];
  Print["Stage 1 - naive exhaustive repertoire"];
  Print["  repertoire dimensions : ", Dimensions[rep]];
  Print["  wall-clock seconds    : ", timing];
  rep];

(* Stage 2: the index-set causal reduction (compact model regenerates behaviour). *)
IndexReductionReport[net_, rep_] := Module[
  {n, model, sizeNaive, sizeModel, colsFromIndex, indexOK, k},
  n = net["n"];
  model = Table[
    <|"node" -> k, "gate" -> net["gates"][[k]],
      "connected" -> net["inputs"][[k]],
      "oneSet" -> Flatten[Position[rep[[All, k]], 1]]|>,
    {k, 1, n}];
  sizeNaive = 2^n * n;
  sizeModel = Total[(1 + Length[#["connected"]]) & /@ model];
  colsFromIndex = Table[
    Table[ApplyGate[model[[k]]["gate"],
      (Reverse[IntegerDigits[x, 2, n]])[[ model[[k]]["connected"] ]],
      net["params"][[k]]], {x, 0, 2^n - 1}],
    {k, 1, n}];
  indexOK = Transpose[colsFromIndex] === rep;
  Print["Stage 2 - index-set causal reduction"];
  Print["  naive repertoire size (bits)      : ", sizeNaive];
  Print["  causal model size (gate + edges)  : ", sizeModel, " units"];
  Print["  compression factor                : ", N[sizeNaive/sizeModel]];
  Print["  model regenerates full behaviour  : ", indexOK];
  Do[
   If[net["gates"][[k]] === "AND",
    Print["  node ", k, " AND closed-form one-set (no scan) matches : ",
     ClosedFormAndOneSet[n, net["inputs"][[k]]] === model[[k]]["oneSet"]]];
   If[net["gates"][[k]] === "OR",
    Print["  node ", k, " OR  closed-form one-set (no scan) matches : ",
     ClosedFormOrOneSet[n, net["inputs"][[k]]] === model[[k]]["oneSet"]]],
   {k, 1, n}];
  indexOK];

(* Stage 3: deconvolution from the repertoire alone (original hidden). *)
DeconvolutionReport[net_, rep_] := Module[
  {n, dec, ver, connOK, k, recoveredConn, trueConn},
  n = net["n"];
  dec = DeconvolveRepertoire[rep, n];
  ver = VerifyReconstruction[rep, dec];
  connOK = True;
  Do[
   recoveredConn = dec["reports"][[k]]["connected"];
   trueConn = net["inputs"][[k]];
   If[Sort[recoveredConn] =!= Sort[trueConn], connOK = False],
   {k, 1, n}];
  Print["Stage 3 - deconvolution (original network hidden)"];
  Print["  recovered gates                   : ", dec["gates"]];
  Print["  exact repertoire reproduction     : ", ver];
  Print["  functional connectivity == origin : ", connOK];
  {ver, connOK, dec}];

(* Convenience entry point used by the headless verification. *)
RunFullDemo[] := Module[{netA, repA, iA, dA, netB, repB, iB, dB},
  netA = ExampleNetworkA[]; repA = NaiveRepertoire[netA];
  iA = IndexReductionReport[netA, repA]; dA = DeconvolutionReport[netA, repA];
  netB = ExampleNetworkB[]; repB = NaiveRepertoire[netB];
  iB = IndexReductionReport[netB, repB]; dB = DeconvolutionReport[netB, repB];
  And[iA, dA[[1]], dA[[2]], iB, dB[[1]], dB[[2]]]];
