AppendTo[$Path, "src/Packages"];
Needs["Integration`Gates`"];
base = FileNameJoin[{"results", "tests", "gates001"}]; If[!DirectoryQ[base], CreateDirectory[base, CreateIntermediateDirectories -> True]];
inputs2 = {{0,0},{0,1},{1,0},{1,1}};
expAND = {0,0,0,1};
expOR = {0,1,1,1};
expXOR = {0,1,1,0};
expNAND = {1,1,1,0};
expNOR = {1,0,0,0};
expXNOR = {1,0,0,1};
expIMPL = {1,1,0,1};
expNIMPL = {0,0,1,0};
expK1 = expOR;
expK2 = expAND;
outAND = Integration`Gates`TruthTable["AND",2][[All,2]];
outOR = Integration`Gates`TruthTable["OR",2][[All,2]];
outXOR = Integration`Gates`TruthTable["XOR",2][[All,2]];
outNAND = Integration`Gates`TruthTable["NAND",2][[All,2]];
outNOR = Integration`Gates`TruthTable["NOR",2][[All,2]];
outXNOR = Integration`Gates`TruthTable["XNOR",2][[All,2]];
outIMPL = Integration`Gates`TruthTable["IMPLIES",2][[All,2]];
outNIMPL = Integration`Gates`TruthTable["NIMPLIES",2][[All,2]];
outK1 = Integration`Gates`TruthTable["KOFN",2,<|"k"->1|>][[All,2]];
outK2 = Integration`Gates`TruthTable["KOFN",2,<|"k"->2|>][[All,2]];
okAND = outAND === expAND;
okOR = outOR === expOR;
okXOR = outXOR === expXOR;
okNAND = outNAND === expNAND;
okNOR = outNOR === expNOR;
okXNOR = outXNOR === expXNOR;
okIMPL = outIMPL === expIMPL;
okNIMPL = outNIMPL === expNIMPL;
okK1 = outK1 === expK1;
okK2 = outK2 === expK2;
outNOT = Integration`Gates`TruthTable["NOT",1][[All,2]];
okNOT = outNOT === {1,0};
can1 = Integration`Gates`ApplyGate["CANALISING", {1,0}, <|"canalisingIndex"->1, "canalisingValue"->1, "canalisedOutput"->0|>];
can2 = Integration`Gates`ApplyGate["CANALISING", {0,1}, <|"canalisingIndex"->1, "canalisingValue"->1, "canalisedOutput"->0|>];
okCAN = (can1 === 0 && can2 === 1);
status = If[And@@{okAND,okOR,okXOR,okNAND,okNOR,okXNOR,okIMPL,okNIMPL,okK1,okK2,okNOT,okCAN}, "OK", "FAIL"];
Export[FileNameJoin[{base, "Status.txt"}], {status, DateString[]}, "Text"];
Export[FileNameJoin[{base, "TruthTables.json"}], <|"AND"->outAND, "OR"->outOR, "XOR"->outXOR, "NAND"->outNAND, "NOR"->outNOR, "XNOR"->outXNOR, "IMPLIES"->outIMPL, "NIMPLIES"->outNIMPL, "KOFN1"->outK1, "KOFN2"->outK2, "NOT"->outNOT|>, "JSON"];
Association["Status"->status, "ResultsPath"->base]

(* AUDIT04-D: completion sentinel, written LAST.
   The runner deletes this before the run, so its presence afterwards proves
   every expression above it evaluated. Status.txt is written earlier and is
   followed by further exports in most tests, so a fresh verdict alone does not
   show the test finished -- a kernel dying between the two leaves a plausible
   OK beside incomplete artefacts. That is also the shape of the AUDIT03 defect
   where a kernel skipped a malformed expression, exited 0, and the runner read
   a pass. *)
Export[FileNameJoin[{base, "Done.txt"}], DateString[], "Text"];
