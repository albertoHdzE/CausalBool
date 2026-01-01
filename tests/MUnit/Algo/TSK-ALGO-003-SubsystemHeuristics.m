Get["src/Packages/Integration/Gates.m"];

base = FileNameJoin[{"results", "tests", "algo003"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

(* Compression metric consistent with THEORY-001/003 tests *)
compressionWeight[gate_, d_Integer] := Switch[gate,
  "AND" | "OR" | "NAND" | "NOR", 1 + d,
  "XOR" | "XNOR" | "MAJORITY", 1 + 1,
  "NOT", 1,
  _, 1 + d
];
computeCompression[cm_List, dyn_List] := Module[{n = Length[dyn], ics},
  ics = Table[Flatten@Position[cm[[i]], 1], {i, n}];
  Total@Table[compressionWeight[dyn[[i]], Length[ics[[i]]]], {i, n}]
];

(* Jaccard similarity over input sets to propose blocks *)
inputSets[cm_List] := Table[Flatten@Position[cm[[i]], 1], {i, Length[cm]}];
jaccard[a_List, b_List] := Module[{ia = a, ib = b}, If[ia === {} && ib === {}, 1.0,
  N[Length@Intersection[ia, ib]/Max[1, Length@Union[ia, ib]]]]];

proposeBlocks[cm_List] := Module[{n = Length[cm], adjU, visited = ConstantArray[False, Length[cm]], blocks = {}},
  adjU = Unitize[cm + Transpose[cm]]; (* undirected adjacency numeric *)
  Do[adjU[[i, i]] = 0, {i, n}];
  Do[
    If[!visited[[i]],
      Module[{queue = {i}, block = {}},
        visited[[i]] = True;
        While[queue =!= {}, Module[{u = First[queue]}, queue = Rest[queue]; AppendTo[block, u];
          Do[If[adjU[[u, v]] == 1 && !visited[[v]], visited[[v]] = True; queue = Append[queue, v]], {v, n}]]];
        AppendTo[blocks, Sort@block]
      ]
    ], {i, n}];
  blocks
];

(* Build block-diagonal cm from blocks for compression factorisation check *)
blockDiagonalCM[cm_List, blocks_List] := Module[{n = Length[cm], perm, cmP},
  perm = Flatten@blocks;
  cmP = cm[[perm, perm]];
  cmP
];

gates = {"AND","OR","XOR","NAND","NOR","XNOR","MAJORITY","NOT"};

runOne[n_Integer, seed_Integer] := Module[{cm, dyn, blocks, cWhole, cSumBlocks, cutEdges = 0, totalEdges = 0, cutFrac, ok},
  SeedRandom[seed];
  cm = ConstantArray[0, {n, n}];
  Do[
    Module[{deg = RandomInteger[{1, Min[5, n - 1]}], choices},
      choices = RandomSample[Complement[Range[n], {i}], deg];
      cm[[i, choices]] = 1;
    ], {i, n}];
  dyn = Table[RandomChoice[gates], {n}];

  blocks = proposeBlocks[cm];
  cWhole = computeCompression[cm, dyn];
  cSumBlocks = Total@Table[computeCompression[cm[[blk, blk]], dyn[[blk]]], {blk, blocks}];
  (* inter-block edges fraction *)
  totalEdges = Total[Flatten[cm]];
  cutEdges = Total[Flatten@Table[Total[cm[[i, Complement[Range[n], blk]]]], {blk, blocks}, {i, blk}]];
  cutFrac = If[totalEdges == 0, 0.0, N[cutEdges/totalEdges]];
  ok = (cutFrac == 0.0) && (cWhole == cSumBlocks);
  <|"n"->n, "seed"->seed, "blocks"->blocks, "compressionWhole"->cWhole, "compressionBlocks"->cSumBlocks, "cutEdges"->cutEdges, "totalEdges"->totalEdges, "cutFrac"->cutFrac, "okFactorise"->ok|>
];

metrics = {runOne[20, 401], runOne[50, 402]};
Export[FileNameJoin[{base, "Subsystems.json"}], metrics, "JSON"];
Export[FileNameJoin[{base, "Status.txt"}], If[AllTrue[metrics[[All, "okFactorise"]], TrueQ], "OK", "FAIL"], "Text"];

(* Produce a compact LaTeX block listing *)
blocksTexRows = StringRiffle[
  Table[StringJoin[{"$n=", ToString[m["n"]], "$: blocks=", ToString[m["blocks"]], ", cutFrac=", ToString[NumberForm[m["cutFrac"], {3, 2}]], ", C=", ToString[m["compressionWhole"]], ", C blocks=", ToString[m["compressionBlocks"]], " \\"}], {m, metrics}], "\n"];
blocksTex = StringJoin[
  "\\subsection*{Subsystem Blocks (ALGO-003)}\n",
  "\\begin{itemize}\n",
  StringRiffle[Table[StringJoin["\\item ", r], {r, StringSplit[blocksTexRows, "\n"]}], "\n"],
  "\n\\end{itemize}\n"
];
Export[FileNameJoin[{base, "Blocks.tex"}], blocksTex, "Text"];
