(* LogicEval.m — AUDIT02/H: evaluate the Boolean formulas carried in the
   "logic" field of data/bio/processed/*.json.

   WHY THIS EXISTS
   ---------------
   Each processed network stores, per node, BOTH a classification label in
   "gates" and the node's actual Boolean formula in "logic". The bio pipeline
   consumed only the label. Labels outside the twelve gate families (CUSTOM,
   IDENTITY, INPUT, and nodes absent from "gates") reached
   Integration`Gates`ApplyGate and fell through to a silent 0 — 3,977 of 5,204
   node instances, 76.4%, across 170/170 networks. IDENTITY and INPUT were given
   correct pass-through semantics in AUDIT02/B2; CUSTOM needs the formula, which
   is what this file evaluates.

   SCOPE — MEASURED, NOT ASSUMED
   -----------------------------
   The "logic" field is not one language. Over the 4,628 expressions in the
   corpus:

     Boolean infix/prefix  (& | ! AND OR NOT TRUE FALSE)   3,709   80.1%
     multi-valued          (X:k, e.g. "Cdc14:2")             512   11.1%
     threshold-functional  GEQ / LT against theta parameters     407    8.8%

   Only the first class is evaluable as Boolean and is what this file supports.
   The other two are REFUSED with a typed reason, never coerced:

     - multi-valued expressions need more than one bit per node, so they cannot
       be represented in a Boolean state vector at all;
     - threshold expressions reference theta parameters that are NOT node
       names: 0 of the 276 theta symbols in the corpus resolve from the JSON, so
       the formula is not evaluable from this data at any level.

   Refusal is a first-class result here. A wrong number is worse than no number.

   VARIABLE SCOPE
   --------------
   Formulas are evaluated against the FULL named state, not the cm-derived input
   subvector. Measured reason: of 3,709 class-1 formulas, 3,161 (85.2%) have
   variables exactly equal to their cm connectivity, and of the 548 that differ,
   466 are self-references (the cm omits self-edges) — e.g. node Tin's formula
   reads Tin. A subvector keyed on cm would silently drop those.

   No ToExpression is used anywhere. Corpus node names include N, D, E, C and K,
   which are Wolfram builtins; parsing them as symbols would corrupt the formula.
   The tokeniser and recursive-descent parser below operate on strings only. *)

BeginPackage["Integration`LogicEval`"]

LogicParseStatus::usage = "LogicParseStatus[expr] returns \"Boolean\", \"MultiValued\", \"Threshold\", or \"Unparseable\" for a logic string.";
LogicVariables::usage = "LogicVariables[expr] returns the identifiers referenced by a Boolean logic string.";
EvaluateLogic::usage = "EvaluateLogic[expr, state] evaluates a Boolean logic string against an Association of name -> 0/1, returning 0/1 or Failure.";

EvaluateLogic::refused = "AUDIT02/H: logic expression refused (`1`): `2`";
EvaluateLogic::unbound = "AUDIT02/H: logic expression references `1`, which is not in the supplied state.";

Begin["`Private`"]

(* ---- classification ------------------------------------------------------ *)
(* Order matters: threshold form is checked first because a GEQ() expression may
   also contain digits that would otherwise look like a level suffix. *)
LogicParseStatus[expr_String] := Which[
  StringMatchQ[expr, RegularExpression[".*\\b(GEQ|LEQ|LT|GT|EQ)\\s*\\(.*"]], "Threshold",
  StringMatchQ[expr, RegularExpression[".*[A-Za-z_0-9\\-]+:[0-9].*"]],       "MultiValued",
  True, "Boolean"
];
LogicParseStatus[_] := "Unparseable";

(* ---- tokeniser ----------------------------------------------------------- *)
(* Identifiers may contain letters, digits, underscore and hyphen (e.g.
   "Bub2-Bfa1"), so '-' is an identifier character here, never a minus sign.
   Lexing is positional: collect identifier spans and operator spans, then merge
   them in document order. This keeps each identifier's TEXT attached to its
   token, which a fixed StringCases rule cannot do. *)
lexTokens[expr_String] := Module[{ids, ops, all},
  (* Overlaps -> False is essential: StringPosition otherwise returns a match at
     EVERY start position, so "AND" would also yield "ND" and "D". *)
  ids = StringPosition[expr, RegularExpression["[A-Za-z_][A-Za-z_0-9\\-]*"], Overlaps -> False];
  ids = {#[[1]], "id", StringTake[expr, #]} & /@ ids;
  ops = Flatten[
    Function[ch,
      {#[[1]], "op", ch} & /@ StringPosition[expr, ch]
    ] /@ {"&", "|", "!", "(", ")", ","}, 1];
  (* drop operator hits that fall inside an identifier span (cannot happen for
     these characters, but keep the guard explicit) *)
  all = Join[ids, ops];
  SortBy[all, First][[All, {2, 3}]]
];

(* ---- recursive-descent parser -------------------------------------------- *)
(* Grammar (both infix and prefix forms occur in the corpus, sometimes nested):
     expr    := orExpr
     orExpr  := andExpr ("|" andExpr)*
     andExpr := unary ("&" unary)*
     unary   := "!" unary | primary
     primary := "(" expr ")"
              | AND "(" expr ("," expr)* ")"
              | OR  "(" expr ("," expr)* ")"
              | NOT "(" expr ")"
              | TRUE | FALSE
              | identifier                                                   *)

SetAttributes[{pExpr, pOr, pAnd, pUnary, pPrimary}, HoldFirst];

parseFormula[toks_List, state_Association] := Module[{pos = 1, tk, val},
  tk[] := If[pos <= Length[toks], toks[[pos]], {"eof", ""}];
  adv[] := (pos++);

  pPrimary[] := Module[{t = tk[], inner, args, name},
    Which[
      t[[1]] === "op" && t[[2]] === "(",
        adv[]; inner = pOr[];
        If[FailureQ[inner], Return[inner]];
        If[tk[][[2]] =!= ")", Return[Failure["LogicParse", <|"Reason" -> "missing )"|>]]];
        adv[]; inner,
      t[[1]] === "id",
        name = t[[2]]; adv[];
        Which[
          MemberQ[{"AND", "OR", "NOT"}, ToUpperCase[name]] && tk[][[2]] === "(",
            adv[];
            args = {};
            While[True,
              inner = pOr[];
              If[FailureQ[inner], Return[inner]];
              AppendTo[args, inner];
              If[tk[][[2]] === ",", adv[], Break[]]];
            If[tk[][[2]] =!= ")", Return[Failure["LogicParse", <|"Reason" -> "missing ) after " <> name|>]]];
            adv[];
            Switch[ToUpperCase[name],
              "AND", If[MemberQ[args, 0], 0, 1],
              "OR",  If[MemberQ[args, 1], 1, 0],
              "NOT", 1 - First[args]],
          ToUpperCase[name] === "TRUE", 1,
          ToUpperCase[name] === "FALSE", 0,
          True,
            If[KeyExistsQ[state, name], state[name],
               Failure["LogicUnbound", <|"Name" -> name|>]]
        ],
      True, Failure["LogicParse", <|"Reason" -> "unexpected token", "Token" -> t|>]
    ]
  ];

  pUnary[] := If[tk[][[1]] === "op" && tk[][[2]] === "!",
    (adv[]; Module[{v = pUnary[]}, If[FailureQ[v], v, 1 - v]]),
    pPrimary[]];

  pAnd[] := Module[{acc = pUnary[], rhs},
    If[FailureQ[acc], Return[acc]];
    While[tk[][[1]] === "op" && tk[][[2]] === "&",
      adv[]; rhs = pUnary[];
      If[FailureQ[rhs], Return[rhs]];
      acc = If[acc === 1 && rhs === 1, 1, 0]];
    acc];

  pOr[] := Module[{acc = pAnd[], rhs},
    If[FailureQ[acc], Return[acc]];
    While[tk[][[1]] === "op" && tk[][[2]] === "|",
      adv[]; rhs = pAnd[];
      If[FailureQ[rhs], Return[rhs]];
      acc = If[acc === 1 || rhs === 1, 1, 0]];
    acc];

  val = pOr[];
  If[FailureQ[val], val,
    If[pos <= Length[toks],
      Failure["LogicParse", <|"Reason" -> "trailing tokens", "At" -> pos|>],
      val]]
];

(* ---- public API ---------------------------------------------------------- *)
LogicVariables[expr_String] := Module[{toks},
  toks = lexTokens[expr];
  DeleteDuplicates@Select[
    Cases[toks, {"id", n_} :> n],
    !MemberQ[{"AND", "OR", "NOT", "TRUE", "FALSE"}, ToUpperCase[#]] &]
];

EvaluateLogic[expr_String, state_Association] := Module[{status, toks, res},
  status = LogicParseStatus[expr];
  If[status =!= "Boolean",
    Return[Failure["LogicRefused", <|"Class" -> status, "Expression" -> expr|>]]];
  toks = lexTokens[expr];
  If[toks === {}, Return[Failure["LogicParse", <|"Reason" -> "empty"|>]]];
  res = parseFormula[toks, state];
  res
];

EvaluateLogic[expr_, _] := Failure["LogicRefused", <|"Class" -> "Unparseable", "Expression" -> expr|>];

End[]
EndPackage[]
