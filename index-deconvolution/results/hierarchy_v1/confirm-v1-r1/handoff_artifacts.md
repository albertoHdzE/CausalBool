#### A1. automatically inferred success: largest saving among structured confirmation strings with >= 3 rules

- case `confirmation-F06-4096-1002-base`, method `hid_full`, n = 4096 bits
- input sha256 `42a069d1f7491ee33307c68852e2fe835571557523806a4bdd6387c55581a45a` (regenerated; row says `42a069d1f7491ee3…`)
- archive `archives/b4/b4a185907a8521dc599669ed718a39cb152207f1527b036025058799459aaafe.isd`, sha256 `b4a185907a8521dc599669ed718a39cb152207f1527b036025058799459aaafe`
- archive 1624 bits (row 1624); raw archive 4168 bits; portfolio 2472 bits (lzma); search stop `rounds_exhausted`, source `global:split[2048]>xform(flags=0,r=4)`
- decoded by `decode.py` equals the input: **True**; ledger sum 1624 bits = archive 1624 bits
- graph (read back from the archive bytes):

  | id | op | length | refs | detail |
  |---:|---|---:|---:|---|
  | 0 | LITERAL | 13 | 2 | {"bits": "0001011110101"} |
  | 1 | XFORM | 13 | 1 | {"child": 0, "complement": false, "reverse": false, "right_rotation": 4} |
  | 2 | REPEAT | 2041 | 1 | {"child": 1, "copies": 157} |
  | 3 | LITERAL | 7 | 1 | {"bits": "0101000"} |
  | 4 | CONCAT | 2048 | 1 | {"children": [2, 3]} |
  | 5 | PATCH | 2048 | 1 | {"child": 4, "flips": 58, "positions": "32 shown of 58"} |
  | 6 | LITERAL | 13 | 1 | {"bits": "1011110101000"} |
  | 7 | REPEAT | 1014 | 1 | {"child": 6, "copies": 78} |
  | 8 | LITERAL | 10 | 1 | {"bits": "1011110101"} |
  | 9 | CONCAT | 1024 | 1 | {"children": [7, 8]} |
  | 10 | PATCH | 1024 | 1 | {"child": 9, "flips": 36, "positions": "32 shown of 36"} |
  | 11 | REPEAT | 1014 | 1 | {"child": 0, "copies": 78} |
  | 12 | LITERAL | 10 | 1 | {"bits": "0001011110"} |
  | 13 | CONCAT | 1024 | 1 | {"children": [11, 12]} |
  | 14 | PATCH | 1024 | 1 | {"child": 13, "flips": 34, "positions": "32 shown of 34"} |
  | 15 | CONCAT | 2048 | 1 | {"children": [10, 14]} |
  | 16 | CONCAT | 4096 | 0 | {"children": [5, 15]} |

- exact byte ledger, summed per record (190 fields in `handoff_artifacts.json`): envelope 9, dag 1, rule0 4, rule1 4, rule2 4, rule3 3, rule4 4, rule5 63, rule6 4, rule7 3, rule8 4, rule9 4, rule10 40, rule11 3, rule12 4, rule13 4, rule14 37, rule15 4, rule16 4 — total 203 bytes

#### A2. baseline loss: largest loss among structured confirmation strings

