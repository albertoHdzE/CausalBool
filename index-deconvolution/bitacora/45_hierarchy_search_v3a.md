# 45 · HID-search-v3a: four refinement seeds lengthen the archives

2026-10-04. Run `search-confirm-v3a-r1`, freeze `05dd799d…`. Ready for Codex review; not
yet accepted.

The question was narrow. Boundary stage B refines one coarse cut per round. Would
refining the four best distinct coarse partitions, under the same caps, shorten the
full method's complete archive on six boundary cells? The answer from 120 fresh paired
units is no. The equal-cell mean saving is −0.0063 bits per input bit, with 99% interval
[−0.0083, −0.0042] (seed 55001, 10,000 draws). The upper bound is below zero, so the
prespecified reading is HARMFUL.

The loss sits in F12 at 4,096 and 16,384 bits: k = 4 is worse on 26 and 25 of 40
strings and never better. The only gain is S02 at 4,096 bits, with 18 of 40 strings
better and 5 worse. Both large F12 cells tie on every string. Under k = 4, the shared
shortest-period length charge runs out in 219 of 256 strings, which never happens under
k = 1, and the search commits fewer rounds. That co-occurs with the loss; the design
does not make it the cause.

Engineering held throughout. The one-seed path reproduced all 1,792 accepted search-v2
archives byte for byte before the freeze. Every one of the 3,072 rows is valid and
complete, and every HID job carries a consistent trace. The independent audit recomputed
the estimate, the cell means and the interval from archive bytes. Development on
inspected strings had already leaned the same way (28 better, 104 tied, 44 worse); it
was not a gate.

Details: `results/hierarchy_search_v3a/search-confirm-v3a-r1/REPORT.md`, notebook 20.
