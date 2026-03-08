#!/usr/bin/env wolframscript
(* ::Package:: *)

(* 
   NatureBDM.wl
   Computes Behavioural Complexity (BDM) for Biological Networks using the legacy D5.m library.
   Part of the "Nature" Protocol Level 2.
*)

Print["------------------------------------------------"];
Print["   Nature Protocol: Behavioural Complexity (BDM)"];
Print["------------------------------------------------"];

(* 1. Environment Setup *)
currentDir = DirectoryName[$InputFileName];
projectRoot = FileNameJoin[{currentDir, "..", ".."}];
bioLinkPath = FileNameJoin[{currentDir, "BioLink.m"}];
d5Path = FileNameJoin[{projectRoot, "mathematicabdm", "D5.m"}];
outputFile = FileNameJoin[{projectRoot, "results", "bio", "bdm_nature.json"}];

(* Load BioLink *)
If[!FileExistsQ[bioLinkPath],
    Print["[Error] BioLink.m not found at: ", bioLinkPath];
    Exit[1];
];
Get[bioLinkPath];

(* Load D5 Database *)
If[!FileExistsQ[d5Path],
    Print["[Error] D5.m not found at: ", d5Path];
    Exit[1];
];
Print[">> Loading D5.m Legacy Database..."];
d5Raw = Get[d5Path];
(* D5.m is a list of {string, prob}. Convert to Map: string -> prob *)
ctmMap = Association[Rule @@@ d5Raw];
minProb = Min[Values[ctmMap]];
Print[">> Database loaded. Entries: ", Length[ctmMap]];
Print[">> Minimum Probability: ", minProb];

(* 2. Define Metrics *)

(* CTM: K(s) ~ -Log2(P(s)) *)
CTM[s_String] := Module[{prob},
    prob = Lookup[ctmMap, s, 0];
    If[prob == 0,
        (* Fallback for unknown strings: Max complexity estimate *)
        (* Using -Log2(minProb) + length penalty is a standard approximation *)
        N[-Log2[minProb] + StringLength[s]],
        N[-Log2[prob]]
    ]
];

(* BDM: Block Decomposition Method *)
(* We use block size 12 to balance granularity and coverage *)
BlockSize = 12;

BDM[s_String] := Module[{blocks, counts, complexity, n},
    n = StringLength[s];
    (* If short enough, look up directly *)
    If[n <= 49 && KeyExistsQ[ctmMap, s],
        Return[CTM[s]]
    ];
    
    (* Decomposition *)
    blocks = StringPartition[s, UpTo[BlockSize]];
    counts = Counts[blocks];
    
    (* BDM = Sum( K(block) + Log2(Multiplicity) ) *)
    complexity = Total[
        Function[{block, count}, 
            CTM[block] + Log2[count]
        ] @@@ Normal[counts]
    ];
    
    complexity
];

(* 3. Logic Parser Helper *)
(* Converts Python logic string to Mathematica BooleanTable *)
ComputeTruthTable[logicStr_String, inputs_List] := Module[
    {exprStr, expr, vars, table, bitString},
    
    (* 1. Sanitize Logic String *)
    (* Python Logic: AND(A, B) -> Mathematica: And[A, B] *)
    (* We convert the string to match Mathematica functional syntax *)
    
    exprStr = logicStr;
    
    (* First, replace parens with brackets *)
    exprStr = StringReplace[exprStr, {"(" -> "[", ")" -> "]"}];
    
    (* Then map function names to TitleCase *)
    (* Note: We use WordBoundary to avoid partial matches *)
    exprStr = StringReplace[exprStr, {
        "AND" -> "And", 
        "OR" -> "Or", 
        "NOT" -> "Not", 
        "XOR" -> "Xor",
        "NAND" -> "Nand",
        "NOR" -> "Nor",
        "XNOR" -> "Xnor",
        "IMPLIES" -> "Implies",
        "EQUIVALENT" -> "Equivalent"
    }];
    
    (* 2. Map Inputs to Safe Variables (x1, x2...) *)
    (* Sort by length desc to avoid substring collisions *)
    vars = Table["x" <> ToString[i], {i, Length[inputs]}];
    sortedInputs = SortBy[Range[Length[inputs]], -StringLength[inputs[[#]]] &];
    
    Do[
        idx = sortedInputs[[i]];
        name = inputs[[idx]];
        var = vars[[idx]];
        (* Use WordBoundary to ensure exact match *)
        exprStr = StringReplace[exprStr, RegularExpression["\\b" <> name <> "\\b"] -> var];
    , {i, Length[inputs]}];
    
    (* Handle "INPUT" or constants *)
    If[StringContainsQ[logicStr, "INPUT"], Return["INPUT"]];
    If[inputs === {}, Return["CONST"]];
    
    (* 3. Evaluate Truth Table *)
    (* Parse expression *)
    expr = ToExpression[exprStr];
    
    (* Generate Table *)
    (* We must pass the variables as Symbols *)
    varSymbols = Symbol /@ vars;
    
    Check[
        table = BooleanTable[expr, varSymbols];
        bitString = StringJoin[ToString /@ Boole[table]];
        bitString,
        "ERROR"
    ]
];

(* 4. Main Execution Loop *)
processedDir = Integration`BioLink`BioBridgePath[];
files = FileNames["*.json", processedDir];
Print[">> Found ", Length[files], " networks in ", processedDir];

results = {};

Do[
    fileName = FileBaseName[file];
    Print["   > Processing: ", fileName];
    
    net = Integration`BioLink`ImportNetworkJSON[file];
    rawGates = Lookup[net["raw"], "gates", <||>];
    rawLogic = net["logic"];
    
    netBDM = <||>;
    totalBDM = 0;
    
    nodes = net["nodes"];
    
    Do[
        (* Get inputs and logic *)
        gateInfo = Lookup[rawGates, node, <||>];
        inputs = Lookup[gateInfo, "inputs", {}];
        logic = Lookup[rawLogic, node, "INPUT"];
        
        tt = ComputeTruthTable[logic, inputs];
        
        score = 0.0;
        If[tt === "INPUT" || tt === "CONST" || tt === "ERROR",
            score = 0.0; (* No complexity for inputs/constants *)
        ,
            score = BDM[tt];
        ];
        
        netBDM[node] = score;
        totalBDM = totalBDM + score;
        
    , {node, nodes}];
    
    AppendTo[results, <|
        "network" -> fileName,
        "category" -> Lookup[net["raw"], "category", "Unclassified"],
        "nodes" -> Length[nodes],
        "total_bdm" -> totalBDM,
        "avg_bdm" -> If[Length[nodes]>0, totalBDM/Length[nodes], 0],
        "gene_bdm" -> netBDM
    |>];
    
, {file, files}];

(* 5. Export *)
Export[outputFile, results, "JSON"];
Print[">> SUCCESS. Results saved to: ", outputFile];
Print["------------------------------------------------"];
