AppendTo[$Path, "src/Packages"];
Needs["Integration`Experiments`"];
base = FileNameJoin[{"results", "tests", "mixed001OnPossibleBehaviour"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
predictiveEval[v_List, Ic_List, gate_String, params_Association] := Which[
  gate === "OR", Boole[MemberQ[v[[Ic]], 1]],
  gate === "AND", Boole[FreeQ[v[[Ic]], 0] && Length[v[[Ic]]]>0],
  gate === "XOR", Mod[Total[v[[Ic]]], 2],
  gate === "XNOR", 1 - Mod[Total[v[[Ic]]], 2],
  gate === "NAND", Boole[MemberQ[v[[Ic]], 0]],
  gate === "NOR", Boole[FreeQ[v[[Ic]], 1]],
  gate === "NOT", Module[{i = Lookup[params, "i", If[Length[Ic]==1, Ic[[1]], Ic[[1]]]]}, 1 - v[[i]]],
  gate === "IMPLIES" || gate === "NIMPLIES", Module[{pair = Lookup[params, "pair", If[Length[Ic] >= 2, {Ic[[1]], Ic[[2]]}, {Ic[[1]], Ic[[1]]}]], a, b}, a = v[[pair[[1]]]]; b = v[[pair[[2]]]]; If[gate === "IMPLIES", Boole[(1 - a) == 1 || b == 1], Boole[a == 1 && b == 0]]],
  gate === "MAJORITY", Boole[Total[v[[Ic]]] >= Ceiling[Length[Ic]/2]],
  gate === "KOFN", Module[{k = Lookup[params, "k", 1], strict = TrueQ[Lookup[params, "strict", False]]}, If[strict, Boole[Count[v[[Ic]], 1] > k], Boole[Count[v[[Ic]], 1] >= k]]],
  gate === "CANALISING", Module[{ci = Lookup[params, "canalisingIndex", If[Length[Ic] >= 1, Ic[[1]], Ic[[1]]]], vcan = Lookup[params, "canalisingValue", 1], cout = Lookup[params, "canalisedOutput", 0]}, If[v[[ci]] == vcan, cout, Boole[MemberQ[v[[Ic]], 1]]]],
  True, 0
];
inputsFor[n_Integer] := IntegerDigits[Range[0, 2^n - 1], 2, n];
onPossibleBehaviour[cm_List, dyn_List, target_Integer, params_Association:<||>, inputs_List:Automatic] := Module[{n = Length[dyn], inps, Ic = Flatten@Position[cm[[target]], 1], p = Lookup[params, target, <||>], zeros, decRep, offs},
  inps = If[inputs === Automatic, inputsFor[n], inputs];
  zeros = Select[Range[Length[inps]], predictiveEval[inps[[#]], Ic, dyn[[target]], p] == 0 &];
  decRep = 2^(Ic - 1);
  offs = zeros - 1; (* j-1 offsets for zero outputs *)
  <|"DecimalRepertoire" -> decRep, "Summands" -> offs|>
];
givePlaces[beh_Association] := beh["Summands"] + 1;

(* Define a sophisticated 10-node network using the full catalogue; target node 4 *)
cm10 = {
  {0,1,1,0,0,0,0,0,0,0},
  {1,0,1,0,0,0,0,0,0,0},
  {0,0,0,1,1,0,0,0,0,0},
  {0,1,1,0,1,0,0,0,0,0},
  {0,0,0,0,0,1,0,0,0,0},
  {0,0,0,0,1,0,1,0,0,0},
  {0,0,0,0,0,1,0,0,0,0},
  {1,0,0,0,0,0,0,0,1,0},
  {0,1,0,0,0,0,0,0,0,1},
  {0,0,1,1,0,0,1,1,0,0}
};
dyn10 = {"AND","OR","XOR","KOFN","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY"};
params10 = <|4 -> <|"k" -> 2|>|>; (* Node 4 is KOFN with k=2 *)

(* Baseline computation *)
res10 = Integration`Experiments`CreateRepertoiresDispatch[cm10, dyn10, params10];
inputs10 = res10["RepertoireInputs"]; outputs10 = res10["RepertoireOutputs"];
zerosBaseline = Flatten@Position[outputs10[[All, 4]], 0];

(* Predictive behaviour and places for node 4 = 0 *)
beh = onPossibleBehaviour[cm10, dyn10, 4, params10, inputs10];
places = givePlaces[beh];

ok = Sort[places] === Sort[zerosBaseline];
Export[FileNameJoin[{base, "Behaviour.json"}], beh // Normal, "JSON"];
Export[FileNameJoin[{base, "Places.json"}], places, "JSON"];
Export[FileNameJoin[{base, "ZerosBaseline.json"}], zerosBaseline, "JSON"];
Export[FileNameJoin[{base, "Status.txt"}], {If[ok, "OK", "FAIL"], DateString[]}, "Text"];
Association["Status" -> If[ok, "OK", "FAIL"], "ResultsPath" -> base]