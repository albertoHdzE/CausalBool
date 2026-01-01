(* ::Package:: *)

(* Wolfram Language package *)(* Wolfram Language Raw Program *)

(* This function implements the OR logical operation on a list of binary values (0s and 1s)
   It returns 1 if there is at least one 1 in the list, otherwise returns 0
   Input: list - A list of binary values (0s and 1s)
   Output: 1 if any element is 1, 0 if all elements are 0 *)
myOr[list_] :=
    (hayUnos = Position[list, 1];
     If[ Length[hayUnos] > 0,
         Return[1],
         Return[0]
     ];);

(* This function implements the NAND logical operation on a list of binary values (0s and 1s)
   It returns 1 if there is at least one 0 in the list, otherwise returns 0
   Input: list - A list of binary values (0s and 1s)
   Output: 1 if any element is 0, 0 if all elements are 1 *)
myNand[list_] :=
    (hayCeros = Position[list, 0];
     If[ Length[hayCeros] > 0,
         Return[1],
         Return[0]
     ];);

myAnd[list_] :=
    (ayCeros = Position[list, 0];
     If[ Length[ayCeros] === 0,
         Return[1],
         Return[0]
     ];);

(* The uncommented version using Xor @@ and replacement rules is more efficient:
   1. It uses built-in Xor operator which is optimized at low level
   2. The replacement operations are vectorized
   3. Avoids multiple Position[] calls which scan the list multiple times
   4. Avoids explicit Length[] calculations
   
   The commented version has to:
   1. Scan list twice with Position[]
   2. Calculate two lengths
   3. Perform multiple comparisons
   
   An even more efficient version would be:
   myXor[list_] := Mod[Total[list], 2]
   
   This simply sums the list and takes modulo 2, which is equivalent to XOR
   and avoids any replacement rules or type conversions. *)
(* myXor[list_] := (Xor @@ list /. Thread[{1 -> True, 0 -> False}] /. Thread[{True -> 1, False -> 0}]); *)

 (*   (posi0 = Position[list, 0];
     posi1 = Position[list, 1];
     If[ Length[posi0] === 0 || Length[posi1] === 0,
         Return[0],
         Return[1]
     ];);*)

myXor[list_] := Mod[Total[list], 2]
     
myMajority[list_] := (If[Count[list,1]>Count[list,0],Return[1],Return[0]]);

getRow[matrix_, noRow_] :=
    (Return[matrix[[noRow]]]);

getCol[matrix_, noCol_] := (Return[matrix[[All, noCol]]]);

(*Who sent me signals*)
getIndexesOfNodesInputs[node_, cm_] :=
    (Return[Sort[Flatten[Position[getRow[cm, node], 1]]]]);

(*To who send signals to*)
getIndexesOfNodesOutputs[node_, matrix_] := (Return[Position[getCol[matrix, node],1]]);

(* Extract elements from a list by index *)
getListInputsByIndex[input_, indexes_] :=
    (Return[Part[input, indexes]]);


(*inverse binary conversion, left=0
   
   allPosibleInputsReverse[2] 
   out:= {{0,0}, {1,0}, {0,1}, {1,1}}
*)
allPosibleInputsReverse[noNodes_] :=
    (Table[Reverse[IntegerDigits[x, 2, noNodes]], {x, 0, (2^noNodes) - 1, 1}]);

(*setInputsToBinPhiStyle[4, {1, 2}]
out:= {{1, 0, 0, 0}, {0, 1, 0, 0}}*)
setInputsToBinPhiStyle[length_, listDecimalNumbers_] :=
    (Table[Reverse[IntegerDigits[Part[listDecimalNumbers, x], 2, length]], {x, 1, Length[listDecimalNumbers], 1}]);
    
(* normal binary conversion, right=0
allPosibleInputsNormal[3]
out:= {{0, 0, 0}, {0, 0, 1}, {0, 1, 0}, {0, 1, 1}, {1, 0, 0}, {1, 0, 1}, {1, 1, 0}, {1, 1, 1}}*)
allPosibleInputsNormal[noNodes_] :=
    (Table[IntegerDigits[x, 2, noNodes], {x, 0, (2^noNodes) - 1, 1}]);



(*transform cm to edge list

cm05 = {{0, 1, 1, 1, 1}, {1, 1, 1, 0, 0}, {1, 0, 0, 1, 0}, {1, 1, 0, 0, 0}, {0, 1, 1, 1, 0}};
connMatrix2EdgeList[cm05]

out: <|"EdgeList" -> {2 -> 1, 3 -> 1, 4 -> 1, 5 -> 1, 1 -> 2, 2 -> 2, 
   3 -> 2, 1 -> 3, 4 -> 3, 1 -> 4, 2 -> 4, 2 -> 5, 3 -> 5, 4 -> 5}|>
*)
connMatrix2EdgeList[cm_] :=
    Block[ {},
        grafo = List[];
        For[o = 0, o < Length[cm], o++;
               noNodo = o;
               fila = Part[cm, o];
               (*Print["Fila "<> ToString[noNodo]<>": "<> ToString[fila]];*)
               inputIndexes = Position[fila, 1];
               inputIndexes = Flatten[inputIndexes];
               For[u = 0, u < Length[inputIndexes], u++;
                    nodo = ToExpression[ToString[Extract[inputIndexes, u]] <> "->" <> ToString[noNodo]];
                    AppendTo[grafo, nodo];
               ];
        ];
        (*Print["Edge LIst: "<> ToString[grafo]];*)
        <|"EdgeList" -> grafo|>
    ];
    


(*Build map of Basins of Attraction in dec from binary representation*)
buildGraphBADecimalFromBinaryInOut[binInputs_, binOutputs_] :=
    Block[ {},
        netInDecimalForm = Table[FromDigits[Part[binInputs, i], 2], {i, 1, Length[binInputs],1}];
        (*Print["INPUTS in decimal form"];
        Print[netInDecimalForm];*)
        netOutDecimalForm = Table[FromDigits[Part[binOutputs, g], 2], {g, 1, Length[binOutputs], 1}];
        (*Print["OUTPUTS in decimal form"];
        Print[netOutDecimalForm];*)
        edgesList = Table[ToExpression[ToString[Part[netInDecimalForm, x]] <> "->" <> ToString[Part[netOutDecimalForm, x]]], {x, 1, Length[netInDecimalForm], 1}];
        <|"InDec" -> netInDecimalForm, "OutDec" -> netOutDecimalForm,"EdgesList" -> edgesList|>
    ];

(*
cm05 = {{0, 1, 1, 1, 1}, {1, 1, 1, 0, 0}, {1, 0, 0, 1, 0}, {1, 1, 0, 0, 0}, {0, 1, 1, 1, 0}};
dyn05 = {"AND", "AND", "OR", "AND", "OR"};

Example:
calculateOneOutptuOfNetwork[{1, 0, 1, 0, 1}, cm05, dyn05]
out:= <|"Output" -> {0, 0, 1, 0, 1}|>
*)
calculateOneOutptuOfNetwork[input_,cm_,dynamic_] :=
    Block[ {noNodes,oneNetOutput,n,indexesInputs,inputsToThisNode,nodeOp,resOp},
    	noNodes=Length[input];
        oneNetOutput = List[];
        
        For[n = 0, n < noNodes, n++;
    	    indexesInputs = getIndexesOfNodesInputs[n, cm];
            inputsToThisNode = getListInputsByIndex[input, indexesInputs];
            nodeOp = Part[dynamic, n];
            
            (* begin -----------------------------*)
            (*Print["------------"];
            Print["indexes of inputs: "<> ToString[indexesInputs]];
            Print["inputs to this node: "<> ToString[inputsToThisNode]];
            Print["Dynamica this node: "<> ToString[nodeOp]];*)
            (* end   -----------------------------*)
            

            If[ nodeOp === "AND",
                resOp = myAnd[inputsToThisNode],
                Null
            ];
            
            If[ nodeOp === "XOR",
                resOp = myXor[inputsToThisNode],
                Null
            ];
            
            If[ nodeOp === "OR",
                resOp = myOr[inputsToThisNode],
                Null
            ];
            
            If[ nodeOp === "NAND",
                resOp = myNand[inputsToThisNode],
                Null
            ];
            
            If[ nodeOp === "MAJORITY",
                resOp = myMajority[inputsToThisNode],
                Null
            ];

            AppendTo[oneNetOutput, resOp];
        ];
        
     <|"Output"-> oneNetOutput |>
    ];


  
(*Full input-output repertoires

Example:
cm03 = {{0, 1, 1}, {1, 1, 0}, {1, 1, 1}};
dyn03 = {"AND", "AND", "OR"};
runDynamic[cm03, dyn03]
out:= <|"RepertoireOutputs" -> {{0, 0, 0}, {0, 0, 1}, {0, 0, 1}, 
                               {0, 1, 1}, {0, 0, 1}, {0, 0, 1}, 
                               {1, 0, 1}, {1, 1, 1}}|>
*)
runDynamic[cm_, dynamic_] :=
    Block[ {noNodes,inputs,unitaryInputUnrestrictedProbability,associationsInputOutputs},
        noNodes = Length[dynamic];
        inputs = allPosibleInputsReverse[noNodes];
       
        unitaryInputUnrestrictedProbability = Divide[1, Length[inputs]];
        associationsInputOutputs = List[];

        noInputs = Length[inputs];
        repertoireResultsNet = List[];
        ucInputVectorProbability = List[];
        For[k = 0, k < noInputs, k++;
                 oneNetOutput = List[];
                 input = Part[inputs, k];
                 (*Print[input];*)
                 For[n = 0, n < noNodes, n++;
	                     indexesInputs = getIndexesOfNodesInputs[n, cm];
	                     inputsToThisNode = getListInputsByIndex[input, indexesInputs];
	                     nodeOp = Part[dynamic, n];
	                     (* beging -------------------*)
	                     (*Print["------ Node: "<> ToString[n]];
	                     Print["input indexes: "<> ToString[indexesInputs]];
	                     Print["real inputs: " <> ToString[inputsToThisNode]];
	                     Print["Operation: " <> ToString[nodeOp]];*)
	                     (* end ------------------------ *)
	                     If[ nodeOp === "AND",
	                         resOp = myAnd[inputsToThisNode],
	                         Null
	                     ];
	                     If[ nodeOp === "OR",
	                         resOp = myOr[inputsToThisNode],
	                         Null
	                     ];
	                     If[ nodeOp === "XOR",
	                         resOp = myXor[inputsToThisNode],
	                         Null
	                     ];
	                     If[ nodeOp === "NAND",
	                         resOp = myNand[inputsToThisNode],
	                         Null
	                     ];
	                     (* being -------------------- *)
	                     (*Print["Result: "];
	                     Print[resOp];*)
	                     (* end  ----------------------  *)
	                     AppendTo[oneNetOutput, resOp];
                 ];
                 (* begin --------------------*)
                 (*Print["********* Input: "<> ToString[input]];
                 Print["********* Output: "<> ToString[oneNetOutput]];*)
                 (* end -----------------------*)
                 AppendTo[repertoireResultsNet, oneNetOutput];
                 (*AppendTo[associationsInputOutputs,Association[{input-> Flatten[oneNetOutput]}]];*)
                 (*AppendTo[associationsInputOutputs,Flatten[oneNetOutput]];
                 AppendTo[ucInputVectorProbability, N[unitaryInputUnrestrictedProbability]];*)
        ];
        (*
        attAssociations = Merge[associationsInputOutputs,Identity];
        attractors = DeleteDuplicates[repertoireResultsNet];
        attracDec = Table[FromDigits[Part[attractors, b], 2], {b, 1, Length[attractors], 1}];
        attracProb = 1/Length[attractors];
        probAttractors = Table[attracProb*Count[repertoireResultsNet, Part[attractors, r]], {r, 1, Length[attractors], 1}];
        completeAttractorsProb = Table[N[attracProb*Count[repertoireResultsNet,Part[repertoireResultsNet, r]]], {r, 1,Length[repertoireResultsNet], 1}];
        *)
        <|"RepertoireInputs" -> inputs,
        "RepertoireOutputs" -> repertoireResultsNet
        (*"UnitaryInputUnrestrictedProbability" -> unitaryInputUnrestrictedProbability,
        "Attractors" -> attractors,
        "AttractorsDec" -> attracDec,
        "AttAssociations"-> attAssociations,
        "OnlyAttractorsProbabilities" -> probAttractors,
        "CompleteAttractorProbVector" -> completeAttractorsProb,
        "UCInputVectorProbability" -> ucInputVectorProbability*)
        |>
    ];
    
