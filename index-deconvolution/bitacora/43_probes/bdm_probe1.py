import sys, math, random
sys.path.insert(0, "src")
from description_lengths import ctm_1d, bdm_1d, bdm_1d_partition, bdm_1d_trace
def tr(s, **kw):
    t = bdm_1d_trace(s, **kw)
    print(kw, "covered", t["covered_bits"], "of", t["n"])
    for r in t["rows"]:
        print("  ", r["start"], r["block"], f"ctm={r['ctm']:.3f}", "occ", r["occurrence"], f"adds={r['added']:.3f}")
    print("  total", round(t["rows"][-1]["running"],3))
X="1111100000"
tr(X, block=5)
tr(X, block=5, shift=1)
try: tr(X, block=5, shift=2)
except Exception as e: print("shift2 raise:", e)
tr(X, block=5, shift=2, remainder="drop")
# repetition term: aggregated at end, not incremental?
print("log2 check", bdm_1d("11111"*4, block=5), ctm_1d("11111")+math.log2(4))