- case `confirmation-F12-4096-1014-ragged`, method `hid_full`, n = 4099 bits
- input sha256 `1277211d0284e0d57c4c26e604bc635d7803d6b5c4b0d2cd99eef7acd67c7b89` (regenerated; row says `1277211d0284e0d5…`)
- archive `archives/eb/eb39fc916d10d15d176f18b2f74258e945af4de62ab718c84fdec3ef21235505.isd`, sha256 `eb39fc916d10d15d176f18b2f74258e945af4de62ab718c84fdec3ef21235505`
- archive 3456 bits (row 3456); raw archive 4176 bits; portfolio 2176 bits (zlib); search stop `candidate_cap`, source `seg:fixed[256,phase=6]:local>xform(flags=0,r=2)`
- decoded by `decode.py` equals the input: **True**; ledger sum 3456 bits = archive 3456 bits
- graph (read back from the archive bytes):

  | id | op | length | refs | detail |
  |---:|---|---:|---:|---|
  | 0 | LITERAL | 6 | 1 | {"bits": "001010"} |
  | 1 | LITERAL | 17 | 2 | {"bits": "10100001001010101"} |
  | 2 | XFORM | 17 | 2 | {"child": 1, "complement": false, "reverse": false, "right_rotation": 2} |
  | 3 | XFORM | 17 | 1 | {"child": 2, "complement": false, "reverse": false, "right_rotation": 1} |
  | 4 | REPEAT | 255 | 1 | {"child": 3, "copies": 15} |
  | 5 | LITERAL | 1 | 2 | {"bits": "1"} |
  | 6 | CONCAT | 256 | 1 | {"children": [4, 5]} |
  | 7 | REPEAT | 255 | 1 | {"child": 2, "copies": 15} |
  | 8 | LITERAL | 1 | 1 | {"bits": "0"} |
  | 9 | CONCAT | 256 | 1 | {"children": [7, 8]} |
  | 10 | REPEAT | 255 | 1 | {"child": 1, "copies": 15} |
  | 11 | CONCAT | 256 | 2 | {"children": [10, 5]} |
  | 12 | XFORM | 256 | 1 | {"child": 11, "complement": false, "reverse": false, "right_rotation": 1} |
  | 13 | LITERAL | 256 | 1 | {"bits": "1010000100101010110100001001010101101000\u2026"} |
  | 14 | LITERAL | 256 | 1 | {"bits": "0100001001010101101000010010101011010000\u2026"} |
  | 15 | LITERAL | 256 | 1 | {"bits": "0100011110011011110111011011101110110100\u2026"} |
  | 16 | LITERAL | 256 | 1 | {"bits": "0001010100111100110011000110101011110101\u2026"} |
  | 17 | LITERAL | 256 | 1 | {"bits": "0000110001011111000101010100100100111101\u2026"} |
  | 18 | LITERAL | 256 | 1 | {"bits": "1001011111011110001110100010100110111100\u2026"} |
  | 19 | LITERAL | 256 | 1 | {"bits": "0101110101110010011110100010011000001011\u2026"} |
  | 20 | LITERAL | 39 | 1 | {"bits": "011101110111010101000100010000100010001"} |
  | 21 | REPEAT | 234 | 1 | {"child": 20, "copies": 6} |
  | 22 | LITERAL | 22 | 1 | {"bits": "0111011101110101010001"} |
  | 23 | CONCAT | 256 | 1 | {"children": [21, 22]} |
  | 24 | LITERAL | 256 | 1 | {"bits": "0001000010001000101110111011101010100010\u2026"} |
  | 25 | LITERAL | 39 | 1 | {"bits": "110111010101000100010000100010001011101"} |
  | 26 | REPEAT | 234 | 1 | {"child": 25, "copies": 6} |
  | 27 | LITERAL | 22 | 1 | {"bits": "1101110101010001000100"} |
  | 28 | CONCAT | 256 | 1 | {"children": [26, 27]} |
  | 29 | LITERAL | 39 | 1 | {"bits": "001000100010111011101110101010001000100"} |
  | 30 | REPEAT | 234 | 1 | {"child": 29, "copies": 6} |
  | 31 | LITERAL | 22 | 1 | {"bits": "0010001000101110111011"} |
  | 32 | CONCAT | 256 | 1 | {"children": [30, 31]} |
  | 33 | LITERAL | 39 | 1 | {"bits": "101010100010001000010001000101110111011"} |
  | 34 | REPEAT | 234 | 1 | {"child": 33, "copies": 6} |
  | 35 | LITERAL | 19 | 1 | {"bits": "1010101000100010000"} |
  | 36 | CONCAT | 253 | 1 | {"children": [34, 35]} |
  | 37 | CONCAT | 4099 | 0 | {"children": [0, 6, 9, 12, 13, 11, 14, 15, 16, 17, 18, 19, 23, 24, 28, 32, 36]} |

- exact byte ledger, summed per record (145 fields in `handoff_artifacts.json`): envelope 9, dag 1, rule0 3, rule1 5, rule2 4, rule3 4, rule4 3, rule5 3, rule6 4, rule7 3, rule8 3, rule9 4, rule10 3, rule11 4, rule12 4, rule13 35, rule14 35, rule15 35, rule16 35, rule17 35, rule18 35, rule19 35, rule20 7, rule21 3, rule22 5, rule23 4, rule24 35, rule25 7, rule26 3, rule27 5, rule28 4, rule29 7, rule30 3, rule31 5, rule32 4, rule33 7, rule34 3, rule35 5, rule36 4, rule37 19 — total 432 bytes