filterByCondition[inRep_, outRep_, indexElement_, expectedOut_] := Block[
  {indexes, outs, ins},

  (* Find the indexes where the condition is met *)
  indexes = Flatten[Position[outRep[[All, indexElement]], expectedOut]];

  (* Extract the corresponding elements from in_rep *)
  ins = inRep[[indexes]];
  outs= outRep[[indexes]];

  (* Return the results *)
  <|"indexes" -> indexes, "ins" -> ins, "outs"->outs|>
];


   
(*Save full in-out repertoire to a filepath
Example:
cm03 = {{0, 1, 1}, {1, 1, 0}, {1, 1, 1}};
dyn03 = {"AND", "AND", "OR"};
runDynamicHD[cm03, dyn03, "/Users/beto/Documents/Projects/CausalBool/run.csv"]

out:=
<|"RepertoireInputs" -> {{0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {1, 1, 0}, {0, 0, 1}, {1, 0, 1}, {0, 1, 1}, {1, 1, 1}}, 
 "RepertoireOutputs" -> {{0, 0, 0}, {0, 0, 1}, {0, 0, 1}, {0, 1, 1}, {0, 0, 1}, {0, 0, 1}, {1, 0, 1}, {1, 1, 1}}, 
 "UnitaryInputUnrestrictedProbability" -> 1/8, 
 "Attractors" -> {{0, 0, 0}, {0, 0, 1}, {0, 1, 1}, {1, 0, 1}, {1, 1, 1}}, 
 "AttractorsDec" -> {0, 1, 3, 5, 7}, 
 "OnlyAttractorsProbabilities" -> {1/5, 4/5, 1/5, 1/5, 1/5}, 
 "CompleteAttractorProbVector" -> {0.2, 0.8, 0.8, 0.2, 0.8, 0.8, 0.2, 0.2}, 
 "UCInputVectorProbability" -> {0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125}|>

*)
runDynamicHD[cm_, dynamic_, resultsPath_] :=
    Block[ {},
        noNodes = Length[dynamic];
        inputs = allPosibleInputsReverse[noNodes];
        (*inputs=allPosibleInputsNormal[noNodes];*)
        unitaryInputUnrestrictedProbability = Divide[1, Length[inputs]];
        associationsInputOutputs = List[];
        (*Print["INPUTS "];
        Print[inputs];*)
        noInputs = Length[inputs];
        repertoireResultsNet = List[];
        ucInputVectorProbability = List[];
        For[k = 0, k < noInputs, k++;
             oneNetOutput = List[];
             input = Part[inputs, k];
             (*Print[input];*)
             For[n = 0, n < noNodes, n++;
                 indexesInputs = getIndexesOfNodesInputs[n, cm];
                 inputsToThisNode = getListInputsByIndex[input, indexesInputs];
                 nodeOp = Part[dynamic, n];
                 (*Print[indexesInputs];
                 Print[inputsToThisNode];
                 Print[nodeOp];*)
                 If[ nodeOp === "AND",
                     resOp = myAnd[inputsToThisNode],
                     Null
                 ];
                 If[ nodeOp === "OR",
                     resOp = myOr[inputsToThisNode],
                     Null
                 ];
                 If[ nodeOp === "XOR",
                     resOp = myXor[inputsToThisNode],
                     Null
                 ];
                 If[ nodeOp === "NAND",
                     resOp = myNand[inputsToThisNode],
                     Null
                 ];
                 (*Print[resOp];*)
                 AppendTo[oneNetOutput, resOp];
             ];
             AppendTo[repertoireResultsNet, oneNetOutput];
             AppendTo[associationsInputOutputs,Association[{input-> Flatten[oneNetOutput]}]];
             AppendTo[ucInputVectorProbability, N[unitaryInputUnrestrictedProbability]];
        ];
        (*attAssociations = Merge[associationsInputOutputs,Identity];*)
        attractors = DeleteDuplicates[repertoireResultsNet];
        attracDec = Table[FromDigits[Part[attractors, b], 2], {b, 1, Length[attractors], 1}];
        attracProb = 1/Length[attractors];
        probAttractors = Table[attracProb*Count[repertoireResultsNet, Part[attractors, r]], {r, 1, Length[attractors], 1}];
        completeAttractorsProb = Table[N[attracProb*Count[repertoireResultsNet,Part[repertoireResultsNet, r]]], {r, 1,Length[repertoireResultsNet], 1}];
        
        Export[resultsPath<>"/RepertoireInputs.csv", inputs, "CSV"];
        Export[resultsPath<>"/RepertoireOutputs.csv", repertoireResultsNet, "CSV"];
        Export[resultsPath<>"/Attractors.csv",attractors , "CSV"];
        
        
        <|"RepertoireInputs" -> inputs,
        "RepertoireOutputs" -> repertoireResultsNet,
        "UnitaryInputUnrestrictedProbability" -> unitaryInputUnrestrictedProbability,
        "Attractors" -> attractors,
        "AttractorsDec" -> attracDec,
        (*"AttAssociations"-> insOutsAssociations,*)
        "OnlyAttractorsProbabilities" -> probAttractors,
        "CompleteAttractorProbVector" -> completeAttractorsProb,
        "UCInputVectorProbability" -> ucInputVectorProbability
        |>
    ];
    


(* found if in a list there are 0s, 1s or both
Examples:
 
elementsInColumn[{1, 1}]
out:= <|"RES" -> 1|>

elementsInColumn[{0, 0}]
out:= <|"RES" -> 0|>

elementsInColumn[{0, 1}]
out:= <|"RES" -> *|>

*)
elementsInColumn[col_] := Module[{res},
   res = 0;
   If[Length[Position[col, 0]] > 0 && Length[Position[col, 1]] > 0,
                     res = "*",
                      
    If[Length[Position[col, 0]] > 0 && 
      Length[Position[col, 1]] === 0,
                    res = 0,
                           
     If[Length[Position[col, 0]] === 0 && Length[Position[col, 1]] > 0,
                          res = 1,
                          Null]
                        ]
                   ];
   <|"RES" -> res|>
   ];

(* From a matrix, apply above function by column
Let's say:
matrix = {
    {1, 0, 1},
    {0, 1, 0},
    {1, 0, 1},
    {0, 1, 0}
};
RES for column 1 = * cause it has 0s and 1s (same for col2 and col3)


*)
findPatternsInInputsPerAttTotal[inputsPerAtt_] := Module[{kk},
   ptt = Table[
     Table[elementsInColumn[Part[inputsPerAtt, kk][[All, hh]]]["RES"], 
     	{hh, 1, Length[Part[inputsPerAtt, kk][[1]]], 1}], 
     		{kk, 1, Length[inputsPerAtt], 1}];
   <|"Pattern" -> ptt|>
   ];

giveIndexesOfDifferences[list1_, list2_] := Module[{},
   diff = 
    Table[If[Part[list1, bb] !=  Part[list2, bb], bb, Null], {bb, 1, Length[list1], 1}] /. Null -> Sequence[];
   <|"Differences" -> diff|>
   ];



(* Given an adjacency matrix and a dynamics:
1. Find attractors (All possible outs)
2. Find all possible inputs that generate an especific attractor.
3. Find patters in inputs. 
For example, given this association:

   attractor -> all possible inputs that generate it 
{<|{0, 0, 0} -> {{0, 0, 0}}|>, --> one single pattern (input) can generater such attractor
 <|{0, 0, 1} -> {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}, {1, 0, 1}}|>, --> pattern is {*,*,*} see example in function findPatternsInInputsPerAttTotal 
 <|{0, 1, 1} -> {{1, 1, 0}}|>, --> one single pattern
 <|{1, 0, 1} -> {{0, 1, 1}}|>, --> one single pattern
 <|{1, 1, 1} -> {{1, 1, 1}}|>} --> one single pattern
 
 4. Compare the first element of inputs with the rest of all possible and find differences.
 Example of all possible patters (step 3):
 {{0, 0, 0}, {0, 1, 1}, {1, 1, 0}, {1, 1, 1}, {"*", "*", "*"}}
 
 (see ChangeInNodes in USAGE EXAMPLE)
 {0, 0, 0} vs {0, 1, 1} results in differences at positions 2 and 3. 
 {0, 0, 0} vs {1, 1, 0} results in differences at positions 1 and 2.
 
 5. Apply step (4) to attractors. (See EffectInNodes in USAGE EXAMPLE)

USAGE EXAMPLE: 

analysisBasinsAttraction[{{0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {1, 1, 
   0}, {0, 0, 1}, {1, 0, 1}, {0, 1, 1}, {1, 1, 1}}, {{0, 0, 0}, {0, 0,
    1}, {0, 0, 1}, {0, 1, 1}, {0, 0, 1}, {0, 0, 1}, {1, 0, 1}, {1, 1, 
   1}}]
   
out:= <|"ChangeInNodes" -> {{2, 3}, {1, 2}, {1, 2, 3}, {1, 2, 3}}, 
 "EffectInNodes" -> {{1, 3}, {2, 3}, {1, 2, 3}, {3}}|>
*)
analysisBasinsAttraction[myInputs_, myOutputs_] :=
    Module[{assoInputsOutputs,attAndItsInputs,qq,FlatAtts,inputsPerAtt,assAttAndInputs,allPatterns, ff, gg, 
    	assPattOfInputsAndAtt, ll, assInputPattersToAtts, onlyPattsPattToAtts, onlyInputsPattToAtts, mm, changesInInputs, 
    	effectInOutputs, atts },
        assoInputsOutputs = 
         Table[Association[Part[myInputs, qq] -> Part[myOutputs, qq]], {qq,1, Length[myInputs], 1}];
        attAndItsInputs = GroupBy[assoInputsOutputs, Values];
        FlatAtts = Map[Flatten[#] &, Keys[attAndItsInputs]];
        atts = Keys[attAndItsInputs];
        inputsPerAtt = Table[Map[Flatten[#] &, Keys[attAndItsInputs[Part[atts, ff]]]], {ff, 1, Length[atts], 1}];
        assAttAndInputs = Table[Association[<|Part[FlatAtts, gg] -> Part[inputsPerAtt, gg]|>], {gg, 1, Length[FlatAtts], 1}];
        
        SortBy[assAttAndInputs, Identity];
        allPatterns = findPatternsInInputsPerAttTotal[inputsPerAtt]["Pattern"];
        assPattOfInputsAndAtt = Table[Association[<|Part[allPatterns, ll] -> Part[FlatAtts, ll]|>], {ll, 1,Length[FlatAtts], 1}];
        assInputPattersToAtts = KeySortBy[Merge[assPattOfInputsAndAtt, Identity], Count[#, "*"] &];
        (* being -------------------------*)
        (*Print[assAttAndInputs];
        Print[assInputPattersToAtts];*)
        (*end ----------------------------*)
        onlyInputsPattToAtts = Keys[assInputPattersToAtts];
        onlyPattsPattToAtts = Flatten[#] & /@ Values[assInputPattersToAtts];
        changesInInputs = Table[giveIndexesOfDifferences[Part[onlyInputsPattToAtts, 1],Part[onlyInputsPattToAtts, mm]]["Differences"],
            {mm, 2,Length[onlyInputsPattToAtts], 1}];
        effectInOutputs = Table[giveIndexesOfDifferences[Part[onlyPattsPattToAtts, 1], Part[onlyPattsPattToAtts, mm]]["Differences"], 
            {mm, 2,Length[onlyPattsPattToAtts], 1}];
        <|"ChangeInNodes" -> changesInInputs, 
         "EffectInNodes" -> effectInOutputs|>
    ];

getCompleteSubgraph[vertices_, cm_] :=
    Block[ {},
  (*Print["Vertices: "<>ToString[vertices]];*)
        grafoCompleto = List[];
        vertices2 = vertices;
        cm2 = cm;
        For[i = 0, i < Length[vertices2], i++;
                  nodoProbado = Part[vertices2, i];
                  todasEntradas = Part[cm2, nodoProbado];
                  entradasReales = Flatten[List @@@ Position[todasEntradas, 1]];
                  (*Print["Todas las entradas: "<>ToString[todasEntradas]];
                  Print["Entradas reales: "<>ToString[entradasReales]];*)
                  For[m = 0, m < Length[entradasReales], m++;
                         AppendTo[grafoCompleto, Part[entradasReales, m]];
                         AppendTo[grafoCompleto, nodoProbado];
                  ];
         ];
         (*Print["Grafo completo: "<>ToString[
         grafoCompleto]];*)
        <|"GrafoCompleto" -> grafoCompleto|>
    ];

vertexList2NodeList[vertexList_] :=
    Block[ {},
        fromVertex2NodeList = List[];
        lim = Divide[Length[vertexList], 2];
        multiplo = 2;
        (*Print["AQUI VOY A TRABAJAR.."];
        Print[vertexList];*)
        For[u = 0, u < lim, u++;
                ind = multiplo*u;
                elem1 = Part[vertexList, ind - 1];
                elem2 = Part[vertexList, ind];
                axeStr = ToString[elem1] <> "->" <> ToString[elem2];
                axe = ToExpression[axeStr];
                AppendTo[fromVertex2NodeList, axe];
          (*Print["HASTA AQUI VA..."];
          Print[DeleteCases[fromVertex2NodeList,Null]];*)
         ];
        DeleteCases[fromVertex2NodeList, Null];
        <|"VertexList2NodeList" -> fromVertex2NodeList|>
    ];

testSubGraphOp[g_, i_, cm_, op_] :=
    Block[ {},
        With[ {s = EdgeList[g]},
            listaEjes = 
             Extract[s, Position[IntegerDigits[i, 2, Length[s]], 1]];
            listaVertices = VertexList[Graph[listaEjes]]
        ];
        (*Print[listaEjes];*)
        listaEjesSalida[];
        (*Si se quiere que se completen los grafos*)
        If[ op === 1,(*Si SI se cumple*)
            graCompleto = getCompleteSubgraph[listaVertices, cm];
            listaNodes = graCompleto["GrafoCompleto"];
            newNodeList = vertexList2NodeList[listaNodes];
            listaEjesSalida = newNodeList["VertexList2NodeList"];
            grafito = Graph[listaEjesSalida];,
            (*Si no se cumple*)
            listaEjesSalida = listaEjes;
            grafito = Graph[listaEjesSalida];
        ];
        (*listaEjes=EdgeList[];*)
        (*Print[
        "SubGrafo completo: "];*)
        (*Print[ToString[graCompleto[
        "GrafoCompleto"]]];*)
        (*listaNodes=Flatten[List@@@
        listaEjes];*)
        (*Print["Lista vertices generados automaticamente: "<>ToString[
        listaVertices]];
        Print["Lista completada de vertices:"<>ToString[listaNodes]];
        Print["Lista de ejes completa: "<>ToString[newNodeList[
        "VertexList2NodeList"]]];*)
        opcion = -1;
        If[ (ConnectedGraphQ[grafito]),
            opcion = 2,
            opcion = 1
        ];
        <|"Opcion" -> opcion, "SubgrafoNodeList" -> listaEjesSalida|>
    ];

getEdgeListSubgraphs[
   subGraphsList_] :=
    (Return[Table[EdgeList[Extract[subGraphsList, u]], {u, 1, Length[subGraphsList], 1}]]);

getVertexListSubgraphs[
   subGraphsList_] :=
    (Return[
    Table[VertexList[Graph[EdgeList[Extract[subGraphsList, u]]]], {u, 1, Length[subGraphsList], 1}]]);

getSubStatesSubgraphs[vertexSubgraphsList_, 
   sysCurrentState_] :=
    (Return[Table[Part[sysCurrentState, vertexSubgraphsList[[u]]], {u, 1, Length[vertexSubgraphsList], 1}]]);

getStateOfNodesFromList[listOfCompleteStates_, 
   nodesWanted_] :=
    (Return[Table[Part[listOfCompleteStates[[u]], Flatten[nodesWanted]], {u,1, Length[listOfCompleteStates], 1}]]);

(*getElementContainPattern[inputs,{1,2,3},{1,1,0}]*)

getElementContainPattern[tarjectList_, nodes_, subState_] :=
    Module[ {indexesFound, elemFound, decimalRep, f },
        indexesFound = List[];
        elemFound = List[];
        decimalRep = List[];
        (*Print["------------------------------"];
        Print["------------------------------"];
        Print["Nodes: " <> ToString[nodes]];
        Print["Substate in nodes: " <> ToString[subState]];
        Print["Starting  search..."];*)
        For[f = 0, f < Length[tarjectList], f++;
                analizedElem = Part[tarjectList, f];
                (*Print["Element: " <> ToString[analizedElem]];
                Print["Substate: " <> ToString[Part[analizedElem,nodes]]];*)
                If[ Part[Part[tarjectList, f], nodes] === subState,
                    AppendTo[elemFound, Part[tarjectList, f]];
                    AppendTo[indexesFound, f];
                    AppendTo[decimalRep, FromDigits[Part[tarjectList, f], 2]],
                    Null
                ];
         ];
        <|"Elements" -> elemFound, "Indexes" -> indexesFound, 
         "DecimalRep" -> decimalRep|>
    ];

calculateProbOfOccurrVec[list_, prob_] :=
    Block[ {},
        diffElements = DeleteDuplicates[list];
        noDiffElem = Length[diffElements];
        (*Print["-----------------------------------------"];
        Print["Im going to calculate Probabilities"];
        Print[list];
        Print["Different Elements in list: "];
        Print[diffElements];
        Print["THey are:"];
        Print[noDiffElem];*)
        probVector = List[];
        For[w = 0, w < noDiffElem, w++;
         (*Print["I will calculate with: "];
         Print[Part[diffElements,w]];*)
                                   repeticiones = Count[list, Part[diffElements, w]];
                                   AppendTo[probVector, N[repeticiones*prob]];
         ];
        Print["-----------------------------------------"];
        <|"ProbabilityVector" -> probVector|>
    ];

(*buildCompleteProbDistrib[{{0,0},{1,1}},{1,2},inputs, {1,3}, 0.25]
keys and values = <|{0,0}\[Rule]1,{1,1}\[Rule] 2|>  this is number of \
times a patter appears
inputs = complete list to analyze. Its length = complete \
probabilities distribution length.
0.25 = unitary probability
*)
buildCompleteProbDistrib[keys_, values_, objectList_, part_, unitaryProb_] :=
    Block[ {},
   (*Print["----INTO buildCompleteProbDistrib PROCEDURE -----"];*)
        distProb = List[];
        For[hh = 0, hh < Length[objectList], hh++;
             objectElement = Part[objectList, hh];
             subPart = Part[objectElement, part];
             assignedProb = 0;
             (*begin -----------------------------------------*)
             (*Print[
             "ObjectList:"];
             Print[objectList//MatrixForm];
             Print["Part"<>ToString[part]];
             Print["Calculating probability element: " <> ToString[hh]<> "**" ];
             Print["Object element: "<> ToString[objectElement]];
             Print["Subpart: "<> ToString[subPart]];*)
             (*end -----------------------------------------*)
             For[pa = 1, pa <= Length[keys], pa++,
                     (*begin -----------------------------------------*)
                     (*Print["Testing key: " <> ToString[keys[[pa]]]];*)
                     (*end -----------------------------------------*)
                     If[ subPart === keys[[pa]],
                         (*Print["Encontrado!!"];*)
                         assignedProb = values[[pa]]* unitaryProb,
                         Null
                     ];
             ];
             AppendTo[distProb, assignedProb];
         ];
        <|"ProbabilityDistribution" -> distProb |>
    ];

probabilityDistributionCalculation[mechanism_, purview_, outputs_, inputs_, currentState_, causalOrEffect_] :=
    Module[ {currentSubstate, elementsWithCurrentSubstate, indexesOutElementsCurrentSubstate, 
    	     possiblePastFutureStates, purviewsOfPossiblePastFutureStates, singleProbability, 
    	     pps,ppp, diffPattPurviews, keys, values, completeProbDistr },
    	 
        currentSubstate := Part[currentState, mechanism];
        If[ causalOrEffect === "causal",
            elementsWithCurrentSubstate = getElementContainPattern[outputs, mechanism, currentSubstate],
            elementsWithCurrentSubstate = getElementContainPattern[inputs, mechanism, currentSubstate]
        ];
        indexesOutElementsCurrentSubstate = elementsWithCurrentSubstate["Indexes"];
        (*begin ----------------------------------------------------*)
        (*Print[" *******************  New Evaluation ***********"];
        Print["**Direction: "<>ToString[causalOrEffect]];
        Print["OUTPUTS: "<> ToString[outputs]];
        Print["INPUTS" <> ToString[inputs]];
        Print["Mechanism: "<>ToString[mechanism]<> " Substate:" <> ToString[currentSubstate]];
        Print[ "Purview: "<> ToString[purview]];
        Print["Indixes of elements fulfill requirement:" <> ToString[indexesOutElementsCurrentSubstate]];*)
        (*end ----------------------------------------------------*)
        If[Length[indexesOutElementsCurrentSubstate]>0,
	        If[ causalOrEffect === "causal",
	            possiblePastFutureStates = Table[Part[inputs, indexesOutElementsCurrentSubstate[[pps]]], {pps, 1,Length[indexesOutElementsCurrentSubstate], 1}],
	            possiblePastFutureStates = Table[Part[outputs,indexesOutElementsCurrentSubstate[[pps]]], {pps, 1,Length[indexesOutElementsCurrentSubstate], 1}]
	        ];
	        purviewsOfPossiblePastFutureStates = Table[Part[possiblePastFutureStates[[ppp]],Flatten[purview]], {ppp, 1, Length[possiblePastFutureStates],1}];
	        singleProbability = N[1/Length[purviewsOfPossiblePastFutureStates]];
	        diffPattPurviews = Counts[purviewsOfPossiblePastFutureStates];
	        
	        (*begin ----------------------------------------------------*)
	        (*Print["Posible Past/Future states:" <> ToString[possiblePastFutureStates]];
	        Print["Purviews of possible past/FutureStates:"<>ToString[purviewsOfPossiblePastFutureStates]];
	        Print["Patt found in  purviews: "<> ToString[diffPattPurviews]];*)
	        (*end ----------------------------------------------------*)
	        keys = Keys[diffPattPurviews];
	        values = Values[diffPattPurviews];
	        If[ causalOrEffect === "causal",
	            completeProbDistr = buildCompleteProbDistrib[keys, values, inputs, purview, singleProbability],
	            completeProbDistr = buildCompleteProbDistrib[keys, values, outputs, purview,singleProbability]
	        ];
        
        ];
        
        (*begin ----------------------------------------------------*)
        (*Print["Probability Distri:" <>ToString[completeProbDistr]];*)
        (*end ----------------------------------------------------*)
        <|"OutputsWithCurrentSubstate" -> elementsWithCurrentSubstate["Elements"], 
         "IndexesOutElementsCurrentSubstate" -> indexesOutElementsCurrentSubstate, 
         "PossiblePastFutureStates" ->  possiblePastFutureStates, 
         "PurviewsOfPossiblePastFutureStates" -> purviewsOfPossiblePastFutureStates, 
         "SingleProbability" -> singleProbability, 
         "AllPatternsPurviews" -> diffPattPurviews,  
         "CompleteProbabilityDistribution" -> completeProbDistr["ProbabilityDistribution"]|>
    ];

(*
option:
0=all possible subset,
1=Only connected paths
*)
createValidMechanisms[cm_, option_] :=
    Block[ {edges, subsets, v, vertex, subgrafos, connectedSubgraph,i, gg,
    	vertexListOfSubsets },
    	If[option===1,
	        edges = connMatrix2EdgeList[cm];
	        subsets = Subsets[edges["EdgeList"]];
	        v = Reverse[Sort[VertexList[Graph[edges["EdgeList"]]]]];
	        vertex = ArrayReshape[v, {Length[cm], 1}];
	        
	        (* begin ---------------------*)
	        (*Print["this is v: "<> ToString[v]];
	        Print["Reshapping: "<> ToString[vertex]];*)
	        (* end ---------------------*)
	        
	        (*1) define subgraphs, 2) test if they are connected, 3) get vertex list of connected
	        subgraphs*)
	        subgrafos = Table[Graph[Part[subsets, y]], {y, 2, Length[subsets], 1}];
	        connectedSubgraph = Table[If[ConnectedGraphQ[Part[subgrafos, i]],Part[subgrafos, i]], 
	        	{i, 1, Length[subgrafos], 1}] /.Null -> Sequence[];
	        vertexListOfSubsets = Table[Sort[VertexList[Part[connectedSubgraph, r]]], {r, 1,Length[connectedSubgraph], 1}];
	        
	        (* begin ---------------------*)
	        (*Print["-------------Subgraphs-----------"];
	        Print[subgrafos];
	        Print["------- connected Subgraphs ------------"];
	        Print[connectedSubgraph];
	        Print["----------- vertex list of Subsets ---------------"];
	        Print[vetexListOfSubsets];*)
	        (* end ---------------------*)
	        
	        For[gg = 1, gg <= Length[vertex], gg++, 
	            PrependTo[vertexListOfSubsets, Part[vertex, gg]];
	        ];
	        vertexListOfSubsets = DeleteDuplicates[vertexListOfSubsets];
	        (*begin ---------------------------------------*)
	        (*Print["Edge LIst: "<> ToString[edges]];
	        Print["Vertex list "<> ToString[v]];
	        Print["Vertex list of subsets: "<> ToString[vetexListOfSubsets]];*)
	        (*end------------------------------------------*)
	        ,
	        (*if option = 0, all possible subsets including empty set*)
	        vertexListOfSubsets=Subsets[Range[Length[cm]]];
    	];
        <|"ValidMechanisims" -> vertexListOfSubsets|>
    ];

createValidMechanismsUsingEdgesList[cm_] :=
    Block[ {},
        edges = connMatrix2EdgeList[cm];
        subsets = Subsets[edges["EdgeList"]];
        subsets = Delete[subsets, 1];
        (*Print["Edge LIst: "<> ToString[edges]];
        Print["Possible subgraphs: "];
        Print[subsets];*)
        subgr = Table[Graph[Part[subsets, ts], VertexLabels -> "Name",ImageSize -> Tiny, EdgeStyle -> Arrowheads[0.2]], {ts, 1, Length[subsets], 1}];
        filteredSubgr = Table[If[ ConnectedGraphQ[Part[subgr, ts2]],
                                  Part[subgr, ts2],
                                  Null
                              ], {ts2, 1, Length[subgr], 1}] /.Null -> Sequence[];
        v = Reverse[Sort[VertexList[Graph[edges["EdgeList"]]]]];
        vertex = ArrayReshape[v, {Length[cm], 1}];
        (*Print["Vertex list "<> ToString[v]];*)
        subgrafos = Table[Graph[Part[subsets, y] createValidMechanismsUsingEdgesList], {y, 2,Length[subsets], 1}];
        (*HERE IS A CHANGE: WEAKLYCONNECTEDGRAPHQ FOR CONNECTEDGRAPHQ*)
        connectedSubgraph = Table[If[ ConnectedGraphQ[Part[subgrafos, i]],
                                      Part[subgrafos, i],
                                      Null
                                  ], {i, 1, Length[subgrafos], 1}] /.Null -> Sequence[];
        vetexListOfSubsets = Table[Sort[VertexList[Part[connectedSubgraph, r]]], {r, 1,Length[connectedSubgraph], 1}];
        vetexListOfSubsets = DeleteDuplicates[vetexListOfSubsets];
        For[gg = 1, gg <= Length[vertex], gg++,
                                          PrependTo[vetexListOfSubsets, Part[vertex, gg]];
        ];
        <|"ValidMechanisims" -> vetexListOfSubsets, 
         "AllSubgraphs" -> subgr, 
         "ConnectedSubgraphs" -> filteredSubgr|>
    ];

createConnectedAndWeaklyConnectedSubgraphs[cm_] :=
    Block[ {},
        edges = connMatrix2EdgeList[cm];
        v = Reverse[Sort[VertexList[Graph[edges["EdgeList"]]]]];
        vertex = ArrayReshape[v, {Length[v], 1}];
        subsets = Subsets[edges["EdgeList"]];
        subgrafos = Table[Graph[Part[subsets, y], VertexLabels -> "Name",ImageSize -> Tiny, EdgeStyle -> Arrowheads[0.2]], {y, 2,Length[subsets], 1}];
        weaklyConnectedSubgraph = Table[If[ ConnectedGraphQ[Part[subgrafos, i]],
                                            Part[subgrafos, i],
                                            Null
                                        ], {i, 1, Length[subgrafos], 1}] /.Null -> Sequence[];
        vetexListOfWeakyConnectedGraphs = DeleteDuplicates[Table[Sort[VertexList[Part[weaklyConnectedSubgraph, r]]], {r, 1,Length[weaklyConnectedSubgraph], 1}]];
        For[gg = 1, gg <= Length[vertex], gg++, 
                                          PrependTo[vetexListOfWeakyConnectedGraphs, Part[vertex, gg]]
        ];
        connectedSubgraph = Table[If[ ConnectedGraphQ[Part[subgrafos, i]],
                                      Part[subgrafos, i],
                                      Null
                                  ], {i, 1, Length[subgrafos], 1}] /.Null -> Sequence[];
        vetexListOfConnectedGraphs = DeleteDuplicates[       Table[Sort[VertexList[Part[connectedSubgraph, r]]], {r, 1,Length[connectedSubgraph], 1}]];
        <|"VertexListWeaklyConnectedSubgraphs" -> vetexListOfWeakyConnectedGraphs, 
         "VertexListConnectedSubgraphs" -> vetexListOfConnectedGraphs |>
    ];

calculateIntegrationInformation[partitions_, purviews_, inputs_, outputs_, currentCandidateSetState_, ucPastProbDist_, 
   ucFutProbDist_] :=
    Block[ {},
        ciArray = List[];
        eiArray = List[];
        ceiArray = List[];
        pastPossDistribArray = List[];
        futPossDistribArray = List[];
        For[p = 1, p <= Length[partitions], p++,
                onePartition = Sort[Part[partitions, p]];
                ciByMechanism = List[];
                eiByMechanism = List[];
                ceiByMechanism = List[];
                pastPossDistribArrayByMechanism = List[];
                futPossDistribArrayByMechanism = List[];
                For[pp = 1, pp <= Length[purviews], pp++,
                        onePurview = Sort[ Part[purviews, pp]];
                        (*-------------  PAST ANALYSIS -------------*)
                        pastProbabilityDistribution = probabilityDistributionCalculation[onePartition, onePurview,outputs, inputs, currentCandidateSetState, "causal"];
                        currentPStates = pastProbabilityDistribution["OutputsWithCurrentSubstate"];
                        possiblePStates = pastProbabilityDistribution["PossiblePastFutureStates"];
                        indexesPStates = pastProbabilityDistribution["IndexesOutElementsCurrentSubstate"];
                        pastDistribution = pastProbabilityDistribution["CompleteProbabilityDistribution"];
                        (*begin-------------------------------------------------*)
                        (*Print[" ------------- an analysis start here ------------"];
                        Print["Current set state:"<>ToString[currentCandidateSetState]<>" Partition: "<> ToString[onePartition]<> " Purview:"<> ToString[onePurview]];
                        Print["Past Probabilities distribution: "];
                        Print[ToString[pastDistribution]];*)
                        (*end-------------------------------------------------*)
                        AppendTo[pastPossDistribArrayByMechanism, pastDistribution];
                        ci = EuclideanDistance[pastDistribution, ucPastProbDist];
                        AppendTo[ciByMechanism, ci];
                        (*begin-------------------------------------------------*)
                        (*Print["------ Past Analysis  --------"];
                        Print["Current states : " <> ToString[Length[currentPStates]] <>" elements"];
                        Print[currentPStates];
                        Print["Possible Past States: "];
                        Print[possiblePStates];
                        Print["Indexes Possible Past States" <> ToString[Length[
                        indexesPStates]] <> " elements"];
                        Print[indexesPStates];
                        Print["Past Distribution: " <> ToString[Length[pastDistribution]] <> " elements"];
                        Print[pastDistribution];
                        Print[Counts[pastDistribution]];
                        Print["---------------------------------------------------- "];
                        Print["ci: " <> ToString[ci]];
                        Print["---------------------------------------------------- "];*)
                        (*end-------------------------------------------------*)
                        (*-------------  FUTURE ANALYSIS -------------*)
                        futureProbabilityDistribution = probabilityDistributionCalculation[onePartition, onePurview,outputs, inputs, currentCandidateSetState, "effect"];
                        currentFStates = futureProbabilityDistribution["OutputsWithCurrentSubstate"];
                        possibleFStates = futureProbabilityDistribution["PossiblePastFutureStates"];
                        futDistribution = futureProbabilityDistribution["CompleteProbabilityDistribution"];
                        AppendTo[futPossDistribArrayByMechanism, futDistribution];
                        ei = EuclideanDistance[futDistribution, ucFutProbDist];
                        AppendTo[eiByMechanism, ei];
                        minimo = Min[ci, ei];
                        AppendTo[ceiByMechanism, minimo];
                        (*Print["---------------------------------"];
                        Print["mechanism: " <> ToString[onePartition]<> " purview: "<> ToString[onePurview]];
                        Print["cei: "<> ToString[minimo]];
                        Print["---------------------------------"];*)
                        (*Print["------ FUTURE Analysis  --------"];
                        Print["Current states : " <> ToString[Length[currentFStates]] <> " elements"];
                        Print[currentFStates];
                        Print["Possible Future States: "];
                        Print[possibleFStates];
                        Print["Future Distribution: "];
                        Print[futDistribution];
                        Print[Counts[futDistribution]];
                        Print["------------------------------------------------- "];
                        Print["ei: " <> ToString[ei]];
                        Print["------------------------------------------------- "];*)
                                                        
                ];
                AppendTo[ciArray, ciByMechanism];
                AppendTo[eiArray, eiByMechanism];
                AppendTo[ceiArray, ceiByMechanism];
                AppendTo[pastPossDistribArray, pastPossDistribArrayByMechanism];
                AppendTo[futPossDistribArray, futPossDistribArrayByMechanism];
        ];
        Export["/home/alberto/01_ALPHA/ciArray.csv", ciArray, "CSV"];
        Export["/home/alberto/01_ALPHA/eiArray.csv", eiArray, "CSV"];
        Export["/home/alberto/01_ALPHA/ceiArray.csv", ceiArray, "CSV"];
        Export["/home/alberto/01_ALPHA/pastPossDistribArray.csv",pastPossDistribArray, "CSV"];
        Export["/home/alberto/01_ALPHA/futPossDistribArray.csv",futPossDistribArray, "CSV"];
        
        (*Maximal Irreducible Cause and Effect = Concept*)
        (*Indexes are needed to recover probability Distributions*)
        cMICE = Table[Max[Part[ciArray, h]], {h, 1, Length[ciArray], 1}];
        indexCMICE = Table[Flatten[Position[Part[ciArray, hh], Part[cMICE, hh]]], {hh, 1, Length[ciArray], 1}];
        eMICE = Table[Max[Part[eiArray, ii]], {ii, 1, Length[eiArray], 1}];
        indexEMICE = Table[Flatten[Position[Part[eiArray, jj], Part[eMICE, jj]]], {jj,1, Length[eiArray], 1}];
        (*It is possible to obtain repeted values in MIP,then I take the first*)
        cMIP = Min[ciArray];
        indexCMIP = Position[ciArray, cMIP];
        noRepIndexesCMIP = Length[indexCMIP];
        eMIP = Min[eiArray];
        indexEMIP = Position[eiArray, eMIP];
        noRepIndexEMIP = Length[indexEMIP];
        ppPMIPDistrib = Extract[pastPossDistribArray, First[indexCMIP]];
        ppFMIPDistrib = Extract[futPossDistribArray, First[indexEMIP]];
        cIWholeSystemDistrib = Last[Last[pastPossDistribArray]];
        eiWholeSystemDistrib = Last[Last[futPossDistribArray]];
        smallAlpha = Min[Power[EuclideanDistance[ppPMIPDistrib, cIWholeSystemDistrib],noRepIndexesCMIP],Power[EuclideanDistance[ppFMIPDistrib, eiWholeSystemDistrib],noRepIndexEMIP]]/2;
        (*concepts computation: a) distance between each purview's prob. distrib. and the whole sys prob. distribution is calculated.
        b) every max in (a) is found. These are the concepts*)
        pastSmallAlphasArray = List[];
        conceptPastIndexes = List[];
        futSmallAlphasArray = List[];
        conceptFutIndexes = List[];
        For[aa = 1, aa <= Length[pastPossDistribArray], aa++,
            pastSmallAlphaByMechanism = List[];
            futSmallAlphaByMechanism = List[];
            pastProbDistribOfMechanism = Part[pastPossDistribArray, aa];
            futProbDistribOfMechanism = Part[futPossDistribArray, aa];
            For[bb = 1, bb <= Length[pastProbDistribOfMechanism], bb++,
                      onePastProbDistrb = Part[pastProbDistribOfMechanism, bb];
                      oneFutProbDistrb = Part[futProbDistribOfMechanism, bb];
                      AppendTo[pastSmallAlphaByMechanism,EuclideanDistance[cIWholeSystemDistrib, onePastProbDistrb]];
                      AppendTo[futSmallAlphaByMechanism,EuclideanDistance[eiWholeSystemDistrib, oneFutProbDistrb]];
            ];
            AppendTo[pastSmallAlphasArray, pastSmallAlphaByMechanism];
            AppendTo[futSmallAlphasArray, futSmallAlphaByMechanism];
            maxPastSmallAlpha = Max[pastSmallAlphaByMechanism];
            maxFutSmallAlpha = Max[futSmallAlphaByMechanism];
            secondPastIndex = First[Position[pastSmallAlphaByMechanism, maxPastSmallAlpha]];
            secondFutIndex = First[Position[futSmallAlphaByMechanism, maxFutSmallAlpha]];
            completePastIndex = Flatten[{aa, secondPastIndex}];
            completeFutIndex = Flatten[{aa, secondFutIndex}];
            AppendTo[conceptPastIndexes, completePastIndex];
            AppendTo[conceptFutIndexes, completeFutIndex];
         ];
        
        (*Conceptual Information  By Definition CI=Sum[Distance[probDisCOncept, ucProbDistrb]x conceptValue]*)
        cCITable = Table[
                          EuclideanDistance[Extract[pastPossDistribArray, conceptPastIndexes[[uu]]],ucPastProbDist]*
                          Extract[pastSmallAlphasArray, conceptPastIndexes[[uu]]],{uu,1, Length[conceptPastIndexes], 1}];
        cCI = Total[cCITable];
        Print["cCI: "<> ToString[cCI]];
        eCITable = Table[
                          EuclideanDistance[Extract[futPossDistribArray, conceptFutIndexes[[vv]]],ucFutProbDist]*
                          Extract[futSmallAlphasArray, conceptFutIndexes[[vv]]],{vv, 1,Length[conceptFutIndexes], 1}];
        eCI = Total[eCITable];
        Print["eCI: "<> ToString[eCI]];
        Print["Number of concepts: " <> ToString[Length[conceptPastIndexes]]];
        (*BIG ALPHA*)
        pastConceptValues = Extract[pastSmallAlphasArray, conceptPastIndexes];
        distPastConceptsToUCProbDist = Extract[ciArray, conceptPastIndexes];
        futConceptValues = Extract[futSmallAlphasArray, conceptFutIndexes];
        distFutConceptsToUCProbDist = Extract[eiArray, conceptFutIndexes];
        conceptPartitions = Delete[Subsets[Range[Length[conceptPastIndexes]]], 1];
        bigAlphaArray = List[];
        Print["looping over concept partitions: (" <> ToString[Length[conceptPartitions]]<> ") elements"];
        For[vv = 1, vv <= Length[conceptPartitions], vv++,
                 partition = Part[conceptPartitions, vv];
                 oneBigAlpha = Min[Total[Table[(Part[distPastConceptsToUCProbDist, Part[partition, w]] +
                                                 Part[distFutConceptsToUCProbDist, Part[partition, w]])*
                                                 Part[pastConceptValues, Part[partition, w]], 
                                         {w, 1,Length[partition], 1}]
                                         ],
                                    Total[Table[(Part[distPastConceptsToUCProbDist,Part[partition, w]] +
                                                    Part[distFutConceptsToUCProbDist, Part[partition, w]])*
                                                    Part[futConceptValues, Part[partition, w]], 
                                            {w, 1,Length[partition], 1}]]
                                    ];
                 AppendTo[bigAlphaArray, oneBigAlpha];
         ];
        bigAlpha = Min[bigAlphaArray];
        (*Print["+++++++++++++++++++++++++++++++++++++++++++"];
        Print["CI: "];
        Print[ciArray];
        Print["EI: "];
        Print[eiArray];
        Print["CEI: "];
        Print[ceiArray];
        Print["+++++++++++++++++++++++++++++++++++++++++++"];*)
        <| 
         "CEIArray" -> ceiArray, "CIArray" -> ciArray, 
         "EIArray" -> eiArray, "cMIP" -> cMIP, "eMIP" -> eMIP, 
         "IndexCMIP" -> indexCMIP, "IndexEMIP" -> indexEMIP, 
         "cMICE" -> cMICE, "eMICE" -> eMICE, "IndexCMICE" -> indexCMICE, 
         "IndexEMICE" -> indexEMICE, 
         "PastPossDistribArray" -> pastPossDistribArray, 
         "FutPossDistribArray" -> futPossDistribArray, 
         "SmallAlpha" -> smallAlpha, 
         "PastSmallAlphasArray" -> pastSmallAlphasArray , 
         "ConceptPastIndexes" -> conceptPastIndexes, 
         "FutSmallAlphasArray" -> futSmallAlphasArray , 
         "ConceptFutIndexes" -> conceptFutIndexes, "CCI" -> cCI, 
         "ECI" -> eCI, "BigAlpha" -> bigAlpha|>
    ];





csv2BinConnMatrix[completePathOfcsvFile_] :=
    Block[ {},
        originalMatrix = Import[completePathOfcsvFile, "Table"];
        binConnMatrix = List[];
        For[hh = 1, hh <= Length[originalMatrix], hh++,
              row = Part[originalMatrix, hh];
              newRow = List[];
              For[ii = 1, ii <= Length[row], ii++,
                       If[ Part[row, ii] > 0,
                           AppendTo[newRow, 1],
                           AppendTo[newRow, 0]
                       ];
                 ];
              AppendTo[binConnMatrix, newRow];
         ];
        <|"BinConnMatrix" -> binConnMatrix|>
    ];

createBinRandomCurrentState[length_] :=
    (Return[
    Flatten[Table[RandomInteger[], {mn, 1, length, 1}]]]
    );
    
    
createBinRandomInput[length_] :=
    (Return[
    Flatten[Table[RandomInteger[], {mn, 1, length, 1}]]]
    );

createRandomDynamic[length_] :=
    Block[ {},
        dina = List[];
        For[mm = 1, mm <= length, mm++,
	           ere = RandomInteger[2];(*Exclude NAND*)
	           If[ ere === 0,
	               ele = "AND",
	               If[ ere === 1,
	                   ele = "OR",
	                   If[ ere === 2,
	                       ele = "XOR",
	                       If[ ere === 3,
	                           ele = "NAND"
	                       ]
	                   ]
	               ]
	           ];
	           AppendTo[dina, ele];
         ];
        dina = Flatten[dina];
        <|"Dynamic" -> dina|>
    ];
    
createSimpleRandomDynamic[length_] :=
    Block[ {},
        dina = List[];
        For[mm = 1, mm <= length, mm++,
	           ere = RandomInteger[1];(*Exclude NAND*)
	           If[ ere === 0,
	               ele = "AND",
	               If[ ere === 1,
	                   ele = "OR",
	                   If[ ere === 2,
	                       ele = "XOR",
	                       If[ ere === 3,
	                           ele = "NAND"
	                       ]
	                   ]
	               ]
	           ];
	           AppendTo[dina, ele];
         ];
        dina = Flatten[dina];
        <|"Dynamic" -> dina|>
    ];

ExtracSubMatrix[completeConnMatrix_, colIni_, colEnd_, rowIni_, 
   rowEnd_] :=
    Block[ {},
        extractedMatrix = List[];
        For[row = rowIni, row <= rowEnd, row++,
                                          AppendTo[extractedMatrix,completeConnMatrix[[row]][[colIni ;; colEnd]]];
        ];
        <|"ExtractedMatrix" -> extractedMatrix|>
    ];

csvConnNetwork2ConnMatrix[csvNetFileName_] :=
    Block[ {},
        originalMatrix = Import[csvNetFileName, "CSV"];
        ff = Flatten[originalMatrix];
        connMatrix = ConstantArray[0, {Max[ff], Max[ff]}];
        (*begin ---------------------------------------*)
        (*Print[originalMatrix];
        Print[connMatrix];*)
        (*end-------------------------------------------*)
        For[ii = 1, ii <= Length[originalMatrix], ii++,
                oneConn = Part[originalMatrix, ii];
                firstElement = oneConn[[1]];
                secondElement = oneConn[[2]];
                row = Part[connMatrix, secondElement];
                newRow = ReplacePart[row, firstElement -> 1];
                connMatrix = ReplacePart[connMatrix, secondElement -> newRow];
                (*begin ---------------------------------------*)
                (*Print["New row: " <> ToString[newRow]];
                Print["connectivity matrix: " <> ToString[connMatrix]];*)
                (*end-------------------------------------------*)
          ];
        <|"ConnectivityMatrix" -> connMatrix|>
    ];
    
    
    
    
    (*NEW SECTION---------------------------------------------------------
    --------------------------------------------------------------------
    ---------------------------------------------------------------------*)
    

lengthPath[gr_, i_, j_] :=
    Module[ {dist, indices, dd, nbrs, res},
        dist = GraphDistance[gr, i, j];
        If[ dist != Infinity,
            indices = {};
            dd = dist;
            res = Reap[Nest[Function[{vv}, dd -= 1;
                                           nbrs = VertexList[NeighborhoodGraph[gr, #]] & /@ vv;
                                           nbrs = 
                                            Pick[#, GraphDistance[gr, #, j] & /@ #, dd] & /@ nbrs;
                                           Sow /@ Flatten[Thread /@ Thread[vv \[DirectedEdge] nbrs]];
                                           Union[Flatten[nbrs]]], {i}, dist]][[2, 1]],
            res = 0
        ];
        <|"Path" -> res, "LengthPath" -> Length[res]|>
    ];

(*THis has to be tested, it is unusefull*)

findingPath[gr_, startingNode_, endingNode_] :=
    Module[ {ends, sub, e, gr1(*,lengthPath,v*)},
        ends = {startingNode, endingNode};
        sub = lengthPath[gr, ends]["Path"];
        If[ Length[sub] != 0,
            e = EdgeList[
               gr] /. {x_ <-> y_ /; 
                 GraphDistance[gr, x, endingNode] < 
                  GraphDistance[gr, y, endingNode] :> y \[DirectedEdge] x, 
               x_ <-> y_ /; 
                 GraphDistance[gr, y, endingNode] <= 
                  GraphDistance[gr, x, endingNode] :> x \[DirectedEdge] y};
            gr1 = Graph[e, ImagePadding -> 15];
        ];
        <|"EdgeListPath" -> sub, "LengthPath" -> Length[sub]|>
    ];

(*given a set of nodes, it calculate all possible subsets or mechanisms
For each mechanism, determine all possible subsets of its complement
*)
buildEvaluations[nodes_] :=
    Module[ {powerset, setEvaluations, aa, complemento, mechanism, 
      purviews, bb},
        powerset = Delete[Subsets[nodes], 1] /. {} -> Sequence[];
        setEvaluations = List[];
        For[aa = 1, aa <= Length[powerset], aa++,
         mechanism = Part[powerset, aa];
         complemento = Complement[nodes, mechanism];
         purviews = Subsets[complemento] /. {} -> Sequence[];
         For[bb = 1, bb <= Length[purviews], bb++,
          AppendTo[setEvaluations, Association[{mechanism -> Part[purviews, bb]}]];
     ];
         ];
        <|"AllEvaluations" -> Merge[setEvaluations, Identity]|>
    ];
    
    
validateSubgraphs[edgeList_] :=
    Module[ {edgesOfAllSubGraphs,hh, validSubgraphs, subgra,gg,vertex,gr1 },
    	gr1=Graph[edgeList];
    	vertex = VertexList[gr1];
    	
        edgesOfAllSubGraphs = Delete[Subsets[edgeList], 1];
        validSubgraphs = List[];
        For[hh = 1, hh <= Length[edgesOfAllSubGraphs], hh++,
                 subgra = Graph[Part[edgesOfAllSubGraphs, hh]];
                 If[ WeaklyConnectedGraphQ[subgra], AppendTo[validSubgraphs, Sort[VertexList[subgra]]],Null];
        ];
         For[gg = 1, gg <= Length[vertex], gg++, 
                                          AppendTo[validSubgraphs, List[Part[vertex, gg]]];
         ];
        <|"ValidVertexOfSubgraphs"-> DeleteDuplicates[validSubgraphs]|>
    ];    
    
    
buildEvaluations2[edgeList_] :=
    Module[ {powerset, setEvaluations, aa, complemento, mechanism, purviews, bb,gg, connectedSubgraphs, nodes,
    	currentPurview},
    	
        connectedSubgraphs = validateSubgraphs[edgeList]["ValidVertexOfSubgraphs"];
        gg = Graph[edgeList];
        nodes = Sort[VertexList[gg]];
        powerset = Delete[Subsets[nodes], 1] /. {} -> Sequence[];
        setEvaluations = List[];
        For[aa = 1, aa <= Length[powerset], aa++,
         mechanism = Part[powerset, aa];
         complemento = Complement[nodes, mechanism];
         purviews = Subsets[complemento] /. {} -> Sequence[];
         
	         For[bb = 1, bb <= Length[purviews], bb++,
	         	currentPurview = Part[purviews,bb];
	         	If[MemberQ[connectedSubgraphs, currentPurview ],
	              AppendTo[setEvaluations, Association[{mechanism -> Part[purviews, bb]}]],
	              Null
	         	];
	         ];
         ];
        <|"AllEvaluations" -> Merge[setEvaluations, Identity]|>
    ];

ValidatingTuples[gr_, nodes_] :=
    Module[ {myTuples, validTuples, oneTuple, startingNode, endingNode, pathSize, bb},
        myTuples = Tuples[nodes, 2];
        validTuples = List[];
        For[bb = 1, bb <= Length[myTuples], bb++,
         oneTuple = Part[myTuples, bb];
         startingNode = Part[oneTuple, 1];
         endingNode = Part[oneTuple, 2];
         If[ startingNode != endingNode,
             pathSize = 
              lengthPath[gr, startingNode, endingNode]["LengthPath"],
             pathSize = 0
         ];
         If[ pathSize > 0,
             AppendTo[validTuples, oneTuple],
             Null
         ];
         ];
        <|"ValidTuples" -> validTuples|>
    ];

(*given a list of nodes, calculate all possible 2-tuples
and see if the two elements in a tuple ar connected*)
ValidatingTuples2[gr_,nodes_] :=
    Module[{myTuples, validTuples,bb, oneTuple, startingNode, endingNode, pathSize},
    	myTuples = Tuples[nodes, 2];
    	validTuples = List[];
    	For[bb = 1, bb <= Length[myTuples], bb++,
         oneTuple = Part[myTuples, bb];
         startingNode = Part[oneTuple, 1];
         endingNode = Part[oneTuple, 2];
         If[ startingNode != endingNode,
             pathSize = Length[FindPath[gr, startingNode,endingNode ,1]],
             pathSize = 0
         ];
         If[ pathSize > 0,
             AppendTo[validTuples, oneTuple],
             Null
         ];
         ];
        <|"ValidTuples" -> validTuples|>
    	     
    ];

(*given a node, determine if it is connected with any node of a 
purview [subgraph] *)
compareMechaNodeWithPurview[mechaNode_, purview_, validTuples_] :=
    Module[ {found, aa, nodePurview, comparation},
        found = False;
        For[aa = 1, aa <= Length[purview], aa++,
         nodePurview = Part[purview, aa];
         comparation = {mechaNode, nodePurview};
         (*begin ----------------------------------*)
         (*Print[
         "Current purview: "<>ToString[purview]];
         Print["Connection to test: "<> ToString[
         comparation]];*)
         (*end ----------------------------------*)
         If[ MemberQ[validTuples, comparation],
             found = True;
             Break[],
             found = False
         ];
         ];
        <|"Found" -> found|>
    ];

(*Given a mechanisim (subgraph), determine if any of its nodes
it is connected with any node of a purview (subgraph) *)
compareMechanismWithPurview[mechanism_, purview_, validTuples_] :=
    Module[ {found, bb, nodeMechamisn, theResult},
        found = False;
        theResult = List[];
        For[bb = 1, bb <= Length[mechanism], bb++,
         nodeMechamisn = Part[mechanism, bb];
         (*begin ----------------------------------*)
         (*Print[
         "Node Mechamisn: "<> ToString[nodeMechamisn]];
         Print["Purview: "<> ToString[purview]];*)
         (*end ----------------------------------*)
         found = compareMechaNodeWithPurview[nodeMechamisn, purview, validTuples]["Found"];
         If[ found === True,
             Break[],
             found = False;
             theResult = Association[{mechanism -> purview}];
         ];
         ];
        <|"Found" -> found, "Association2Remove" -> theResult|>
    ];

compareMechanismWithSetOfPurviews[mechanism_, setPurviews_, validTuples_] :=
    Module[ {allAssociations2Remove, cc, onePurview, rm},
        allAssociations2Remove = List[];
        For[cc = 1, cc <= Length[setPurviews], cc++,
         onePurview = Part[setPurviews, cc];
         (*begin ----------------------------------*)
         (*Print[
         "onePurview:"<>ToString[onePurview]];
         Print["Mechanism: "<> ToString[mechanism]];*)
         (*begin ----------------------------------*)
         rm = 
         compareMechanismWithPurview[mechanism, onePurview, validTuples];
         If[ rm["Found"],
             Null,
             AppendTo[allAssociations2Remove, rm["Association2Remove"]]
         ];
        ];
        <|"NoAssociations2Remove" -> Length[allAssociations2Remove], 
         "AllAssociations2Remove" -> allAssociations2Remove|>
    ];

validatingAllEvaluations[completeAssociationsEvaluations_, validTuples_] :=
    Module[{allMechanisims, associations2Remove, dd, mechanism, purviewsSet, cmwsp},
    	
        allMechanisims = Keys[completeAssociationsEvaluations];
        associations2Remove = List[];
        For[dd = 1, dd <= Length[allMechanisims], dd++,
         mechanism = Part[allMechanisims, dd];
         purviewsSet = completeAssociationsEvaluations[mechanism];
         (*begin ----------------------------------*)
         (*Print[
         "Current mechanism: "<>ToString[mechanism]];
         Print["Purviewset: "<> ToString[purviewsSet]];*)
         (*end ----------------------------------*)
         cmwsp = compareMechanismWithSetOfPurviews[mechanism, purviewsSet, validTuples];
         If[ cmwsp["NoAssociations2Remove"] > 0,
             AppendTo[associations2Remove, cmwsp["AllAssociations2Remove"]]
         ];
         ];
        <|"AllAssociationsToRemove" -> Flatten[associations2Remove]|>
    ];

cleaningAssociation[dirtyAssociation_, elementsToRemove_] :=
    Module[ {cleanAssociation, gg, oneElement2Remove, kei2Remove, value2Remove, allValues, newAsso},
        
        cleanAssociation = dirtyAssociation;
        
        For[gg = 1, gg <= Length[elementsToRemove], gg++,
         oneElement2Remove = Part[elementsToRemove, gg];
         kei2Remove = Flatten[Keys[oneElement2Remove]];
         value2Remove = Flatten[Values[oneElement2Remove]];
         allValues = cleanAssociation[kei2Remove];
         newAsso = Association[{kei2Remove -> Delete[allValues, Position[allValues, value2Remove]]}];
         (*being -----------------------*)
         (*Print[
         "---------------------------------------"];
         Print["Element To Remove: "<> ToString[element2Remove]];
         Print["key where to remove:" <> ToString[kei2Remove]];
         Print["value to remove: "<> ToString[value2Remove]];
         Print["Original all values: "<> ToString[allValues]];
         Print["Positions: "<>ToString[Position[allValues,value2Remove]]];
         Print["New association: "<> ToString[
         newAsso]];*)
         (*end -----------------------*)
         cleanAssociation = Delete[cleanAssociation, Key[kei2Remove]];
         AppendTo[cleanAssociation, newAsso];
         ];
        <|"CleanAssociation" -> KeySort[cleanAssociation]|>
    ];

calculateAlpha[completeTableAssociations_, inputs_, outputs_, 
   currentCandidateSetState_, ucPastProbDist_, ucFutProbDist_] :=
    Module[ {ciArray, eiArray, ceiArray, pastPossDistribArray, 
      futPossDistribArray, allKeys, p, onePartition, ciByMechanism, 
      eiByMechanism, ceiByMechanism, pastPossDistribArrayByMechanism, 
      futPossDistribArrayByMechanism, purviews, pp, aPurview, 
      pastProbabilityDistribution,(* currentPStates, possiblePStates, 
      indexesPStates, currentFStates, possibleFStates,*)pastDistribution, 
      ci, futureProbabilityDistribution, futDistribution, ei, minimo, cMICE, 
      indexCMICE, eMICE, indexEMICE, cMIP, indexCMIP, noRepIndexesCMIP, eMIP, 
      indexEMIP, noRepIndexEMIP, ppPMIPDistrib, ppFMIPDistrib, cIWholeSystemDistrib, 
      eiWholeSystemDistrib, smallAlpha, h, hh, ii, jj, pastSmallAlphasArray, 
      conceptPastIndexes, futSmallAlphasArray, conceptFutIndexes, aa, 
      pastSmallAlphaByMechanism, futSmallAlphaByMechanism, pastProbDistribOfMechanism, 
      futProbDistribOfMechanism, bb, onePastProbDistrb, oneFutProbDistrb, maxPastSmallAlpha, 
      maxFutSmallAlpha, secondPastIndex, completePastIndex, completeFutIndex, 
      cCITable, cCI, eCITable, eCI, distPastConceptsToUCProbDist, 
      distFutConceptsToUCProbDist, vv, bigAlpha, secondFutIndex,uu,w, conceptPastValues, 
      conceptFutValues, listConcepts, (*conceptComplements, bigAlphaArray, conceptPartitions, nn, 
      oneBigAlpha,*) zeroInformationPastConcepts, zeroInformationFutConcepts, indexesZeroInformationConcepts, 
      zpic, oneZeroPastConcept, oneZeroFutureConcept, zfic, oneComplement, 
      minFutConceptValue, minPastConceptValue, indexFutMin, indexPastMin, 
      minValueInformationConceptsIndex, pindex, findex, onePindex, oneFindex, nonZeroConcepts },
      
        ciArray = List[];
        eiArray = List[];
        ceiArray = List[];
        pastPossDistribArray = List[];
        futPossDistribArray = List[];
        allKeys = Keys[completeTableAssociations];
        For[ p = 1, p <= Length[allKeys], p++,
			         onePartition = Sort[Part[allKeys, p]];
			         ciByMechanism = List[];
			         eiByMechanism = List[];
			         ceiByMechanism = List[];
			         pastPossDistribArrayByMechanism = List[];
			         futPossDistribArrayByMechanism = List[];
			         purviews = completeTableAssociations[onePartition];
			         
			         For[ pp = 1, pp <= Length[purviews], pp++,
					          aPurview = Sort[Part[purviews, pp]];
					          (*Print["Mechanism"<> "("<>ToString[p]<>" Of "<>ToString[Length[allKeys]]<>"): "<> ToString[onePartition]<> " Purview"<> "("<>ToString[pp]<>" of "<>ToString[Length[purviews]]<>"): " <> ToString[aPurview]];*)
					          (*-------------PAST ANALYSIS-------------*)
					          (*partition and purview determine elements to take in account for probability
					          distribution calculation*)
					          pastProbabilityDistribution = probabilityDistributionCalculation[one, aPurview, outputs, inputs, currentCandidateSetState, "causal"];
					          (*currentPStates = pastProbabilityDistribution["OutputsWithCurrentSubstate"];
					          possiblePStates = pastProbabilityDistribution["PossiblePastFutureStates"];
					          indexesPStates = pastProbabilityDistribution["IndexesOutElementsCurrentSubstate"];*)
					          pastDistribution = pastProbabilityDistribution["CompleteProbabilityDistribution"];

					          
					          (*------------- FUTURE ANALYSIS-------------*)
					          futureProbabilityDistribution = probabilityDistributionCalculation[onePartition, aPurview, outputs, inputs, currentCandidateSetState, "effect"];
					          (*currentFStates = futureProbabilityDistribution["OutputsWithCurrentSubstate"];
					          possibleFStates = futureProbabilityDistribution["PossiblePastFutureStates"];*)
					          futDistribution = futureProbabilityDistribution["CompleteProbabilityDistribution"];

					          
					          (*one ei, ci and cei is calculated per combination mechanism-> puriew*)
					          If[Length[pastDistribution]>0 && Length[futDistribution]>0,
					          	
					          	  AppendTo[pastPossDistribArrayByMechanism, pastDistribution];
						          ci = EuclideanDistance[pastDistribution, ucPastProbDist];
						          AppendTo[ciByMechanism, ci];
						          
						          AppendTo[futPossDistribArrayByMechanism, futDistribution];
						          ei = EuclideanDistance[futDistribution, ucFutProbDist];
						          AppendTo[eiByMechanism, ei];
						          
						          
						          minimo = Min[ci, ei];
						          AppendTo[ceiByMechanism, minimo];
					          ];
          			     ];
          			     
          			     
				         AppendTo[ciArray, ciByMechanism];
				         AppendTo[eiArray, eiByMechanism];
				         AppendTo[ceiArray, ceiByMechanism];
				         AppendTo[pastPossDistribArray, pastPossDistribArrayByMechanism];
				         AppendTo[futPossDistribArray, futPossDistribArrayByMechanism];
         
         ];
        (*Export["/home/alberto/01_ALPHA/ciArray.csv", ciArray, "CSV"];
        Export["/home/alberto/01_ALPHA/eiArray.csv", eiArray, "CSV"];
        Export["/home/alberto/01_ALPHA/ceiArray.csv", ceiArray, "CSV"];
        Export["/home/alberto/01_ALPHA/pastPossDistribArray.csv", pastPossDistribArray, "CSV"];
        Export["/home/alberto/01_ALPHA/futPossDistribArray.csv", futPossDistribArray, "CSV"];*)
        (*Maximal Irreducible Cause and Effect= Concept*)
        (*Indexes are needed to recover probability Distributions*)
        (**)
        cMICE = Table[Max[Part[ciArray, h]], {h, 1, Length[ciArray], 1}];
        indexCMICE = Table[Flatten[Position[Part[ciArray, hh], Part[cMICE, hh]]], {hh, 1, Length[ciArray], 1}];
        eMICE = Table[Max[Part[eiArray, ii]], {ii, 1, Length[eiArray], 1}];
        indexEMICE = Table[Flatten[Position[Part[eiArray, jj], Part[eMICE, jj]]], {jj, 1, Length[eiArray], 1}];
        
        (*small phi = Distance[ceiWholeSyste, Min[cei]]*)
        (*It is possible to obtain repeted values in MIP, then I take the first*)
        cMIP = Min[ciArray];
        indexCMIP = Position[ciArray, cMIP];
        noRepIndexesCMIP = Length[indexCMIP];
        eMIP = Min[eiArray];
        indexEMIP = Position[eiArray, eMIP];
        noRepIndexEMIP = Length[indexEMIP];
        
        (* begin ---------------------------------------*)
        (*Print["This is ciArray: -------- "];
        Print[ToString[ciArray]];
        Print[" ------ looking for MIPs  --------"];
        Print["cMIP: " <> ToString[cMIP]];
        Print["index cMIP: " <> ToString[indexCMIP]];
        Print["eMIP: " <> ToString[cMIP]];
        Print["index eMIP: " <> ToString[indexCMIP]];*)
        (* end   ---------------------------------------*)
        
        ppPMIPDistrib = Extract[pastPossDistribArray, First[indexCMIP]];
        ppFMIPDistrib = Extract[futPossDistribArray, First[indexEMIP]];
        cIWholeSystemDistrib = Last[Last[pastPossDistribArray]];
        eiWholeSystemDistrib = Last[Last[futPossDistribArray]];
        (*smallAlpha = Min[Power[EuclideanDistance[ppPMIPDistrib, cIWholeSystemDistrib], noRepIndexesCMIP], Power[EuclideanDistance[ppFMIPDistrib, eiWholeSystemDistrib], noRepIndexEMIP]]/2;*)
        smallAlpha = Min[EuclideanDistance[ppPMIPDistrib, cIWholeSystemDistrib],EuclideanDistance[ppFMIPDistrib, eiWholeSystemDistrib], noRepIndexEMIP];
        
        (*concepts computation: 
        a) distance between each purview's prob.distrib.and the whole sys prob.distribution is calculated.
        b) every max in (a) is found.These are the concepts*)
        pastSmallAlphasArray = List[];
        conceptPastIndexes = List[];
        conceptPastValues = List[];
        futSmallAlphasArray = List[];
        conceptFutIndexes = List[];
        conceptFutValues = List[];

        For[aa = 1, aa <= Length[pastPossDistribArray], aa++, 
		         pastSmallAlphaByMechanism = List[];
		         futSmallAlphaByMechanism = List[];
		         (*a mechanism relates several purviews
		         {mecha1}-> {{pw11},{pw12}...{pw1n}}
		         {mecha2}-> {{pw21},{pw22}...{p2wn}}
		         ...
		         {mecha_r}-> {{pwr1},{pwr2}...{pwrn}}
		         *)
		         (*it takes a mechanism to analize:
		         {mecha1}-> {{pw11},{pw12}...{pw1n}}
		         *)
		         pastProbDistribOfMechanism = Part[pastPossDistribArray, aa];
		         futProbDistribOfMechanism = Part[futPossDistribArray, aa];
		         
		         For[bb = 1, bb <= Length[pastProbDistribOfMechanism], bb++,
		         	      (*definition: small phi=Distance[Distrib[onePartition], Distrib[wholeSystem]]
		         	      take a purview and calculate distance with el whole system:
		         	      D[pw1, ws],D[pw2]...D[pwn]
		         	      *) 
				          onePastProbDistrb = Part[pastProbDistribOfMechanism, bb];
				          oneFutProbDistrb = Part[futProbDistribOfMechanism, bb];
				          AppendTo[pastSmallAlphaByMechanism, EuclideanDistance[cIWholeSystemDistrib, onePastProbDistrb]];
				          AppendTo[futSmallAlphaByMechanism, EuclideanDistance[eiWholeSystemDistrib, oneFutProbDistrb]];
		           ];
		         AppendTo[pastSmallAlphasArray, pastSmallAlphaByMechanism];
		         AppendTo[futSmallAlphasArray, futSmallAlphaByMechanism];
		         maxPastSmallAlpha = Max[pastSmallAlphaByMechanism];
		         AppendTo[conceptPastValues, maxPastSmallAlpha];
				 maxFutSmallAlpha = Max[futSmallAlphaByMechanism];
				 AppendTo[conceptFutValues, maxFutSmallAlpha];
				 secondPastIndex = First[Position[pastSmallAlphaByMechanism, maxPastSmallAlpha]];
				 secondFutIndex = First[Position[futSmallAlphaByMechanism, maxFutSmallAlpha]];
				 completePastIndex = Flatten[{aa, secondPastIndex}];
				 completeFutIndex = Flatten[{aa, secondFutIndex}];
				 AppendTo[conceptPastIndexes, completePastIndex];
				 AppendTo[conceptFutIndexes, completeFutIndex];
		               
         ];
         
        
		 
         
        (*Conceptual Information By Definition CI=Sum[Distance[
        probDisCOncept,ucProbDistrb]x conceptValue]*)
        cCITable = Table[EuclideanDistance[ Extract[pastPossDistribArray, conceptPastIndexes[[uu]]], ucPastProbDist]*
        	                                Extract[pastSmallAlphasArray, conceptPastIndexes[[uu]]], 
        	            {uu, 1, Length[conceptPastIndexes], 1}
        	       ];
        cCI = Total[cCITable];
        
        eCITable =  Table[EuclideanDistance[ Extract[futPossDistribArray, conceptFutIndexes[[vv]]], ucFutProbDist]*
        	                                 Extract[futSmallAlphasArray, conceptFutIndexes[[vv]]], 
        	              {vv, 1,Length[conceptFutIndexes], 1}];
        eCI = Total[eCITable];
        (*BIG ALPHA*)
        
        
        (*pastConceptValues = Extract[pastSmallAlphasArray, conceptPastIndexes];
        futConceptValues = Extract[futSmallAlphasArray, conceptFutIndexes];*)
        distPastConceptsToUCProbDist = Extract[ciArray, conceptPastIndexes];
        distFutConceptsToUCProbDist = Extract[eiArray, conceptFutIndexes];
        	
        zeroInformationPastConcepts = Flatten[Position[conceptPastValues,0.]];
        zeroInformationFutConcepts = Flatten[Position[conceptFutValues,0.]];
        listConcepts = Range[Length[conceptPastIndexes]];
        
        
        indexesZeroInformationConcepts = List[];
        For[zpic=1,zpic <= Length[zeroInformationPastConcepts], zpic++,
			oneZeroPastConcept = Part[zeroInformationPastConcepts, zpic];
			For[zfic=1,zfic <= Length[zeroInformationFutConcepts], zfic,
			    oneZeroFutureConcept = Part[zeroInformationFutConcepts, zfic];
			    If[oneZeroFutureConcept === oneZeroPastConcept, AppendTo[indexesZeroInformationConcepts, oneZeroPastConcept];Break[],Null];
			];      
        ];
        
        (*If[Length[indexesZeroInformationConcepts]>1,
	        For[del=1,del <= Length[indexesZeroInformationConcepts], del++,
	        	Delete[listConcepts,Position[listConcepts,Flatten[Part[indexesZeroInformationConcepts,del]]]];
	        ], Delete[listConcepts,1]
        ];*)
        
       nonZeroConcepts = Complement[listConcepts, indexesZeroInformationConcepts];
       
       (*-------------------------------------------------------------------------*)
       (*-------------------------------------------------------------------------*)
        
        
       (* conceptPartitions = Delete[Subsets[listConcepts], 1];        
        conceptComplements = Table[Complement[listConcepts,Part[conceptPartitions,nn]],{nn,1,Length[conceptPartitions],1}]/.{} -> Sequence[];
        
        
        
        bigAlphaArray = List[];
        
        For[vv = 1, vv <= Length[conceptComplements], vv++, 
			         oneComplement = Part[conceptComplements, vv];
			         
			         If[Length[Position[zeroInformationPastConcepts,vv]]===0 && Length[Position[zeroInformationFutConcepts,vv]]===0,
			            oneBigAlpha =  Min[Total[Table[(Part[distPastConceptsToUCProbDist, Part[oneComplement, w]] +
			         	                              Part[distFutConceptsToUCProbDist, Part[oneComplement, w]])* 
			         	                              Part[conceptPastValues, Part[oneComplement, w]], 
			         	                            {w, 1, Length[oneComplement], 1}
			         	                            ]
			         	                      ],
			         	                Total[Table[(Part[distPastConceptsToUCProbDist, Part[oneComplement, w]] +
			         	                              Part[distFutConceptsToUCProbDist, Part[oneComplement, w]])* 
			         	                              Part[conceptFutValues, Part[oneComplement, w]], 
			         	                             {w, 1, Length[oneComplement], 1}
			         	                         ]
			         	                      ]
			                                   
			         	            ],Null
			         	            
			          ];
			         	               
			         	                
			         AppendTo[bigAlphaArray, oneBigAlpha];
         ];
        bigAlpha = Min[bigAlphaArray];
      *)  
        (*-------------------------------------------------------------------------*)
        (*-------------------------------------------------------------------------*)
        
        
        minFutConceptValue = Min[Part[conceptFutValues,nonZeroConcepts]];
        minPastConceptValue = Min[Part[conceptPastValues,nonZeroConcepts]];
        
        indexFutMin = Position[conceptFutValues, minFutConceptValue];
        indexPastMin = Position[conceptPastValues, minPastConceptValue];
        
        minValueInformationConceptsIndex = List[];
        For[pindex=1,pindex=Length[indexPastMin],pindex++,
             onePindex=Part[indexPastMin,pindex];
             For[findex = 1, findex<=Length[indexFutMin], findex++,
                   oneFindex = Part[indexFutMin, findex];
                   If[onePindex === oneFindex, AppendTo[minValueInformationConceptsIndex, onePindex];Break[],Null];
             ];
        ];
        
        oneComplement = Complement[nonZeroConcepts,minValueInformationConceptsIndex];
        
        bigAlpha =  Min[Total[Table[(Part[distPastConceptsToUCProbDist, Part[oneComplement, w]] +
                                                        Part[distFutConceptsToUCProbDist, Part[oneComplement, w]])* 
                                                        Part[conceptPastValues, Part[oneComplement, w]], 
                                                      {w, 1, Length[oneComplement], 1}
                                                      ]
                                                ],
                        Total[Table[(Part[distPastConceptsToUCProbDist, Part[oneComplement, w]] +
                                                        Part[distFutConceptsToUCProbDist, Part[oneComplement, w]])* 
                                                        Part[conceptFutValues, Part[oneComplement, w]], 
                                                       {w, 1, Length[oneComplement], 1}
                                                   ]
                                                ]
                                                
                        ];     	                

        
        <|
         "CEIArray" -> ceiArray, "CIArray" -> ciArray, 
         "EIArray" -> eiArray, "cMIP" -> cMIP, "eMIP" -> eMIP, 
         "IndexCMIP" -> indexCMIP, "IndexEMIP" -> indexEMIP, 
         "cMICE" -> cMICE, "eMICE" -> eMICE, "IndexCMICE" -> indexCMICE, 
         "IndexEMICE" -> indexEMICE, 
         "PastPossDistribArray" -> pastPossDistribArray, 
         "FutPossDistribArray" -> futPossDistribArray, 
         "SmallAlpha" -> smallAlpha, 
         "PastSmallAlphasArray" -> pastSmallAlphasArray, 
         "ConceptPastIndexes" -> conceptPastIndexes, 
         "ConceptPastValues" -> conceptPastValues,
         "FutSmallAlphasArray" -> futSmallAlphasArray, 
         "ConceptFutIndexes" -> conceptFutIndexes,
         "ConceptFutValues" -> conceptFutValues, 
         "ZeroInformationPastConcepts" -> zeroInformationPastConcepts, 
         "ZeroInformationFutConcepts" -> zeroInformationPastConcepts, 
         "CCI" -> cCI, 
         "ECI" -> eCI, 
         "BigAlpha" -> bigAlpha|>
    ];
    
    
    
 findMainComplex[onefileName_] := Module[ 
 	{mainComplex, oneConnMatrix, randomDynamic, runningDynamic, ins, outs, 
     attDec, ucInputProbVector, misAttractoresProb, 
     basinsOfAttractionGraph, nodosAttractores, boa,  cs, miGrapho, ta, 
     att, ce,o,u},
     
         oneConnMatrix = csvConnNetwork2ConnMatrix[onefileName]["ConnectivityMatrix"];
         randomDynamic = createRandomDynamic[Length[oneConnMatrix]]["Dynamic"];
         runningDynamic = runDynamic[oneConnMatrix, randomDynamic];
         ins = runningDynamic["RepertoireInputs"];
         outs = runningDynamic["RepertoireOutputs"];
         attDec = runningDynamic["AttractorsDec"];
         ucInputProbVector = runningDynamic["UCInputVectorProbability"];
         misAttractoresProb = runningDynamic["CompleteAttractorProbVector"];
         basinsOfAttractionGraph = Graph[buildGraphBADecimalFromBinaryInOut[ins, outs]["EdgesList"], VertexLabels -> "Name", ImageSize -> Large, EdgeStyle -> Arrowheads[0.01]];
         nodosAttractores = Subgraph[basinsOfAttractionGraph, attDec];
         boa = HighlightGraph[basinsOfAttractionGraph, attDec, GraphHighlightStyle -> "Thick"];
         cs = Part[runningDynamic["RepertoireInputs"], 1];
         miGrapho = connMatrix2EdgeList[oneConnMatrix]["EdgeList"];
         ta = Table[Graph[miGrapho, VertexLabels -> "Name", ImageSize -> Medium, EdgeStyle -> Arrowheads[0.05]], {u, 1, 1, 1}];
         att = Table[boa, {o, 1, 1, 1}];
         Print[ta];
         Print[att];
         ce = ConnectedComponents[Graph[miGrapho]];
         mainComplex =  Extract[ce, Flatten[Position[ce, Max[_?(Length[#] > 1 &)]]]];
         (*Print["Connection Matrix: "<> ToString[oneConnMatrix] ];
         Print["DYNAMIC: "<> ToString[wholeDynamic]];
         Print["Main Complex: "<> ToString[mainComplex]];*)
         <|"MainComplex" -> mainComplex, 
          "CompleteConnMatrix" -> oneConnMatrix, 
          "SysDynamic" -> randomDynamic, 
          "Grapho" -> Graph[miGrapho],
          "Inputs"-> ins,
          "Outputs" -> outs
          |>
     ];

(*Extracts a submatrix from matrix *)
extractSubMatrix[cm_, wholeDynamic_, subSys_] :=
    Module[ {allNodes, colsToRemove, submatrix, oneRow, newRow, uu, newDynamic},
        allNodes = Range[Length[cm]];
        colsToRemove = Partition[Flatten[Complement[allNodes, subSys]], 1];
        submatrix = List[];
        newDynamic = Delete[wholeDynamic, colsToRemove];
        
        (*Print["number or rows to remove: "<> ToString[numberRows]];
        Print["Columns to remove: "<> ToString[colsToRemove]];
        Print["New Dynamica: "<> ToString[newDynamic]];*)
        For[uu = 1, uu <= Length[subSys], uu++,
         oneRow = Part[cm, subSys[[uu]]];
         newRow = Delete[oneRow, colsToRemove];
         AppendTo[submatrix, newRow];
         ];
        <|"Submatrix" -> submatrix, "SubDynamic" -> newDynamic|>
    ];

(*--------------------------------------------
Function from Hector Zenil.
It gets the ith subgraph of a graph. m edges -> 2^(m-1) subgraphs
---------------------------------------------*) 
   
IthEdgeInducedSubgraph[g_, i_] := 
  With[{s = EdgeList[g]}, 
   Graph[Extract[s, Position[IntegerDigits[i, 2, Length[s]], 1]], 
    VertexLabels -> "Name"]];
    
vertexOfAllconnectedSubgraphs[g_] :=
    Module[ {noEdges,v,t,ww},
        noEdges = Length[EdgeList[g]];
        v = List /@ Sort[VertexList[g]];
        t = DeleteDuplicates[
          Table[If[ ConnectedGraphQ[IthEdgeInducedSubgraph[g, ww]],
                    VertexList[IthEdgeInducedSubgraph[g, ww]]
                ,Null], {ww, 1, 2^(noEdges - 1), 1}] /. Null -> Sequence[]];
        
        <|"VertexOfAllConnectedSubgraphs"-> Union[t, v]|>
    ];

(*
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
===========================================================
*)


(* Returns all inputs of length x to a gate_ that produce the output res_

Example:  all inputs of length 3 that returns 1 given a gate OR

findInputsProducingOutput["OR", 3, 1]
Out: {{1, 0, 0}, {0, 1, 0}, {1, 1, 0}, {0, 0, 1}, {1, 0, 1}, {0, 1, 1}, {1, 1, 1}}
*)

findInputsProducingOutput[gate_, length_, res_] := 
    (Which[
    	   (* Its an exhaustive search of all possible tuples that fulfill the output condition*)
    	   gate=="XOR",Cases[Reverse[Reverse[#] & /@ Tuples[{1, 0}, length]], x_ /; ((Xor @@ x /. Thread[{1 -> True, 0 -> False}]) /. Thread[{True -> 1, False -> 0}]) == res],
    	   gate=="OR",Cases[Reverse[Reverse[#] & /@ Tuples[{1, 0}, length]], x_ /; ((Or @@ x /. Thread[{1 -> True, 0 -> False}]) /. Thread[{True -> 1, False -> 0}]) == res],
    	   gate=="AND",Cases[Reverse[Reverse[#] & /@ Tuples[{1, 0}, length]], x_ /; ((And @@ x /. Thread[{1 -> True, 0 -> False}]) /. Thread[{True -> 1, False -> 0}]) == res],
    	   gate=="MAJORITY",Cases[Reverse[Reverse[#] & /@ Tuples[{1, 0}, length]], x_ /; (myMajority[x]) == 1]
    	   	
        ]
    );
    
    

(* Power element-wise. 
1. It creates a list of 2s of leng[bin].
2. Each 2 in the list of (1) is powered-wise by the values in "pow" list
3. Apply binMask to sum

Example:
powering[{1, 0, 1}, {1, 2, 3}]
out:= 10

1. Create {2, 2, 2}  -> list of 2's of length[{1,0,1}
2. Power bases list by power element-wise
   2^1=2
   2^2=4
   2^3=8
3. Apply mask to results in (2)
   2*1 + 4*0 + 8*1 = 10 
*)
powering = Function[{binMask, pow}, Total[MapThread[Times, {MapThread[Power, {ConstantArray[2, Length[binMask]], pow}],binMask}]]];


(* Applies powering function to a list of lists *)
poweringArray[pows_, binArray_] := (Return[Table[powering[Part[binArray, s], pows], {s, 1, Length[binArray],1}]]);


(* For a list of indexed inputs and a gate
returns all inputs that generate a desired ouput

Example: input indexed = {1,8} and gate = "OR", returns all inputs that
generate out=1 and its decimal representation given the indexes.

inIdxProducingOutsToDecimal[{1, 8}, "OR", 1]
out := <|"Decimal" -> {1, 128, 129}, "Binary" -> {{1, 0}, {0, 1}, {1, 1}}|>

fon indexes = {1,8} the input {1, 0} in decimal is 1 because {2^0, 2^7} = {1, 128}
{1,28} masked by {1,0} = {1*1, 28*0} = 1+0 = 1  

NOTE: STILL EXHAUSTIVE SEARCH FOR GET INPUTS THAT GIVES CERTAIN OUTPUT

*)
inIdxProducingOutsToDecimal[indxInputs_, gate_, outWated_]  :=
    Module[ {repertF},
    
    (* Exhaustive search for all possible inputs that generate an output*)
    repertF = findInputsProducingOutput[gate, Length[indxInputs], outWated];
    <|"Decimal"-> poweringArray[indxInputs-1, repertF],
      "Binary" -> repertF
    |>
    ];



(*given two nodes and its inputs, it computes patters of inputs for both
nodes that results in definited outputs

*)
(*Usage Example:
cr2 = combineInsIdxProducingOuts[{1, 3, 5, 6}, "OR", 1, {1, 5, 7, 3}, "AND", 1]

<|"Combination" -> {{1, 0, 0, 0, 0}, {1, 0, 0, 0, 1}, {0, 1, 0, 0, 0},
                    {0, 1, 0, 0, 1}, {1, 1, 0, 0, 0}, {1, 1, 0, 0, 1}, 
                    {0, 0, 1, 0, 0}, {0, 0, 1, 0, 1}, {1, 0, 1, 0, 0},
                    {1, 0, 1, 0, 1}, {0, 1, 1, 0, 0}, {0, 1, 1, 0, 1},
                    {1, 1, 1, 0, 0}, {1, 1, 1, 0, 1}, {0, 0, 0, 1, 0},
                    {0, 0, 0, 1, 1}, {1, 0, 0, 1, 0}, {1, 0, 0, 1, 1},
                    {0, 1, 0, 1, 0}, {0, 1, 0, 1, 1}, {1, 1, 0, 1, 0}, 
                    {1, 1, 0, 1, 1}, {0, 0, 1, 1, 0}, {0, 0, 1, 1, 1},
                    {1, 0, 1, 1, 0}, {1, 0, 1, 1, 1}, {0, 1, 1, 1, 0},
                    {0, 1, 1, 1, 1}, {1, 1, 1, 1, 0}, {1, 1, 1, 1, 1}},
  "Filtered" -> {{1, 1, 1, 0, 1}, {1, 1, 1, 1, 1}}, 
 "jn" -> {1, 3, 5, 6, 7}, 
 "nn" -> {1, 2, 3, 4, 5}, 
 "DecRep" -> {85, 117}
 |>
------*)
combineInsIdxProducingOuts[inputsF_, dynF_, subStateF_, inputsS_, dynS_, subStateS_] :=

    Module[ {common, repertF, repertS, joinedReperts, filtered,joinedNames,newNames,poss,colsToEvaluate},
        common = Intersection[inputsF, inputsS];
        joinedNames = DeleteDuplicates[Join[inputsF, inputsS]];
        newNames = Range[Length[joinedNames]];
        poss = Flatten[Position[joinedNames, Alternatives @@ inputsS]];
        colsToEvaluate = Part[newNames, poss];
        
        (* Performs the exhaustive search for inputs that give desired output for first series of nodes*)
        repertF = findInputsProducingOutput[dynF, Length[inputsF], subStateF];
        repertS = Reverse[Reverse[#] & /@ Tuples[{1, 0}, Length[inputsS] - Length[common]]];
        
        
        If[ ToString[repertF[[1]][[0]]] != "List", repertF = List[repertF]];
        If[ ToString[repertS[[1]][[0]]] != "List", repertS = List[repertS] ];
        
        (* the all nodes in first now combines with rest of set of second inputs*)
        joinedReperts = Flatten[#] & /@ Tuples[{repertF, repertS}];
        
        (* filter for condition of the second set of inputs*)        
        filtered = 
         Which[
         	dynS == "XOR",Cases[joinedReperts,x_ /; ((Xor @@ x[[colsToEvaluate]] /.Thread[{1 -> True, 0 -> False}]) /.Thread[{True -> 1, False -> 0}]) == subStateS],
            dynS == "OR", Cases[joinedReperts,x_ /; ((Or @@ x[[colsToEvaluate]] /. Thread[{1 -> True, 0 -> False}]) /.Thread[{True -> 1, False -> 0}]) == subStateS],
            dynS == "AND",Cases[joinedReperts,x_ /; ((And @@ x[[colsToEvaluate]] /.Thread[{1 -> True, 0 -> False}]) /.Thread[{True -> 1, False -> 0}]) == subStateS],
            dynS == "MAJORITY",Cases[joinedReperts,x_ /; (myMajority[ x[[colsToEvaluate]] ]) == subStateS]
          ];
        
        <|"Combination" -> joinedReperts, 
        "Filtered" -> filtered, 
        "jn"->joinedNames, 
        "nn"-> newNames,
        "DecRep"-> poweringArray[joinedNames-1,filtered]|>
    ];


v2[inputsF_, dynF_, subStateF_, inputsS_, dynS_, subStateS_] :=
Module[{common, repertF, repertS, joinedReperts, filtered, joinedNames, newNames, poss, colsToEvaluate},
    (* Find common elements between inputsF and inputsS *)
    common = Intersection[inputsF, inputsS];

    (* Combine inputsF and inputsS, removing duplicates to get unique node IDs *)
    joinedNames = DeleteDuplicates[Join[inputsF, inputsS]];

    (* Create sequential indices for the unique nodes, e.g., {1, 2, ..., n} *)
    newNames = Range[Length[joinedNames]];

    (* Find positions of inputsS in joinedNames using pattern matching *)
    poss = Flatten[Position[joinedNames, Alternatives @@ inputsS]];

    (* Extract newNames indices corresponding to inputsS positions *)
    colsToEvaluate = newNames[[poss]];

    (* Generate combinations for first system that satisfy dynF and subStateF *)
    repertF = findInputsProducingOutput[dynF, Length[inputsF], subStateF];

    (* Generate all binary combinations for unique inputsS nodes (not in common) *)
    repertS = Tuples[{1, 0}, Length[inputsS] - Length[common]];

    (* Ensure repertF is a list of lists for consistent processing *)
    repertF = If[ListQ[repertF[[1]]], repertF, {repertF}];

    (* Ensure repertS is a list of lists for consistent processing *)
    repertS = If[ListQ[repertS[[1]]], repertS, {repertS}];

    (* Combine all pairs of repertF and repertS, flattening each pair into a single list *)
    joinedReperts = Flatten /@ Tuples[{repertF, repertS}];

    (* Filter combinations based on dynS rule applied to colsToEvaluate *)
    filtered = Which[
        dynS == "XOR",
        Cases[joinedReperts, x_ /; BitXor @@ x[[colsToEvaluate]] == subStateS],
        dynS == "OR",
        Cases[joinedReperts, x_ /; BitOr @@ x[[colsToEvaluate]] == subStateS],
        dynS == "AND",
        Cases[joinedReperts, x_ /; BitAnd @@ x[[colsToEvaluate]] == subStateS],
        dynS == "MAJORITY",
        Cases[joinedReperts, x_ /; myMajority[x[[colsToEvaluate]]] == subStateS]
    ];

    (* Return an Association with all results *)
    <|"Combination" -> joinedReperts,
      "Filtered" -> filtered,
      "jn" -> joinedNames,
      "nn" -> newNames,
      "DecRep" -> poweringArray[joinedNames - 1, filtered]|>
]



(*Adding a node to a combination. 
This is, when a repertoire of outputs exists as a result of previous combinations
and adding a new node is needed
*)
(*
inputsS = {1, 2};
dynS = "OR";
ssS = 1;
inputsF = {2, 3};
repertFF = {{1, 1}, {0, 1}, {1, 0}};
inIdxProducingOutsToDecimal[inputsS, dynS, ssS, inputsF, repertFF]
------------------------------------------------------------

<|"Combination" -> {{1, 1, 0}, {1, 1, 1}, {0, 1, 0}, {0, 1, 1}, {1, 0, 0}, {1, 0, 1}}, 
 "Filtered" -> {{1, 1, 0}, {1, 1, 1}, {0, 1, 1}, {1, 0, 0}, {1, 0, 1}}, 
 "jn" -> {2, 3, 1}, "nn" -> {1, 2, 3}, 
 "DecRep" -> {6, 7, 5, 2, 3}|>
*)
inIdxProducingOutsToDecimal[inputsS_,dynS_, subStateS_,inputsF_,repertFF_]  :=
    Module[ {common, repertS, joinedReperts, filtered, repertF,joinedNames,newNames,poss,colsToEvaluate},

        common = Intersection[inputsF, inputsS];
        joinedNames = DeleteDuplicates[Join[inputsF, inputsS]];
        newNames = Range[Length[joinedNames]];

        poss = Flatten[Position[joinedNames, Alternatives @@ inputsS]];
        colsToEvaluate = Part[newNames, poss];
        
        repertF=repertFF;
        
        (*Of course,  repertFF/repertF cannot be an empty set*)
        (*If[Length[repertF]===0,repertF = findInputsProducingOutput[dynF, Length[inputsF], subStateF]];*)
        
        
        repertS = Reverse[Reverse[#] & /@ Tuples[{1, 0}, Length[inputsS] - Length[common]]];
        
        If[ ToString[repertF[[1]][[0]]] != "List", repertF = List[repertF]];
        If[ ToString[repertS[[1]][[0]]] != "List", repertS = List[repertS] ];
        
        joinedReperts = Flatten[#] & /@ Tuples[{repertF, repertS}];
        
        (*toEvaluate = joinedReperts[[All, colsToEvaluate]];*)
        
        filtered = 
         Which[dynS == "XOR", Cases[joinedReperts,x_ /; ((Xor @@ x[[colsToEvaluate]] /.Thread[{1 -> True, 0 -> False}]) /.Thread[{True -> 1, False -> 0}]) == subStateS],
               dynS == "OR",  Cases[joinedReperts,x_ /; ((Or @@ x[[colsToEvaluate]] /. Thread[{1 -> True, 0 -> False}]) /.Thread[{True -> 1, False -> 0}]) == subStateS],
               dynS == "AND", Cases[joinedReperts,x_ /; ((And @@ x[[colsToEvaluate]] /.Thread[{1 -> True, 0 -> False}]) /.Thread[{True -> 1, False -> 0}]) == subStateS],
               dynS == "MAJORITY", Cases[joinedReperts,x_ /; (myMajority[ x[[colsToEvaluate]] ]) == subStateS]
          ];
        
        
        
        <|"Combination" -> joinedReperts, "Filtered" -> filtered, "jn"->joinedNames, "nn"-> newNames,
        "DecRep"-> poweringArray[joinedNames-1,filtered]|>
    ];
    
(*retunrs list of odd numbers from 0 to a limit*)    
odding[x_] := 
Module[{a,le},
   a = Range[x];
   le = Length@a;
   Return[a[[1 ;; Length@a ;; 2]]];
   ];
(*returns list of even numbres from 0 to a limit*)
evening[x_] := 
Module[{a,le},
   a = Range[x];
   le = Length@a;
   Return[a[[2 ;; Length@a ;; 2]]];
   ];

(*
It looks positions of a specific pattern in input repertoire.
Positions are expressed as indexes
    1|2|3|
	------
1	0|0|0
-	1|0|0
2	0|1|0
-	1|1|0
3	0|0|1
-	1|0|1
4	0|1|1
-	1|1|1

node 1:  limit / powered = repetitions
         (2^3)/2^(1-1)
         8  / 1 = 8 repetitions of 0s or 1s, this is (2^Length[cm])/2^(node-1).
         longi = limit/repetitions = 8/8=1 -> repetitions must be of length of 1
         odding until limit (8) -> {1,3,5,7}. This is, in this locations there is series of 1s of 1 size.
         
node 2:  limit / powered = repetitions
         (2^3)/2^(2-1)
         8  / 2 = 4 repetitions of 0s or 1s, this is (2^Length[cm])/2^(node-1).
         longi = limit/repetitions = 8/4=2 -> repetitions must be of length of 2
         odding until limit (8) -> {1,3}. This is, in this locations there is series of 1s of 1 size.

*)
findPattInInputs[nodes_, wantedPatt_, sizeCM_] := 
Module[
(*example
findPattInInputs[{1, 2, 3, 4, 5}, {0, 0, 0, 0, 0}, 16]
Note: First element has index 0.
*)
   {newNodes, limit, oneNode, outputExpected, powered, repetitions, 
    longi, serie, decLocations, found, sortNodes, le, ass,e, 
    newNodesAss, newPatts},
   
   ass = Thread[nodes -> wantedPatt];
   If[Length[ass]>1, 
   		newNodesAss = KeySortBy[ass, Minus]
   		,
   		newNodesAss=ass
   ];
   newNodes = Keys[newNodesAss];
   newPatts = Values[newNodesAss];
   
   If[Length[nodes]>1, 
   		sortNodes= Sort[nodes]
   		,
   		sortNodes=nodes
   	];
   limit = 2^sizeCM;
   decLocations = List[];
   
   (* begin ----------------*)
   (*Print["Limit: " <>ToString[limit]];
   Print["Association nodes outputs: "<> ToString[ass]];
   Print["New nodes: " <> ToString[newNodes]];
   Print["New Patts: "<> ToString[newPatts]];*)
   (* 
   end    ----------------*)
   If [Length[nodes]>1,
	   For[le = 1, le <= Length[nodes], le++,
	    
	    	(* target node *)
		    oneNode = Part[newNodes, le];
		    (* wanted ouput 0/1 *) 
		    outputExpected = Part[newPatts, le];
		    (* Length of the consecutive 0s/1s *)
		    powered = 2^(oneNode - 1);
		    (* How many sequences of consecutive digits fits in all repertoire*)
		    repetitions = limit/powered;
		    (* synonimous of powered*)
		    longi = limit/repetitions;
		    
		    (*0s->odds, 1s->evens*)
		    (* create list of pivot indexes, where sequences begins*)
		    If[outputExpected === 1, serie = evening[repetitions], 
		     serie = odding[repetitions]];
		    
		    (* Create the list of indexes using pivots
		    A sequence has lenght "powered" or "longi", then each sequence ends
		    at (powered * currentPivot) and starts at (powered*currentPivot)-longi + 1.
		    As they are consecutive indexes, goes one by one. 
		    *)
		    found = 
		     Flatten[Table[
		       Range[((powered*Part[serie, e]) - longi) + 1, 
		        powered*Part[serie, e]], {e, 1, Length[serie], 1}]];
		    	    
		   	(* As goes node by node and its appending "found" indexes to decLocations
		   	it makes intersection between "found" indexes to fulfill conditions for all
		   	appending "found" indexes. 
		   	*)
		    If[Length[decLocations] === 0, decLocations = found, 
		     decLocations = Intersection[decLocations, found]];
		    
		    (* begin -----------------*)
		    (*Print["node: "<>ToString[
		    oneNode]];
		    Print["expectedOutput: "<>ToString[outputExpected]];
		    Print["Powered = length: "<> ToString[powered]];
		    Print["How many times fits in limit (repetitions): "<> ToString[
		    repetitions]];
		    Print["Serie (multiples): "<>ToString[serie]];
		    Print["found locations: "<> ToString[found]];
		    Print["Locations: "<> ToString[decLocations]];
		    Print["--------------------------"]*)
		    (* end   -----------------*)
	    ];
   , 
    
		    oneNode = newNodes;
		    outputExpected = newPatts;
		    
		    powered = 2^(oneNode - 1);
		    repetitions = limit/powered;
		    longi = limit/repetitions;
		    
		    (*0s->odds, 1s->evens*)
		    If[outputExpected ==={1}, 
		    	serie = Flatten[evening[FromDigits[repetitions]]],
		    	serie = Flatten[odding[FromDigits[repetitions]]]
		    ];
		    
		    found = 
		     Flatten[Table[Range[((powered*Part[serie, e]) - longi) + 1, powered*Part[serie, e]], 
		     	{e, 1, Length[serie], 1}]];
		    
		    
		    If[Length[decLocations] === 0, decLocations = found, 
		     decLocations = Intersection[decLocations, found]];
		    
		    (* begin -----------------*)
		    (*Print["node: "<>ToString[
		    oneNode]];
		    Print["expectedOutput: "<>ToString[outputExpected]];
		    Print["Powered = length: "<> ToString[powered]];
		    Print["How many times fits in limit (repetitions): "<> ToString[
		    repetitions]];
		    Print["Serie (multiples): "<>ToString[serie]];
		    Print["found locations: "<> ToString[found]];
		    Print["Locations: "<> ToString[decLocations]];
		    Print["--------------------------"]*)
		    (* 
	    end   -----------------*)
	    
   ];
   
   <|"Locations" -> decLocations|>
   ];
   
   
(* Function to find indices in the input repertoire where nodes match a pattern *)
findPatternIndices[nodes_, wantedPatt_, sizeCM_] := Module[
  {n, m, nodeIndices, pattern, limit, locations, i, ki, pi, period, numSequences, pivots, indices},
  
  (* Initialize parameters *)
  n = sizeCM; (* Number of nodes *)
  m = Length[nodes]; (* Number of nodes to check *)
  nodeIndices = nodes; (* 1-based indexing *)
  pattern = wantedPatt; (* Desired pattern *)
  limit = 2^n; (* Total rows in input repertoire *)
  locations = {}; (* Matching indices *)
  
  (* Validate inputs *)
  If[Length[nodes] != Length[wantedPatt], 
    Return[<|"Locations" -> {}, "Error" -> "Nodes and pattern length mismatch"|>]];
  If[Or @@ (nodeIndices < 1 || nodeIndices > n), 
    Return[<|"Locations" -> {}, "Error" -> "Invalid node indices"|>]];
  If[!SubsetQ[{0, 1}, pattern], 
    Return[<|"Locations" -> {}, "Error" -> "Pattern must contain only 0s and 1s"|>]];
  
  (* Process each node *)
  Do[
    ki = nodeIndices[[i]]; (* Node index (1-based) *)
    pi = pattern[[i]]; (* Desired bit value *)
    
    (* Calculate sequence length and number of sequences *)
    period = 2^(ki - 1); (* Length of consecutive 0s or 1s *)
    numSequences = limit / period; (* Number of sequences *)
    
    (* Generate pivot indices *)
    pivots = If[pi == 1,
      Range[1, numSequences - 1, 2], (* Odd indices for 1s: 1, 3, 5, ... *)
      Range[0, numSequences - 2, 2]  (* Even indices for 0s: 0, 2, 4, ... *)
    ];
    
    (* Compute indices for this node *)
    indices = Flatten[
      Table[
        Range[p * period + 1, (p + 1) * period], (* Indices from start to end *)
        {p, pivots}
      ]
    ];
    
    (* Intersect with previous results *)
    locations = If[locations === {}, indices, Intersection[locations, indices]],
    {i, 1, m}
  ];
  
  (* Return sorted 1-based indices *)
  <|"Locations" -> Sort[locations]|>
];
   
   
(* Function to compute indices where an AND node's output is 1 using the formula J_k = P + 1 + Δ_nc *)
findANDIndicesFormula[node_, cm_, dyn_, n_] := Module[
  {inputs, pivot, powC, decC, powNC, numNC, deltaNCValues, resultIndices, j},
  
  (* Determine inputs to the node from connectivity matrix *)
  inputs = Position[cm[[node]], 1][[All, 1]];
  
  (* Verify the node uses AND function *)
  If[dyn[[node]] != "AND", 
    Return[<|"Node" -> node, "Error" -> "Node does not use AND function"|>, Module]
  ];
  
  (* Calculate power and decimal values for connected nodes *)
  powC = inputs - 1;
  decC = 2^powC;
  pivot = Total[decC]; (* P = sum of dec_c *)
  
  (* Calculate power values for disconnected nodes *)
  powNC = Complement[Range[n] - 1, powC];
  numNC = Length[powNC]; (* Number of disconnected nodes *)
  
  (* Generate all possible Δ_nc values (offsets from disconnected nodes) *)
  deltaNCValues = Flatten[
    Table[
      Sum[v[[i]] * 2^powNC[[i]], {i, 1, numNC}],
      {v, Tuples[{0, 1}, numNC]}
    ]
  ];
  
  (* Compute indices using J_k = P + 1 + Δ_nc *)
  resultIndices = pivot + 1 + deltaNCValues;
  
  (* Filter indices to ensure they are within bounds and meet AND condition implicitly via pivot *)
  resultIndices = Select[resultIndices, # <= 2^n &];
  
  (* Return result with node, pivot, and indices *)
  <|"Node" -> node, "Pivot" -> pivot, "Locations" -> Sort[resultIndices]|>
];



   
(*
In[31]:= dividingList[{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}, 3]
Out[31]= <|"Divisions" -> {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}, {10}}|>
*)
 dividingList[list_, partSize_] := Module[
   {divi, entire, frac, groups,e},
   
   
   divi = Length[list]/partSize;
   entire = IntegerPart[divi];
   frac = FractionalPart[divi];
   
   
   groups = 
    Table[Take[list, {((partSize*e) - partSize) + 1, partSize*e}], {e,
       1, entire, 1}];
   
   If[frac > 0, 
    AppendTo[groups, Take[list, (partSize*entire) - Length[list]]]];
   
   <|"Divisions" -> groups|>
   
   ];

onPossibleBehaviour[mechanism_, substate_, dynVector_, cm_]:=
Module[
	{res},
	
	res=findIndexesOfOutputs4Mechanism[mechanism, substate, dynVector, cm];
	<|"DecimalRepertoire"-> res["DecimalRepertoire"],
      "Sumandos"-> res["Sumandos"]|>
]

(*given a substate for a mechanism, it find where that substate patter is in outputs*)
findIndexesOfOutputs4Mechanism[mechanism_, substate_, dynVector_, cm_] := 
Module[
	(*
cm16 = {{0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0}, 
        {0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1},
        {0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0},
        {1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0},
        {0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0}, 
        {0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0},
        {0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1},
        {1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0},
        {0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0}, 
        {1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0}, 
        {0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1},
        {0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0},
        {0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0},
        {0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0},
        {1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0},
        {0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0}};

dyn16 = {"AND", "OR", "OR", "AND", "OR", "OR", "AND", "OR", "OR", 
   "AND", "OR", "OR", "AND", "AND", "OR", "AND"};

findIndexesOfOutputs4Mechanism[{5, 7, 9, 10}, {0, 0, 1, 0}, dyn16, cm16]

*)
   {longi, inputs, inputs2, repert, joinedNames, repertoire, hh, sumandos,sum},
   
   longi = Length[mechanism];
   
   If[longi === 1,  	
	   	(*obtains nodes that send signals to this node*)
	    inputs = getIndexesOfNodesInputs[mechanism[[1]], cm];
	    repert = combiningRepersWithSharedInputs[inputs, dynVector[[mechanism[[1]]]], substate[[1]]];
	    repertoire=repert["Filtered"];
	    joinedNames = inputs;
   ];
   
   If[longi === 2,
	    inputs = getIndexesOfNodesInputs[mechanism[[1]], cm];
	    inputs2 = getIndexesOfNodesInputs[mechanism[[2]], cm];
	    repert = combiningRepersWithSharedInputs[inputs, dynVector[[mechanism[[1]]]], substate[[1]],
	    	                                     inputs2, dynVector[[mechanism[[2]]]], substate[[2]]];
	    repertoire=repert["Filtered"];
	    joinedNames = repert["jn"];
	    
	    (* begin ----------------------*)
	    (*Print["In processing 2 nodes"];
	    Print["Repertoire: "<> ToString[repertoire]];*)
	    (* end   ----------------------*)
    ];
   
   If[longi > 2,
    
	    inputs = getIndexesOfNodesInputs[mechanism[[1]], cm];
	    inputs2 = getIndexesOfNodesInputs[mechanism[[2]], cm];
	    
	    (*begin --------------------------"*)
	    (*Print["Im processing more than 2 nodes"];
	    Print["Inputs1: "<>ToString[inputs]];
	    Print["inputs2: "<>ToString[inputs2]];*)
	    (*end --------------------------"*)
	    
	    repert = combiningRepersWithSharedInputs[inputs, dynVector[[mechanism[[1]]]], substate[[1]], 
	    	                                     inputs2, dynVector[[mechanism[[2]]]], substate[[2]]];
	    joinedNames = repert["jn"];
	    repertoire = repert["Filtered"];
	    
	    (*begin --------------------------"*)
	    (*Print["joinedNames: "<>
	    ToString[joinedNames]];
	    Print["Repertoire: "<>ToString[repertoire]];
	    Print["Decimal: "<> ToString[repert[
	    "DecRep"]]];*)
	    (*end --------------------------"*)
	    
	    For[hh = 3, hh <= longi, hh++,
		     
		     repertoire = repert["Filtered"];
		     If[Length[repertoire]===0, Break[]];
		     
		     inputs = getIndexesOfNodesInputs[mechanism[[hh]], cm];
		     repert = combiningRepersWithSharedInputs[inputs, dynVector[[mechanism[[hh]]]], substate[[hh]], joinedNames, repertoire];
		     joinedNames = repert["jn"];
		     
		     
		     (*begin --------------------------"*)
		     (*Print["Inputs1 "<>
		     ToString[inputs]];
		     Print["joinedNames: "<>ToString[joinedNames]];
		     Print[Sort[repert["DecRep"]]];
		     Print[Length[repert["DecRep"]]];
		     Print["Repertoire: "<>ToString[repertoire]];
		     Print["Decimal: "<> ToString[Sort[repert["DecRep"]]]];*)
		     (*end --------------------------"*)
	     
	     ];
    
    ];
    
    If[Length[repertoire]>0,
    	sum=2^#&/@((Complement[Range[Length[cm]],joinedNames])-1);    
    	(*Next row computes Total of each subset in sum list*)
    	sumandos=Total[#] & /@ Distribute[{{}, {#}} & /@ sum , List, List, List, Union] // Sort;
    , sumandos={}];
    
    <|
       (*"Repertoire" ->repertoire,*)
       "AllInputNodes"-> joinedNames,
       "DecimalRepertoire"-> repert["DecRep"],
       "Sumandos"-> sumandos
    
    |>
   
   ];
   
   
   
 (* it finds attractors for a partition *)  
calculatingAttractors4PartitionInSerie[partition_, dynVector_, cm_] := 
  Module[{decimalRep,sumandos,patt1,patt2, noDecRep, noSumandos,res,x,limit,noAttracFound},
   (*
   Example --------
    calculatingAttractors4Partition[{1, 2, 3, 4, 5}, {"AND", "OR", "OR", "AND", "OR"}, cm16]
   ---------------- 
    *)   
   
   decimalRep = Association[{}];
   sumandos = Association[{}];
   limit = 2^(Length[partition])-1;
   
   noAttracFound=0;
   
   (*allPossiblePatt = allPosibleInputsReverse[Length[partition]];*)
   For[x=0,x<=(limit/2),x++,
	   	patt1=Reverse[IntegerDigits[x, 2, Length[partition]]];
	   	patt2=Reverse[IntegerDigits[limit-x, 2, Length[partition]]];
	   	
	   	res = findIndexesOfOutputs4Mechanism[partition, patt1, dynVector, cm];
	   	noDecRep=Length[res["DecimalRepertoire"]];
	   	noSumandos=Length[res["Sumandos"]];

	   	noAttracFound=noAttracFound+(noDecRep*noSumandos);
	   	(*Print[ToString[patt1]<>": "<>ToString[noAttracFound]];*)
	   	
	   	If[Length[res["DecimalRepertoire"]]>0,
	    	AppendTo[decimalRep, patt1 -> res["DecimalRepertoire"]];
	    	AppendTo[sumandos, patt1 -> res["Sumandos"]];
	    ];
	    
	    res = findIndexesOfOutputs4Mechanism[partition, patt2, dynVector, cm];
	   	noDecRep=Length[res["DecimalRepertoire"]];
	   	noSumandos=Length[res["Sumandos"]];
	   	
		noAttracFound=noAttracFound+(noDecRep*noSumandos);
		(*Print[ToString[patt2]<>": "<>ToString[noAttracFound]];*)
	   	
	   	If[Length[res["DecimalRepertoire"]]>0,
	    	AppendTo[decimalRep, patt2 -> res["DecimalRepertoire"]];
	    	AppendTo[sumandos, patt2 -> res["Sumandos"]];
    	 ];
    	 
    	 If[noAttracFound>=2^Length[cm], Break[]];
    ];
      
   <|"AllDecimalRepresentations" -> decimalRep,
      "AllSumandos" -> sumandos
    |>
   
];

(*Divide system and calculate attractors in outputs for each division*)
calculatingPattsInDivisionsOfCM[cm_, dynVec_, divisionSize_] := 
Module[
   {nodes,divNodes,decimalRepertoires,divDyns,sumandos,ww,rr},
   
   nodes = Range[Length[cm]];
   divNodes = dividingList[nodes, divisionSize]["Divisions"];
   divDyns = dividingList[dynVec, divisionSize]["Divisions"];
   decimalRepertoires = List[];
   sumandos = List[];
   
   (* begin ----------------------*)
   (*Print["Nodes"<>ToString[nodes]];
   Print["DivNodes"<>ToString[divNodes]];
   Print["DivDyns"<>ToString[divDyns]];
   Print[Part[divNodes,1]];
   Print[Length[divNodes]];*)
   (* end ----------------------*)
   
   For[ww = 1, ww <= Length[divNodes], ww++,
    
    rr = calculatingAttractors4Partition[Part[divNodes, ww], 
      dynVec(*Part[divDyns, ww]*), cm];
    
    (* begin ----------------------*)
    (*Print["-----------------------"];
    Print["Nodes part "<>ToString[Part[divNodes,ww]]];
    Print["Dyns part: " <> ToString[Part[divDyns,ww]]];
    Print[rr["AllDecimalRepresentations"]];*)
     
    (*end ----------------------*)
    
    AppendTo[decimalRepertoires, rr["AllDecimalRepresentations"]];
    AppendTo[sumandos, rr["AllSumandos"]];
    
    ];
   
   <|
    "Locations" -> decimalRepertoires,
    "Sumandos" -> sumandos
    
    |>
   
   ];
   
   
givePlaces[locations_, sumandos_] := (unfoldLocationsAndSumandos[locations, sumandos]);

(*add sumandos to each location in locations set*)
unfoldLocationsAndSumandos[locations_, sumandos_] := 
(* Example-----
aa = {1, 2, 3, 4};
bb = {2, 3};
unfoldLocationsAndSumandos[aa, bb]
Out: {3, 4, 4, 5, 5, 6, 6, 7}
-------------------------------
*)
(Return[Sort[Flatten[Table[Part[locations, w] + sumandos, {w, 1, Length[locations],1}]]]]);

(*
aa = locations[[1]][{0, 0, 0, 0, 0, 0, 0, 0}]
bb = sumandos[[1]][{0, 0, 0, 0, 0, 0, 0, 0}]
cc = locations[[2]][{0, 0, 0, 0, 0, 0, 0, 0}]
dd = sumandos[[2]][{0, 0, 0, 0, 0, 0, 0, 0}]
joiningPatterns[{0, 0, 0, 0, 0, 0, 0, 0}, aa, bb, {0, 0, 0, 0, 0, 0, 0, 0}, cc, dd]
*)
joiningPatterns[key1_, locations1_, sumandos1_, key2_, locations2_,  sumandos2_] := Module[
   {s1, s2, found, shorterLocats, shorterSum, longLocats, longSum, i, oneSum, allLocations},
   
   s1 =  Length[locations1] + Length[sumandos1];
   s2 = Length[locations2] + Length[sumandos2];
   found = List[];
   
   If[s1 > s2, shorterLocats = locations2; shorterSum = sumandos2; 
    longLocats = locations1; longSum = sumandos1,
    shorterLocats = locations1; shorterSum = sumandos1; 
    longLocats = locations2; longSum = sumandos2
    ];
   
   allLocations = unfoldLocationsAndSumandos[shorterLocats, shorterSum];
   
   For[i = 1, i <= Length[longLocats], i++,
    oneSum = Part[longLocats, i] + longSum;
    AppendTo[found, Intersection[allLocations, oneSum]];
    ];
   
   If[Length[found]>0,found = (Sort[Flatten[found]])(*/. {} -> Sequence[]*),found=List[]];
   
   
   <|"NewKey" -> Join[key1, key2],
      "Locations" -> found
    |>
   
   ];
   
joiningPatterns[key1_, locations1_, key2_, locations2_, sumandos2_] := Module[
	{s1, s2, found, shorterLocats, shorterSum, longLocats,longSum, i, oneSum, allLocations},
   
   s1 = Length[locations1];
   s2 = Length[locations2] + Length[sumandos2];
   found = List[];
   shorterLocats = List[];
   shorterSum = List[];
   longLocats = List[];
   longSum = List[];
   
   If[s1 > s2,
    shorterLocats = locations2; shorterSum = sumandos2; 
    longLocats = locations1,
    shorterLocats = locations1; longLocats = locations2; 
    longSum = sumandos2
    ];
   
   If[Length[shorterSum] > 0,
    allLocations = 
     unfoldLocationsAndSumandos[shorterLocats, shorterSum],
    allLocations = shorterLocats
    ];
   
   (* begin ---------------------*)
   (*Print["Shorter locations"<>
   ToString[shorterLocats]];
   Print["Shorter sumandos"<>ToString[shorterSum]];
   Print["Longer locations"<>ToString[longLocats]];
   Print["Longer sumandos"<>ToString[longSum]];
   Print["After unfolding locatios + sumandos: ******"];
   Print["Unfolded locations" <>ToString[allLocations]];
   Print["Long sumandos: " <>ToString[Length[longSum]]];*)
   (* 
   end ---------------------*)
   
   If[Length[longSum] > 0,
    For[i = 1, i <= Length[longLocats], i++,
     oneSum = Part[longLocats, i] + longSum;
     AppendTo[found, Intersection[allLocations, oneSum]];
     ],
    AppendTo[found, Intersection[allLocations, longLocats]];
    ];
   
   If[Length[found] > 0,
    found = (Sort[Flatten[found]])(*/.{}\[Rule]Sequence[]*),
    found = List[]
    ];
   
   <|"NewKey" -> Join[key1, key2], "Locations" -> found|>];
   
   
   

calculatingAttractors[locationsPerDivision_, sumandosPerDivision_] :=
      Module[ {numDivisions, lpd, spd, newJoining, final, finalBin, allKeys1, allKeys2, 
        numKeys1, numKeys2, key1, oneKey1, key2, oneKey2, jp, co,ll,newJoiningAux},
(*
cm05 = {{0, 1, 1, 1, 1}, {1, 1, 1, 0, 0}, {1, 0, 0, 1, 0}, {1, 1, 0, 
    0, 0}, {0, 1, 1, 1, 0}};
dyn05 = {"AND", "AND", "OR", "AND", "OR"};

ff05 = calculatingPattsInDivisionsOfCM[cm05, dyn05, 2]
locations05 = ff05["Locations"];
sumandos05 = ff05["Sumandos"];
(*ByteCount[ff05]*)

cca05 = calculatingAttractors[locations05, sumandos05]

Run LengthEncode
out:  <|"AttractorsByPosition" -> <|{0, 0, 0, 0, 0} -> {0, 16}, {0, 0, 0, 0,
      1} -> {2, 4, 6, 18, 20, 22}, {0, 0, 1, 0, 0} -> {1, 17}, {0, 0, 
     1, 0, 1} -> {5, 8, 9, 10, 12, 13, 14, 21, 24, 25, 26, 28, 
     29}, {0, 0, 1, 1, 1} -> {3, 11, 19, 27}, {0, 1, 1, 1, 1} -> {7, 
     15, 23}|>|>

*)
          lpd = locationsPerDivision;
          spd = sumandosPerDivision;
          numDivisions = Length[lpd];
          newJoining = Association[{}];
          final = Association[{}];
          finalBin = Association[{}];
          
          
          (*the first two divisions are joined using keys, locations and sumandos,
          after that, are not used for first set of data. 
          Sumandos are used only for the second set of data*)
          allKeys1 = Keys[lpd[[1]]];
          allKeys2 = Keys[lpd[[2]]];
          numKeys1 = Length[allKeys1];
          numKeys2 = Length[allKeys2];
          
          For[key1 = 1, key1 <= numKeys1, key1++,
	           oneKey1 = Part[allKeys1, key1];
	
	           For[key2 = 1, key2 <= numKeys2, key2++,
	              oneKey2 = Part[allKeys2, key2];
	              jp = joiningPatterns[oneKey1, lpd[[1]][oneKey1],  spd[[1]][oneKey1], 
	              	                   oneKey2, lpd[[2]][oneKey2],  spd[[2]][oneKey2]];
	              	                   
	              (* begin ------------------*)
	              (*Print[ToString[oneKey1]<> ToString[oneKey2]];*)
	              (* end   ------------------*)
	              If[ Length[jp["Locations"]] > 0,
	                  AppendTo[newJoining, jp["NewKey"] -> jp["Locations"]];
	                  (* begin ---------------*)
	             	  (*Print[jp["NewKey"]];
	             	  Print["---------------------"];*)
	      		 	  (*  end ---------------*)
	      			];
	            ];
           
           ];
           
          lpd = Delete[lpd, {{1},{2}}];
          spd = Delete[spd, {{1},{2}}];
          
          co = 2;
          
          If[Length[lpd]>0,
	          While[Length[lpd] > 0,
		           
		           co = co + 1;
		           (* being ----------------*)
		           (*Print["Number of remining divisions: " <> ToString[Length[lpd]]];
		           Print["Processing now; " <> ToString[co] <> " ***************"];*)
		           (* end   ----------------*)
		           
		           (*here are not used sumandos for first set of data*)
		           allKeys1 = Keys[newJoining];
		           numKeys1 = Length[allKeys1];
		           allKeys2 = Keys[lpd[[1]]];
		           numKeys2 = Length[allKeys2];
		           newJoiningAux=Association[{}];
		           
		           For[key1 = 1, key1 <= numKeys1, key1++,
		            oneKey1 = Part[allKeys1, key1];
		            For[key2 = 1, key2 <= numKeys2, key2++,
		               oneKey2 = Part[allKeys2, key2];
		               
		              jp = joiningPatterns[oneKey1, newJoining[oneKey1], oneKey2, lpd[[1]][oneKey2],spd[[1]][oneKey2]];
		              
		              (* begin ---------------------*)
		               (*Print["   Processing keys: "];
		               Print["   "<>ToString[oneKey1]<> " + "<> ToString[oneKey2]];
		               Print["   Found in: "<> ToString[jp["Locations"]]];
		               Print["------------------"];*)
		               (* end   ---------------------*)
		               
		               
		               If[ Length[jp["Locations"]] >= 1,
		               	   ll=Length[lpd];
		                   If[ (*Length[lpd] > 1*)co != numDivisions,
		                       AppendTo[newJoiningAux, jp["NewKey"] -> jp["Locations"]],
		                       AppendTo[final, jp["NewKey"] -> jp["Locations"]]
		                     ];
		                    (* being --------------*)
		               		(*Print["----- WITHOUT SUMANDOS IN THE FIRST SET OF DATA"];  
		                   	Print[jp["NewKey"]];*)
		                   	(* end  --------------*)
		                 ];
		             ];
		            ];
		           newJoining = newJoiningAux;
		           lpd = Delete[lpd, 1];
		           spd = Delete[spd, 1];
	           ];
          ,final=newJoining];
          finalBin = final;
          
          (*attractors are converted to decimal in Phi format (reverse)*)
          final=KeySort[KeyMap[FromDigits[#, 2] &, KeyMap[Reverse, finalBin]]];

          <|
          "DecAttractorsByPosition" -> final,
          "BinAttractorsByPosition"-> finalBin
          |>
      ];
      
(*Run Length Coding/Decoding*)      
RunLengthEncode[x_List] := {First[#], Length[#]}& /@ Split[x];
RunLengthDecode[x_List] := (Flatten[Table[Table[Part[x, a][[1]], {b, 1, Part[x, a][[2]], 1}], {a, 1,Length[x], 1}]]);


(*encodes attractorsByPosition arrangements*)
runLengthEnconding[attractorsByPosition_] := Module[
   {abp, allKeys, size, empty, oneKey, prob, locations,a},
(*Given am association AttractorsByPosition in this way:
<|{bin_att1}->{List_of_positions_1},{bin_att2}->{List_of_positions_2}|>
it encodes it using run-Length encoding.
{prob,number_of_times},{prob2,number of times}

runLengthEnconding[atts16];
{{0.0000610352, 1}, {0.00012207, 1}, {0.0000610352, 1}, {0.00012207, 1},
 {0.0010376, 1}, {0.00134277, 1}, {0.0010376, 1}, {0.00134277,1}
}
*)   
   abp = attractorsByPosition;
   allKeys = Keys[abp];
   size = 2^(Length[First[allKeys]]);
   empty = Table[0, {a, 1, size, 1}];
   
   
   While[Length[allKeys] >= 1,
    oneKey = Part[allKeys, 1];
    allKeys = Delete[allKeys, 1];
    locations = abp[oneKey];
    
    prob = N[Length[locations]/size];
    empty = ReplacePart[empty, (Split[locations] + 1) -> prob];
    
    (* being --------------------*)
    (*Print["current Key: "<> 
    ToString[oneKey]];
    Print["locations: "<> ToString[locations]];
    Print["Probability: "<>ToString[prob]];
    Print["New values in empty array: "<>ToString[Extract[empty,Split[locations]]]];*)
    (*end -----------------------*)
    
    abp = Delete[abp, 1];
    ];
   empty = RunLengthEncode[empty];
   <|"Encoding" -> empty|>
   ];

(*
Compute past probability distribution with the size of the whole system.
But this makes sense just when mechanism is the whole system, or in unpartitioned case
this cannot be done when partitioned case.
-----------------------------------------------------------
cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};
cs03 = {1, 0, 0};
mecch = {1, 2};
subSt = {1, 0};
pur = {2, 3};
pastProbDistroWholeSysRef[mecch, subSt, pur, dyn03, cm03]

<|"ProbabilityDistribution" -> {0, 0, 0.25, 0.25, 0.125, 0.125, 0.125, 0.125}, 
 "ProbabilityDistrEncoded" -> {{0, 2}, {0.25, 2}, {0.125, 4}}|>
 -----------------------------------------------------------------
*)
pastProbDistroWholeSysRef[mechanism_, subState_, purview_, dynVector_, cm_] := Module[
   {sizeDistr, newDistr, locations, dec, sum, allLocations, prob, 
    allInputs, cc, uniqueInputs, probByInputPatt, r, oneUniqueInput, rr, oneInput, locs,
    timesOneInput, probabilidad,e},
   
   sizeDistr = Length[cm];
   newDistr = Table[0, {e, 1, 2^sizeDistr, 1}];
   
   (*looks in outputs the current substate for a mechanism and compute
   absolute probability*)
   locations = findIndexesOfOutputs4Mechanism[mechanism, subState, dynVector, cm];
   dec = locations["DecimalRepertoire"];
   sum = locations["Sumandos"];
   allLocations = unfoldLocationsAndSumandos[dec, sum];
   prob = N[1/Length[allLocations]];
   
   (* begin --------------------*)
   (*Print["All locations:" <> ToString[allLocations]];
   Print["Probability: " <> ToString[prob]];*)
   (*end -------------------------*)
   
   (*Extracts patterns in inputs for allLocations in outputs*)
   allInputs = 
    Table[Extract[Reverse[IntegerDigits[Part[allLocations, e], 2, sizeDistr]], Split[purview]],
    	{e, 1, Length[allLocations], 1}];
   
   (*returns relationship between key and number of times that it appers
   in allInputs*)
   (* 
   cc={k1->timesk1, k2->timesk2... };
   uniqueInputs=k1,k2...;
   *)
   
   (*counting inputs in order to know times per pattern*)
   cc = Counts[allInputs];
   uniqueInputs = Keys[cc];
   probByInputPatt = Association[{}];
   
   For[r = 1, r <= Length[allInputs], r++,
    	oneUniqueInput = Part[allInputs, r];
    	AppendTo[probByInputPatt, oneUniqueInput -> prob*cc[Flatten[oneUniqueInput]]];
    ];
    
    For[rr = 1, rr <= Length[uniqueInputs], rr++,
    	oneInput = Part[uniqueInputs, rr];
    	timesOneInput = cc[oneInput];
    
    	(*Print["-------------"];
    	Print["patt: "<>ToString[oneInput]<> " found in: "<> ToString[locs]];*)
    
    	(*re-scan inputs including unfolding locations in order to distribute
    	absolute probability*)
    	locs = findPattInInputs[purview, oneInput, sizeDistr]["Locations"];
    	(*If[Length[locs]>timesOneInput,
    		probabilidad = prob/Length[locs], 
    		probabilidad = prob
    	];*)
    	
    	probabilidad = probByInputPatt[oneInput]/Length[locs];
    	newDistr = ReplacePart[newDistr, Split[locs] -> probabilidad];
    ];
   
   <|
   "ProbabilityDistribution" -> newDistr,
   "ProbabilityDistrEncoded"-> RunLengthEncode[newDistr]
   |>
   ];


	
futureProbDistroWholeSysRef[mechanism_,substate_,purview_,cm_,dynVector_, unconsProbsByBit_]:= 
	                                
Module[{locs,binInputs,i,j,purviews,h,col,zeroReps,oneReps,numTotalElem,zeroProb,oneProb,
		newProbs,(*updatingSubVector,*)outputs, g, futCompleteDistr(*, newDistrib,e, att, positions, prob*)},
		
		(*Locations are ordinlas, then, number = (locations-1)*)
		locs = findPattInInputs[mechanism, substate, Length[cm]]["Locations"];
		binInputs = Table[Reverse[IntegerDigits[Part[locs, i] - 1, 2, Length[cm]]], {i,1, Length[locs], 1}];
		
		(*for each input, output is computed and purview extracted*)
		outputs = Table[calculateOneOutptuOfNetwork[Part[binInputs, g],cm,dynVector]["Output"] ,{g,1,Length[binInputs],1}];
		purviews = Table[Extract[Part[outputs, j], Split[purview]], {j, 1, Length[outputs], 1}];
		
		(* begin -------------*)
		(*Print["Locations (inputs) for substate: "<> ToString[locs]];
		Print["Outputs: "<> ToString[purviews]];*)
		(* end -------------*)
		
		newProbs = Association[{}];

		For[h = 1, h <= Length[purview], h++,
			  col = purviews[[All, h]];
			  zeroReps = Count[col, 0];
			  oneReps = Count[col, 1];
			  numTotalElem = Length[col];
			  If[zeroReps > 0, zeroProb = N[zeroReps/numTotalElem], zeroProb = 0];
			  If[oneReps > 0, oneProb = N[oneReps/numTotalElem], oneProb = 0];
			  AppendTo[newProbs, Part[purview, h] -> {zeroProb, oneProb}];
			  
			  (* begin ------------------*)
			  (*Print["--------------"];
			  Print["No Elements: " <> ToString[numTotalElem]];
			  Print["Column: " <> ToString[col]];
			  Print["Zeros number: " <> ToString[zeroReps] <> ". Prob: " <> ToString[zeroProb]];
			  Print["Ones number: " <> ToString[oneReps] <> ". Prob: " <> ToString[oneProb]];*)
			  (* end   ------------------*)
		  ];

		(*Print["NEW PROBABILITIES: "<> ToString[newProbs]];*)
		
		
		futCompleteDistr=unfoldProbDistrFromByBitProbDistr[unconsProbsByBit, newProbs]["UpdatedDistribution"];
		
		<|"ProbabilityDistribution"-> futCompleteDistr |>
		
		
	];




(*
Given a partition of system (mechanism) being in the current state,
this function calculate all possible past states reggarding a purview.
Then calculate the probability distribution

cm031 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn031 = {"OR", "AND", "XOR"};
parentPastProbDistro[{1}, {1}, {2, 3}, dyn031, cm031]

<|"ProbabilityDistribution" -> {0, 0.333333, 0.333333, 0.333333}, 
 "ProbabilityDistrEncoded" -> {{0, 1}, {0.333333, 3}}|>
*)
   
parentPastProbDistro[mechanism_, subState_, purview_, dynVector_, cm_] := Module[
   {sizeDistr, newDistr, locations, dec, sum, allLocations, prob, 
    allInputs, cc, uniqueInputs, probByInputPatt, r, onePatt,repetitions, oneUniqueInput,i},
   
   (*sizeDistr = Length[cm];*)
   (*size of new Distro = all possible binary patters of size of purview*)
   sizeDistr = Length[purview];
   newDistr = List[];
   
   (*it looks for pattern of current substate in outputs repertoire, the it computes
   absolute probability for number of coincidences*)
   locations = findIndexesOfOutputs4Mechanism[mechanism, subState, dynVector, cm];
   dec = locations["DecimalRepertoire"];
   sum = locations["Sumandos"];
   allLocations = unfoldLocationsAndSumandos[dec, sum];
      
   (* begin --------------------*)
   (*Print["All locations:" <> ToString[allLocations]];
   Print["Probability: " <> ToString[prob]];*)
   (*end -------------------------*)
   
   (*Extracts patterns in inputs for "allLocations" in outputs*)
   allInputs = 
    Table[Extract[Reverse[IntegerDigits[Part[allLocations, e], 2, Length[cm]]], Split[purview]],
    	{e, 1, Length[allLocations], 1}];
   
      
   (*counting all diff patterns in inputs for mecha in current state*)
   cc = Counts[allInputs];
   uniqueInputs = Keys[cc];
   (*prob = N[1/Length[uniqueInputs]];*)
   (*note: in parent level, prob depends on the absolute number
   of found patterns*)
   prob = N[1/Length[allInputs]];
   
   
   probByInputPatt = Association[{}];
   
   (*rescan inputs in order to finding all occurrences of possible patters
   that lead me to mecha in this current state*)
   For[i=1,i<= Length[uniqueInputs],i++,
   		oneUniqueInput = Part[uniqueInputs, i];
   		(*note: only in full sys computation input repertoire is reescanned and
   		prob divided between new repetitions found in reescan action*)
   		(*locs = findPattInInputs[purview, oneUniqueInput, Length[cm]]["Locations"];*)
   		(*probByInputPatt = AppendTo[probByInputPatt, oneUniqueInput-> (prob/Length[locs])*Length[locs]];*)
   		repetitions=cc[oneUniqueInput];
   		
   		probByInputPatt = AppendTo[probByInputPatt, oneUniqueInput-> prob*repetitions];
   ];
   
   For[r = 0, r < 2^sizeDistr, r++,
    	onePatt = Reverse[IntegerDigits[r,2,sizeDistr]];
    	If[KeyExistsQ[cc,onePatt], 
    		AppendTo[newDistr, probByInputPatt[Flatten[onePatt]]]
    		,
    		AppendTo[newDistr, 0]
    	];    	
    ];
    
       
   <|
   "ProbabilityDistribution" -> newDistr,
   "ProbabilityDistrEncoded"-> RunLengthEncode[newDistr]
   |>
];
   
   
(*----------------------------------
------------------------------------
------------------------------------
------------------------------------
*)
   


 Region Title 

partitionedPastProbDistro[parentMecha_, parentPur_, sysCS_, childMecha_, childPur_, sysDyn_, sysCm_]:= 
Module[
	{nodeSet4BitDstr,fullBitProbDistro,i,oneNode,childCS,locations,dec,sum,allLocations,
	allInputs,e,j,cc,distro,uniqueInputs, prob,probByInputPatt,oneUniqueInput,repetitions,pos,tempNames,
	assNewNames, nodes},
	
	(*bit prob distro for nodes that are in the parent purview, but not in the child purview
	is needed*)
	nodeSet4BitDstr = Sort[Complement[parentPur, childPur]];
	fullBitProbDistro = Association[{}];
	
	(*compute full bit distro for nodes out of child purview but into parent purview*)
	For[i=1, i<= Length[nodeSet4BitDstr], i++,
		oneNode = Part[nodeSet4BitDstr,i];
		(*it is not necesary to compute full bit prob distro in inputs. Always
		is the same: {0.5, 0.5}*)
		AppendTo[fullBitProbDistro,oneNode->{0.5,0.5}];
	];
	
	
	(*------------------ begin *)
	(*Print["Nodes for bit Distribution: "<> ToString[nodeSet4BitDstr]];
	Print["BitDistro: "];
	Print[fullBitProbDistro];*)
	(*------------------- end*)
	
	(*finding position of childMecha's state in outputs repertoire*)
	childCS = Extract[sysCS,Split[childMecha]];
	locations = findIndexesOfOutputs4Mechanism[childMecha, childCS, sysDyn, sysCm];
	dec = locations["DecimalRepertoire"];
	sum = locations["Sumandos"];
	allLocations = unfoldLocationsAndSumandos[dec, sum];
	
	(*computing inputs for locations found in last step*)
	allInputs = 
    Table[Extract[Reverse[IntegerDigits[Part[allLocations, e], 2, Length[sysCm]]], Split[childPur]],
    	{e, 1, Length[allLocations], 1}];
    
    
       (*counting all diff patterns in inputs for mecha in current state*)
   cc = Counts[allInputs];
   uniqueInputs = Keys[cc];
   (*prob = N[1/Length[uniqueInputs]];*)
   (*note: in parent level, prob depends on the absolute number
   of found patterns*)
   prob = N[1/Length[allInputs]];
   
   
   probByInputPatt = Association[{}];
   
   (*rescan inputs in order to finding all occurrences of possible patters
   that lead me to mecha in this current state*)
   For[i=1,i<= Length[uniqueInputs],i++,
   		oneUniqueInput = Part[uniqueInputs, i];
   		(*note: only in full sys computation inputs-repertoire is reescanned, then
   		prob divided between new found repetitions during reescaning*)
   		(*locs = findPattInInputs[purview, oneUniqueInput, Length[cm]]["Locations"];*)
   		(*probByInputPatt = AppendTo[probByInputPatt, oneUniqueInput-> (prob/Length[locs])*Length[locs]];*)
   		repetitions=cc[oneUniqueInput];
   		
   		probByInputPatt = AppendTo[probByInputPatt, oneUniqueInput-> prob*repetitions];
   ];
    
    (*Length of distro is a funtion of the parentPur's Length*)	
    distro = ConstantArray[0,2^Length[parentPur]];	
    
    tempNames = Range[Length[parentPur]];
    assNewNames = AssociationThread[parentPur,tempNames];
  
    
    (*finds positions where one found patter is, then, positions in probability distro
    is defined as prob for each patter multiplied per 0.5 x times Length of nodes out
    of child purview but part of parent purview *)
    For [i=1, i<=Length[uniqueInputs],i++,
    	oneUniqueInput = Part[uniqueInputs, i];
    	
    	nodes = Values[KeyTake[assNewNames,childPur]];
    	  
    	(*arguments: 1)Nodes to evaluate, 2)Patter to find, 3)Length of cm in order to compute
    	length of distribution. In this case (3) must be the size of parent purview*)
    	pos= findPattInInputs[nodes, oneUniqueInput, Length[parentPur]]["Locations"];
    	For[j=1, j<=Length[pos],j++,
    		distro = ReplacePart[distro,Part[pos,j]->probByInputPatt[oneUniqueInput]*(0.5^Length[nodeSet4BitDstr])];
    	];
    ];
   
   	
	<|
   "ProbabilityDistribution" -> distro,
   "ProbabilityDistrEncoded"-> RunLengthEncode[distro]
   |>

];

(*
computes probability distro in past analysis when mecha = []. 
This is, computes unconstrained distribution for a partition.
This must be over patthers with parent purview's length.

Full Bit probability distribution in inputs is always {0.5,0.5}
------------------------------------------
unconstrainedPastPartitionedDistro[{1, 2}]
Out= <|"UnconstrainedPastPartitionedDistro" -> {0.25, 0.25, 0.25, 0.25}|>
------------------------------------------
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
           POSSIBLE MODIFICATION
           ++++++++++++++++++++++
           +++++++++++++++++++++++
*)
unconstrainedPastPartitionedDistro[parentPurview_]:= Module[
	{allPatts,probsByNode,newKeys,finalNewProbs,uppd},
	
	allPatts=Table[Reverse[IntegerDigits[ii,2,Length[parentPurview]]],{ii,0,(2^Length[parentPurview])-1,1}];
	
	(*Full Bit probability distribution in inputs is always {0.5,0.5}*)
	probsByNode = ConstantArray[{0.5,0.5},Length[parentPurview]];
	newKeys = Range[Length[parentPurview]];
	finalNewProbs =AssociationThread[newKeys, probsByNode];
	(*unconstrained Past Partitioned Distro*)
	uppd=Values[composeProbDistroFromBitProb4SetInputs[allPatts, finalNewProbs]["PattsWithProb"]];
	<|"UnconstrainedPastPartitionedDistro" -> uppd|>
];

(*
+ bddistro = full bit distribution, shich is computed for outputs since for inputs is well
known (always = {0.5,0.5})
+ parentPurview: since unconstrained distro does not care the mechanism, distro is computed
over all elements of parent purview using full bit distro.
*)
unconstrainedFutPartitionedDistro[parentPurview_, fbdistro_]:= Module[
	{allPatts,probsByNode,newKeys,finalNewProbs,ufpd},
	
	allPatts=Table[Reverse[IntegerDigits[ii,2,Length[parentPurview]]],{ii,0,(2^Length[parentPurview])-1,1}];
	
	(*Full Bit probability distribution in inputs is always {0.5,0.5}*)
	probsByNode = Values[fbdistro][[parentPurview]];
	newKeys = Range[Length[parentPurview]];
	finalNewProbs =AssociationThread[newKeys, probsByNode];
	(*unconstrained Past Partitioned Distro*)
	ufpd=Values[composeProbDistroFromBitProb4SetInputs[allPatts, finalNewProbs]["PattsWithProb"]];
	<|"UnconstrainedFutPartitionedDistro" -> ufpd|>
];

   
 (*
 Given two probability distributions coded as run-Length,
 this function compute Euclidian distance between them.
 
 d1 = {{0.037037, 6}, {0.00925926, 2}, {0.037037, 6}, {0.00925926,2},
  {0.037037, 6}, {0.00925926, 2}, {0.037037, 6}, {0.00925926,2}};

d2 = {{0.037037, 6}, {0.00925926, 2}, {0.037037, 6}, {0.00925926,2},
  {0.037037, 6}, {0.00925926, 2}, {0.037037, 6}, {0.00925926,2}};

distanceRunLengthEnconde[d1, d2]

Out: <|"EuclidianDistance" -> 0.|>
 
 
 *)  
distanceRunLengthEnconde[set1_, set2_] :=
    Module[ {smallerSet, largerSet, limit, total, progSmallCounter, 
    progLargeCounter, partSmallCounter,
    partLargeCounter, largerGoForward, smallerGoForward, oneSmaller, 
    oneLarger, timesSmallCounter,
    timesLargeCounter, oneNumSmaller, oneNumLarger, diff, newLength, 
    newElement1, newElement2(*, copySmallSet,copyLargeSet*)},
        
        
        If[ Length[set1] > Length[set2],
            smallerSet = set2;
            largerSet = set1,
            smallerSet = set1;
            largerSet = set2
        ];
        
        limit = Total[#[[2]] & /@ smallerSet];
        total = 0;
        
        progSmallCounter = 0;
        progLargeCounter = 0;
        partSmallCounter = 1;
        partLargeCounter = 1;
        largerGoForward = True;
        smallerGoForward = True;

        
        While[progLargeCounter < limit,
         

         oneSmaller = Part[smallerSet, partSmallCounter];
         oneLarger = Part[largerSet, partLargeCounter];
         
         timesSmallCounter = oneSmaller[[2]];
         timesLargeCounter = oneLarger[[2]];
         oneNumSmaller = oneSmaller[[1]];
         oneNumLarger = oneLarger[[1]];
         
        If[ smallerGoForward === True,
             progSmallCounter = progSmallCounter + timesSmallCounter
         ];
         If[ largerGoForward === True,
             progLargeCounter = progLargeCounter + timesLargeCounter
         ];
         
         (* begin ---------------------*)
         (*Print["** Progresive small counter: "<>ToString[progSmallCounter]];
         Print["** Progresive large counter: "<>ToString[progLargeCounter]];
         Print["small part: " <> ToString[oneSmaller]];
         Print["large part: " <> ToString[oneLarger]];*)
         (*  end ---------------------*)
         
         largerGoForward = False;
         smallerGoForward = False;
         
         If[ (progSmallCounter >  progLargeCounter) && (progLargeCounter <= limit),
             total = total + (((oneNumSmaller - oneNumLarger)^2)*timesLargeCounter);
             (*Print["(("<>ToString[oneNumSmaller]<>"-"<>ToString[oneNumLarger]<>")^2)"<>"*"<>ToString[timesLargeCounter]];*)
             partLargeCounter = partLargeCounter + 1;
             largerGoForward = True,
             If[ (progSmallCounter === progLargeCounter) && (progLargeCounter <= limit),
                 total = total + (((oneNumSmaller - oneNumLarger)^2)*timesLargeCounter);
                 (*Print["(("<>ToString[oneNumSmaller]<>"-"<>ToString[oneNumLarger]<>")^2)"<>"*"<>ToString[timesLargeCounter]];*)
                 partSmallCounter = partSmallCounter + 1;
                 partLargeCounter = partLargeCounter + 1;
                 largerGoForward = True;
                 smallerGoForward = True,
                 If[ (progSmallCounter <  progLargeCounter) && (progLargeCounter < limit),
                 	
                     diff = progLargeCounter - progSmallCounter;
                     newLength = timesLargeCounter - diff;
                     newElement1 = {oneNumLarger, newLength};
                     newElement2 = {oneNumLarger, diff};
                     largerSet[[partLargeCounter]] = newElement1;
                     largerSet = Insert[largerSet, newElement2, partLargeCounter + 1];
                     progLargeCounter=progLargeCounter-timesLargeCounter;
                     largerGoForward = True;
                 ]
             ]
         ];
         
          
         
         (* begin -----------------*)
         (*copySmallSet = smallerSet;
         copyLargeSet = largerSet;
         copySmallSet = Insert[copySmallSet, "I'll process next ->", partSmallCounter];
         copyLargeSet = Insert[copyLargeSet, "I'll process next ->", partLargeCounter];
         Print[copySmallSet];
         Print[copyLargeSet];
         Print["Total: "<> ToString[total]];
         Print["---------------"];*)
         
         (* end   -----------------*)
         
         ];
         
         <|"EuclidianDistance"->Sqrt[total]|>
    ];
    
    
 
 
 
(* Unconstrained probability distriburion is, rougly, zeros and ones distribution in the outputs
matrix for any node:
For instance, for 3 nodes in Tononi's example, outputs for XOR gate there are 4 0s and 
4 1s, then prob(0)=0.5, prob(1) = 0.5

cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};
calcUnconstrProbDistrInOutputsByNode[3, cm03, dyn03]

 Out: "ProbabilityDistributionByNode" -> {0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5}
 
 because outputs for 3th node with XOR dyn is: {0,1,1,0,0,1,1,0}
*)
calcUnconstrProbDistrInOutputsByNode[node_, cm_, dynVector_] := Module[
   {locations, res,total,zeroProb,oneProb,probDistr,w},
   
   total = 2^Length[cm];
 
   
   (*OR and XOR gates have less 0's than one's in a consecutive
   binary numeration. For AND gate there are less 1's than 0,s*)
   
   If[(dynVector[[node]]=== "XOR")|| (dynVector[[node]] === "OR"),
	    res = findIndexesOfOutputs4Mechanism[List[node], {0}, dynVector, cm];
	    locations = unfoldLocationsAndSumandos[res["DecimalRepertoire"], res["Sumandos"]];
	    zeroProb = N[Length[locations]/total];
	    oneProb = N[1 - zeroProb];
	    probDistr = Table[If[MemberQ[locations, w],zeroProb,oneProb],{w,1,total,1}];
	    ,
	    res = findIndexesOfOutputs4Mechanism[List[node], {1}, dynVector, cm];
	    locations = unfoldLocationsAndSumandos[res["DecimalRepertoire"], res["Sumandos"]];
	    oneProb = N[Length[locations]/total];
	    zeroProb = N[1 - oneProb];
	    probDistr = Table[If[MemberQ[locations, w],oneProb,zeroProb],{w,1,total,1}];
    ];
    
      
   
   
   
   (* begin --------------------*)
   (*Print["Node: "<> ToString[
   node]];
   Print["Gate type: "<> ToString[dynVector[[node]]]];
   Print["Locations: "<> ToString[locations]];
   Print["Total number of elements: "<> ToString[total]];
   Print["Number of Found elements: "<> ToString[Length[locations]]];
   Print["rest elements: "<> ToString[total-Length[
   locations]]];*)
   (* 
   end   --------------------*)
   <|"ProbabilityDistributionByNode" -> probDistr|>

];
   
   
computeBitProbInInputsByNode[node_,cm_,dynVector_]:=Module[
	{locs, zeroProb, oneProb},
	
	(*in OR and XOR there are more 0s than 1s*)
	If[dynVector[[node]] === "OR"|| dynVector[[node]] === "XOR", 
		locs = findPattInInputs[{node}, {0}, Length[cm]]["Locations"];
		zeroProb = N[Length[locs]/(2^Length[cm])];
		oneProb = N[1-zeroProb];
		,
		locs = findPattInInputs[node, {1}, Length[cm]]["Locations"];
		oneProb = N[Length[locs]/(2^Length[cm])];
		zeroProb = N[1-oneProb];
	];
	
	<|"ZeroProb"-> zeroProb,
	  "OneProb"-> oneProb
	|>

];

   

(*Bit Probability Distrubition for a single node*)
calcUBPOutputs[node_, cm_, dynVector_] := 
Module[
   {locations, res,total,zeroProb,oneProb},
(* compute probability of a node in function of the number of 0s and 1s
   according to its dynamic and inputs

cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};
calcUBPOutputs[3, cm03, dyn03]
 
Out: <|"ZeroProb" -> 0.5, "OneProb" -> 0.5|>
 
because outputs for 3th node with XOR dyn is: {0,1,1,0,0,1,1,0}
*)  
   
   
   total = 2^Length[cm];
   
   (*OR and XOR gates have less 0's than one's in a consecutive
   binary numeration. For AND gate there are less 1's than 0,s*)
   
   If[(dynVector[[node]]=== "XOR")|| (dynVector[[node]] === "OR"),
    res = findIndexesOfOutputs4Mechanism[List[node], {0}, dynVector, cm];
    locations = unfoldLocationsAndSumandos[res["DecimalRepertoire"], res["Sumandos"]];
    zeroProb = N[Length[locations]/total];
    oneProb = N[1 - zeroProb];
    ,
    res = findIndexesOfOutputs4Mechanism[List[node], {1}, dynVector, cm];
    locations = unfoldLocationsAndSumandos[res["DecimalRepertoire"], res["Sumandos"]];
    oneProb = N[Length[locations]/total];
     zeroProb = N[1 - oneProb];
    ];
   
   
   
   (* begin --------------------*)
   (*Print["Node: "<> ToString[node]];
   Print["Gate type: "<> ToString[dynVector[[node]]]];
   If[dynVector[[node]]==="OR"||dynVector[[node]]==="XOR", Print["Locations (0s): "<> ToString[locations]],
   		Print["Locations (1s): "<> ToString[locations]]
   ];
   
   Print["Total number of elements: "<> ToString[total]];
   Print["Number of Found elements: "<> ToString[Length[locations]]];
   Print["rest elements: "<> ToString[total-Length[locations]]];
   *)
   
   (* end   --------------------*)
   <|"ZeroProb" -> zeroProb, 
    "OneProb" -> oneProb|>
   
   
   ];
   
   

(* Given a connectivity matrix and dynamic of a system, it computes unconstrained
probability for all the system, node by node using the format: node ->{0'PROB, 1'PROB]

cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};
calcFullBitUnconstrProbInOutputs[cm03, dyn03]

Out: <|"UnconstrProbbsByBit" -> <|1 -> {0.25, 0.75}, 2 -> {0.75, 0.25}, 3 -> {0.5, 0.5}|>|>

because...
outputs		
1	2	3
---------
0	0	0
0	0	1
1	0	1
1	0	0
1	0	0
1	1	1
1	0	1
1	1	0

*)
calcFullBitUnconstrProbInOutputs[cm_, dynVector_] := Module[
   {nodes,generalProbVector,hh,ucp},
    nodes = Range[Length[cm]];
    
    generalProbVector=Association[{}];
    
    For[hh=1, hh<= Length[nodes],hh++,
    	ucp=calcUBPOutputs[Part[nodes,hh], cm, dynVector];
    	AppendTo[generalProbVector,hh -> {ucp["ZeroProb"],ucp["OneProb"]}];
    ]; 
   
   <|"UnconstrProbbsByBit"-> generalProbVector|>
];

(* Given a partition o nodes, it computes the unconstrained probability distribution
in outputs for this subset.

cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};

calcBitUnconstrProb4OnePartInOuts[{1,2}, cm03, dyn03]

Out: <|"UnconstrProbbVector" -> <|1 -> {0.25, 0.75}, 2 -> {0.75, 0.25}|>|>

*)
calcBitUnconstrProb4OnePartInOuts[partition_, cm_, dynVector_] := Module[
   {generalProbVector,hh,ucp},
    
   
    generalProbVector=Association[{}];
    
    For[hh=1, hh<= Length[partition],hh++,
    	ucp=calcUBPOutputs[Part[partition,hh], cm, dynVector];
    	AppendTo[generalProbVector,Part[partition,hh] -> {ucp["ZeroProb"],ucp["OneProb"]}];
    ]; 
   
   <|"UnconstrProbbVector"-> generalProbVector|>
];

(* in IIT probability of a pattern (in/out) is calculated by multiplication of
individual probabilities or probability by node.
For instance, for the pattern: {1,1,1}
and given the probability by bit 1->{0.25,0.75}, 2-> {0.3,0.7}, 3->{0.1,0.9}

the composed prob for this pattern would be: (0.75 * 0.7 * 0.9) = 0.4725
which are prob for 1s

proByBit = <|1 -> {0.25, 0.75}, 2 -> {0.3, 0.7}, 3 -> {0.1, 0.9}|>
patt = {1, 1, 1}

composeProbForASinglePatternFromBitProbbs[patt, proByBit]

Out: <|"Probability" -> 0.4725|>


*)
composeProbForASinglePatternFromBitProbbs[pattern_,unconsProbbVectorByBit_]:=
Module[{emptyVector,rr,zeroProbb,oneProbb},
	
	emptyVector = List[];
	
	For[rr = 1, rr <= Length[unconsProbbVectorByBit], rr++,
		   zeroProbb = unconsProbbVectorByBit[rr][[1]];
		   oneProbb = unconsProbbVectorByBit[rr][[2]];
		   If[pattern[[rr]] === 0, AppendTo[emptyVector, zeroProbb], AppendTo[emptyVector, oneProbb]];
		   (*Print["0P="<> ToString[zeroProbb]<> ", 1P="<> ToString[oneProbb]];
		   Print[emptyVector];*)
		];
		
		<|"Probability"-> Times @@ emptyVector|>

];


(*Given a set of inputs and a prob vector by bit (general prob by bit)
it computes the prob by combination of bits in patter.
It is the repetition of "composeProbForASinglePatternFromBitProbbs" method for an array of inputs

proByBit = <|1 -> {0.25, 0.75}, 2 -> {0.3, 0.7}, 3 -> {0.1, 0.9}|>
patts = {{1, 1, 1}, {1, 0, 0}, {0, 0, 0}}

composeProbDistroFromBitProb4SetInputs[patts, proByBit]

Out: <|"PattsWithUnconstProb" -> <|{1, 1, 1} -> 0.4725, {1, 0, 0} -> 0.0225, {0, 0, 0} -> 0.0075|>|>

*)
composeProbDistroFromBitProb4SetInputs[setPatterns_, unconsProbbVectorByBit_]:= Module[
	{associationAttractorGralFutProbb,gg,emptyVector,oneAtt,attFutGeneralProb},
	associationAttractorGralFutProbb = Association[{}];

		For[gg = 1, gg <= Length[setPatterns], gg++,
		  oneAtt = Part[setPatterns, gg];
		  emptyVector = List[];
		  attFutGeneralProb = composeProbForASinglePatternFromBitProbbs[oneAtt,unconsProbbVectorByBit]["Probability"];
		  AppendTo[associationAttractorGralFutProbb, oneAtt -> attFutGeneralProb];
		  
		  ];
		  
		
		(*Print["atts and its general prob = " <> ToString[associationAttractorGralFutProbb]];*)
		<|"PattsWithProb"-> associationAttractorGralFutProbb|>
	
	
	];
	
	
(*
Unconstrained past probability distribution is actually 
1/length[input-repertoire]
*)
createUnconstrPastProbbDistr[numSysNodes_]:=
Module[{longi,prob,uPD,e},
	longi = 2^numSysNodes;
	prob = N[1/longi];
	uPD = Table[prob,{e,1,longi,1}];
	
	<|"UnconstrPastProbDist"-> uPD|>
];
	
	
	

(* this procedure makes the same than the next one. Difference between update and unfold procedures
is the former makes calculatios over the list of attractors, this is, over all possible outputs. The
last calculate the complete repertoire of outputs. Then last, is larger than first one since 
Length[attractors] <= Length[RepertoireOutputs]

example:
------------------------------------------------------------------------------------------
oldBitProbDistr = <|1 -> {0.75, 0.25}, 2 -> {0.25, 0.75}, 3 -> {0.25, 0.75}, 4 -> {0.75, 0.25}|>;
assPat2Prob = <|{0, 0, 0, 0} -> 0.0351563, {0, 0, 1, 0} -> 0.105469, 
                {1, 0, 1, 0} -> 0.0351563, {0, 1, 0, 0} -> 0.105469,
                {0, 1, 1, 0} -> 0.316406, {0, 1, 1, 1} ->  0.105469,
                {1, 1, 1, 0} -> 0.105469, {1, 1, 1, 1} -> 0.0351563|>;

attsSet = Keys[assPat2Prob];

newProbVec = <|2 -> {0, 1.}, 4 -> {1., 0}|>;


Timing[updateAssPattToProbByNewBitProbVector[oldBitProbDistr, newProbVec, assPat2Prob]]
Timing[unfoldProbDistrFromByBitProbDistr[oldBitProbDistr, newProbVec, attsSet]]
------------------------------------------------------------------------------------------

{0.000334, <|"NewAttWithProbb" -> <|{0, 0, 0, 0} -> 0., {0, 0, 1, 0} -> 0., {1, 0, 1, 0} -> 0., {0, 1, 0, 0} -> 
     0.1875, {0, 1, 1, 0} -> 0.5625, {0, 1, 1, 1} -> 0., {1, 1, 1, 0} -> 0.1875, {1, 1, 1, 1} -> 0.|>|>}
     
 {0.000403, <|"UpdatedDistribution" -> {0., 0., 0., 0.1875, 0.5625, 0.,0.1875, 0.}|>}

*)
updateAssPattToProbByNewBitProbVector[oldBitProbbVector_,newBitProbbVector_, assPattToProbb_]:= Module[
	{atts,attWithProbbCopy,generalProbs,envolvedNodes, newBitProb, oldBitProb,
	oldZeroProb,oldOneProb,newZeroProb,newOneProb,ii,oneAtts,oneGenProb,multiplos,jj,div,bit},
	
		attWithProbbCopy = assPattToProbb; 
		atts = Keys[attWithProbbCopy];
		generalProbs = Values[attWithProbbCopy];
		
		envolvedNodes = Keys[newBitProbbVector];
		newBitProb = Values[newBitProbbVector];
		oldBitProb = Extract[Association[oldBitProbbVector], Split[envolvedNodes]];
		
		oldZeroProb = #[[1]] & /@ oldBitProb;
		oldOneProb = #[[2]] & /@ oldBitProb;
		
		newZeroProb = #[[1]] & /@ newBitProb;
		newOneProb = #[[2]] & /@ newBitProb;
		
		(* begin ------------------------*)
		(*Print["Nodes:" <> ToString[envolvedNodes]];
		Print["New zero probabilities: " <> ToString[newZeroProb]];
		Print["New one probabilities: " <> ToString[newOneProb]];
		Print["Old zero probabilities: " <> ToString[oldZeroProb]];
		Print["Old one probabilities: " <> ToString[oldOneProb]];*)
		(* end   ------------------------*)
		
		For[ii = 1, ii <=   Length[atts], ii++,
		  oneAtts = Part[atts, ii];
		  oneGenProb = Part[generalProbs, ii];
		  multiplos = List[];
		  
		  (* begin ----------------*)
		  (*Print["----------------"];
		  Print["Attractor to process: " <> ToString[oneAtts]];
		  Print["Probability (GP): " <> ToString[oneGenProb]];*)
		  (* end   ----------------*)
		  
		  For[jj = 1, jj <= Length[envolvedNodes], jj++,
		   		bit = Part[oneAtts, envolvedNodes[[jj]]];
		   		If[bit === 0, 
		   			div = oldZeroProb[[jj]]; AppendTo[multiplos, newZeroProb[[jj]]]
		    		,
		    		div = oldOneProb[[jj]]; AppendTo[multiplos, newOneProb[[jj]]];
		          ];
		   
				   (* begin -------------------*)
				   (*Print["*** DIVINDING"];
				   Print["  Value extracted[" <> ToString[envolvedNodes[[jj]]] <> "]=" <> ToString[bit]];
				   Print["    Dividing: " <> "(" <> ToString[oneGenProb] <> "/" <> ToString[div] <> ")="];*)
				   (*  end  -------------------*)
				   
				   oneGenProb = oneGenProb/div;
				   (*Print["    " <> ToString[oneGenProb]];*)
		   ];
		  
		  
		  
		  oneGenProb = oneGenProb*(Times @@ multiplos);
		  attWithProbbCopy[oneAtts] = oneGenProb ;
		  
		  (* begin -------------------*)
		  (*Print["Multiplos: " <> ToString[multiplos]];
		  Print["Multiplying: " <> ToString[oneGenProb]];
		  Print["NEW ATTRACTORS ASSOCIATIONS: " <> ToString[attWithProbbCopy]];*)
		  (*  end  -------------------*)
		  
		  ];
		  
		  <|"NewAttWithProbb"->attWithProbbCopy |>

];





(*
CREATE FUTURE DISTRIBUTION ONLY FOR ATTRACTORS LIST

1) computes new bit prob for a mechanism
2) update general prob attractors distribution with new
   bit prob found in (1)

---------------------------------------------------------------------------------------------------
cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};
cs03 = {1, 0, 0};

fbupo03 = calcFullBitUnconstrProbInOutputs[cm03, dyn03]["UnconstrProbbsByBit"]


ff03 = calculatingPattsInDivisionsOfCM[cm03, dyn03, 2];
locations03 = ff03["Locations"];
sumandos03 = ff03["Sumandos"];
cca03 = calculatingAttractors[locations03, sumandos03];
atts03 = Keys[cca03["AttractorsByPosition"]];


createFutProbDistrFromOldBitProbDistr[{1, 2, 3}, {1, 0, 0}, {1, 3}, cm03, dyn03, fbupo03, atts03]["UpdatedProbDistr"]
---------------------------------------------------------------------------------------------------


Out1: <|1 -> {0.25, 0.75}, 2 -> {0.75, 0.25}, 3 -> {0.5, 0.5}|>
Out2: {0., 1., 0., 0., 0., 0.}

*)

createFutProbDistrFromOldBitProbDistr[mechanism_, substate_, purview_, cm_, dynVector_, oldProbBitDist_, attsSet_]:= 
	                                
Module[{locs,binInputs,i,j,purviews,h,col,zeroReps,oneReps,numTotalElem,zeroProb,oneProb,
		newProbs,(*updatingSubVector,*)outputs, g(*, futCompleteDistr, newDistrib,e, att, positions, prob*)},
		
		(*Locations are ordinlas, then, number = (locations-1)*)
		locs = findPattInInputs[mechanism, substate, Length[cm]]["Locations"];
		binInputs = Table[Reverse[IntegerDigits[Part[locs, i] - 1, 2, Length[cm]]], {i,1, Length[locs], 1}];
		
		(*for each input, output is computed and purview extracted*)
		outputs = Table[calculateOneOutptuOfNetwork[Part[binInputs, g],cm,dynVector]["Output"] ,{g,1,Length[binInputs],1}];
		purviews = Table[Extract[Part[outputs, j], Split[purview]], {j, 1, Length[outputs], 1}];
		
		(* begin -------------*)
		(*Print["Locations (inputs) for substate: "<> ToString[locs]];
		Print["Outputs: "<> ToString[purviews]];*)
		(* end -------------*)
		
		newProbs = Association[{}];

		For[h = 1, h <= Length[purview], h++,
			  col = purviews[[All, h]];
			  zeroReps = Count[col, 0];
			  oneReps = Count[col, 1];
			  numTotalElem = Length[col];
			  If[zeroReps > 0, zeroProb = N[zeroReps/numTotalElem], zeroProb = 0];
			  If[oneReps > 0, oneProb = N[oneReps/numTotalElem], oneProb = 0];
			  AppendTo[newProbs, Part[purview, h] -> {zeroProb, oneProb}];
			  
			  (* begin ------------------*)
			  (*Print["--------------"];
			  Print["No Elements: " <> ToString[numTotalElem]];
			  Print["Column: " <> ToString[col]];
			  Print["Zeros number: " <> ToString[zeroReps] <> ". Prob: " <> ToString[zeroProb]];
			  Print["Ones number: " <> ToString[oneReps] <> ". Prob: " <> ToString[oneProb]];*)
			  (* end   ------------------*)
		  ];

		(*Print["NEW PROBABILITIES: "<> ToString[newProbs]];*)
		
		
		(*updatingSubVector = calcBitUnconstrProb4OnePartInOuts[purview, cm, dynVector]["UnconstrProbbVector"];
		
		newDistrib = updateAttProbabilityVector[unconsProbsByBit, attsWithUnconstProbb, newProbs]["NewAttWithProbb"];
		
		futCompleteDistr = Table[0, {e, 1, 2^Length[cm], 1}];
				
		For[i=1,i<=Length[atts],i++,
			att = atts[[i]];
			positions = attPos[[i]]+1;
			prob = newDistrib[att];
			futCompleteDistr = ReplacePart[futCompleteDistr,Split[positions]->prob];
		
		];*)
		
		futCompleteDistr=unfoldProbDistrFromByBitProbDistr[oldProbBitDist, newProbs, attsSet]["UpdatedDistribution"];
		
		<|"UpdatedProbDistr"-> futCompleteDistr |>
		
		
	];


(*
UPDATES GRAL. PROBABILITY DISTRIBUTION FROM USING OLD AND NEW BIT PROB.
for all possible putputs and for atts.
*)
(*this assume that all possible pattern must be computed*)
unfoldProbDistrFromByBitProbDistr[originalProbBitDist_, newBitProb_]:= Module[
(*
----------------------------------------------------------------------------------
cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};
fbupo03 = calcFullBitUnconstrProbInOutputs[cm03, dyn03]["UnconstrProbbsByBit"];
newProbVec = <|2 -> {0, 1.}, 3 -> {1., 0}|>;
unfoldProbDistrFromByBitProbDistr[fbupo03, newProbVec]
<|"UpdatedDistribution" -> {0., 0., 0., 0., 0., 0., 0.75, 0}|>
----------------------------------------------------------------------------------
*)
{newKeis,i,x,oldKeis,newProbDist,e,locations,copyOriginalProbBitDist},

		newKeis = Keys[newBitProb];
		copyOriginalProbBitDist = originalProbBitDist;

		For[i = 1, i <= Length[newBitProb], i++,
		  copyOriginalProbBitDist[newKeis[[i]]] = newBitProb[[i]];
		  ];

		oldKeis = Keys[copyOriginalProbBitDist];
		newProbDist = Table[0, {e, 1, 2^Length[oldKeis], 1}];

		locations = (findPattInInputs[List[oldKeis[[1]]], {0}, Length[oldKeis]]["Locations"]);
		newProbDist = ReplacePart[newProbDist, Split[locations] -> copyOriginalProbBitDist[oldKeis[[1]]][[1]]];
		
		(* begin ----------------*)
		(*Print["locations where node " <> ToString[oldKeis[[1]]] <> " = 0:" <> ToString[locations]];
		Print["prob distrib updated: " <> ToString[newProbDist]];*)
		(*  end ----------------*)

		locations = (findPattInInputs[List[oldKeis[[1]]], {1}, Length[oldKeis]]["Locations"]);
		newProbDist = ReplacePart[newProbDist,Split[locations] -> copyOriginalProbBitDist[oldKeis[[1]]][[2]]];
		
		(* begin ----------------*)
		(*Print["locations where node " <> ToString[oldKeis[[1]]] <> " = 1:" <> ToString[locations]];
		Print["prob distrib updated: " <> ToString[newProbDist]];*)
		(*  end ----------------*)

		For[x = 2, x <= Length[copyOriginalProbBitDist], x++,
			  locations = (findPattInInputs[List[oldKeis[[x]]], {0}, Length[oldKeis]]["Locations"]);
			  
			  newProbDist = Flatten[ReplacePart[newProbDist, 
						     Thread[Split[locations] -> 
						     	   ((Extract[newProbDist,Split[locations]])*(copyOriginalProbBitDist[oldKeis[[x]]][[1]]))]]
						     ];
			  (* begin ----------------*)		  
			  (*Print["locations where node " <> ToString[oldKeis[[x]]] <> " = 0:" <> ToString[locations]];
			  Print["prob distrib updated: " <> ToString[newProbDist]];*)
			  (*  end ----------------*)
			  
			  locations = (findPattInInputs[List[oldKeis[[x]]], {1}, Length[oldKeis]]["Locations"]);
			  
			  newProbDist = Flatten[ReplacePart[newProbDist, 
						     Thread[Split[locations] -> 
						     	((Extract[newProbDist,Split[locations]])*(copyOriginalProbBitDist[oldKeis[[x]]][[2]]))]]
						    ];
			  (* begin ----------------*)
			  (*Print["locations where node " <> ToString[oldKeis[[x]]] <> " = 1:" <> ToString[locations]];
			  Print["prob distrib updated: " <> ToString[newProbDist]];*)
		  	  (*  end ----------------*)
		  ];
		  
		  
		  <|"UpdatedDistribution"-> newProbDist|>

];

(*this case, unlkely the above function, need a set of patterns with a probability associated*)
unfoldProbDistrFromByBitProbDistr[oldProbBitDist_, newBitProb_, attsSet_]:= Module[
{newKeis,i,x,oldKeis,newProbDist,e,locations,copyOriginalProbBitDist,outAss},
(*
-----------------------------------------------------------------------------------------
assPat2Prob = <|{0, 0, 0, 0} -> 0.0351563, {0, 0, 1, 0} -> 0.105469, 
                {1, 0, 1, 0} -> 0.0351563, {0, 1, 0, 0} -> 0.105469,
                {0, 1, 1, 0} -> 0.316406, {0, 1, 1, 1} ->  0.105469,
                {1, 1, 1, 0} -> 0.105469, {1, 1, 1, 1} -> 0.0351563|>;

attsSet = Keys[assPat2Prob];
oldBitProbDistr = <|1 -> {0.75, 0.25}, 2 -> {0.25, 0.75}, 3 -> {0.25, 0.75}, 4 -> {0.75, 0.25}|>;
newProbVec = <|2 -> {0, 1.}, 4 -> {1., 0}|>;

unfoldProbDistrFromByBitProbDistr[oldBitProbDistr, newProbVec, attsSet]
out:= <|"UpdatedDistribution" -> {0., 0., 0., 0.1875, 0.5625, 0.,0.1875, 0.}|>
-----------------------------------------------------------------------------------------
*)

		newKeis = Keys[newBitProb];
		copyOriginalProbBitDist = oldProbBitDist;
		outAss = Association[{}];

		For[i = 1, i <= Length[newBitProb], i++,
		  copyOriginalProbBitDist[newKeis[[i]]] = newBitProb[[i]];
		  ];

		oldKeis = Keys[copyOriginalProbBitDist];
		newProbDist = Table[0, {e, 1, Length[attsSet], 1}];

		locations = Position[(#[[1]] == 0) & /@ attsSet, True];
		newProbDist = ReplacePart[newProbDist, locations -> copyOriginalProbBitDist[oldKeis[[1]]][[1]]];
		
		(* begin ----------------*)
		(*Print["locations where node " <> ToString[oldKeis[[1]]] <> " = 0:" <> ToString[locations]];
		Print["prob distrib updated: " <> ToString[newProbDist]];*)
		(*  end ----------------*)

		locations = Position[(#[[1]] == 1) & /@ attsSet, True];
		newProbDist = ReplacePart[newProbDist,locations -> copyOriginalProbBitDist[oldKeis[[1]]][[2]]];
		
		(* begin ----------------*)
		(*Print["locations where node " <> ToString[oldKeis[[1]]] <> " = 1:" <> ToString[locations]];
		Print["prob distrib updated: " <> ToString[newProbDist]];*)
		(*  end ----------------*)

		For[x = 2, x <= Length[copyOriginalProbBitDist], x++,
			  locations = Position[(#[[x]] == 0) & /@ attsSet, True];
			  
			  newProbDist = Flatten[ReplacePart[newProbDist, 
						     Thread[Split[locations] -> 
						     	   ((Extract[newProbDist,locations])*(copyOriginalProbBitDist[oldKeis[[x]]][[1]]))]]
						     ];
			  (* begin ----------------*)		  
			  (*Print["locations where node " <> ToString[oldKeis[[x]]] <> " = 0:" <> ToString[locations]];
			  Print["prob distrib updated: " <> ToString[newProbDist]];*)
			  (*  end ----------------*)
			  
			  locations = Position[(#[[x]] == 1) & /@ attsSet, True];
			  
			  newProbDist = Flatten[ReplacePart[newProbDist, 
						     Thread[Split[locations] -> 
						     	((Extract[newProbDist,locations])*(copyOriginalProbBitDist[oldKeis[[x]]][[2]]))]]
						    ];
			  (* begin ----------------*)
			  (*Print["locations where node " <> ToString[oldKeis[[x]]] <> " = 1:" <> ToString[locations]];
			  Print["prob distrib updated: " <> ToString[newProbDist]];*)
		  	  (*  end ----------------*)
		  ];
		  
		  (*normalizing probability distribution*)
		  newProbDist = newProbDist*(1/Total[newProbDist]);
		  
		  
		  <|"UpdatedDistribution"-> newProbDist|>

];

(*
COMPUTES COMPLETE FUTURE PROBABILITY DISTRIBUTION FOR A MECHAMISM AND A PURVIEW
Size = 2^numNodes where Size always > numAtts
----------------------------------------------------------------------------------------
cm03 = {{0, 1, 1}, {1, 0, 1}, {1, 1, 0}};
dyn03 = {"OR", "AND", "XOR"};

unconstrProbByBit03 = calcFullBitUnconstrProbInOutputs[cm03, dyn03]["UnconstrProbbsByBit"];

cca03 = calculatingAttractors[locations03, sumandos03]
atts03 = Keys[cca03["AttractorsByPosition"]];
unconstrProb4Att03 = composeProbDistroFromBitProb4SetInputs[atts03, unconstrProbByBit03]["PattsWithProb"]

fpd03 = createFutProbDistrFromOldBitProbDistr[{3}, {0}, {1, 2}, cm03, dyn03, unconstrProbByBit03]["ProbabilityDistribution"]
----------------------------------------------------------------------------------------

out:= {0.25, 0.25, 0., 0., 0.25, 0.25, 0., 0.}

*)

parentFutProbDistro[mechanism_,substate_,purview_,cm_,dynVector_]:= 
	                                
Module[{locs,binInputs,i,j,purviews,h,col,zeroReps,oneReps,numTotalElem,zeroProb,oneProb,
		newProbs,outputs, g, futCompleteDistr,set,probsByNode,newKeys,finalNewProbs},
		
		(*Locations are ordinals, then, number = (locations-1)*)
		locs = findPattInInputs[mechanism, substate, Length[cm]]["Locations"];
		binInputs = Table[Reverse[IntegerDigits[Part[locs, i] - 1, 2, Length[cm]]], {i,1, Length[locs], 1}];
		
		(*for each input, output is computed and purview extracted*)
		outputs = Table[calculateOneOutptuOfNetwork[Part[binInputs, g],cm,dynVector]["Output"] ,{g,1,Length[binInputs],1}];
		purviews = Table[Extract[Part[outputs, j], Split[purview]], {j, 1, Length[outputs], 1}];
		
		(* begin -------------*)
		(*Print["Locations (inputs) for substate: "<> ToString[locs]];
		Print["Outputs: "<> ToString[purviews]];*)
		(* end -------------*)
		
		newProbs = Association[{}];

		For[h = 1, h <= Length[purview], h++,
			  col = purviews[[All, h]];
			  zeroReps = Count[col, 0];
			  oneReps = Count[col, 1];
			  numTotalElem = Length[col];
			  If[zeroReps > 0, zeroProb = N[zeroReps/numTotalElem], zeroProb = 0];
			  If[oneReps > 0, oneProb = N[oneReps/numTotalElem], oneProb = 0];
			  AppendTo[newProbs, Part[purview, h] -> {zeroProb, oneProb}];
			  
			  (* begin ------------------*)
			  (*Print["--------------"];
			  Print["No Elements: " <> ToString[numTotalElem]];
			  Print["Column: " <> ToString[col]];
			  Print["Zeros number: " <> ToString[zeroReps] <> ". Prob: " <> ToString[zeroProb]];
			  Print["Ones number: " <> ToString[oneReps] <> ". Prob: " <> ToString[oneProb]];*)
			  (* end   ------------------*)
		  ];

		(*Print["NEW PROBABILITIES: "<> ToString[newProbs]];*)
		
		set=Table[Reverse[IntegerDigits[ii,2,Length[purview]]],{ii,0,(2^Length[purview])-1,1}];
		probsByNode = Values[newProbs];
		newKeys = Range[Length[purview]];
		finalNewProbs =AssociationThread[newKeys, probsByNode];
		futCompleteDistr=Values[composeProbDistroFromBitProb4SetInputs[set, finalNewProbs]["PattsWithProb"]];

		
		<|"ProbabilityDistribution"-> futCompleteDistr |>
		
		
	];




partitionedFutProbDistro[parentMecha_, parentPur_, childMecha_, childCS_,
	                           childPur_,sysCm_,sysDyn_, sysBitProbDistro_]:= 
	                                
Module[{locs,binInputs,i,j,purviews,h,col,zeroReps,oneReps,numTotalElem,zeroProb,oneProb,
		newProbs,outputs, g, futCompleteDistr,set,nodesOutPurview,ee,node,probsByNode,
		newKeys,finalNewProbs},
		
		nodesOutPurview = Complement[parentPur,childPur];
				
		(*Locations are ordinals, then, number = (locations-1)*)
		locs = findPattInInputs[childMecha, childCS, Length[sysCm]]["Locations"];
		binInputs = Table[Reverse[IntegerDigits[Part[locs, i] - 1, 2, Length[sysCm]]], {i,1, Length[locs], 1}];
		
		(*for each input, output is computed and purview extracted*)
		outputs = Table[calculateOneOutptuOfNetwork[Part[binInputs, g],sysCm,sysDyn]["Output"] ,{g,1,Length[binInputs],1}];
		purviews = Table[Extract[Part[outputs, j], Split[childPur]], {j, 1, Length[outputs], 1}];
		
		(* begin -------------*)
		(*Print["Locations (inputs) for substate: "<> ToString[locs]];
		Print["Outputs: "<> ToString[purviews]];*)
		(* end -------------*)
		
		newProbs = Association[{}];

		For[h = 1, h <= Length[childPur], h++,
			  col = purviews[[All, h]];
			  zeroReps = Count[col, 0];
			  oneReps = Count[col, 1];
			  numTotalElem = Length[col];
			  If[zeroReps > 0, zeroProb = N[zeroReps/numTotalElem], zeroProb = 0];
			  If[oneReps > 0, oneProb = N[oneReps/numTotalElem], oneProb = 0];
			  AppendTo[newProbs, Part[childPur, h] -> {zeroProb, oneProb}];
			  
			  (* begin ------------------*)
			  (*Print["--------------"];
			  Print["No Elements: " <> ToString[numTotalElem]];
			  Print["Column: " <> ToString[col]];
			  Print["Zeros number: " <> ToString[zeroReps] <> ". Prob: " <> ToString[zeroProb]];
			  Print["Ones number: " <> ToString[oneReps] <> ". Prob: " <> ToString[oneProb]];*)
			  (* end   ------------------*)
		  ];

		(*Print["NEW PROBABILITIES: "<> ToString[newProbs]];*)
		

		For[ee=1,ee <= Length[nodesOutPurview],ee++,
			node = Part[nodesOutPurview, ee];
			AppendTo[newProbs, node -> sysBitProbDistro[node]]
		];

		
		newProbs = KeySort[newProbs];
		
		set=Table[Reverse[IntegerDigits[ii,2,Length[parentPur]]],{ii,0,(2^Length[parentPur])-1,1}];
		probsByNode = Values[newProbs];
		newKeys = Range[Length[parentPur]];
		finalNewProbs =AssociationThread[newKeys, probsByNode];
		futCompleteDistr=Values[composeProbDistroFromBitProb4SetInputs[set, finalNewProbs]["PattsWithProb"]];
				
		<|"ProbabilityDistribution"-> futCompleteDistr |>
];




	
javaEMD[d1_,d2_]:= Module[
	
	{emdDir,testClass,obj,EMDistance},
	
	emdDir = "/Users/beto/WolframWorkspaces/Base/Alpha/EMD";
	Needs["JLink`"];
	
	InstallJava[];
	SetDirectory[emdDir];
	AddToClassPath[emdDir];
	
	testClass = LoadJavaClass["Aux2"];
	obj = JavaNew[testClass];
	
	Methods[obj];
	
	EMDistance=obj@emdDist[d1,d2];
	
	(*EMDistance = ToExpression[Import["!python3 /Users/beto/WolframWorkspaces/Base/Alpha/run_pyphi_emd.py " <> ToString[nodes]
		<> " " <> 
		StringReplace[StringTrim[ToString[d1], ("{" | "}") ...], Whitespace -> ""] <> " " <>
		StringReplace[StringTrim[ToString[d2], ("{" | "}") ...], Whitespace -> ""] <> " 2>&1", "Text"]];*)
	
	<|"Distance"->EMDistance|>

];


pyEMD[d1_,d2_]:= Module[
	
	{(*emdDir,testClass,obj,*)nodes,EMDistance},
	
	(*emdDir = "/Users/beto/WolframWorkspaces/Base/Alpha/EMD";
	Needs["JLink`"];
	
	InstallJava[];
	SetDirectory[emdDir];
	AddToClassPath[emdDir];
	
	testClass = LoadJavaClass["Aux2"];
	obj = JavaNew[testClass];
	
	Methods[obj];
	
	EMDistance=obj@emdDist[d1,d2];
	*)
	
	(*Assumes that pyphi is installed with python3 in mac*)
	nodes = Log2[Length[d1]];
	EMDistance = ToExpression[Import["!python3 /Users/beto/WolframWorkspaces/Base/Alpha/run_pyphi_emd.py " <> ToString[nodes]
		<> " " <> 
		StringReplace[StringTrim[ToString[d1], ("{" | "}") ...], Whitespace -> ""] <> " " <>
		StringReplace[StringTrim[ToString[d2], ("{" | "}") ...], Whitespace -> ""] <> " 2>&1", "Text"]];
	
	<|"Distance"->EMDistance|>

];


pyII[tpm_,cm_,cs_]:= Module[
	
	{pyphi,nodes,cadena,atpm,acm,acs},
	
	(*Assumes that pyphi is installed with python3 in mac*)
	nodes = Length[tpm[[1]]];
	atpm = StringReplace[ToString[tpm], "{" -> ""]; 
	atpm = StringReplace[ToString[atpm], "}" -> ""];
	atpm = StringReplace[ToString[atpm], " " -> ""];
	acm = StringReplace[ToString[cm], "{" -> ""]; 
	acm = StringReplace[ToString[acm], "}" -> ""];
	acm = StringReplace[ToString[acm], " " -> ""];
	acs = StringReplace[ToString[cs], "{" -> ""]; 
	acs = StringReplace[ToString[acs], "}" -> ""];
	acs = StringReplace[ToString[acs], " " -> ""];
	cadena = "!python3 /Users/beto/WolframWorkspaces/Base/Alpha/run_pyphi_phi.py " <> ToString[nodes]
		<> " " <> atpm <> " " <> acm <> " " <> acs(* <> " 2>&1"*);
	(*Print[cadena];*)
	pyphi = ToExpression[Import[cadena, "Text"]];
	
	<|"II"->pyphi|>

];

(*
pyEMD[d1_,d2_]:= Module[
	{EMDistance,nodes},
	
	nodes=Log2[Length[d1]];
	
	EMDistance = ToExpression[Import["/Users/beto/WolframWorkspaces/Base/Alpha/EMD/EMD " <> ToString[nodes]
		<> " " <> 
		StringReplace[StringTrim[ToString[d1], ("{" | "}") ...], Whitespace -> ""] <> " " <>
		StringReplace[StringTrim[ToString[d2], ("{" | "}") ...], Whitespace -> ""] <> " 2>&1", "Text"]];
	
	<|"Distance"->EMDistance|>

];
*)

EMD[d1_,d2_]:=Module[
	{n,c,d,edges,g,cd,f,costs,states},
	
	(*number of nodes*)
	n = Log2[Length[d1]];
	(*all possible states of nodes*)
	states = allPosibleInputsReverse[n];
	costs = N[Flatten[DistanceMatrix[states, states, DistanceFunction -> HammingDistance]]];
	
	(* defines series that represent numbers of nodes *)
	c = Range[2^n];
	d = Range[2^n + 1, 2*2^n];
	
	edges = Flatten[Outer[UndirectedEdge, c, d]];
	
	
	g = Graph[Range[2*2^n], edges, EdgeCost -> costs];
	cd = N[Join[d1, Minus[d2]]];
	
	f = FindMinimumCostFlow[g, cd];
	
	(*it tries to compute Minimum cost flow, 1tly with mathematica in one direction (d1,d2),
	if does not works, trys in otrer direction (d2,d1), if this does not works either, it
	uses python implementation*)
	
	If[Head[f] === FindMinimumCostFlow, (*Print["&&&&&&&&&&&&&&&  CAMBIO &&&&&&&&&&&&"];
										Print[cd];*)
		                                cd=N[Join[d2, Minus[d1]]];
		                                f = FindMinimumCostFlow[g, cd];
		                                If[Head[f]===FindMinimumCostFlow,
		                                	(*Print[" 	&&&&&&&&&&&&&&&  CAMBIO2 &&&&&&&&&&&&"];*)
		                                   	f = pyEMD[d1,d2]["Distance"];
		                                ]
		];
    

	(*This takes twise the time used my mathematica implementation of FindMinimumCostFlow*)
	(*f = pyEMD[d1,d2]["Distance"];*)
	
	<|"Distance"->f|>

];

loadDistrosFromFile[parentPurview_,childPurview_,childMecha_]:=Module[
	{fileName,ln,searchedLine,str,lnComplete,found},
	
	fileName = FileNameJoin[{$TemporaryDirectory,
							ToString[Length[parentPurview]]<>"x"<>
							ToString[Length[childPurview]]<>"x"<>
							ToString[Length[childMecha]]}];
							
	ln="Not Found";			
	found = False;
	lnComplete="";
	searchedLine="";			
	
	If[FileExistsQ[fileName],	
		searchedLine = "{"<>ToString[parentPurview]<>", "<>ToString[childPurview]<>", "<>ToString[childMecha]<>"}";
		               
		str = OpenRead[fileName];
		
		While[ (found === False) && (lnComplete != ToString[EndOfFile]),
			ln="Not Found";
			lnComplete = ReadLine[str];
			
			If[lnComplete != ToString[EndOfFile],
				ln=ToExpression[lnComplete];
				ln=ToString[Extract[ln,{{1},{2},{3}}]];
				If[ln===searchedLine, ln=lnComplete; found=True
					,
					found=False;
					ln="EndOfFile";
				];
			];
			
		];		
				
		Close[str];	
	];
	
	<|"Line"-> ln|>
	
	];
	
	
saveDistrosInFile[parentPurv_,childPurv_,childMecha_,pDistro_,fDistro_]:=Module[
	{fileName,data,str},
	
	fileName = FileNameJoin[{$TemporaryDirectory,
							ToString[Length[parentPurv]]<>"x"<>
							ToString[Length[childPurv]]<>"x"<>
							ToString[Length[childMecha]]}];
							                                         
	If[FileExistsQ[fileName], str = OpenAppend[fileName],str = OpenWrite[fileName]];
	
	data={parentPurv,childPurv,childMecha,pDistro,fDistro};
	WriteLine[str, ToString[data]];
	Close[str];
];





computeCEI4Partition[cm_,dyn_,cs_,nodes4Mecha_,nodes4Purv_,
	                 aChildMecha_,aChildPurview_,
	                 refPastProb_,refFutProb_,
                     uppd_,ufpd_,fbupo_,fullGraph_]:=Module[
    {ppd,fpd,ln,ppdC,fpdC,ppd2,fpd2,ci,ei,cei,(*aa,*) connected, contained, subConnected, sg, nodes,nulo,
    caChildMecha,caChildPurview,oneSubCS,oneSubCSComp,aChildMechaComp,aPurviewComp,caChildMechaComp,caPurviewComp,
    pusing,fusing,(*verification,*)validPartition},
	
	caChildMecha=aChildMecha;
	caChildPurview=aChildPurview;

	nulo=False;
	contained = False;
    connected = True;
    subConnected = True;
	nodes = DeleteDuplicates[Sort[Join[aChildMecha,aChildPurview]]];
    sg = Subgraph[fullGraph,nodes];
    connected = ConnectedGraphQ[sg];
   	(*contained = testContainsElement[aChildMecha,aChildPurview]["Res"];*)
    subConnected = testConnectedPartitions[aChildMecha,aChildPurview,fullGraph]["Res"];
    (*subConnected = connected;*) (*I'll suppose if connected then subconnected*)
	
	If[contained === False && connected && subConnected,
    				    		    
  		    (*aa = deleteIntersection[aChildMecha,aChildPurview];
			caChildMecha = aa["Mecha"];
			caChildPurview = aa["Purview"];
			oneSubCS = Extract[cs, Split[caChildMecha]];*)
			
			(* begin ---------------------------*)
			(*Print["------------ AS "<>ToString[caChildMecha]<>", "<>ToString[caChildPurview]];*)
			(* end  ---------------------------*)	
			
			(* compute complements at CHILD level*)		
			aChildMechaComp = Complement[nodes4Mecha,aChildMecha];
			aPurviewComp = Complement[nodes4Purv,aChildPurview];
			caChildMechaComp=aChildMechaComp;
			caPurviewComp=aPurviewComp;
			oneSubCSComp = Extract[cs, Split[aChildMechaComp]];
			
			validPartition=True;
	

			(* begin ---------------------------*)
			(*Print["------------ Processing Complement "<>ToString[aChildMechaComp]<>", "<>ToString[aPurviewComp]];*)
			(* end  ---------------------------*)
				
    	    (*aa = deleteIntersection[aChildMechaComp,aPurviewComp];
			aChildMechaComp = aa["Mecha"];
			aPurviewComp = aa["Purview"];
			oneSubCSComp = Extract[cs, Split[aChildMechaComp]];*)
			
			(* begin ---------------------------*)
			(*Print["------------ AS "<>ToString[aChildMechaComp]<>", "<>ToString[aPurviewComp]];*)
			(* end  ---------------------------*)	
			
			
			If[Length[aChildMechaComp]>Length[nodes4Mecha]/2,
				If[(caChildPurview==={} && aChildMechaComp==={}) || 
					(testContainsElement[caChildMecha,aPurviewComp]["Res"] || testContainsElement[aChildMechaComp,caChildPurview]["Res"]),
					validPartition=False,
					validPartition=True
				];
			];
			


		   	If[validPartition,		
				(*aChildMecha is directelly modified when duplicated nodes are deleted*)
				If[(Length[caChildMecha]>0 || Length[aChildMechaComp]>0) && 
				   (Length[caChildPurview]>0 || Length[aPurviewComp]>0),
				
									
						If[caChildMecha === {}, ppd=uppd;fpd=ufpd,
							If[caChildPurview === {}, ppd=1;fpd=1,
								ln=loadDistrosFromFile[nodes4Purv,caChildPurview,caChildMecha]["Line"];
								If[ln==="Not Found" || ln==="EndOfFile",
										ppd=partitionedPastProbDistro[nodes4Mecha, nodes4Purv, cs, caChildMecha, caChildPurview,dyn, cm]["ProbabilityDistribution"];
										fpd=partitionedFutProbDistro[nodes4Mecha, nodes4Purv, caChildMecha, oneSubCS,caChildPurview,cm,dyn, fbupo]["ProbabilityDistribution"];
					                    saveDistrosInFile[nodes4Purv,caChildMecha,caChildPurview,ppd,fpd];
					                    ,
					                    ppd = ToExpression[ln][[4]];
					                    fpd = ToExpression[ln][[5]];
					                    (*Print["Found in file"];*)
										
								];
							];
						];
						
						
						(*compute distributions for complements*)
						If[aChildMechaComp === {}, ppdC=1;fpdC=ufpd,
							If[aPurviewComp === {}, ppdC=1;fpdC=1,
							
									ln=loadDistrosFromFile[nodes4Purv,aPurviewComp,aChildMechaComp]["Line"];
									If[ln==="Not Found" || ln==="EndOfFile",
										ppdC =partitionedPastProbDistro[nodes4Mecha,nodes4Purv,cs,aChildMechaComp,aPurviewComp,dyn,cm]["ProbabilityDistribution"];
										fpdC=partitionedFutProbDistro[nodes4Mecha,nodes4Purv,aChildMechaComp,oneSubCSComp,aPurviewComp,cm,dyn,fbupo]["ProbabilityDistribution"];
										saveDistrosInFile[nodes4Purv,aChildMechaComp,aPurviewComp,ppdC,fpdC];
										,
										ppdC = ToExpression[ln][[4]];
										fpdC = ToExpression[ln][[5]];
										(*Print["Found in file"];*)
									];
								
						 	];
						];
					
						(*original x complement*)
						ppd2=ppd*ppdC;
						fpd2=fpd*fpdC;
						(*NORMALIZATION*)
						If[Total[Flatten[List[ppd2]]]>0,ppd2=ppd2*(1/Total[Flatten[List[ppd2]]])];
						If[Total[Flatten[List[fpd2]]]>0,fpd2=fpd2*(1/Total[Flatten[List[fpd2]]])];
						
						
						If[Length[ppdC] === 0, ppd2 = ppd; pusing="ppd"];
						If[Length[ppdC]>= 1, ppd2 = ppdC; pusing="ppdC"];
						If[Length[fpdC] === 0, fpd2 = fpd; fusing="fpd"];
						If[Length[fpdC]>= 1, fpd2 = fpdC; fusing="fpdC"];
						
						
						(* begin ---------------------------*)
						(*Print["--------- Past repertoire: "<>ToString[refPastProb]];
						Print["--------- partition:       "<>ToString[ppd]];
						Print["--------- complement:      "<>ToString[ppdC]];
						Print["--------- USING:      "<>ToString[pusing]];
						(*Print["--------- Past partitioned repertoire (pxc): "<>ToString[ppd2]];*)
						Print["--------- Future repertoire: "<>ToString[refFutProb]];
						Print["--------- partition          "<>ToString[fpd]];
						Print["--------- complement         "<>ToString[fpdC]];
						Print["--------- USING:      "<>ToString[fusing]];*)
						(*Print["--------- Future partitioned repertoire (pxc): "<>ToString[fpd2]];*)
						(* end  ---------------------------*)
					
						ci = EMD[refPastProb,ppd2]["Distance"];
						ei = EMD[refFutProb,fpd2]["Distance"];
						(*ci = EMD[uppd,ppd2]["Distance"];
						ei = EMD[ufpd,fpd2]["Distance"];*)
						cei = Min[ci, ei];
						
						(*Print results only when cei = 0*)
						(*
						If[cei===0.,
							Print["============"];
							Print["------------ Processing "<>ToString[aChildMecha]<>", "<>ToString[aChildPurview]];
							Print["------------ Processing Complement "<>ToString[aChildMechaComp]<>", "<>ToString[aPurviewComp]];
							Print["------------ cei: {"<>ToString[ci]<>","<>ToString[ei]<>"}: "<>ToString[cei]];					
						];
						*)
						(* begin ---------------------------*)
						(*Print["--------- cei: {"<>ToString[ci]<>","<>ToString[ei]<>"}: "<>ToString[cei]];*)
						(* end  ---------------------------*)
						
						,
						Print["Both cannot be = {}"];
						nulo=True;
					];(*(Length[aChildMecha]>0 || Length[aChildMechaComp]>0)*)
		   	,
		   	ci=0;
		   	ei=0;
		   	cei=0;
		   	ppd={};
		   	fpd={};
		   	ppdC={};
		   	fpdC={};
		   	ppd2={};
		   	fpd2={};
		   	];(*If[validPartition,*)
				

	];
				
	
		<|
		"Nulo"->nulo,
		"ci"->ci,
		"ei"->ei,
		"cei"->cei,
		"ppd"-> ppd,
		"fpd"->fpd,
		"ppdC"-> ppdC,
		"fpdC"->fpdC,
		"ppdNorm"->ppd2,
		"fpdNorm"->fpd2,
		"childMechaComp"->caChildMechaComp, (*saving copies of originals coz originals are probably modified*)
		"purviewComp"->caPurviewComp
		|>		
];
                     







(*
+ refFut/pastProb =  reference Future probability.
				This is the prob ditribution at parent level. This is, at the beggining
				I have a (PARENT) mechanism and a (PARENT) purview over I want to compute MIP.
				Parents are divided in order to be assesed, these division are in the CHILD
				level 
+ fbupo = Full Bit Unconstrained Probability for Outputs

For a given partition, it computes all possible partitions in order to find MIP, this is
the partition of the partitions (at child level) that generates the smallest value of integrated
information (in comparison with Parent level). This si small phi of a partition. 

Example: (PAST ANALYSIS)
PARENT PARTITION: mecha: AB, purview: BC (parent distros must be computed previously)
CHILD PARTITIONS
1) [ ],A	X	BC,B    -->EMD[Parent, child1] = 0.5
2) [ ],B	X	BC,A	-->EMD[Parent, child2] = 0.5
3) [ ],AB	X	BC,[]	-->EMD[Parent, child3] = 0.5
4) B,[]		X	C,AB	-->EMD[Parent, child4] = 0.3334** MIP
5) B,A		X	C,B		-->EMD[Parent, child5] = 0.5
6) B,B		X	C,A		-->EMD[Parent, child6] = 0.5
7) B,AB		X	C,[]	-->EMD[Parent, child7] = 0.5
*)

findMIP[cm_,dyn_,cs_,refFutProb_, refPastProb_, nodes4Mecha_,nodes4Purv_,fbupo_,fullGraph_]:=Module[
	{j,k,aChildMecha,caChildMecha,aChildPurview,caChildPurview,
		pMIPZero, fMIPZero, pMIPNonZero, fMIPNonZero, ceiPartition,
		ci, ei, conta,childrenMechas, childrenPurviews, pMIPFinal,fMIPFinal,uppd,ufpd,
		ln},
	
    
    (*saving values for control*)
    (*
	ceArray = List[];
	ciArray = List[];
	ceiArray = List[];
	*)

	
	(*1)Mecha, 2)Purview, 3)MechaComplement, 4) PurviewComplement,
	  5)ciMIP/eiMIP, 6)distribution, 7) complement Distro*)
	(*when the MIP = 0*)

	pMIPZero = List[{}, {}, {}, {}, 100, {}, {}];
	fMIPZero = List[{}, {}, {}, {}, 100, {}, {}];
	(*when there is a MIP > 0 && a MIP = 0, then returns the MIP > 0*)
	pMIPNonZero = List[{}, {}, {}, {}, 100, {}, {}];
	fMIPNonZero = List[{}, {}, {}, {}, 100, {}, {}];
	
	(*depending on values of flags graterThanZero/OnlyZero this take the
	final value as result*)
	pMIPFinal = List[{}, {}, {}, {}, 100, {}, {}];
	fMIPFinal = List[{}, {}, {}, {}, 100, {}, {}];
	
	(*for counting number of valid mechanisms*)
	conta = 0;
	
	(*nodes4Mecha input is the PARENT level
	mechas is the CHILD level*)
	childrenMechas = Subsets[nodes4Mecha];
	childrenPurviews = Subsets[nodes4Purv];

	
	ln = loadUnconstrainedDistrosFromFile[nodes4Purv]["Line"];
	If[ln==="Not Found" || ln===EndOfFile,
		uppd=unconstrainedPastPartitionedDistro[nodes4Purv]["UnconstrainedPastPartitionedDistro"];
		ufpd=unconstrainedFutPartitionedDistro[nodes4Purv,fbupo]["UnconstrainedFutPartitionedDistro"];
		saveUnconstrainedDistroInFile[nodes4Purv,uppd,ufpd];
		,
		uppd = ToExpression[ln][[2]];
		ufpd = ToExpression[ln][[3]];
		(*Print["Found in File"];*)
	];
	
	j=0;
	
	While[True,		
		j++;
		(*aChildMecha is the CHILD level*)		
		aChildMecha = Part[childrenMechas, j];
		caChildMecha = aChildMecha;		
		
		k=0;
		(*the other half is calculated with complements*)
		While[True,
			k++;			
			(*onePurview is in the CHILD level*) 
			aChildPurview = Part[childrenPurviews, k];
			caChildPurview = aChildPurview; 
			
			
			(* begin ---------------------------*)
			(*Print["------------ looking for MIP at children level in:"];
			Print["------------ Processing "<>ToString[aChildMecha]<>", "<>ToString[aChildPurview]];*)
			(* end  ---------------------------*)	
							   
			If[aChildMecha!={}||aChildPurview!={},
				
				   	ceiPartition=computeCEI4Partition[cm,dyn,cs,nodes4Mecha,nodes4Purv,
		         	aChildMecha,aChildPurview,refPastProb,refFutProb,uppd,ufpd,fbupo,fullGraph];
		         	
		         	If[ceiPartition["Nulo"]===False,
		         	
				         	ci=ceiPartition["ci"];
				         	ei=ceiPartition["ei"];
									
							(*saving pMIP*)
							(*this includes 0 *)
							If[ci <= pMIPZero[[5]],(* this is = 100 at the beggining*)
								pMIPZero[[1]] = aChildMecha;
								pMIPZero[[2]] = aChildPurview; 
								pMIPZero[[3]] = ceiPartition["childMechaComp"]; 
								pMIPZero[[4]] = ceiPartition["purviewComp"]; 
								pMIPZero[[5]] = ci; 
								pMIPZero[[6]] = ceiPartition["ppd"]; (*Distribution at CHILD Level*)
								pMIPZero[[7]] = ceiPartition["ppdC"];
							]; 
							
							(*saving fMIP*)
							If[ei <= fMIPZero[[5]],
								fMIPZero[[1]] = aChildMecha;
								fMIPZero[[2]] = aChildPurview;
								fMIPZero[[3]] = ceiPartition["childMechaComp"]; 
								fMIPZero[[4]] = ceiPartition["purviewComp"];
								fMIPZero[[5]] = ei;
								fMIPZero[[6]] = ceiPartition["fpd"]; (*distro at CHILD level*)
								fMIPZero[[7]] = ceiPartition["fpdC"];
							];
							
							If[(fMIPZero[[5]]===0)&&(pMIPZero[[5]]===0),Break[]];
					
		         	];(*If[ceiPartition["Nulo"]===False*)
		       
		       		(*,
		       		If[aChildMecha==={} && aChildPurview ==={},Print["------------ Mecha and Pur cannot be empty set at the same time"]];*)
			]; (*If[aChildMecha!={}||aChildPurview!={},*)
								
   		If[k>=Length[childrenPurviews]/2,Break[]];
   		];(*While purCounter*)
   	
   	
   	If[j>=Length[childrenMechas],Break[]];
   	
   	];(*While mechaCounter*)	
   
   	<|"pMIP"-> pMIPZero, "fMIP"-> fMIPZero|>

];


(*
+ refFutProb =  reference Future probability. 
                this is the probability distribution against probability distributions
                are assesed using EMD. This is the unconstrained probability distribution
                or probability distribution of the whole system.

+ fbupo = Full Bit Unconstrained Probability for Outputs

This function USE ATTRACTORS PROBABILITY
*)
(*
findMIP[cm_,dyn_,cs_,refFutProb_, refPastProb_, nodes4Mecha_,nodes4Purv_, fbupo_, atts_]:=Module[
	{j,k,aChildMecha,aChildMechaComp,onePurview,onePurviewComp,oneSubCS,oneSubCSComp,
		ppd, fpd, pMIP, fMIP, ppd2, fpd2, ceArray, ciArray, ceiArray, ppdC, fpdC, ci, ei, cei, mechas, purviews},
		
		
	ceArray = List[];
	ciArray = List[];
	ceiArray = List[];
	
	(*1)Mecha, 2)Purview, 3)MechaComplement, 4) PurviewComplement, 
	  5)ciMIP/eiMIP, 6)distribution 7)complement distro*)
	pMIP = List[{}, {}, {}, {}, 100, {}, {}];
	fMIP = List[{}, {}, {}, {}, 100, {}, {}];
	
	
	mechas = Subsets[nodes4Mecha];
	purviews = Subsets[nodes4Purv];
	
	(*valid mechanisms*)
	For[j = 1, j <= (Length[mechas])/2, j++,
		
		aChildMecha = Part[mechas, j];
		oneSubCS = Extract[cs, Split[aChildMecha]];
		
		For[k = 1, k <= Length[purviews], k++,
			onePurview = Part[purviews, k];
			
			If[aChildMecha === {} && onePurview === {}, Break[] ,
				
				If[aChildMecha === {}, ppd=pastUncProbDist;fpd=futUncProbDist,
					
					If[onePurview === {}, ppd=1;fpd=1,
						
						(*compute complements*)
						aChildMechaComp = Complement[Range[Length[cm]],aChildMecha];
						oneSubCSComp = Extract[cs, Split[aChildMechaComp]];
						onePurviewComp = Complement[Range[Length[cm]],onePurview];
						
						(*PAST prob distribution*)
						ppd = parentPastProbDistro[aChildMecha, oneSubCS,
								onePurview, dyn, cm]["ProbabilityDistribution"];
						
						(*FUTURE prob distribution for mecha and purview*)
						(*only for attractors*)
						fpd = createUnpartitionedFutProbDistro[aChildMecha, oneSubCS,
							onePurview, cm, dyn, fbupo, atts]["UpdatedProbDistr"];
	
					];
				];
			];
			
			(*compute distributios for complements*)
			ppdC =parentPastProbDistro[aChildMechaComp, oneSubCSComp,
								onePurviewComp, dyn, cm]["ProbabilityDistribution"];
			fpdC = createUnpartitionedFutProbDistro[aChildMechaComp, oneSubCSComp,
							onePurviewComp, cm, dyn, fbupo, atts]["UpdatedProbDistr"];
			 
			(*original x complement*)
			ppd2=ppd(*ppdC*);
			fpd2=fpd(*fpdC*);
			
						 
			(*distance between unconstrained probability distributions*)
			ci = EMD[refPastProb, ppd2]["Distance"];
			ei = EMD[refFutProb, fpd2]["Distance"];
			
			
			
			(*saving pMIP*)
			If[(ci < pMIP[[5]]) && (ci > 0), 
				pMIP[[1]] = aChildMecha;
				pMIP[[2]] = onePurview; 
				pMIP[[3]] = aChildMechaComp; 
				pMIP[[4]] = onePurviewComp; 
				pMIP[[5]] = ci; 
				pMIP[[6]] = ppd2;
				pMIP[[7]] = ppdC;
			];
			
			(*saving fMIP*)
			If[(ei < fMIP[[5]]) && (ei > 0), 
				fMIP[[1]] = aChildMecha;
				fMIP[[2]] = onePurview;
				pMIP[[3]] = aChildMechaComp; 
				pMIP[[4]] = onePurviewComp;
				fMIP[[5]] = ei;
				fMIP[[6]] = fpd2;
				fMIP[[7]] = fpdC;
			];
			
			(*only for control and test*)
			AppendTo[ciArray, ci];
			AppendTo[ceArray, ei];
			
			cei = Min[ci, ei];
			AppendTo[ceiArray, cei];
   
   	    
		    (*Print["Mecha: "<> ToString[aChildMecha]<> " Purview: "<> ToString[onePurview]];
		    Print["ci: "<> ToString [ci]<> " ei: "<> ToString[ei]<> " *** CEI ***: "<> ToString[cei]];
		    Print["past: "];
		    Print[pastPdWSys];
		    Print[ppd];
		    Print["Fut:"];
		    Print[futPdWSys];
		    Print[fpd];
		    Print["***"];*)
		    
   
   		];(*For k = 1*)
   	];(*For J = 1*)	
   	
   	<|"pMIP"-> pMIP, "fMIP"-> fMIP|>

];
*)
(*
options:
unconstr_ = 0, All patterns || only attractors
norm_ = 1 normalized, 0 = not normalized
wholeSys_ = 0 full system, 1= only attractors,futDist_,vmOption_
*)
computeUnconstrainedDistros[cm_,dyn_,cs_,{unconstr_,norm_,wholeSys_,futDist_,vmOption_}]:=Module[
	{resumeOptions,fbupo,ff,locations,sumandos,cca,atts,attsPos,patts,attWithUncostProb,
	uncFutProb,uncPastProb,e},
	
	resumeOptions = "["<>ToString[unconstr]<>","<> ToString[norm]<>","
	                   <>ToString[wholeSys]<>","<>ToString[futDist]<>"]";
	If[unconstr === 0, 
		resumeOptions = resumeOptions <> "All patts", 
		resumeOptions = resumeOptions <> "Only attractors" 
	];
	
	If[norm === 1, 
		resumeOptions = resumeOptions <> ", NORMALIZED", 
		resumeOptions = resumeOptions <> ", NOT normalized" 
	];
	
	If[wholeSys === 0, 
		resumeOptions = resumeOptions <> ", Fut whole system -> WHOLE system", 
		resumeOptions = resumeOptions <> ", Fut whole system -> ONLY Attractors" 
	];
	
	If[futDist === 0, 
		resumeOptions = resumeOptions <> ", Fut distr -> All Patts", 
		resumeOptions = resumeOptions <> ", Fut distr -> ONLY Attractors" 
	];
	
	(*Print[resumeOptions];*)
	
	
	(*-------------------------------------------------------
	 1) general bit unconstrained probability in outputs
	---------------------------------------------------------
	*)
	 fbupo = calcFullBitUnconstrProbInOutputs[cm, dyn]["UnconstrProbbsByBit"];
	 (*<|1 -> {0.25, 0.75}, 2 -> {0.75, 0.25}, 3 -> {0.5, 0.5}|>*)
	
	(*-------------------------------------------------------
	2) dividing system into possible patterns.
	arguments: cm = adyacency matrix, dyn = dynamic of the system, 2= length
	of division of the system used to compute (find patterns) the system
	-------------------------------------------------------
	*)
	ff = calculatingPattsInDivisionsOfCM[cm, dyn, 2];
	locations = ff["Locations"];
	sumandos = ff["Sumandos"];
	
	(*-------------------------------------------------------
	3) calculating attractors. It returns decimal phi representation (inverse) of attractors
	-------------------------------------------------------
	*)
	cca = calculatingAttractors[locations, sumandos]["AttractorsByPosition"];
	atts = Keys[cca];
	(*transforming decimal representation attractors to binary representation*)
	atts = Reverse[IntegerDigits[#, 2, Length[cm]]] & /@ atts;
	attsPos = Values[cca];
	(*<|0 -> {0}, 1 -> {3, 4}, 3 -> {7}, 4 -> {1}, 5 -> {2, 6}, 7 -> {5}|>
	{{0, 0, 0} -> {0}, {1, 0, 0} -> {3, 4}, {1, 1, 0} -> {7}, {0, 0, 1} -> {1}, {1, 0, 1} -> {2, 6}, {1, 1, 1} -> {5}}
	*)
	
	
	(*-------------------------------------------------------
	4) Unconstrained future probability computation
	note on normalization: when not all possible patters are considered (i.e. only atts are considered)
	sum of probabilities < 1, then, normalization is necesary.
	-------------------------------------------------------
	*)
	(*all possible patterns considered to construct unconstrained fut prob distribution*)
	If[unconstr===0,
		patts = Table[Reverse[IntegerDigits[e, 2, Length[cm]]], {e, 0,2^Length[cm] - 1, 1}];
		attWithUncostProb = composeProbDistroFromBitProb4SetInputs[patts, fbupo]["PattsWithProb"];
		uncFutProb = Values[attWithUncostProb];
		(*if normalization*)
		If[norm===1,
			uncFutProb = uncFutProb*(1/Total[uncFutProb]);
			attWithUncostProb = Association[Thread[patts -> uncFutProb]];
		];
	];
	(*{0.09375, 0.28125, 0.03125, 0.09375, 0.09375, 0.28125, 0.03125,0.09375}*)
	
	(*ONLY ATTRACTORS*)
	If[unconstr===1,
		(*number of repetitions of a output/length of the set of all possible outputs*)
		uncFutProb = N[Length[#]/(2^Length[cm]) & /@ attsPos];
		(*normalization*)
		If[norm===1,
			uncFutProb = uncFutProb*(1/Total[uncFutProb]);
			attWithUncostProb = Association[Thread[atts -> uncFutProb]]
		];
	];
	(*{0.125, 0.25, 0.125, 0.125, 0.25, 0.125}*)
	
	(*this is, the general probability calculated only for attractors, then
	normalizing or not normalazing*)
	(*If[norm===0,
		(*of course, here there is not anything to do*)
		attWithUncostProb = composeProbDistroFromBitProb4SetInputs[atts, fbupo]["PattsWithProb"];
		uncFutProb = Values[attWithUncostProb];
	];*)
	(*If[norm===1,
		(*attWithUncostProb = composeProbDistroFromBitProb4SetInputs[atts, fbupo]["PattsWithProb"];
		uncFutProb = Values[attWithUncostProb];*)
		uncFutProb = uncFutProb*(1/Total[uncFutProb]);
		attWithUncostProb = Association[Thread[atts -> uncFutProb]];
	];*)
	
	(*
	-------------------------------------------------------
	5) Unconstrained past probability distribution computation
	-------------------------------------------------------
	*)
	uncPastProb = ConstantArray[N[1/(2^Length[cm])], 2^Length[cm]];
	
	<|
	"UnconstrFutProb"-> uncFutProb,
	"UnconstrPastProb"-> uncPastProb,
	"bitProbDistro4Outs"-> fbupo
	
	|>

];

(*
{unconstr_,wholeSys_,futDist_} referes to options: 1=Only for atts, 0= all possible pattern calculation
 + unconstr = Unconstrained future probability,
 + norm = general probability for attractors normalizated or not.
 + wholeSys = fut probability distribution for the whole system
 + futDist  = fut distribution calculated for a mechanism and a purview
 + vmOption = 0=all possible partition including emptyset, 1= only connected partitions

fbupo = full bit unconstrained probablity for outputs
*)
(*
computeSmallAlpha[cm_,dyn_,cs_,uncFutProb_,uncPastProb_,fbupo_,nodes4Mechas_,nodes4Purviews_,
	            {unconstr_,norm_,wholeSys_,futDist_,vmOption_}]:=
Module[
	{atts,(*vm,*)MIP,(*pastPdWSys,futPdWSys,allNodes,ciWSyS,eiWSys,*)
	iniPastInfoDiff,iniFutInfoDiff},
	
		
	(*-----------------------------------------------------;
	6) Create all possible partitions. These are mechanism and purviews
	-----------------------------------------------------;
	*)
	(*vm = createValidMechanisms[cm,vmOption]["ValidMechanisims"];*)
	
	
	(*-----------------------------------------------------;
	7) CEI for whole system
	   This is != than unconstrained probability distribution.
	-----------------------------------------------------;
	*)
	(*PAST prob distribution for the whole system*)
	(*
	allNodes=Range[Length[cm]];
	pastPdWSys = parentPastProbDistro[allNodes, cs, allNodes, dyn, cm]["ProbabilityDistribution"];
		
	(*FUTURE prob distribution for the whole system*)
	If[wholeSys===0,
		futPdWSys=createFutProbDistrFromOldBitProbDistr[allNodes,cs,allNodes, cm, dyn, fbupo]["ProbabilityDistribution"];
    ];
    
    (*ce whole system -only attractors-*)
    If[wholeSys===1,
    	futPdWSys = createFutProbDistrFromOldBitProbDistr[allNodes, cs, allNodes, cm, dyn, fbupo, atts]["UpdatedProbDistr"];
	];
		
	ciWSyS = EMD[uncPastProb, pastPdWSys]["Distance"];
	eiWSys = EMD[uncFutProb, futPdWSys]["Distance"];
	*)
	
	iniPastInfoDiff=100;
	iniFutInfoDiff=100;
	
	
	(*-----------------------------------------------------;
	8) Calculatin MIP
	For vm, it test all possible combinations between mechanisms and purviews
	and finds the couple [mecha, purview] that produce the Minimum Information Partition
	-----------------------------------------------------;
	*)
	
	(*MIP*)
	If[futDist===0,
		(*for all patterns*)
		MIP=findMIP[cm,dyn,cs,uncFutProb,uncPastProb,nodes4Mechas,nodes4Purviews, fbupo];,
		(*only for attractors*)
		MIP=findMIP[cm,dyn,cs,uncFutProb,uncPastProb,nodes4Mechas,nodes4Purviews, fbupo, atts];
	];
		
   	(*Print["phiCMIP:" <> ToString[phiCMIP]];
   	Print["phiEMIP:" <> ToString[phiEMIP]];
   	
   	
   	Print["ci: "];
   	Print[ciArray];
   	Print["ei: "];
   	Print[ceArray];
   	Print["cieArray: "];
   	Print[ceiArray];*)
   	
   	<|"pMIP"->MIP["pMIP"], "fMIP"-> MIP["fMIP"]
   	(*,"FutProbDistWholeSys"->futPdWSys,"PastProbDistWholeSys"->pastPdWSys, "ciWSys"->ciWSyS,
   	  "eiWSys"-> eiWSys*)
   	 |>
   	
   	
   
];
*)

testContainsElement[l1_,l2_]:= Module[
	{cl1,cl2,res(*,i*)},
	
	res = False;
	(*watch on the shorter list*)
	If[Length[l1]>Length[l2], 
		cl1=l1;
		cl2=l2;(*cl2=shorter*)
		,
		(*else*)
		cl1=l2;cl2=l1 
	];

	(*Testing if one element of a list is part of the other one*)
	(*
	For[i=1,i<=Length[cl1],i++,
		If[MemberQ[cl2,Part[cl1,i]],
			res=True;
			Break[];
		];
	];
	*)
	
	(*If[l1===l2,res=True];*)
	(*Testing whether one set is a subset of the other*)
	If[(Length[cl2]<Length[cl1])||(Length[cl2]===Length[cl1])
		,res=SubsetQ[l1,l2]
	];
	
	
	<|"Res"-> res|>

];





(*
The best optios for coonectivity test
---------------------------------------------------------------
cm03 = {{0, 1, 1, 1}, {1, 0, 1, 1}, {1, 1, 0, 1}, {1, 1, 1, 0}};
el = connMatrix2EdgeList[cm03]["EdgeList"];
g = Graph[el]
justConnectedQ[g]
--------------------------------------------------------------
*)
justConnectedQ[g_] := 
 With[{am = AdjacencyMatrix@TransitiveClosureGraph[g], 
   n = VertexCount[g]},
   Total[Unitize[am + Transpose[am]], 2] == n (n - 1)
 ];

(*
It divides mecha and purview into all possible partitions and test
every possible combination for strong connectivity
----------------------------------------------------------------
cm03 = {{0, 1, 1, 1}, {1, 0, 1, 1}, {1, 1, 0, 1}, {1, 1, 1, 0}};
el = connMatrix2EdgeList[cm03]["EdgeList"];
g = Graph[el]
testConnectedPartitions[{3, 1}, {1, 2, 3, 4}, g]
----------------------------------------------------------------
*)
testConnectedPartitions[mecha_,purview_,fullGraph_]:= Module[
	{connected, mechaParts, purviewParts, nodes},
	connected=True;
	mechaParts = Delete[Subsets[mecha],1];
	purviewParts=Delete[Subsets[purview],1];
	
	(*................. begin*)
	(*Print[".............................."];
	Print["Mecha parts: "<>ToString[mechaParts]];
	Print["Purview parts: "<>ToString[purviewParts]];*)
	(*................. end*)
	
	For[i=1, i<=Length[mechaParts],i++,
		For[j=1, j<=Length[purviewParts],j++,
			nodes = Join[Part[mechaParts,i],Part[purviewParts,j]];
			connected = ConnectedGraphQ[Subgraph[fullGraph,nodes]];
			(*................. begin*)
			(*Print["Testing connectivity on union: "<> ToString[nodes]];
			Print["Result: "<>ToString[connected]];*)
			(*................. end*)
			If[connected === False,Break[]];
		];
	];
	
	<|"Res"-> connected|>

];



loadUnconstrainedDistrosFromFile[parentPurview_]:=Module[
	{fileName,ln,str,found,lnComplete},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"UNCONSTRAINEDx" <> ToString[Length[parentPurview]]}];
							
	ln="Not Found";				
	found = False;
	lnComplete="";			
	
	If[FileExistsQ[fileName],	
				               
		str = OpenRead[fileName];
		
		While[ (found === False) && (lnComplete != ToString[EndOfFile]),
			ln="Not Found";
			lnComplete = ReadLine[str];
			
			If[lnComplete != ToString[EndOfFile],
				ln=ToExpression[lnComplete];
				ln=ln[[1]];
				If[ln===parentPurview, ln=lnComplete; found=True
					,
					found=False;
					ln="EndOfFile";
				];
				
			];
			
		];		
				
		Close[str];	
	];
	
	<|"Line"-> ln|>
	
	];

saveUnconstrainedDistroInFile[parentPurview_,uppd_,ufpd_]:=Module[
	{fileName,data,str},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"UNCONSTRAINEDx" <> ToString[Length[parentPurview]]}];
	If[FileExistsQ[fileName], str = OpenAppend[fileName],str = OpenWrite[fileName]];
	data={parentPurview,uppd,ufpd};
	WriteLine[str, ToString[data]];
	Close[str];
];




loadMIPFromFile[parentMecha_,parentPurview_]:=Module[
	{fileName,ln,searchedLine,str,lnComplete,found},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"MIPx" <> ToString[Length[parentMecha]]<>"x"<>ToString[Length[parentPurview]]}];
	
	ln="Not Found";						
	found = False;	
	lnComplete = "";
	searchedLine="";
	
	If[FileExistsQ[fileName],	
						
		searchedLine = "{"<>ToString[parentMecha] <> ", " <> ToString[parentPurview]<>"}";
		str = OpenRead[fileName];
				
		While[ (found === False) && (lnComplete != ToString[EndOfFile]),
			ln="Not Found";
			lnComplete = ReadLine[str];
			
			If[lnComplete!=ToString[EndOfFile],
				ln=ToExpression[lnComplete];
				ln=ToString[Extract[ln,{{1},{2}}]];
				If[ln===searchedLine, ln=lnComplete; found=True];
				,
				found=False;
				ln="EndOfFile";
			];
			
		];
		
		Close[str];	
	];
	
	<|"Line"-> ln|>
];

saveMIPInFile[parentMecha_,parentPur_,
			  pastChildMecha_, pastChildPurv_,ci_, 
			  futChildMecha_, futChildPurv_,ei_]:=Module[
	{fileName,data,str},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"MIPx" <> ToString[Length[parentMecha]]<>"x"<>ToString[Length[parentPur]]}];
	If[FileExistsQ[fileName], str = OpenAppend[fileName],str = OpenWrite[fileName]];
	data={parentMecha,parentPur,pastChildMecha,pastChildPurv,ci,futChildMecha,futChildPurv,ei};
	WriteLine[str, ToString[data]];
	Close[str];
];


loadWholeSysDistroFromFile[parentMecha_,parentPurview_,sysLength_]:=Module[
	{fileName,ln,searchedLine,str,found,lnComplete},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"WSDx" <> 
		                     ToString[Length[parentMecha]]<>"x"<>
		                     ToString[Length[parentPurview]]<>"x"<>
		                     ToString[sysLength]}];
							
	ln="Not Found";			
	found = False;	
	lnComplete = "";
	
	If[FileExistsQ[fileName],	
						
		searchedLine = "{"<>ToString[parentMecha]<>", "<>ToString[parentPurview]<>"}";
		
		str = OpenRead[fileName];		
		While[ (found === False) && (lnComplete != ToString[EndOfFile]),
			ln="Not Found";
			lnComplete = ReadLine[str];
			
			If[lnComplete!=ToString[EndOfFile],
				ln=ToExpression[lnComplete];
				ln=ToString[Extract[ln,{{1},{2}}]];
				If[ln===searchedLine, ln=lnComplete; found=True];
				,
				found=False;
				ln="EndOfFile";
			];
			
		];
		
		Close[str];	
	];
	
	
	<|"Line"-> ln|>
	
	];

saveWholeSysDistroInFile[parentMecha_,parentPur_,sysLength_,pDistro_,fDistro_,earth_]:=Module[
	{fileName,data,str},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"WSDx" <> 
		                     ToString[Length[parentMecha]]<>"x"<>
		                     ToString[Length[parentPur]]<>"x"<>
		                     ToString[sysLength]}];
	If[FileExistsQ[fileName], str = OpenAppend[fileName],str = OpenWrite[fileName]];
	data={parentMecha,parentPur,pDistro,fDistro,earth}; (*earth = sum[pEMD, fEMD]*)
	WriteLine[str, ToString[data]];
	Close[str];
];

deleteIntersection[mecha_,purview_]:=Module[
	{purviewAux=purview,mechaAux=mecha},
	 
	If[Length[purview] > Length[mecha]||Length[purview] === Length[mecha], 
	    purviewAux=DeleteCases[purviewAux, Alternatives @@ mecha];
	    ,
	    If[Length[mecha] > Length[purview], 
	      mechaAux=DeleteCases[mechaAux, Alternatives @@ purview];
	      ];
	  ];
	  
	  <|"Mecha"-> mechaAux, "Purview"-> purviewAux|>

];



(* mechanism is the master partition or master mecha to compute concept for*)
computeMIP[mechanism_, purview_,cm_,dyn_,cs_,fbupo_,fullGraph_]:=Module[
	{l1,l2,ln,pastWSDistro,futWSDistro,sAlpha,csMecha,cMechanism},
	
	cMechanism = mechanism;
	
	ln = loadMIPFromFile[mechanism, purview]["Line"];
		  If[(ln!="Not Found") && (ln!="EndOfFile"),
		  		l1={{},{},{},{},{},{},{}};
			  	l2={{},{},{},{},{},{},{}}; 
			  	l1[[1]]=ToExpression[ln][[3]];(*pastchildMecha*)
			  	l1[[2]]=ToExpression[ln][[4]];(*pastchildPurview*)
			  	l1[[5]]=ToExpression[ln][[5]];(*ci*)
			  	l2[[1]]=ToExpression[ln][[6]];(*futChildMecha*)
			  	l2[[2]]=ToExpression[ln][[7]];(*futChildPurv*)
			  	l2[[5]]=ToExpression[ln][[8]];(*ei*)
			  	sAlpha=Association["pMIP"-> l1, "fMIP"-> l2];
			  				  	
			  	(* begin ---------------------------*)			  	
			  	Print[sAlpha];
			  	Print["**MIP Found in File: "<>ToString[Min[l1[[5]],l2[[5]]]]];			  	
			  	(* end  ---------------------------*)				  	
			  	,					  	
			    (*Distros at the PARENT level with Length[oneParentPur]*)
			    (*TODO: Are these distributions used to compute conceptual information?*)
			    If[mechanism === {},cMechanism = Range[Length[cm]]];			    
			    csMecha = Extract[cs,Split[cMechanism]];
			    
			    (*mater mecha is used to compute the whole distribution*)
			    pastWSDistro = parentPastProbDistro[cMechanism, csMecha, purview, dyn, cm]["ProbabilityDistribution"];
			    futWSDistro = parentFutProbDistro[cMechanism, csMecha, purview, cm, dyn]["ProbabilityDistribution"];
			    (*small Alpha = MIP in a partition. Distros with Length[oneParentPur]*)  
			    sAlpha = findMIP[cm, dyn, cs, futWSDistro, pastWSDistro, mechanism, purview, fbupo, fullGraph];
			    
			    (* begin ---------------------------*)
			    (*Print[sAlpha];*)
			    (* end  ---------------------------*)
			    
		   ];
	
	<|"MIPStructure"-> sAlpha|>
	

];



selectBetweenTwoSAlphaStructures[sAlpha1_,sAlpha2_]:=Module[
	{master,slave},
	
	(*I just want to name a master an slave. Idealmente master[[5]] != 100*)
	If[sAlpha1["pMIP"][[5]]!=100 && sAlpha1["fMIP"][[5]]!=100,
		master = sAlpha1;slave = sAlpha2
			,
			If[(sAlpha2["pMIP"][[5]]===100 && sAlpha2["fMIP"][[5]]===100) &&
				(sAlpha1["pMIP"][[5]]===100 && sAlpha1["fMIP"][[5]]===100),
				master = sAlpha1;slave = sAlpha2
			];
	];
	
	(*if there is not alpha value, it makes it 0, and select
	partition where there was an small alpha value*)
	If[(slave["pMIP"][[5]] === 100) && master["pMIP"][[5]] != 100,
		slave["pMIP"] = master["pMIP"];
		slave[["pMIP",5]] = 0;
	];
	
	If[(slave["fMIP"][[5]] === 100) && master["fMIP"][[5]] != 100,
		slave["fMIP"] = master["fMIP"];
		slave[["fMIP",5]] = 0;
	];
	
	(*select the smaller alpha value*)
	If[(slave["pMIP"][[5]] != 100) && master["pMIP"][[5]] != 100,
		If[slave["pMIP"][[5]] > master["pMIP"][[5]],
			slave["pMIP"] = master["pMIP"]
		];		
	];
	
	If[(slave["fMIP"][[5]] != 100) && master["fMIP"][[5]] != 100,
		If[slave["fMIP"][[5]] > master["fMIP"][[5]],
			slave["fMIP"] = master["fMIP"]
		];		
	];
	
	
	<|"SelectedMIP"-> slave|>
	


];


(*
Find concept of a mechanism. This is, small phi, past and future is computed for each
possible purview (partition) of the whole system.
Concept is then, couple [mechanism, purview] that results in the highest value of smallphi
for a single mechanism.

intputs: mechanism (pivot for computation) and nodes of the whole system. From the nodes
of the system all possible partition is computed to form all possible purviews.

Update: 
pastt and future reference distros are those computed at partition level and not
to the whole system level. Then must be computed for pivot mecha and each purview.
*)
(* At this level mecha cannot be [ ] (the empty set). See fig 8 in main paper*)
computeConceptOfAMechanism[parentMecha_, systemNodes_,cm_, dyn_,cs_,fbupo_,pastWholeSysDistro_,
							futWholeSysDistr_,fullGraph_]:=
	                        
Module[
	{oneParentPur,parentPurviewsSet,ciRef,eiRef,maxPastSAlphaList,maxFutSAlphaList,
		copyPastPur,copyFutPur,i,sAlpha,subCS,csubCS,
		pd,fd,d1,d2,earth(*, parentPEMD, parentFEMD*),nodes,sg,contained1,connected1,
		subConnected1,contained2,connected2,subConnected2,minAlpha, pChildMecha, pChildPurv,
		fChildMecha, fChildPurv,cparentMecha,coneParentPur(*,mechComp, purComp, sAlpha1, sAlpha2*)},
	
	(*TODO: PurviewSet could be defined by function that compute valid partitions
	this is, under the view of connected graphs*)
	(*set of purviews is in PARENT level, this is the partition of the whole system*)
	(*At this level, empty set is not used (see fig 8 of main paper) *)
	parentPurviewsSet = Delete[Subsets[systemNodes],1];
	
	ciRef = 0;
	eiRef = 0;
	maxPastSAlphaList = List[];
	maxFutSAlphaList = List[];
	copyPastPur = {};
	copyFutPur = {};
	
	subCS = Extract[cs, Split[parentMecha]];
	
	(*compute smallAlpha for one mechanism vs all possible purviews*)
	For[i = 1, i <= Length[parentPurviewsSet], i++,
  
  		  (*PARENT level*)
  		  cparentMecha = parentMecha;
  		  csubCS = Extract[cs, Split[cparentMecha]];
		  oneParentPur = Part[parentPurviewsSet, i];
		  coneParentPur = oneParentPur;
		  
		  
		  
		  (*test of selfcontained at parent level*)
		  (*TODO If Length[oneParentPur and parentMecha] = Length[systemNodes] then exclude 
		  containment analysis but...
		  THINKING ON THAT, for me, it makes not any sense to ask how does 1 influences 1?, or
		  how does 2 influences 2, or even more, how does {1,2,3} influences {1,2,3}		  
		  *)
		  
		  
		  
		  (* begin ----------------------------*)
		  (*Print["**Processing "<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]];*)
		  (* end ----------------------------*)
		  
		  
		  nodes = DeleteDuplicates[Sort[Join[cparentMecha,oneParentPur]]];
		  sg = Subgraph[fullGraph,nodes];
		  contained1 = False;
		  connected1 = True;
		  subConnected1 = True;
		  (*probably CONTAINED only must to test if mecha and purview are the same*)
	  	  (*contained1 = testContainsElement[cparentMecha,oneParentPur]["Res"];*)
		  connected1 = ConnectedGraphQ[sg];
		  (*test of connectio at parent and child levels*)
		  subConnected1 = testConnectedPartitions[cparentMecha,oneParentPur, fullGraph]["Res"];
		  (*subConnected1 = connected1;*) (*I'll suppose if connected then subconnected*)
		  		  
		  
		  If[(contained1 === False) && (connected1===True) && (subConnected1 ===True),		  
				  (*REMOVE INTERSECTION BETWEEN MECHA AND PRUVIEW*)
				  (*aa = deleteIntersection[cparentMecha,oneParentPur];
				  cparentMecha = aa["Mecha"];
				  oneParentPur = aa["Purview"];
				  subCS = Extract[cs, Split[cparentMecha]];*)
							  
				  (*Print["**AS: "<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]];*)
		  
				  
				  If[Length[cparentMecha]>0 && Length[oneParentPur]>0,
					  nodes = Sort[Join[cparentMecha,oneParentPur]];
					  sg = Subgraph[fullGraph,nodes];
					  contained2 = False;
					  connected2 = True;
					  subConnected2 = True;
					  If[Length[cparentMecha]<= Length[systemNodes]/2,
					  	contained2 = testContainsElement[cparentMecha,oneParentPur]["Res"];
					  ];
					  connected2 = ConnectedGraphQ[sg];
					  subConnected2 = testConnectedPartitions[cparentMecha,oneParentPur, fullGraph]["Res"];
					  (*subConnected2 = connected2;*) (*I'll suppose if connected then subconnected*)
					  ,
					  connected2 = False;
					  contained2 = True;
					  subConnected2 = False;
				  ];
		 ];
		 
		 
		  (*Only if mecha + purview as subgraph is connected, then looks for MIP*)
		  If[((contained1 === False) && (connected1===True) && (subConnected1 ===True))
		  	 &&
		  	 ((contained2 === False) && (connected2===True) && (subConnected2 ===True))
		  	 ,
		  		  (* computes prob distributions for the whole system that in this case is represented
				     for the couple of evaluation: [mecha, purview].
				     Next two lines are used in case where reference probability distributios are not
				     provided as inputs to this function
				     
				     TODO: Add the case where prob distributions are calculted only for attractors.
				     this implies to append options of computation as input to this function.
				  *)
				  
				  (*considering that whole system  or reference prob distrubitions be that corresponding to
				  the system definited by the mechanism and purview in question
				  *)
				  
				  (*
				  If[coneParentPur != oneParentPur || cparentMecha != parentMecha,
				  	
				  		(*cparentMecha is the modified version of parentMecha*)
				  		If[(Length[parentMecha]>Length[cparentMecha]) && 
				  			(Length[coneParentPur]===Length[oneParentPur]),
				  			mechComp = Complement[parentMecha,cparentMecha];
				  			purComp = coneParentPur; (*coneParentPur = original*)
				  			aa = deleteIntersection[mechComp,purComp];
						    mechComp = aa["Mecha"];
						    purComp = aa["Purview"];
				  		];
				  		
				  		If[(Length[coneParentPur]>Length[oneParentPur]) && 
				  			(Length[cparentMecha]===Length[cparentMecha]),
				  			mechComp = cparentMecha;
				  			purComp = Complement[coneParentPur,oneParentPur];
				  			aa = deleteIntersection[mechComp,purComp];
						    mechComp = aa["Mecha"];
						    purComp = aa["Purview"];
				  		];
					  	
					  	Print["--------- Since CONVERTED, processing complement"];
					  	Print["-------------------------------------------"];
					  	
					  	(*cparentMecha is the modified, parentMecha is the original
					  	  oneParentPur is the modified, coneParentPur is the original
					  	*)
					  	If[mechComp!= {} && purComp !={},
					  		Print["--------- Computing in two partitions"];
					  		Print["--------- FIRST: "<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]];
						  	sAlpha1 = computeMIP[cparentMecha, oneParentPur,cm,dyn,cs,fbupo,fullGraph]["MIPStructure"];
						  	Print["--------- SECOND: "<> ToString[mechComp]<>", "<>ToString[purComp]];
						  	sAlpha2 = computeMIP[mechComp, purComp,cm,dyn,cs,fbupo,fullGraph]["MIPStructure"];	
						  	sAlpha = selectBetweenTwoSAlphaStructures[sAlpha1, sAlpha2]["SelectedMIP"];
						  	Print["--------- UPDATED ALPHA STRUCTURE: "];
						  	Print[sAlpha];
						  	,
						  	sAlpha = computeMIP[cparentMecha,oneParentPur,cm,dyn,cs,fbupo,fullGraph]["MIPStructure"];
						  	(*newMin = Min[sAlpha["pMIP"][[5]],sAlpha["fMIP"][[5]]];
						  	sAlpha[["pMIP",5]] = newMin;
						  	sAlpha[["fMIP",5]] = newMin;*)
						  	Print["--------- NEW ALPHA STRUCTURE: "<> ToString[sAlpha]];
					  	];
					  	
					  	If[sAlpha["pMIP"][[5]]!=100,	
						    saveMIPInFile[parentMecha,coneParentPur,sAlpha["pMIP"][[1]],sAlpha["pMIP"][[2]],
						    	          sAlpha["pMIP"][[5]],sAlpha["fMIP"][[1]],sAlpha["fMIP"][[2]],
						    	          sAlpha["fMIP"][[5]]];
					      ];
					      
					      ,
					      sAlpha = computeMIP[parentMecha,coneParentPur,cm,dyn,cs,fbupo,fullGraph]["MIPStructure"];
				  
				  ];
				  *)
				  sAlpha = computeMIP[cparentMecha,oneParentPur,cm,dyn,cs,fbupo,fullGraph]["MIPStructure"];
				  saveMIPInFile[parentMecha,coneParentPur,sAlpha["pMIP"][[1]],sAlpha["pMIP"][[2]],
						    	          sAlpha["pMIP"][[5]],sAlpha["fMIP"][[1]],sAlpha["fMIP"][[2]],
						    	          sAlpha["fMIP"][[5]]];
		   	      
		   	      
		   	      
		   	      If[(i===1)||(i>1 && Length[maxPastSAlphaList]===0),
		   	      	maxPastSAlphaList = sAlpha["pMIP"];
		   	      	maxFutSAlphaList = sAlpha["fMIP"];
		   	      ];
		   	      
				   
				  If[sAlpha["pMIP"][[5]] >= ciRef, (*MIP*)
				  	   (*mecha and purview at children level*)
				   
					   pChildMecha = sAlpha["pMIP"][[1]];
					   pChildPurv = sAlpha["pMIP"][[2]];
					   ciRef = sAlpha["pMIP"][[5]];
					   maxPastSAlphaList = sAlpha["pMIP"];
					   (*purview at parent level*)
					   copyPastPur = oneParentPur;
					   (*parentPEMD = EMD[pastWSDistro,pastRefProbDistro]["Distance"];*)
				   ];
				   
				   If[sAlpha["fMIP"][[5]] >= eiRef,
				   	  (*mecha and purview at children level*)
				   	  
					   fChildMecha = sAlpha["fMIP"][[1]];
				  	   fChildPurv = sAlpha["fMIP"][[2]];
					   eiRef = sAlpha["fMIP"][[5]];
					   maxFutSAlphaList = sAlpha["fMIP"];
					   (*purview at parent level*)
					   copyFutPur = oneParentPur;
					   (*parentFEMD = EMD[futWSDistro,futRefProbDistro]["Distance"];*)
				   ];
				   (* begin ---------------------------*)
				   
				   (*Print["ceiRef: {"<>ToString[ciRef]<>","<>ToString[eiRef]<>"}"];
				   Print["=============================================================="];*)
				   
				   (* end  ---------------------------*)	
			
			  (*Else, this is, if is a disconected subgraph: *)	   
			  (* begin ---------------------------*)
			  
			  (*
			  ,
			  If[connected1===False,Print["-------Disconected before reduction "<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]] ];
			  If[subConnected1===False,Print["-------Disconected before reduction internally"<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]] ];
			  If[contained1===True, Print["-------Self Contained before reduction"<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]]];
			  If[connected2===False,Print["-------Disconected after reduction "<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]] ];
			  If[subConnected2===False,Print["-------Disconected after reduction internally"<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]] ];
			  If[contained2===True, Print["-------Self Contained after reduction"<> ToString[cparentMecha]<>", "<>ToString[oneParentPur]]];
			  *)
			  (* end  ---------------------------*)		  		  
		  ];(*If[ConnectedGraphQ[sg],*)
		  	  
  	];(*For[i = 1, i <= Length[parentPurviewsSet]*)
  	
  	(*
  	HERE I HAVE TO LOAD/SAVE DISTROS FOR WHOLE SYSTEM WITH PARENT MECHA AND COPY PAST/FUT PURVIEWS
  	*)
  	If[copyPastPur != {} && copyFutPur != {},
  		
  		ln=loadWholeSysDistroFromFile[cparentMecha,copyPastPur,Length[systemNodes]]["Line"];
  		If[ln!="Not Found"&&ln!=ToString[EndOfFile],
  			earth=ToExpression[ln][[5]];
  			,  		
  			subCS = Extract[cs, Split[cparentMecha]];
		  	pd = pastProbDistroWholeSysRef[cparentMecha, subCS, copyPastPur, dyn, cm]["ProbabilityDistribution"];
		  	fd = futureProbDistroWholeSysRef[cparentMecha, subCS, copyFutPur, cm, dyn, fbupo]["ProbabilityDistribution"];
		  	d1 = EMD[pastWholeSysDistro, pd]["Distance"];
		  	d2 = EMD[futWholeSysDistr, fd]["Distance"];
		  	earth = d1 + d2;
		  	saveWholeSysDistroInFile[cparentMecha,copyPastPur,Length[systemNodes],pd,fd,earth];
  		];
  	];
	
	If[Length[maxPastSAlphaList]>1 && Length[maxFutSAlphaList]>1,
		minAlpha=Min[maxPastSAlphaList[[5]],maxFutSAlphaList[[5]]];
		,
		minAlpha={};
	];
	
	
	
	<|
	
	"PastChildMecha"-> pChildMecha,
	"PastChildPurv"-> pChildPurv,
	"FutChildMecha"-> fChildMecha,
	"FutChildPurv"-> fChildPurv,
	"ParentMecha"->cparentMecha, 
	"ParentPastPurview"-> copyPastPur, 
	"ParentFutPurview"-> copyFutPur,
	"MinAlpha"->minAlpha,
	"Earth"-> earth
	 |>
	
];


loadConceptFromFile[parentMecha_]:=Module[
	{fileName,ln,found,str,lnComplete},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"Cx" <> 
		                     ToString[Length[parentMecha]]}];
							
	ln="Not Found";
	found = False;			
	
	If[FileExistsQ[fileName],	
		
		str = OpenRead[fileName];
		
		While[ (found === False) && (lnComplete != ToString[EndOfFile]),
			ln="Not Found";
			lnComplete = ReadLine[str];
			
			If[lnComplete != ToString[EndOfFile],
				ln=ToExpression[lnComplete];
				ln=ln[[1]];
				If[ln===parentMecha, ln=lnComplete; found=True
					,
					found=False;
					ln="EndOfFile";
				];
				
			];
			
		];		
				
		Close[str];
	];
	(*returns an string*)
	<|"Line"-> ln|>
	
	];

saveConceptInFile[parentMecha_,parentPastPur_,parentFutPurv_,minAlpha_,pastChildMecha_,
	              PastChildPurv_,FutChildMecha_,FutChildPurv_,earth_]:=Module[
	{fileName,data,str},
	
	fileName = FileNameJoin[{$TemporaryDirectory,"Cx" <> 
		                     ToString[Length[parentMecha]]}];
		                     
	If[FileExistsQ[fileName], str = OpenAppend[fileName],str = OpenWrite[fileName]];
	data={parentMecha,parentPastPur,parentFutPurv,minAlpha,pastChildMecha,
	              PastChildPurv,FutChildMecha,FutChildPurv,earth};
	              
	WriteLine[str, ToString[data]];
	Close[str];
];




(* Conceptual information is the distance between unconstrained distros
and the distribution of probabilities of parent mechanism and purview.

the "parent" term here refers to the partition that define a concept. See figure 10 in 
main paper. Child term refers to the partition of parent partition where max phi value
is found.

sysFbupo full bit unconstrained probability Distribution for Outputs
*)
computeConceptualSpace[sysNodes_,pastRefProbDistro_, futRefProbDistro_,
								  cm_, dyn_,cs_,sysFbupo_,opt_]:= (*opt = 1 -> test strong connection, 0-> no test*) 
    Module[
	{mechaSet,constell,i,aChildMecha,oneConcept,conceptStructure,el,g,CI, concepts,
	alphas, distances,connected,conceptConnected,ln},
	
	(*TODO: Mechanisms Set could be defined by the function that computes the
	valid partitions, this is, under the view of connected graphs*)
	mechaSet = Delete[Subsets[sysNodes],1];
	constell = List[];
	
	(*create full graph*)
	el = connMatrix2EdgeList[cm]["EdgeList"];
	g = Graph[el];
	
	
	
	(*Only if the connection test is activated, this is executed, if not,
	performs computation*)
	If[opt===1,		
		connected = ConnectedGraphQ[g];
		, 
		connected = True
	];
	
	Print["*******************************************************"];				
	Print["COMPUTING CONCEPTUAL STRUCTURE: " <> ToString[Length[mechaSet]] <> " CONCEPTS"];
	Print["*******************************************************"];
	
	(*only full connected graphs are calculated, otherwise alpha = 0*)
	If[connected,
			(*Monitor[i=0;*)
			(*takes nodes of whole system and divides in all possible mechanism*)
			For[i=1, i<= Length[mechaSet],i++,
				(*it takes one (PARENT) mecha. One parent mecha defines one concept
				this is, there is a (potential) concept per each parent mecha*)
				aChildMecha = Part[mechaSet,i];
				
				(*one mechanism is tested against all possible purviews. This is
				all possible partitions of the whole sys in order to find concepts
				*)
				
				Print["*******************************************************"];				
				Print["COMPUTING CONCEPT "<> ToString[i]<> " of " <> ToString[Length[mechaSet]]];
				Print[ToString[aChildMecha]];
				Print["*******************************************************"];
								
				(*test if a parent mecha is connected*)
				conceptConnected = testConnectedPartitions[aChildMecha,sysNodes,g]["Res"];
				(*If ConnectedGraphQ was True, then are all partitions connected?? I`ll suppose
				that yes *)
				(*conceptConnected = True;*)
				
				(*
				If[conceptConnected===False, 
					Print["{"<>ToString[aChildMecha]<>","<>ToString[sysNodes]<>"}"<>" Disconnected partition"]
					,
					Print["---Processing: "<>"{"<>ToString[aChildMecha]<>","<>ToString[sysNodes]<>"}---"];
				];
				*)
				
				oneConcept = List[];
				conceptStructure = List[];
				
				If[conceptConnected,
					ln=loadConceptFromFile[aChildMecha]["Line"];
					If[(ln!="Not Found") && (ln!="EndOfFile"),
						conceptStructure = {{},{},{},{},{},{},{},{},{},{}};
						conceptStructure[[1]] = ToExpression[ln][[1]];
				        conceptStructure[[2]] = ToExpression[ln][[2]];
				        conceptStructure[[3]] = ToExpression[ln][[3]];
				        conceptStructure[[4]] = ToExpression[ln][[4]];
				        conceptStructure[[5]] = ToExpression[ln][[5]];
				        conceptStructure[[6]] = ToExpression[ln][[6]];
				        conceptStructure[[7]] = ToExpression[ln][[7]];
				        conceptStructure[[8]] = ToExpression[ln][[8]];
				        conceptStructure[[9]] = ToExpression[ln][[9]];
				        ,
				        (*aChildMecha is here the master mecha for concept computation*)
				        oneConcept=computeConceptOfAMechanism[aChildMecha,sysNodes,cm,dyn,cs,sysFbupo,pastRefProbDistro,
									futRefProbDistro,g];
						saveConceptInFile[oneConcept["ParentMecha"],oneConcept["ParentPastPurview"],
							              oneConcept["ParentFutPurview"],oneConcept["MinAlpha"],
							              oneConcept["PastChildMecha"],oneConcept["PastChildPurv"],
							              oneConcept["FutChildMecha"],oneConcept["FutChildPurv"],
							              oneConcept["Earth"]];
						
					];

					(*,
					Print["CONCEPT DISCONNECTED"];
					*)
				
				];(*If[oneConcept["MaxAlpha"] >0*)
				
					(* begin -----------------------*)					
					(*Print["MinAlpha: "<> ToString[oneConcept["MinAlpha"]]];*)
					(* end   -----------------------*)
					
					(*only > 0 count as concept*)
					If[Length[oneConcept] >0 && conceptConnected,
						
						conceptStructure = {{},{},{},{},{},{},{},{},{},{}};
				        conceptStructure[[1]] = oneConcept["ParentMecha"];
				        conceptStructure[[2]] = oneConcept["ParentPastPurview"];
				        conceptStructure[[3]] = oneConcept["ParentFutPurview"];
				        conceptStructure[[4]] = oneConcept["MinAlpha"];
				        conceptStructure[[5]] = oneConcept["PastChildMecha"]; (*ChildPastMecha*)
				        conceptStructure[[6]] = oneConcept["PastChildPurv"]; (*childPastPur*)
				        conceptStructure[[7]] = oneConcept["FutChildMecha"];  (*childFutMecha*)
				        conceptStructure[[8]] = oneConcept["FutChildPurv"];  (*childFutPurx*)
				        conceptStructure[[9]] = oneConcept["Earth"];  (*childFutPurx*)

					];
					
					(*
					Print["****************************"];
			        If[conceptConnected,Print[conceptStructure], Print["EMPTY CONCEPT"]];
			        Print["****************************"];
			        *)
			        If[Length[conceptStructure]>0 && conceptStructure[[4]]<100 && conceptStructure[[4]]>0., AppendTo[constell,conceptStructure]];
				
			];(*For[i=1, i<= Length[mechasSet]*)(*,ProgressIndicator[i,{0,Length[mechaSet]}]];*)
	,
	(*else, this is g is not a full connected graph, then alpha = 0*)
	Print["Alpha = 0 (Not fully connected)"];
	];(*If[ConnectedGraphQ[g],*)
	

	
	
	(*
	values = constell[[All, 5]];
	partitions = constell[[All, 1]];
	
	sumas = List[];
	
	(*a single nodo is not a partiton accoding with code of Tononi*)
	(*Here, values = conceptual information by concept. When subsets are computed
	I try to find distances of partition of concepts (Xemd). Then, min distance
	is equal to bigAlpha value*)
	If[Length[#] > 1, AppendTo[sumas, Total[#]]] & /@ Delete[Subsets[values], 1];
	(*AppendTo[sumas, Total[#]] & /@ Delete[Subsets[values], 1];*)
	sumas = sumas /. Null -> Sequence[];
	bigAlpha=Min[sumas];
	*)
	
	 (*mechanisms where a concept was found*)	
	 concepts = constell[[All,1]];
	 (*alphas values for each concept*)
	 alphas=constell[[All,4]];
	 (*EMD[concept,unrestricted distribution]*)
	 distances = constell[[All,9]];
	 
	 CI = Total[alphas*distances];
	 
	 
	 
	<|"Conste"-> constell,"ConceptualInformation"-> CI,"Concepts"->concepts,
	"Alphas"-> alphas, "Distances"-> distances|> 

];


makeCut[cm_, cut_] := Module[
   {toDelete, copyCM, from},
   copyCM = cm;
   toDelete = cut[[1]];
   from = cut[[2]];
   
   For[i = 1, i <= Length[from], i++,
    For[j = 1, j <= Length[toDelete], j++,
      If[copyCM[[from[[i]]]][[toDelete[[j]]]] === 1, 
      		copyCM[[from[[i]]]] = ReplacePart[copyCM[[from[[i]]]], toDelete[[j]] -> 0]];
      ];
    ];
   
   <|"NewCM" -> copyCM|>
];


(* *********************************************  
	                 QUEYRANNE -begin-
   *********************************************
*)
sfoUniqueFast[A_]:=Module[
	{aa},
	If[Length[A]>1,
   		aa = Sort[DeleteDuplicates[A]],
   		aa=A;
   	];
   	<|"C"-> aa|>
];



sfoSetdiffFast[A_, B_] := Module[
   {AA, BB, C},
   If[Length[B] > Length[A],
    	AA = B; BB = A;, 
    	AA = A; BB = B;
    ];
    
    If[Length[B] === 0,BB=List[B]];
    If[Length[A] === 0,AA=List[A]];
    
    C=Complement[AA, BB];
    
    <|"C"-> C|>
   ];


evalCutFn[G_, A_] := Module[
   {aa, n, aux1, aux2, aux},
   If[Length[A]>1,aux= Flatten[A], aux=A ];
   aa=sfoUniqueFast[aux]["C"];
   n = Length[G[[1]]];
   aux1=Flatten[List[Part[G, aa, sfoSetdiffFast[Range[n], aa]["C"]]]];
   aux2=Total[aux1];
   <|"C"-> aux2|>
   ];

mySfoPendentpair[G_, V_, S_] := Module[
   {x, vnew, n, Wi, used, vold, i, keys, one, two, three, four, j,
    argmin,s,t},
   x = 1;
   vnew = V[[x]];
   n = Length[V];
   Wi = List[];
   used = ConstantArray[0, n];
   used[[x]] = 1;
   (*
   Print["==========================================="];
   Print["            THIS IS THE BEGGINING          "];
   Print["==========================================="];
   *)
   For[i = 1, i <= (n - 1), i++,
    	vold = vnew;
    	Wi = Flatten[{Wi, vold}];
    	keys = (1*^3)*ConstantArray[1, n];
    	
    	(*
    	Print["******************"];
    	Print["    ROUND "<> ToString[i]];
    	Print["******************"];
    	*)
    
    	For[j = 1, j <= n, j++,
     		If[used[[j]] === 1,
       		Continue[],
       		one = Flatten[{Wi, V[[j]]}];
       		two = V[[j]];
       		Parallelize[three = evalCutFn[G,S[[one]]]["C"]];
       		Parallelize[four = evalCutFn[G,S[[two]]]["C"]];
       		keys[[j]] = three - four;
       		keys=Flatten[keys];
       		(*
       		Print["-------------"<>ToString[j]];
       		Print["one: "<> ToString[one]];
       		Print["Two: "<> ToString[two]];
       		Print["three: "<>ToString[three]];
       		Print["four: "<>ToString[four]];
       		Print["keys("<>ToString[j]<>")= "<>ToString[keys[[j]]]];
       		*)
       	     ];
     	];
    	argmin = Sort[ Flatten[Position[keys, Min[keys]]]][[1]];
    	vnew = V[[argmin]];
    	used[[argmin]] = 1;
    ];
   
   s = vold;
   t = vnew;
   <|"s"-> s,
     "t"->t|>
];
   
mySfoQueyranne[G_] := Module[
   {n, S, s, A, inew, h, pendentPair, t, u, i, R, uno, dos,tres,V},
   V = Range[Length[G[[1]]]];
   n = Length[V];
   S = List[];
   S = V;
   s = ConstantArray[0, n - 1];
   (*A = List[];*)
   A = ConstantArray[List[],n];
   inew = Range[n];
   For[h = 1, h <= (n - 1), h++,
    	(* Fnew[AA_] := F[S[[AA]]];*)
    	Parallelize[pendentPair = mySfoPendentpair[G, inew, S]];
    	u = pendentPair["t"];
    	t = pendentPair["s"];
        
    	(*A = AppendTo[A,S[[u]]];*)
    	A[[h]] = S[[u]];
    	s[[h]] = evalCutFn[G,u]["C"];
    	uno={};
    	dos={};
    	tres={};
    	uno = S[[t]];
    	dos = S[[u]];
    	tres = {uno, dos};
    	S[[t]] = Flatten[tres];
    	inew = sfoSetdiffFast[inew, u]["C"];
    	S[[u]] = S[[u]]*-1;
    ];
   
   i = Sort[Flatten[Position[s, Min[s]]]][[1]];
   R = A[[i]]
];

(* *********************************************  
	                 QUEYRANNE -end-
   *********************************************
*)



(* *********************************************  
	                 HECTOR'S CODE -begin-
   *********************************************
*)


BDM[array_, dim_Integer: 4] := 
 If[TrueQ[Min[Dimensions[array]] < dim], 
  BDM[array, Min[Dimensions[array]]], 
  First[Block[{part = Partition[array, {dim, dim}]}, 
    Total[{Log[2, #[[2]]] + #[[
          1]]} & /@ ({HashSquares[#[[1]]], #[[2]]} & /@ 
        Tally[Flatten[part, 1]])]]]];
        
CalculateInformationEdgesBDM[cm_] := 
 Module[{mutatedgraphs,g,graph},
    
    g =  connMatrix2EdgeList[cm]["EdgeList"];
  graph = Graph[g];
  
  mutatedgraphs = 
    AdjacencyMatrix /@ (EdgeDelete[graph, #] & /@ EdgeList[graph]);
     
  Reverse[SortBy[
    Thread[{EdgeList[graph], 
      BDM[AdjacencyMatrix@graph] - (N /@ BDM[#] & /@ mutatedgraphs)}],
     Last]]];
     
     
CalculateInformationEdgesCompress[cm_] := 
 Module[
 {mutatedgraphs,g, graph}, 

  g =  connMatrix2EdgeList[cm]["EdgeList"];
  graph = Graph[g]; 
  SetDirectory["/Users/beto/WolframWorkspaces/Base/Alpha"];
  reducedD2 = << "squares2Dsize1to4.m";
  Clear[reducedD2];
  
  mutatedgraphs = AdjacencyMatrix /@ (EdgeDelete[graph, #] & /@ EdgeList[graph]);

  
  Reverse[SortBy[
    Thread[{EdgeList[graph], 
      ByteCount@
        Compress[AdjacencyMatrix@graph, 
         4] - (ByteCount@Compress[#, 4] & /@ mutatedgraphs)}], Last]];     
  ];
        
        
        



(* *********************************************  
	                 HECTOR'S CODE  -end-
   *********************************************
*)



computeBigAlpha[sysNodes_,cm_,dyn_,cs_,concepts_,alphas_,distances_,pastRefProbDistro_, 
	            futRefProbDistro_, sysFbupo_]:=Module[
	{alphaValue,oneCut,cutConcepts,
	conceptsRemained,posConceptsRemained,places,alphaCut,
	alphaMIP,w,cmWithCut,fCutPart,sCutPart
	(*,
	revOneCut,revCutConcepts,revConceptsRemained,posRevConceptsRemained,revCMWithCut,
	alphaRevCut,cuts,i*)
	
	
	},
	
		
	alphaValue = 1000;
	(*Test/loading for Combinatorica*)
	
	(*
	If[!(MemberQ[$Packages,"Combinatorica`"]),
		Block[{$ContextPath}, Needs["Combinatorica`"]]
		(*,Print["Combinatorica is already loaded"]*)
	];
	
	(*create cuts
	  example:
	  cuts = Combinatorica`KSetPartitions[Range[3], 2]
	  {{{1}, {2, 3}}, {{1, 2}, {3}}, {{1, 3}, {2}}}
	*)
	cuts = Combinatorica`KSetPartitions[sysNodes, 2];
	
	For[i=1,i<=Length[cuts],i++,
		
		Print["******************************************"];
		Print["PROCESSING CUT COUPLE " <> ToString[i*2] <> " of " <> ToString[Length[cuts]*2]];
		Print["******************************************"];
		
		oneCut = Part[cuts,i];
		revOneCut = Reverse[oneCut];
		
		cmWithCut = makeCut[cm,oneCut]["NewCM"];
		revCMWithCut = makeCut[cm, revOneCut]["NewCM"];
		
		
		(* begin -----------------------*)
		(*
		Print["------------------------------------------"];
		Print["PROCESSING CUT: " <> ToString[oneCut]];
		Print["------------------------------------------"];
		*)
		(* end   -----------------------*)
		(*Connectivity test unabeled (opt=0)*)
		cutConcepts = computeConceptualSpace[sysNodes,pastRefProbDistro,futRefProbDistro,cmWithCut,dyn,cs,sysFbupo,0]["Concepts"];
		(* begin -----------------------*)
		(*
		Print["------------------------------------------"];
		Print["PROCESSING REVERSE CUT: " <> ToString[revOneCut]];
		Print["------------------------------------------"];
		*)
		(* end   -----------------------*)
		revCutConcepts = computeConceptualSpace[sysNodes,pastRefProbDistro,futRefProbDistro,revCMWithCut,dyn,cs,sysFbupo,0]["Concepts"];
		
		conceptsRemained = Complement[concepts, cutConcepts];
		revConceptsRemained = Complement[concepts, revCutConcepts];
		
		posConceptsRemained = Flatten[Table[Position[concepts,Part[conceptsRemained,w]],{w,1,Length[conceptsRemained],1}]];
		posRevConceptsRemained = Flatten[Table[Position[concepts,Part[revConceptsRemained,w]],{w,1,Length[revConceptsRemained],1}]];
		
		places = Split[posConceptsRemained];
		alphaCut=Total[Extract[alphas,places]*Extract[distances,places]];
		places = Split[posRevConceptsRemained];
		alphaRevCut=Total[Extract[alphas,places]*Extract[distances,places]];
		
		alphaMIP = Max[alphaCut,alphaRevCut];
		If[alphaMIP<alphaValue, alphaValue= alphaMIP];
			
		
	];
	*)
	
	
	fCutPart=mySfoQueyranne[cm];
	If[Length[fCutPart]===0,fCutPart={fCutPart}];
	sCutPart=Complement[sysNodes,fCutPart];
	oneCut={fCutPart,sCutPart};
	cmWithCut = makeCut[cm,oneCut]["NewCM"];
	cutConcepts = computeConceptualSpace[sysNodes,pastRefProbDistro,futRefProbDistro,cmWithCut,dyn,cs,sysFbupo,0]["Concepts"];
	conceptsRemained = Complement[concepts, cutConcepts];
	posConceptsRemained = Flatten[Table[Position[concepts,Part[conceptsRemained,w]],{w,1,Length[conceptsRemained],1}]];
	places = Split[posConceptsRemained];
	alphaCut=Total[Extract[alphas,places]*Extract[distances,places]];
	
	alphaMIP=alphaCut;
	If[alphaMIP<alphaValue, alphaValue= alphaMIP];
	
	
	
	(*
	revOneCut = Reverse[oneCut];
	revCMWithCut = makeCut[cm, revOneCut]["NewCM"];
	revCutConcepts = computeConceptualSpace[sysNodes,pastRefProbDistro,futRefProbDistro,revCMWithCut,dyn,cs,sysFbupo,0]["Concepts"];
	revConceptsRemained = Complement[concepts, revCutConcepts];
	posRevConceptsRemained = Flatten[Table[Position[concepts,Part[revConceptsRemained,w]],{w,1,Length[revConceptsRemained],1}]];
	places = Split[posRevConceptsRemained];
	alphaRevCut=Total[Extract[alphas,places]*Extract[distances,places]];
		
	alphaMIP = Max[alphaCut,alphaRevCut];
	If[alphaMIP<alphaValue, alphaValue= alphaMIP];*)
	
    
	
	
	<|"Alpha"->alphaValue|>
	
];



IntegratedInformation[cm_,dyn_,cs_]:=Module[
	{unconstrDistros,allOptions,pastUnconstrDistr,futUnconstrDistr,fbupo,mechaPivot,conceptualSpace,concepts,alphas,
	distances,alpha},
	allOptions = {0, 0, 0, 0, 0};
	unconstrDistros = computeUnconstrainedDistros[cm, dyn, cs, allOptions];
	pastUnconstrDistr = unconstrDistros["UnconstrPastProb"];
	futUnconstrDistr = unconstrDistros["UnconstrFutProb"];
	fbupo = unconstrDistros["bitProbDistro4Outs"];
	mechaPivot = Range[Length[cm]];
	conceptualSpace= computeConceptualSpace[mechaPivot, pastUnconstrDistr, futUnconstrDistr, cm, dyn, cs, fbupo, 1]["Conste"];
	concepts = conceptualSpace[[All, 1]];
	alphas = conceptualSpace[[All, 4]];
	distances = conceptualSpace[[All, 9]];
	alpha=computeBigAlpha[mechaPivot, cm, dyn, cs, concepts, alphas, distances, pastUnconstrDistr, futUnconstrDistr,fbupo]["Alpha"];
	
	<|"Alpha"-> alpha|>
];



IIandBDM[cm_]:= Module[
	{dyn,input,cs,ii,outs,image},
	dyn=createRandomDynamic[Length[cm]]["Dynamic"];
	input=createBinRandomInput[Length[cm]];
	cs=calculateOneOutptuOfNetwork[input,cm,dyn]["Output"];
	(*ii=IntegratedInformation[cm,dyn,cs]["Alpha"];*)
	outs = runDynamic[cm, dyn]["RepertoireOutputs"];
	ii=pyII[outs,cm,cs]["II"];
	(*Print["Integrated Information: "<> ToString[ii]];*)
	image=ListLinePlot[Last /@ CalculateInformationEdgesBDM[cm],PlotStyle -> Thick, AspectRatio -> 1/2, Frame -> True,
		ImageSize -> 300, PlotRange -> All];
	<|"II"-> ii, "BDM"-> image,"Dynamic"-> dyn|>
];



IIandBDM[cm_,dyn_]:= Module[
	{input,cs,ii,outs,image},
	input=createBinRandomInput[Length[cm]];
	cs=calculateOneOutptuOfNetwork[input,cm,dyn]["Output"];
	(*ii=IntegratedInformation[cm,dyn,cs]["Alpha"];*)
	outs = runDynamic[cm, dyn]["RepertoireOutputs"];
	ii=pyII[outs,cm,cs]["II"];
	(*Print["Integrated Information: "<> ToString[ii]];*)
	image=ListLinePlot[Last /@ CalculateInformationEdgesBDM[cm],PlotStyle -> Thick, AspectRatio -> 1/2, Frame -> True,
		ImageSize -> 300, PlotRange -> All];
	<|"II"-> ii, "BDM"-> image,"Dynamic"-> dyn|>
];




myDynamic[start_,end_]:= Module[
{},
	Dynamic myChangingNumber;
	myChangingNumber = start;
	For[i=start, i<=end,i++,
		myChangingNumber = myChangingNumber +1
	];

];
