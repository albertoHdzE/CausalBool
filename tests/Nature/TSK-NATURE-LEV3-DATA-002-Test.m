(* TSK-NATURE-LEV3-DATA-002-Test.m *)
(* Validates Phase 2: Manual Curation (Gold Standard) *)

Print["------------------------------------------------"];
Print["   Test: Phase 2 Manual Curation (DATA-002)"];
Print["------------------------------------------------"];

projectDir = DirectoryName[DirectoryName[DirectoryName[$InputFileName]]];
metadataPath = FileNameJoin[{projectDir, "data", "bio", "curated", "metadata.csv"}];
processedDir = FileNameJoin[{projectDir, "data", "bio", "processed"}];

If[!FileExistsQ[metadataPath],
    Print[">> Metadata CSV not found! FAIL"];
    Exit[1];
];

Print[">> Loading metadata from: ", metadataPath];
data = Import[metadataPath, "Dataset", HeaderLines -> 1];
rows = Length[data];
Print[">> Found ", rows, " entries."];

If[rows < 20,
    Print[">> WARNING: Less than 20 entries found (Target N=20)."];
];

files = Normal[data[All, "Filename"]];
missingFiles = {};
validFiles = 0;

Do[
    file = files[[i]];
    fullPath = FileNameJoin[{processedDir, file}];
    If[!FileExistsQ[fullPath],
        AppendTo[missingFiles, file];
        Print[">> Missing: ", file];
    ,
        (* Validate JSON Content *)
        json = Import[fullPath, "JSON"];
        nodes = Lookup[json, "nodes", {}];
        edges = Lookup[json, "edges", {}];
        
        If[Length[nodes] > 0,
            validFiles++;
        ,
            Print[">> Invalid JSON (no nodes): ", file];
        ];
    ];
, {i, Length[files]}];

Print["------------------------------------------------"];
Print["   Results"];
Print["------------------------------------------------"];
Print["Total Entries: ", rows];
Print["Valid Files:   ", validFiles];
Print["Missing Files: ", Length[missingFiles]];

dataOK = (Length[missingFiles] == 0 && validFiles >= 20);

(* AUDIT03-B. This file had a real verdict and NO STATUS EXPORT, so the runner
   could not score it -- and it sits outside tests/MUnit, so the manifest guard
   could not see it either. It has therefore never run in any suite. Both are
   fixed: it exports the verdict it already computes, and it is declared in
   tests/MUnit/MANIFEST.tsv. *)
statusBase = FileNameJoin[{"results", "tests", "nature_lev3_data"}];
If[!DirectoryQ[statusBase],
   CreateDirectory[statusBase, CreateIntermediateDirectories -> True]];
Export[FileNameJoin[{statusBase, "Status.txt"}],
       {If[TrueQ[dataOK], "OK", "FAIL"], DateString[]}, "Text"];

Print[If[TrueQ[dataOK], ">> STATUS: PASSED", ">> STATUS: FAILED"]];
If[!TrueQ[dataOK], Exit[1]];

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{statusBase, "Done.txt"}], DateString[], "Text"];
