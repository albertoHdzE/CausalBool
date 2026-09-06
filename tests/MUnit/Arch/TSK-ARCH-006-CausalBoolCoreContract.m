(* TSK-ARCH-006 — the companion core's contract, independent of the parity gate.

   AUDIT04 Phase A. papers/method/code/lib/CausalBoolCore.wl scored THREE kills
   out of three in the mutation run and ZERO of them came from a unit test: all
   three were caught by tools/run_crosscheck_parity.sh alone.

   That is not a failure of the declared exception -- it is the exception working
   exactly as written. CORE.md declares this file self-contained because a reader
   reproducing the paper must run it from a clean checkout, and says it is "kept
   honest by the 135/135 cross-language parity run, not by sharing code". The
   parity run did keep it honest.

   But it is the ONLY thing watching it. If the parity gate were skipped, made
   conditional, or refused for an absent kernel, this owner would be undefended
   and nothing would say so. These tests are a second, independent line: they
   need no Python side and no cross-language comparison.

   INDEPENDENT DERIVATION. Every expected value below is derived from the
   contract stated in CausalBoolCore.wl and re-derived by hand here -- including
   the "32 of 64" divergence, which is recomputed from the definition rather
   than copied from the audit note that records it. *)

base = FileNameJoin[{"results", "tests", "arch6"}];
If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];

Get[FileNameJoin[{Directory[], "papers", "method", "code", "lib", "CausalBoolCore.wl"}]];

(* ---- 1. allOffsets is the FULL subset-sum family of the free coordinates ----
   n = 4, connected = {1, 3} leaves free = {2, 4} with bit weights {2, 8}, whose
   subset sums are {0, 2, 8, 10}. Derived from the definition, not observed.

   The mutant core-alloffsets truncates ws by one element, so it would yield
   {0, 2} -- half the family. Asserting the exact SET, not its length, because a
   family of the right size and the wrong members is also wrong. *)
off42 = allOffsets[4, {1, 3}];
okOffsetsExact = off42 === {0, 2, 8, 10};
okOffsetsCount = Length[off42] === 2^2;

(* n = 5, connected = {2}: free = {1, 3, 4, 5}, weights {1, 4, 8, 16},
   16 subset sums, the largest being their total. *)
off51 = allOffsets[5, {2}];
okOffsets5 = Length[off51] === 2^4 && Max[off51] === 1 + 4 + 8 + 16 &&
             First[off51] === 0;

(* ---- 2. the empty-ws guard ------------------------------------------------
   CORE.md records that one of the three copies of this function LACKED this
   guard. With every coordinate connected there are no free ones, and the
   correct answer is the single offset {0}, not an empty family. *)
okOffsetsAllConnected = allOffsets[3, {1, 2, 3}] === {0};

(* ---- 3. givePlaces is the Minkowski sum, sorted -------------------------- *)
okGivePlaces = givePlaces[{0, 4}, {0, 1}] === {0, 1, 4, 5};

(* ---- 4. the composed update is NOT the synchronous one -------------------
   THE DECLARED DIVERGENCE, pinned as a number.

   Node 6 is XOR over its connected inputs {1, 3, 5}, but the composed reading
   (convention D-2d) feeds it the NEWLY COMPUTED y5 rather than the input x5.
   The synchronous form is written out here independently.

   Derivation of the expected count, by hand: the two agree iff
   y5 == x5, where y5 = Boole[x2 == 1 && x4 == 1]. Over the 8 assignments of
   (x2, x4, x5) they DIFFER in 4 -- one where x2 = x4 = 1 with x5 = 0, and three
   where x2 && x4 is false with x5 = 1. The remaining coordinates x1, x3, x6 are
   free, giving 2^3 = 8 completions each. So 4 * 8 = 32 of 64 rows.

   core-composed-y5 replaces y5 by input[[5]], collapsing the composed reading
   onto the synchronous one and driving this count to ZERO. Collapsing the two
   would silently change the flagship by half its rows. *)
syncNode6[x_List] := Mod[x[[1]] + x[[3]] + x[[5]], 2];
allInputs = Tuples[{0, 1}, 6];
node6Diffs = Count[allInputs, x_ /; composedUpdate6Node[x][[6]] =!= syncNode6[x]];
okComposedDiffers = node6Diffs === 32;

(* Nodes 1-5 must agree with their own definitions on ALL 64 rows: the
   divergence is confined to node 6, which is what makes it a declared reading
   rather than a bug. *)
okNodes1to5 = AllTrue[allInputs, Function[x,
   composedUpdate6Node[x][[1 ;; 5]] === {
     x[[1]],
     Boole[x[[2]] == 0],
     x[[3]],
     Boole[x[[1]] == 0 || x[[4]] == 1],
     Boole[x[[2]] == 1 && x[[4]] == 1]}]];

(* ---- 5. ApplyGate: NOT is a negation ------------------------------------
   core-applygate-default makes it the identity, so a reader reproducing the
   paper would silently run a different engine. *)
okNot = ApplyGate["NOT", {0}] === 1 && ApplyGate["NOT", {1}] === 0;

(* The remaining families, on their defining rows -- so a mutant in any one of
   them meets an assertion here and not only the parity run. *)
okGates =
  ApplyGate["AND", {1, 1}] === 1 && ApplyGate["AND", {1, 0}] === 0 &&
  ApplyGate["OR", {0, 0}] === 0 && ApplyGate["OR", {0, 1}] === 1 &&
  ApplyGate["XOR", {1, 1}] === 0 && ApplyGate["XOR", {1, 0}] === 1 &&
  ApplyGate["NAND", {1, 1}] === 0 && ApplyGate["NOR", {0, 0}] === 1 &&
  ApplyGate["XNOR", {1, 1}] === 1 &&
  ApplyGate["IMPLIES", {1, 0}] === 0 && ApplyGate["IMPLIES", {0, 0}] === 1 &&
  ApplyGate["NIMPLIES", {1, 0}] === 1 &&
  ApplyGate["MAJORITY", {1, 1, 0}] === 1 && ApplyGate["MAJORITY", {1, 0, 0}] === 0 &&
  ApplyGate["KOFN", {1, 1, 0}, <|"k" -> 2|>] === 1 &&
  ApplyGate["KOFN", {1, 0, 0}, <|"k" -> 2|>] === 0;

(* ---- 6. an unsupported gate REFUSES rather than returning a silent 0 -----
   AUDIT02/P1. A silent 0 is indistinguishable from a legitimate FALSE, which is
   how labels outside the twelve families used to vanish into the output. *)
okUnsupported = MatchQ[Quiet[ApplyGate["NOT_A_GATE", {1}]], _Failure];

allOK = okOffsetsExact && okOffsetsCount && okOffsets5 && okOffsetsAllConnected &&
        okGivePlaces && okComposedDiffers && okNodes1to5 && okNot && okGates &&
        okUnsupported;

status = If[TrueQ[allOK], "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];

Association[
  "Status" -> status,
  "OffsetsExact" -> okOffsetsExact, "OffsetsCount" -> okOffsetsCount,
  "Offsets5" -> okOffsets5, "OffsetsAllConnected" -> okOffsetsAllConnected,
  "GivePlaces" -> okGivePlaces,
  "ComposedDiffersOn32of64" -> okComposedDiffers, "Node6DiffCount" -> node6Diffs,
  "Nodes1to5Agree" -> okNodes1to5,
  "NOTIsNegation" -> okNot, "TwelveFamilies" -> okGates,
  "UnsupportedRefuses" -> okUnsupported,
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
