(* r4_catalogue_from_gates.wl — emit the R4 mechanism catalogue as truth tables
   computed BY Integration`Gates`ApplyGate itself (zero semantic drift).
   Run from repo root:  wolfram -script tools/r4_catalogue_from_gates.wl
   Output: experiments/r4_segmented_grammar/catalogue_from_gates.json *)

AppendTo[$Path, FileNameJoin[{Directory[], "src", "Packages"}]];
Needs["Integration`Gates`"];

(* neighborhood value convention (PROTOCOL \[Section]3):
   w = 4*b[t-3] + 2*b[t-2] + 1*b[t-1];
   gate inputs ordered by the mechanism's support (list of lags):
   inputs[[k]] = b[t - lags[[k]]]                                        *)
inputsForW[w_, lags_] := Module[{b1, b2, b3},
   b1 = BitGet[w, 0]; b2 = BitGet[w, 1]; b3 = BitGet[w, 2];
   Table[Which[lags[[k]] == 1, b1, lags[[k]] == 2, b2, True, b3], {k, Length[lags]}]];

mechanisms = {};
addMech[fam_String, params_Association, lags_List] :=
   Module[{tt, const},
      tt = Table[ApplyGate[fam, inputsForW[w, lags], params], {w, 0, 7}];
      const = SameQ @@ tt;
      AppendTo[mechanisms,
         <|"family" -> fam, "params" -> params, "support" -> lags,
           "tt" -> tt, "constant" -> const|>]];

subsets123 = Subsets[{1, 2, 3}, {1, 3}];
permsOf[sub_List] := Permutations[sub];

(* n-ary symmetric families: support = sorted subset *)
Do[
   Do[addMech[f, <||>, sub], {f, {"AND", "OR", "XOR", "NAND", "NOR", "XNOR"}}],
   {sub, subsets123}];
(* NOT: arity 1 only *)
Do[addMech["NOT", <||>, sub], {sub, Select[subsets123, Length[#] == 1 &]}];
(* MAJORITY: frame pins tiePolicy strict (ties->0), declared explicitly *)
Do[addMech["MAJORITY", <|"tiePolicy" -> "strict"|>, sub], {sub, subsets123}];
(* KOFN: 1<=k<=d, BOTH strict modes (frame ambiguity closed in A3) *)
Do[
   Do[addMech["KOFN", <|"k" -> k, "strict" -> s|>, sub],
      {k, Length[sub]}, {s, {False, True}}],
   {sub, subsets123}];
(* oriented families: all permutations of every subset *)
Do[
   Do[addMech[f, <||>, p], {p, permsOf[sub]}],
   {f, {"IMPLIES", "NIMPLIES"}}, {sub, Select[subsets123, Length[#] == 2 &]}];
(* CANALISING: canalisingIndex is within-support POSITION (Ic-relative, ORDERING 4b);
   semantics: If[input[[i]]==v, canalisedOutput, OR[list]]  -- fallthrough is OR *)
Do[
   Module[{p = perm},
      Do[addMech["CANALISING",
          <|"canalisingIndex" -> i, "canalisingValue" -> v,
            "canalisedOutput" -> o|>, p],
       {i, Length[p]}, {v, {0, 1}}, {o, {0, 1}}]],
   {perm, Flatten[permsOf /@ subsets123, 1]}];

(* convention anchors: these identities must hold or the mapping above is wrong *)
anchorChecks = <|
   "XOR3_is_rule150" -> (Select[mechanisms,
        #family == "XOR" && #support == {1, 2, 3} &][[1, "tt"]] ==
       Table[Mod[BitCount[w], 2], {w, 0, 7}]),
   "AND3_is_rule248" -> (Select[mechanisms,
        #family == "AND" && #support == {1, 2, 3} &][[1, "tt"]] ==
       Table[If[w == 7, 1, 0], {w, 0, 7}]),
   "OR3_is_rule254" -> (Select[mechanisms,
        #family == "OR" && #support == {1, 2, 3} &][[1, "tt"]] ==
       Table[If[w == 0, 0, 1], {w, 0, 7}])|>;
Scan[If[#[[2]] === False, Print["ANCHOR FAIL: ", #[[1]]]; Exit[1]] &, Normal[anchorChecks]];

export = <|
   "convention" -> "tt[w] for w=0..7; w = 4*b[t-3]+2*b[t-2]+1*b[t-1];
      gate inputs ordered by 'support' (lags); generated via ApplyGate",
   "generated_by" -> "tools/r4_catalogue_from_gates.wl",
   "n_mechanisms" -> Length[mechanisms],
   "n_constant" -> Count[mechanisms, m_ /; m["constant"]],
   "mechanisms" -> mechanisms|>;
Export[FileNameJoin[{Directory[], "experiments", "r4_segmented_grammar",
    "catalogue_from_gates.json"}], export];
Print["exported ", Length[mechanisms], " mechanisms (",
   Count[mechanisms, m_ /; m["constant"]], " constant-flagged); anchors OK"];
