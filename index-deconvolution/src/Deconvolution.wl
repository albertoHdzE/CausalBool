(* Deconvolution.wl

   Wolfram Language implementation of the index-set deconvolution, mirroring the
   Python reference in src/deconvolution.py.  It inverts the CausalBool forward
   method: given only an output repertoire it recovers, per node, the functional
   connectivity and the gate.

   Requires ApplyGate and CreateRepertoiresDispatch from CausalBoolCore.wl to be
   loaded first (the caller does this).  Following the style of CausalBoolCore.wl
   this file defines plain global symbols rather than a package, so that the two
   files share a context and see each other's definitions.

   Conventions match CausalBoolCore.wl: LSB-first inputs, cm[[k, i]] = 1 iff node
   i feeds node k, connectivity given as 1-based node positions.  Bit position i
   (0-based) corresponds to node position i+1 (1-based), because the LSB-first
   input vector element at 1-based position p is bit p-1 of the decimal input.
*)

(* Core gate family supported by CausalBoolCore.wl (excludes CANALISING). *)
CBCoreAnyArity = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY"};
CBCanonicalPriority = {"AND", "OR", "NAND", "NOR", "XOR", "XNOR", "NOT",
   "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "REGULATORY", "REGULATORY_DNF"};

(* Minimal DNF cover of a reduced truth table, as activator/inhibitor clauses
   (0-based positions within the support), via Wolfram's exact minimiser.
   Built with an explicit LSB-first minterm convention to avoid any ambiguity. *)
CBRegulatoryDNFClauses[reduced_, m_] := Module[
  {vars, minterms, expr, dnf, terms, clauses},
  vars = Table[Symbol["cbx" <> ToString[j]], {j, 1, m}];
  minterms = Flatten[Position[reduced, 1]] - 1;
  If[minterms === {}, Return[{}]];
  expr = Or @@ (Function[y,
       And @@ Table[
         If[BitAnd[y, 2^(j - 1)] > 0, vars[[j]], Not[vars[[j]]]], {j, 1, m}]] /@ minterms);
  dnf = BooleanConvert[BooleanMinimize[expr], "DNF"];
  terms = If[Head[dnf] === Or, List @@ dnf, {dnf}];
  clauses = Map[Function[term,
     Module[{lits, acts = {}, inhs = {}, lit},
      lits = If[Head[term] === And, List @@ term, {term}];
      Do[
       If[Head[lit] === Not,
        AppendTo[inhs, Position[vars, lit[[1]]][[1, 1]] - 1],
        AppendTo[acts, Position[vars, lit][[1, 1]] - 1]],
       {lit, lits}];
      <|"activators" -> Sort[acts], "inhibitors" -> Sort[inhs]|>]], terms];
  clauses];

(* --- essential variables (pivots vs sumandos) ---
   Sorted 1-based node positions on which an output column of length 2^n depends. *)
EssentialVariables[column_List, n_Integer] := Module[{ess = {}, bit, sensitive, x},
  Do[
   bit = 2^(i);
   sensitive = False;
   Do[
    If[BitAnd[x, bit] == 0,
     If[column[[x + 1]] =!= column[[BitOr[x, bit] + 1]],
      sensitive = True; Break[]]],
    {x, 0, 2^n - 1}];
   If[sensitive, AppendTo[ess, i + 1]],
   {i, 0, n - 1}];
  ess];

(* --- reduce a column onto its essential variables ---
   Length 2^m reduced truth table, LSB-first over essential vars ascending. *)
ReduceColumn[column_List, n_Integer, essential_List] := Module[
  {m = Length[essential], reduced, x, y, j},
  reduced = Table[Null, {2^m}];
  Do[
   y = 0;
   Do[If[BitAnd[x, 2^(essential[[j]] - 1)] != 0, y = BitOr[y, 2^(j - 1)]],
     {j, 1, m}];
   If[reduced[[y + 1]] === Null,
     reduced[[y + 1]] = column[[x + 1]],
     If[reduced[[y + 1]] =!= column[[x + 1]],
       Message[ReduceColumn::inconsistent]; Return[$Failed]]],
   {x, 0, 2^n - 1}];
  reduced];
ReduceColumn::inconsistent = "A non-essential variable affects the output; essential set is wrong.";

(* --- truth table of a candidate gate, LSB-first --- *)
GateTruthTable[gate_String, m_Integer, params_: <||>] :=
  Table[ApplyGate[gate, Reverse[IntegerDigits[y, 2, m]], params], {y, 0, 2^m - 1}];

(* --- gate identification against the core family --- *)
CBCandidateGates[m_Integer] := Module[{c = {}},
  If[m == 0, Return[{}]];
  c = Join[c, {#, <||>} & /@ CBCoreAnyArity];
  If[m == 1, AppendTo[c, {"NOT", <||>}]];
  If[m == 2, c = Join[c, {{"IMPLIES", <||>}, {"NIMPLIES", <||>}}]];
  Do[AppendTo[c, {"KOFN", <|"k" -> k|>}], {k, 1, m}];
  c];

(* IdentifyGate[reduced] -> {matches, canonical}. *)
IdentifyGate[reduced_List] := Module[
  {m, matches, canonical, priority},
  m = IntegerExponent[Length[reduced], 2];  (* exact log2 of a power of two *)
  If[m == 0,
   canonical = If[reduced[[1]] == 1, {"TRUE", <||>}, {"FALSE", <||>}];
   Return[{{canonical}, canonical}]];
  matches = Select[CBCandidateGates[m],
    GateTruthTable[#[[1]], m, #[[2]]] === reduced &];
  (* Regulatory (activator/inhibitor) clause: a single 1 in the reduced table,
     whose position encodes activators (bit 1) and inhibitors (bit 0). *)
  If[Total[reduced] == 1,
   Module[{ystar = Position[reduced, 1][[1, 1]] - 1, activators},
    activators = Select[Range[0, m - 1], BitAnd[ystar, 2^#] > 0 &];
    AppendTo[matches, {"REGULATORY", <|"activators" -> activators, "arity" -> m|>}]]];
  (* Regulatory disjunctive normal form: minimal DNF cover of the on-set,
     expressed as a union of activator/inhibitor clauses (pivot-shifted cosets).
     Named only when it genuinely compresses and the arity is small. *)
  If[1 < Total[reduced] < Length[reduced] && m <= 12,
   Module[{clauses, params, tt},
    clauses = CBRegulatoryDNFClauses[reduced, m];
    params = <|"clauses" -> clauses, "arity" -> m|>;
    tt = Table[
      If[AnyTrue[clauses, Function[cl,
          AllTrue[cl["activators"], (Reverse[IntegerDigits[y, 2, m]])[[# + 1]] == 1 &] &&
           AllTrue[cl["inhibitors"], (Reverse[IntegerDigits[y, 2, m]])[[# + 1]] == 0 &]]],
       1, 0], {y, 0, 2^m - 1}];
    If[tt === reduced && Length[clauses] < Total[reduced],
     AppendTo[matches, {"REGULATORY_DNF", params}]]]];
  If[matches === {},
   Return[{{{"LUT", <|"table" -> reduced|>}}, {"LUT", <|"table" -> reduced|>}}]];
  priority[mm_] := {Position[CBCanonicalPriority, mm[[1]]][[1, 1]],
     Lookup[mm[[2]], "k", 0]};
  canonical = First[SortBy[matches, priority]];
  {matches, canonical}];

(* --- full-repertoire deconvolution ---
   DeconvolveRepertoire[rep, n] -> <|C, gates, params, reports|>. *)
DeconvolveRepertoire[rep_List, n_Integer] := Module[
  {cm, gates, params, reports, k, column, ess, reduced, mc, matches, canonical},
  cm = Table[0, {n}, {n}];
  gates = Table["FALSE", {n}];
  params = Table[<||>, {n}];
  reports = Table[Null, {n}];
  Do[
   column = rep[[All, k]];
   ess = EssentialVariables[column, n];
   reduced = ReduceColumn[column, n, ess];
   mc = IdentifyGate[reduced];
   matches = mc[[1]]; canonical = mc[[2]];
   Do[cm[[k, i]] = 1, {i, ess}];
   gates[[k]] = canonical[[1]];
   params[[k]] = canonical[[2]];
   reports[[k]] = <|"node" -> k, "connected" -> ess,
     "reduced" -> reduced, "numMatches" -> Length[matches],
     "canonical" -> canonical|>,
   {k, 1, n}];
  <|"n" -> n, "C" -> cm, "gates" -> gates, "params" -> params, "reports" -> reports|>];

(* --- verification: replay recovered network, compare byte for byte --- *)
VerifyReconstruction[originalRep_List, recovered_Association] := Module[
  {paramsAssoc, n, rep2},
  n = Length[recovered["gates"]];
  paramsAssoc = Association[Table[node -> recovered["params"][[node]], {node, 1, n}]];
  rep2 = CreateRepertoiresDispatch[recovered["C"], recovered["gates"], paramsAssoc]["RepertoireOutputs"];
  rep2 === originalRep];

(* --- closed-form index sets (no exhaustive scan) --- *)
(* AND one-set: all connected bits pinned to 1; disconnected bits range freely. *)
ClosedFormAndOneSet[n_Integer, Ic_List] := Module[
  {pmask, discBits, offsets},
  pmask = Total[2^(# - 1) & /@ Ic];
  discBits = Complement[Range[n], Ic];
  offsets = Total /@ Subsets[2^(# - 1) & /@ discBits];
  Sort[(pmask + # + 1) & /@ offsets]];

(* OR one-set: complement of the zero-set, where all connected bits are 0. *)
ClosedFormOrOneSet[n_Integer, Ic_List] := Module[
  {discBits, zeroOffsets, zeroSet},
  discBits = Complement[Range[n], Ic];
  zeroOffsets = Total /@ Subsets[2^(# - 1) & /@ discBits];
  zeroSet = (# + 1) & /@ zeroOffsets;
  Sort[Complement[Range[2^n], zeroSet]]];
