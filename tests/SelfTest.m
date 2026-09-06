(* AUDIT03-B. This file exported {"OK", DateString[]} UNCONDITIONALLY: a test
   that could not fail, calling a self-test package that was itself a fourth
   private copy of the gate semantics with a silent-zero fallthrough for nine of
   the twelve families.

   It also sat OUTSIDE tests/MUnit, so the runner never saw it and
   tools/check_test_manifest.sh could not classify it. It is now declared in
   tests/MUnit/MANIFEST.tsv.

   SelfTestRun now returns its own verdict against a predicate written
   independently of the engine, and this file exports that verdict. *)

Get["src/Packages/Integration/SelfTest.m"];

res = SelfTestRun[];

status = If[TrueQ[res["AllOK"]], "OK", "FAIL"];

If[status =!= "OK",
  Print["SELFTEST FAIL"];
  Print["  outputs  : ", res["Outputs"]];
  Print["  expected : ", res["Expected"]];
  Print["  rows ok  : ", res["RowsOK"]]];

(* HARNESS FRAGILITY, recorded because it bit twice in five minutes.
   run-tests.sh derives a test's status path by GREPPING ITS SOURCE TEXT --
   comments included. Its FileNameJoin branch reads a three-element list as a
   DIRECTORY, so writing the status through a three-element FileNameJoin makes
   the runner look for Status.txt inside a directory named Status.txt and report
   NO STATUS EXPORTED while the file sits on disk. Quoting that same list shape
   in a COMMENT reproduces the fault exactly, which is how this note came to be
   worded without it. The contiguous-string form below is what
   TSK-PATTERN-Ordering-Invariance already uses -- and it needs THREE path
   segments, because the runner's first pattern consumes exactly two after
   "results/" and would otherwise swallow the filename as a directory. Hence
   results/tests/selftest/, which is also where every other test's status
   lives. *)
If[!DirectoryQ["results/tests/selftest"],
   CreateDirectory["results/tests/selftest", CreateIntermediateDirectories -> True]];
Export["results/tests/selftest/Status.txt", {status, DateString[]}, "Text"];

If[status =!= "OK", Exit[1]];

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export["results/tests/selftest/Done.txt", DateString[], "Text"];
