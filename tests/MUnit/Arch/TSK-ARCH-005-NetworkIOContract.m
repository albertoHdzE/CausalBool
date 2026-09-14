(* TSK-ARCH-004 — the contract of the corpus loader, src/scripts/NetworkIO.m.

   AUDIT04 Phase A. This owner had NO TESTS AT ALL. The mutation run measured it
   at ZERO KILLS of any kind: its mutant `io-drop-logic` -- which makes the
   loader read the classification LABEL instead of the authoritative formula --
   survived the entire verification set, both closure tiers included.

   That mutant is not hypothetical. It reproduces the AUDIT02/H defect that two
   of the five collapsed LoadJSONNetwork copies actually carried, and the AUDIT04
   Phase 5 corpus diagnostic reached the same defect from the other direction:
   1,943 of 3,977 nodes were recorded as having no derivable truth table purely
   because a label outside the twelve families was read as a statement about
   evaluability. The owner was fixed; the test that keeps it fixed was never
   written. This is that test.

   HERMETIC BY CONSTRUCTION. The fixture is built here rather than read from
   data/bio/processed, so the test asserts the LOADER'S CONTRACT and cannot pass
   or fail because the corpus changed underneath it. The expected values are
   derived from the contract stated in NetworkIO.m, not from what it currently
   returns. *)

base = FileNameJoin[{"results", "tests", "arch5"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

Get[FileNameJoin[{Directory[], "src", "scripts", "NetworkIO.m"}]];

(* ---- fixture -------------------------------------------------------------
   Node C carries the gate label "CUSTOM", which is OUTSIDE the twelve families,
   and a genuine Boolean formula in "logic". This is the exact shape the defect
   mishandles: the label says nothing evaluable, the formula says everything. *)
fixtureDir = FileNameJoin[{base, "fixture"}];
If[!DirectoryQ[fixtureDir], CreateDirectory[fixtureDir, CreateIntermediateDirectories -> True]];
fixturePath = FileNameJoin[{fixtureDir, "net.json"}];

fixture = <|
  "name" -> "arch5-fixture",
  "nodes" -> {"A", "B", "C"},
  "cm" -> {{0, 0, 0}, {0, 0, 0}, {1, 1, 0}},
  "gates" -> <|
     "A" -> <| "gate" -> "INPUT",  "parameters" -> {} |>,
     "B" -> <| "gate" -> "INPUT",  "parameters" -> {} |>,
     "C" -> <| "gate" -> "CUSTOM", "parameters" -> {} |>
  |>,
  "logic" -> <| "C" -> "A & !B" |>
|>;
Export[fixturePath, fixture, "JSON"];

net = LoadJSONNetwork[fixturePath];

(* ---- 1. the key is "logic", and it survives the load --------------------- *)
okKeyPresent = AssociationQ[net] && KeyExistsQ[net, "logic"];

(* ---- 2. it carries the FORMULA, not the label ----------------------------
   Under io-drop-logic the loader reads json["gates"], so this value would be
   the gate RECORD for C -- an Association -- rather than the formula string. *)
okFormulaNotLabel =
  okKeyPresent &&
  AssociationQ[net["logic"]] &&
  KeyExistsQ[net["logic"], "C"] &&
  net["logic"]["C"] === "A & !B";

(* ---- 3. the label is still read, into "dynamic" --------------------------
   The two fields are DIFFERENT CONCEPTS and both must arrive. A loader that
   dropped the label to fix the formula would be the opposite defect. *)
okLabelStillRead =
  okKeyPresent && net["dynamic"] === {"INPUT", "INPUT", "CUSTOM"};

(* ---- 4. the formula is not silently the label ----------------------------
   The negative control. Without it, assertions 1-3 would still pass for a
   loader that happened to put a formula-shaped string in the gates field. *)
okNotTheGateRecord =
  okFormulaNotLabel && !AssociationQ[net["logic"]["C"]];

(* ---- 5. a corpus file with NO logic key still loads ----------------------
   Lookup's default branch. Most of the corpus predates the "logic" field, so a
   missing key must yield an empty Association, never $Failed and never Missing. *)
noLogicPath = FileNameJoin[{fixtureDir, "nologic.json"}];
Export[noLogicPath, KeyDrop[fixture, "logic"], "JSON"];
netNoLogic = LoadJSONNetwork[noLogicPath];
okMissingLogicIsEmpty =
  AssociationQ[netNoLogic] && netNoLogic["logic"] === <||>;

(* ---- 6. a non-Association "logic" is coerced, not propagated -------------- *)
badLogicPath = FileNameJoin[{fixtureDir, "badlogic.json"}];
Export[badLogicPath, Append[fixture, "logic" -> {"not", "an", "association"}], "JSON"];
netBadLogic = LoadJSONNetwork[badLogicPath];
okBadLogicCoerced =
  AssociationQ[netBadLogic] && netBadLogic["logic"] === <||>;

(* ---- 7. a missing file REFUSES rather than returning an empty network ----- *)
okMissingFileRefuses =
  LoadJSONNetwork[FileNameJoin[{fixtureDir, "does-not-exist.json"}]] === $Failed;

(* ---- 8. the rest of the contract still holds ----------------------------- *)
okShape =
  okKeyPresent && net["n"] === 3 &&
  net["nodeNames"] === {"A", "B", "C"} &&
  net["cm"] === {{0, 0, 0}, {0, 0, 0}, {1, 1, 0}};

allOK = okKeyPresent && okFormulaNotLabel && okLabelStillRead &&
        okNotTheGateRecord && okMissingLogicIsEmpty && okBadLogicCoerced &&
        okMissingFileRefuses && okShape;

status = If[TrueQ[allOK], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];

Association[
  "Status" -> status,
  "KeyPresent" -> okKeyPresent,
  "FormulaNotLabel" -> okFormulaNotLabel,
  "LabelStillRead" -> okLabelStillRead,
  "NotTheGateRecord" -> okNotTheGateRecord,
  "MissingLogicIsEmpty" -> okMissingLogicIsEmpty,
  "BadLogicCoerced" -> okBadLogicCoerced,
  "MissingFileRefuses" -> okMissingFileRefuses,
  "Shape" -> okShape,
  "ResultsPath" -> base
]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
