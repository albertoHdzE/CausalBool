(* ::Package:: *)
(* AUDIT03/R3.2 - dump Integration`BioMetrics`Private`encodeNodeCost over a grid
   so the Wolfram implementation can be compared ELEMENTWISE (U8) against the two
   Python ones. Nothing is asserted here; the comparison lives in
   verify_description_length.py, which owns the verdict.

   Run:
     HOME=$HOME /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script \
       audit/AUDIT03_R3_description_length/dump_biometrics_grid.m
   Writes audit/AUDIT03_R3_description_length/biometrics_grid.json *)

AppendTo[$Path, "src/Packages"];
Needs["Integration`BioMetrics`"];

gates = {"AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT", "IMPLIES",
         "NIMPLIES", "MAJORITY", "KOFN", "CANALISING", "CUSTOM"};

(* cmRow with exactly d ones in an n-wide row; encodeNodeCost reads only its
   POSITION count, so any placement of the d ones is equivalent - fixed here to
   the first d slots so the Python side can build the identical row. *)
row[n_, d_] := PadRight[ConstantArray[1, d], n, 0];

rows = Flatten[
  Table[
    <|"n" -> n, "d" -> d, "gate" -> g,
      "bits" -> N@Integration`BioMetrics`Private`encodeNodeCost[
                  row[n, d], g, <||>, n]|>,
    {n, 1, 8}, {d, 0, n}, {g, gates}],
  2];

Export["audit/AUDIT03_R3_description_length/biometrics_grid.json",
       <|"generated_by" -> "audit/AUDIT03_R3_description_length/dump_biometrics_grid.m",
         "n_cells" -> Length[rows],
         "cells" -> rows|>, "JSON"];

Print["wrote ", Length[rows], " cells"];
