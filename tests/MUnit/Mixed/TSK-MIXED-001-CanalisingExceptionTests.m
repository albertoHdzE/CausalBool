(* TSK-MIXED-001-CanalisingExceptionTests.m — AUDIT02/W0.2

   Closes the last F36 exception. ORDERING §4 carried
   TSK-MIXED-001-Comparison.m and TSK-MIXED-001-OnPossibleBehaviour.m as
   documented exceptions whose local CANALISING branches read NETWORK-ABSOLUTE
   indices, against the Ic-RELATIVE convention pinned in §4/§4b, and required
   that "alignment requires its own executed test before landing". This is that
   test.

   It asserts three things, and the second is what makes the first meaningful:

     POSITIVE  the migrated relative reading agrees with
               Integration`Gates`ApplyGate on Part[row, Ic] over the whole grid.
     NEGATIVE  the OLD absolute reading DISAGREES with the engine somewhere in
               that grid. Without this, a test that merely passes proves nothing:
               it could be passing because the grid never reaches the divergence.
     DEFAULT   with no explicit canalisingIndex the two conventions coincide,
               which is why the exception was survivable for so long. *)

AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];

base = FileNameJoin[{"results", "tests", "mixed001CanalisingException"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

(* the two readings, isolated *)
relativeEval[v_List, Ic_List, params_Association] := Module[
  {bits = v[[Ic]], ci = Lookup[params, "canalisingIndex", 1],
   vcan = Lookup[params, "canalisingValue", 1], cout = Lookup[params, "canalisedOutput", 0]},
  If[bits[[ci]] == vcan, cout, Boole[MemberQ[bits, 1]]]];

absoluteEval[v_List, Ic_List, params_Association] := Module[
  {bits = v[[Ic]], ci = Lookup[params, "canalisingIndex", If[Length[Ic] >= 1, Ic[[1]], Ic[[1]]]],
   vcan = Lookup[params, "canalisingValue", 1], cout = Lookup[params, "canalisedOutput", 0]},
  If[v[[ci]] == vcan, cout, Boole[MemberQ[bits, 1]]]];

engineEval[v_List, Ic_List, params_Association] :=
  Integration`Gates`ApplyGate["CANALISING", v[[Ic]], params];

(* grid: n = 5, every support of size 2..4, every relative ci, both values,
   both canalised outputs, every row of the n-bit space. Supports are chosen so
   that Ic[[ci]] =!= ci occurs often -- that is precisely where the conventions
   part company. *)
n = 5;
supports = Select[Subsets[Range[n], {2, 4}], Length[#] >= 2 &];
rows = IntegerDigits[Range[0, 2^n - 1], 2, n];

posMismatch = 0; negMismatch = 0; defaultMismatch = 0; cases = 0;
Do[
  Module[{Ic = supports[[s]], p},
    Do[
      p = <|"canalisingIndex" -> ci, "canalisingValue" -> vcan, "canalisedOutput" -> cout|>;
      Do[
        cases++;
        If[relativeEval[rows[[r]], Ic, p] =!= engineEval[rows[[r]], Ic, p], posMismatch++];
        (* the absolute reading is only defined when ci indexes the full row *)
        If[ci <= n && absoluteEval[rows[[r]], Ic, p] =!= engineEval[rows[[r]], Ic, p],
          negMismatch++],
        {r, Length[rows]}],
      {ci, Length[Ic]}, {vcan, {0, 1}}, {cout, {0, 1}}]],
  {s, Length[supports]}];

(* DEFAULT case: no canalisingIndex supplied *)
Do[Module[{Ic = supports[[s]], p = <|"canalisingValue" -> 1, "canalisedOutput" -> 0|>},
   Do[If[relativeEval[rows[[r]], Ic, p] =!= absoluteEval[rows[[r]], Ic, p],
        defaultMismatch++], {r, Length[rows]}]],
  {s, Length[supports]}];

posOK = (posMismatch === 0);
negOK = (negMismatch > 0);          (* the test MUST be able to see the bug *)
defOK = (defaultMismatch === 0);
allOK = posOK && negOK && defOK;

Print["cases evaluated              : ", cases];
Print["POSITIVE relative vs engine  : ", posMismatch, " mismatches (want 0)      -> ", posOK];
Print["NEGATIVE absolute vs engine  : ", negMismatch, " mismatches (want > 0)   -> ", negOK];
Print["DEFAULT  relative vs absolute: ", defaultMismatch, " mismatches (want 0)      -> ", defOK];

Export[FileNameJoin[{base, "Summary.json"}],
  <|"cases" -> cases,
    "positiveMismatches" -> posMismatch,
    "negativeMismatches" -> negMismatch,
    "defaultMismatches" -> defaultMismatch,
    "positiveControlPassed" -> posOK,
    "negativeControlPassed" -> negOK,
    "defaultAgreementHolds" -> defOK,
    "allPassed" -> allOK|>, "JSON"];

Export[FileNameJoin[{base, "Status.txt"}],
  If[allOK, "OK", "FAIL"] <> "\n" <> DateString[], "Text"];

If[!allOK, Print["TSK-MIXED-001-CanalisingException: FAIL"]; Exit[1]];
Print["TSK-MIXED-001-CanalisingException: OK"];
