baseDir = DirectoryName[$InputFileName];
(* AUDIT03: composedUpdate6Node now lives in the shared library. *)
Get[FileNameJoin[{baseDir, "..", "lib", "CausalBoolCore.wl"}]];

cm06 = {
  {1, 0, 0, 0, 0, 0},
  {0, 1, 0, 0, 0, 0},
  {0, 0, 1, 0, 0, 0},
  {1, 0, 0, 1, 0, 0},
  {0, 1, 0, 1, 0, 0},
  {1, 0, 1, 0, 1, 0}
};

dyn06 = {"OR", "NOT", "OR", "IMPLIES", "AND", "XOR"};

phi[j_Integer, n_Integer] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, n]], 2];
phiSet[set_List, n_Integer] := Sort[phi[#, n] & /@ set];

lsbInputs[n_Integer] := Reverse /@ IntegerDigits[Range[0, 2^n - 1], 2, n];
msbInputs[n_Integer] := IntegerDigits[Range[0, 2^n - 1], 2, n];

(* AUDIT03 — one owner for the composed 6-node update. It is COMPOSED, not
   synchronous: node 6 takes the newly computed y5, so it differs from
   CreateRepertoiresDispatch on 32 of 64 rows by design. See the CAUTION in
   CausalBoolCore.wl. *)
networkUpdate[input_List] := composedUpdate6Node[input];

andLSB06 = {11, 12, 15, 16, 27, 28, 31, 32, 43, 44, 47, 48, 59, 60, 63, 64};
xorLSB06 = {2, 4, 5, 7, 10, 11, 13, 16, 18, 20, 21, 23, 26, 27, 29, 32, 34, 36, 37, 39, 42, 43, 45, 48, 50, 52, 53, 55, 58, 59, 61, 64};

inputsMSB06 = msbInputs[6];
outputsMSB06 = networkUpdate /@ inputsMSB06;

andMSB06 = Flatten@Position[outputsMSB06[[All, 5]], 1];
xorMSB06 = Flatten@Position[outputsMSB06[[All, 6]], 1];

andPhi06 = phiSet[andLSB06, 6];
xorPhi06 = phiSet[xorLSB06, 6];

verifiedAnd06Q = andPhi06 === andMSB06;
verifiedXor06Q = xorPhi06 === xorMSB06;
verifiedPhiInvolution06Q = And @@ Table[phi[phi[j, 6], 6] == j, {j, 1, 64}];

If[!TrueQ[verifiedAnd06Q && verifiedXor06Q && verifiedPhiInvolution06Q],
  Print["Verification failed for ordering_invariance_6node.wl"];
  Exit[1];
];

summaryRows = {
  "Node 5 (AND) & 16 & \\texttt{" <> ToString[verifiedAnd06Q] <> "} & \\texttt{" <> ToString[verifiedPhiInvolution06Q] <> "} \\\\",
  "Node 6 (XOR) & 32 & \\texttt{" <> ToString[verifiedXor06Q] <> "} & \\texttt{" <> ToString[verifiedPhiInvolution06Q] <> "} \\\\"
};

sessionLines = {
  "In := phi06[j_] := 1 + FromDigits[Reverse[IntegerDigits[j - 1, 2, 6]], 2]",
  "In := andLSB06 = " <> ToString[InputForm[andLSB06]],
  "In := andPhi06 = Sort[phi06 /@ andLSB06]",
  "In := andMSB06 = " <> ToString[InputForm[andMSB06]],
  "",
  "(* Transported AND one-set under MSB ordering *)",
  "Out = " <> ToString[InputForm[andPhi06]],
  "",
  "(* Direct MSB exhaustive baseline for node 5 *)",
  "Out = " <> ToString[InputForm[andMSB06]],
  "",
  "(* Exact invariance check for AND *)",
  "Out = " <> ToString[InputForm[verifiedAnd06Q]],
  "",
  "In := xorLSB06 = " <> ToString[InputForm[xorLSB06]],
  "In := xorPhi06 = Sort[phi06 /@ xorLSB06]",
  "In := xorMSB06 = " <> ToString[InputForm[xorMSB06]],
  "",
  "(* Transported XOR one-set under MSB ordering *)",
  "Out = " <> ToString[InputForm[xorPhi06]],
  "",
  "(* Direct MSB exhaustive baseline for node 6 *)",
  "Out = " <> ToString[InputForm[xorMSB06]],
  "",
  "(* Exact invariance check for XOR *)",
  "Out = " <> ToString[InputForm[verifiedXor06Q]],
  "",
  "(* Involution check: phi(phi(j)) = j for all j in U *)",
  "Out = " <> ToString[InputForm[verifiedPhiInvolution06Q]]
};

summary = <|
  "PhiInvolutionVerified" -> verifiedPhiInvolution06Q,
  "AND" -> <|
    "LSBSet" -> andLSB06,
    "TransportedSet" -> andPhi06,
    "MSBBaseline" -> andMSB06,
    "Verified" -> verifiedAnd06Q
  |>,
  "XOR" -> <|
    "LSBSet" -> xorLSB06,
    "TransportedSet" -> xorPhi06,
    "MSBBaseline" -> xorMSB06,
    "Verified" -> verifiedXor06Q
  |>
|>;

Export[FileNameJoin[{baseDir, "ordering_invariance_session.txt"}], StringRiffle[sessionLines, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "ordering_invariance_summary_rows.tex"}], StringRiffle[summaryRows, "\n"], "Text"];
Export[FileNameJoin[{baseDir, "ordering_invariance_summary.json"}], Normal[summary], "JSON"];

Print[StringRiffle[sessionLines, "\n"]];
