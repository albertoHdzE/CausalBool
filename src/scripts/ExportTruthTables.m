
(* ExportTruthTables.m *)
SetDirectory[DirectoryName[$InputFileName] <> "/../../"];

(* Robust Load Function *)
LoadJSON[file_] := Module[{json},
  If[!FileExistsQ[file],
     Print["File not found: ", file];
     Return[$Failed];
  ];
  json = Import[file, "RawJSON"];
  Return[json];
];

ExportTruthTables[] := Module[
  {networks, data, netName, json, n, rules, cm, nodeNames, i, inputIndices, k, tt, cleanRule, evalStr, res, geneData, inputNames},
  networks = {"lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"};
  data = <||>;
  
  Do[
    netName = networks[[j]];
    Print["Processing ", netName, "..."];
    json = LoadJSON["data/bio/processed/" <> netName <> ".json"];
    
    If[json === $Failed, Continue[]];
    
    nodeNames = json["nodes"];
    n = Length[nodeNames];
    rulesMap = json["logic"]; (* Association gene -> rule *)
    cm = json["cm"];
    
    Print["  Nodes: ", n];
    
    geneData = {};
    
    Do[
       geneName = nodeNames[[i]];
       (* Logic map might not have entry if k=0 *)
       ruleStr = If[KeyExistsQ[rulesMap, geneName], rulesMap[geneName], ""];
       
       (* cm is Target x Source (Row i is inputs to i) *)
       (* We need inputs to node i, so we take Row i *)
       inputIndices = Flatten[Position[cm[[i]], 1]];
       k = Length[inputIndices];
       inputNames = nodeNames[[inputIndices]];
       
       (* Skip if no inputs (Input Node) *)
       If[k == 0, 
          AppendTo[geneData, <|"gene" -> geneName, "k" -> 0, "tt" -> "Input"|>];
          Continue[]
       ];
       
       If[ruleStr === "",
          (* Has inputs but no rule? Error in data or parsing *)
          Print["Warning: Gene ", geneName, " has inputs but no logic rule."];
          AppendTo[geneData, <|"gene" -> geneName, "k" -> k, "tt" -> "MissingRule"|>];
          Continue[]
       ];

       If[k <= 12,
         (* Parse Rule *)
         (* Handle functional syntax: AND(A, B) -> And[A, B] *)
         cleanRule = ruleStr;
         
         (* First, standard operators if any *)
         cleanRule = StringReplace[cleanRule, {
           "!" -> "Not", "&" -> "&&", "|" -> "||"
         }];
         
         (* Replace keywords with Mathematica Functions *)
         (* Note: If infix "A AND B", replacing AND with And gives "A And B" which is invalid. *)
         (* But "A && B" is valid. *)
         (* If functional "AND(A, B)", replacing with "And[A, B]" is valid. *)
         
         (* Heuristic: Try to detect functional vs infix? *)
         (* The error showed "AND(CII, ...)" so it is functional. *)
         
         cleanRule = StringReplace[cleanRule, {
           "AND" -> "And", "OR" -> "Or", "NOT" -> "Not",
           "(" -> "[", ")" -> "]"
         }];
         
         (* Handle mixed case? e.g. "A and B" (lowercase). *)
         (* Usually capitalized in these JSONs. *)
         
         (* Check if rule is missing *)
         If[MissingQ[cleanRule], 
            AppendTo[geneData, <|"gene" -> geneName, "k" -> k, "tt" -> "MissingRule"|>];
            Continue[]
         ];
         
         (* Generate TT *)
         tt = Table[
            (* Map input vars to bits *)
            evalStr = cleanRule;
            
            Do[
               bit = IntegerDigits[row, 2, k][[idx]];
               (* Use True/False for Mathematica functions *)
               valStr = If[bit == 1, "True", "False"];
               patt = RegularExpression["(?<![a-zA-Z0-9])" <> inputNames[[idx]] <> "(?![a-zA-Z0-9])"];
               evalStr = StringReplace[evalStr, patt -> valStr];
            , {idx, k}];
            
            (* Eval *)
            res = ToExpression[evalStr];
            
            (* Handle failures *)
            If[FailureQ[res] || res === $Failed, 
               0, (* Default to 0 on syntax error *)
               If[res === True, 1, If[res === False, 0, 0]]
            ]
         , {row, 0, 2^k - 1}];
         
         AppendTo[geneData, <|"gene" -> geneName, "k" -> k, "tt" -> tt|>];
       ,
         AppendTo[geneData, <|"gene" -> geneName, "k" -> k, "tt" -> "TooBig"|>];
       ];
       
    , {i, n}];
    
    data[netName] = geneData;
    
  , {j, Length[networks]}];
  
  Export["data/bio/processed/truth_tables.json", data, "JSON"];
  Print["Exported Truth Tables to data/bio/processed/truth_tables.json"];
];

ExportTruthTables[];
