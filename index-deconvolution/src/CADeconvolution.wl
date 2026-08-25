(* CADeconvolution.wl

   Wolfram Language port of the cellular-automaton deconvolution
   (src/ca_deconvolution.py).  Recovers a Boolean network from an ensemble of
   elementary cellular-automaton space-time diagrams and verifies it reproduces
   both the diagrams and the automaton's exact global map.

   Requires CausalBoolCore.wl (ApplyGate) and Deconvolution.wl (IdentifyGate)
   loaded first.  Global-symbol style, 1-based indices, LSB-first convention.
*)

(* --- elementary cellular automaton, periodic boundary --- *)
ECANextCell[l_, c_, r_, rule_] := BitAnd[BitShiftRight[rule, 4 l + 2 c + r], 1];

EvolveECA[rule_, initial_, steps_] := Module[{w = Length[initial], rows, cur, nxt},
  rows = {initial};
  Do[
   cur = Last[rows];
   nxt = Table[ECANextCell[cur[[Mod[i - 2, w] + 1]], cur[[i]],
       cur[[Mod[i, w] + 1]], rule], {i, 1, w}];
   AppendTo[rows, nxt],
   {steps - 1}];
  rows];

(* --- LSB-first key of a state over a 1-based support list --- *)
CBKeyOf[state_, support_] :=
  Sum[If[state[[support[[j]]]] == 1, 2^(j - 1), 0], {j, 1, Length[support]}];

(* --- gate application extended with look-up tables, regulatory clauses and
       the constant gates that the deconvolution can emit --- *)
ApplyGateExt[gate_, inputs_, params_] := Which[
  gate === "TRUE", 1,
  gate === "FALSE", 0,
  gate === "LUT",
    params["table"][[ Sum[If[inputs[[j]] == 1, 2^(j - 1), 0], {j, 1, Length[inputs]}] + 1 ]],
  gate === "REGULATORY",
    If[AllTrue[Range[0, Length[inputs] - 1],
       inputs[[# + 1]] == If[MemberQ[params["activators"], #], 1, 0] &], 1, 0],
  gate === "REGULATORY_DNF",
    If[AnyTrue[params["clauses"],
       Function[cl,
        AllTrue[cl["activators"], inputs[[# + 1]] == 1 &] &&
         AllTrue[cl["inhibitors"], inputs[[# + 1]] == 0 &]]], 1, 0],
  True, ApplyGate[gate, inputs, params]];

(* --- network forward dynamics that understand LUT gates --- *)
CBStep[net_, state_] := Table[
  ApplyGateExt[net["gates"][[k]],
   state[[ Sort[Flatten[Position[net["C"][[k]], 1]]] ]], net["params"][[k]]],
  {k, 1, net["n"]}];

CBEvolveNetwork[net_, initial_, steps_] := Module[{rows = {initial}},
  Do[AppendTo[rows, CBStep[net, Last[rows]]], {steps - 1}];
  rows];

CBNetworkRepertoire[net_] := Module[{n = net["n"]},
  Table[CBStep[net, Reverse[IntegerDigits[x, 2, n]]], {x, 0, 2^n - 1}]];

CAGlobalMap[rule_, w_] := Table[
  Module[{v = Reverse[IntegerDigits[x, 2, w]]},
   Table[ECANextCell[v[[Mod[i - 2, w] + 1]], v[[i]], v[[Mod[i, w] + 1]], rule],
     {i, 1, w}]],
  {x, 0, 2^w - 1}];

(* --- deconvolution helpers --- *)
CBWindow[i_, r_, w_] := Sort[DeleteDuplicates[Table[Mod[i - 1 + d, w] + 1, {d, -r, r}]]];

CBConsistentQ[samples_, support_] := Module[{seen = <||>, ok = True, k, o},
  Do[
   k = CBKeyOf[s[[1]], support]; o = s[[2]];
   If[KeyExistsQ[seen, k], If[seen[k] =!= o, ok = False; Break[]], seen[k] = o],
   {s, samples}];
  ok];

CBEssentialCells[samples_, window_] := Module[{ess = {}, rest, groups, k, o},
  Do[
   rest = DeleteCases[window, j];
   groups = <||>;
   Do[
    k = CBKeyOf[s[[1]], rest]; o = s[[2]];
    groups[k] = Union[Lookup[groups, k, {}], {o}],
    {s, samples}];
   If[AnyTrue[Values[groups], Length[#] > 1 &], AppendTo[ess, j]],
   {j, window}];
  ess];

CBCollectSamples[diagrams_, cell_] := Flatten[
  Table[Table[{diagrams[[d, t]], diagrams[[d, t + 1, cell]]},
     {t, 1, Length[diagrams[[d]]] - 1}], {d, 1, Length[diagrams]}], 1];

DeconvolveCACell[diagrams_, cell_, maxRadius_, w_] := Module[
  {samples, support = None, r, win, ess, m, table, keysSeen, coverage, mc, canonical},
  samples = CBCollectSamples[diagrams, cell];
  Do[
   win = CBWindow[cell, r, w];
   If[CBConsistentQ[samples, win], support = win; Break[]],
   {r, 0, maxRadius}];
  If[support === None, support = CBWindow[cell, maxRadius, w]];
  ess = CBEssentialCells[samples, support];
  Which[
   ess =!= {} && CBConsistentQ[samples, ess], support = ess,
   ess === {} && CBConsistentQ[samples, {}], support = {}];
  m = Length[support];
  table = Table[0, {2^m}];
  keysSeen = {};
  Do[
   Module[{k = CBKeyOf[s[[1]], support]},
    table[[k + 1]] = s[[2]]; AppendTo[keysSeen, k]],
   {s, samples}];
  coverage = Length[DeleteDuplicates[keysSeen]]/2^m;
  mc = IdentifyGate[table];
  canonical = mc[[2]];
  <|"cell" -> cell, "support" -> support, "reduced" -> table,
    "coverage" -> N[coverage], "canonical" -> canonical,
    "numMatches" -> Length[mc[[1]]]|>];

DeconvolveCA[diagrams_, maxRadius_: 3] := Module[
  {w, reports, cm, gates, params, k, rec},
  w = Length[diagrams[[1, 1]]];
  reports = Table[DeconvolveCACell[diagrams, i, maxRadius, w], {i, 1, w}];
  cm = Table[0, {w}, {w}];
  gates = Table["FALSE", {w}];
  params = Table[<||>, {w}];
  Do[
   rec = reports[[k]];
   Do[cm[[k, c]] = 1, {c, rec["support"]}];
   gates[[k]] = rec["canonical"][[1]];
   If[rec["canonical"][[1]] === "LUT",
    params[[k]] = <|"table" -> rec["reduced"]|>,
    params[[k]] = rec["canonical"][[2]]],
   {k, 1, w}];
  <|"n" -> w, "C" -> cm, "gates" -> gates, "params" -> params, "reports" -> reports|>];

VerifyCA[diagrams_, net_, rule_] := Module[{trajExact, globalExact},
  trajExact = AllTrue[diagrams,
    CBEvolveNetwork[net, #[[1]], Length[#]] === # &];
  globalExact = (CBNetworkRepertoire[net] === CAGlobalMap[rule, net["n"]]);
  <|"trajectory_exact" -> trajExact, "global_map_exact" -> globalExact|>];
