(* verify_wl_pipeline.wl

   Headless verification of the full Wolfram pipeline used by the demonstration
   notebook: naive exhaustive repertoire -> index-set reduction -> deconvolution
   -> exact reconstruction, on two ten-node networks.

   Paths passed via environment variables CB_CORE and CB_DECON.
*)

Get[Environment["CB_CORE"]];
Get[Environment["CB_DECON"]];

(* Build an n-node network from a list of connected-input sets (1-based). *)
buildNetwork[n_, inputsList_, gates_, params_] := Module[{cm},
  cm = Table[0, {n}, {n}];
  Do[Do[cm[[k, i]] = 1, {i, inputsList[[k]]}], {k, 1, n}];
  <|"n" -> n, "C" -> cm, "gates" -> gates, "params" -> params,
    "inputs" -> inputsList|>];

runExample[label_, net_] := Module[
  {n, paramsAssoc, tNaive, rep, model, sizeNaive, sizeModel,
   colsFromIndex, indexOK, dec, ver, connOK, k, recoveredConn, trueConn},
  n = net["n"];
  paramsAssoc = Association[Table[node -> net["params"][[node]], {node, 1, n}]];

  Print["==================================================================="];
  Print[label];
  Print["==================================================================="];

  (* Stage 1: naive exhaustive repertoire *)
  {tNaive, rep} = AbsoluteTiming[
    CreateRepertoiresDispatch[net["C"], net["gates"], paramsAssoc]["RepertoireOutputs"]];
  Print["Stage 1 - naive exhaustive repertoire"];
  Print["  repertoire dimensions : ", Dimensions[rep]];
  Print["  wall-clock seconds    : ", tNaive];

  (* Stage 2: index-set reduction (compact model regenerates full behaviour) *)
  model = Table[
    <|"node" -> k, "gate" -> net["gates"][[k]],
      "connected" -> net["inputs"][[k]],
      "oneSet" -> Flatten[Position[rep[[All, k]], 1]]|>,
    {k, 1, n}];
  (* description length: naive stores 2^n bits per node; the causal model
     stores one gate identifier plus the connected node indices per node *)
  sizeNaive = 2^n * n;
  sizeModel = Total[(1 + Length[#["connected"]]) & /@ model];
  (* verify each column is reconstructed exactly from the model gate + inputs *)
  colsFromIndex = Table[
    Table[ApplyGate[model[[k]]["gate"],
      (Reverse[IntegerDigits[x, 2, n]])[[ model[[k]]["connected"] ]],
      net["params"][[k]]], {x, 0, 2^n - 1}],
    {k, 1, n}];
  indexOK = Transpose[colsFromIndex] === rep;
  Print["Stage 2 - index-set causal reduction"];
  Print["  naive repertoire size (bits)        : ", sizeNaive];
  Print["  causal model size (gate + edges)    : ", sizeModel, " units"];
  Print["  compression factor (bits / units)   : ", N[sizeNaive/sizeModel]];
  Print["  model regenerates full behaviour    : ", indexOK];

  (* Stage 2b: closed-form one-sets for AND / OR nodes (no exhaustive scan) *)
  Do[
   If[net["gates"][[k]] === "AND",
    Print["  node ", k, " AND closed-form one-set matches naive : ",
     ClosedFormAndOneSet[n, net["inputs"][[k]]] === model[[k]]["oneSet"]]];
   If[net["gates"][[k]] === "OR",
    Print["  node ", k, " OR  closed-form one-set matches naive : ",
     ClosedFormOrOneSet[n, net["inputs"][[k]]] === model[[k]]["oneSet"]]],
   {k, 1, n}];

  (* Stage 3: deconvolution from the repertoire alone *)
  dec = DeconvolveRepertoire[rep, n];
  ver = VerifyReconstruction[rep, dec];
  connOK = True;
  Do[
   recoveredConn = dec["reports"][[k]]["connected"];
   trueConn = net["inputs"][[k]];
   If[Sort[recoveredConn] =!= Sort[trueConn], connOK = False],
   {k, 1, n}];
  Print["Stage 3 - deconvolution (original hidden)"];
  Print["  exact repertoire reproduction       : ", ver];
  Print["  functional connectivity == original : ", connOK];
  Print[""];
  {ver, indexOK, connOK}];

(* Example A: AND/OR-structured ten-node network *)
inputsA = Table[Sort[{k, Mod[k, 10] + 1}], {k, 1, 10}];
gatesA = Table[If[OddQ[k], "AND", "OR"], {k, 1, 10}];
paramsA = Table[<||>, {10}];
netA = buildNetwork[10, inputsA, gatesA, paramsA];

(* Example B: mixed-gate ten-node network *)
inputsB = {{1, 2, 3}, {2, 4}, {1, 3, 5}, {4, 6, 8}, {5},
           {6, 7}, {7, 8}, {8, 9}, {9, 10}, {1, 10}};
gatesB = {"XOR", "NAND", "MAJORITY", "KOFN", "NOT",
          "IMPLIES", "NOR", "XNOR", "OR", "AND"};
paramsB = {<||>, <||>, <||>, <|"k" -> 2|>, <||>, <||>, <||>, <||>, <||>, <||>};
netB = buildNetwork[10, inputsB, gatesB, paramsB];

rA = runExample["EXAMPLE A - AND / OR structured (10 nodes)", netA];
rB = runExample["EXAMPLE B - mixed gate family (10 nodes)", netB];

allPass = And @@ Join[rA, rB];
Print["OVERALL PASS: ", allPass];