#### A3. the portfolio archive that wins that loss

- case `confirmation-F12-4096-1014-ragged`, method `baseline_best`, n = 4099 bits
- input sha256 `1277211d0284e0d57c4c26e604bc635d7803d6b5c4b0d2cd99eef7acd67c7b89` (regenerated; row says `1277211d0284e0d5…`)
- archive `archives/79/79ec1c477dd467a75cdd67676d218f147a8ba7a5abc9b13b2582e1a3e5253bfd.isd`, sha256 `79ec1c477dd467a75cdd67676d218f147a8ba7a5abc9b13b2582e1a3e5253bfd`
- archive 2176 bits (row 2176); raw archive 4176 bits; portfolio 2176 bits (zlib); search stop `None`, source `None`
- decoded by `decode.py` equals the input: **True**; ledger sum 2176 bits = archive 2176 bits

- exact byte ledger:

  | owner | field | bytes | hex |
  |---|---|---:|---|
  | envelope | magic | 4 | `49534431` |
  | envelope | codec_id | 1 | `07` |
  | envelope | output_n_bits | 2 | `8320` |
  | envelope | payload_n_bytes | 2 | `8702` |
  | zlib | compressed stream incl. library headers/checksums | 263 | `78dad3ba3035c36b8b6a94d05aceb096d54ea10bb56821a0` |

#### A4. noise case with literal fallback: first F06 confirmation string where HID returned raw mode

- case `confirmation-F06-1024-1005-base`, method `hid_full`, n = 1024 bits
- input sha256 `9b95db04cd80cb11257d52f747035a11e1cb4b90a8b61e5bf4ea42d333c76b0f` (regenerated; row says `9b95db04cd80cb11…`)
- archive `archives/a4/a42d6a4d11ee73ef1626575e09a92c12015ca6a80949aa6014fca828256f6314.isd`, sha256 `a42d6a4d11ee73ef1626575e09a92c12015ca6a80949aa6014fca828256f6314`
- archive 1096 bits (row 1096); raw archive 1096 bits; portfolio 1080 bits (bernoulli); search stop `converged`, source `literal`
- decoded by `decode.py` equals the input: **True**; ledger sum 1096 bits = archive 1096 bits

- exact byte ledger:

  | owner | field | bytes | hex |
  |---|---|---:|---|
  | envelope | magic | 4 | `49534431` |
  | envelope | codec_id | 1 | `00` |
  | envelope | output_n_bits | 2 | `8008` |
  | envelope | payload_n_bytes | 2 | `8001` |
  | literal | P(bits) [1024 bits] | 128 | `5a8eba1bbe23ce7e951d72357cc79c5d223aec6cf98f39fa` |

#### A5. tiny oracle case: 64 identical bits, repetition beats the raw envelope

- target: 64 ones; oracle program `R(L(1),64)`; raw 120 bits; restricted search 112 bits; full search 96 bits
- input sha256 `3138bb9bc78df27c473ecfd1410f7bd45ebac1f59cf3ff9cfe4db77aab7aedd3`, archive sha256 `5b411d85a889cec3575fad8f5bf44f42c6bbe19f95ce04406a3b50eab1f0279e`
- decoded by `decode.py` equals the input: **True**; ledger sum 112 bits = archive 112 bits
- graph (read back from the archive bytes):

  | id | op | length | refs | detail |
  |---:|---|---:|---:|---|
  | 0 | LITERAL | 1 | 1 | {"bits": "1"} |
  | 1 | REPEAT | 64 | 0 | {"child": 0, "copies": 64} |

- exact byte ledger:

  | owner | field | bytes | hex |
  |---|---|---:|---|
  | envelope | magic | 4 | `49534431` |
  | envelope | codec_id | 1 | `01` |
  | envelope | output_n_bits | 1 | `40` |
  | envelope | payload_n_bytes | 1 | `07` |
  | dag | q_rules | 1 | `02` |
  | rule0 | opcode | 1 | `00` |
  | rule0 | length | 1 | `01` |
  | rule0 | P(bits) [1 bits + 7 pad] | 1 | `80` |
  | rule1 | opcode | 1 | `02` |
  | rule1 | child_id | 1 | `00` |
  | rule1 | copies | 1 | `40` |
