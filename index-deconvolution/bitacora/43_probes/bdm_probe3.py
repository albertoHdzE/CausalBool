import sys, random, numpy as np
sys.path.insert(0, "src")
from description_lengths import bdm_1d
from scipy.stats import mannwhitneyu
def kw(b, n, slide):
    if slide: return dict(block=b, shift=1)
    return dict(block=b) if n % b == 0 else dict(block=b, remainder="recursive")
def sig(x, **k):
    B = bdm_1d(x, **k); out=[]
    for i in range(len(x)):
        y = x[:i] + ("1" if x[i]=="0" else "0") + x[i+1:]
        out.append(B - bdm_1d(y, **k))
    return np.array(out)
def auc(a, b):  # P(|I| left < |I| right): seam separation, rank-based
    return mannwhitneyu(np.abs(b), np.abs(a)).statistic/(len(a)*len(b))
rng = random.Random(1)
R = "".join(rng.choice("01") for _ in range(64))
X = "01"*32 + R
nulls = [(lambda r: "".join(r.choice("01") for _ in range(128)))(random.Random(100+j)) for j in range(30)]
assert len(set(nulls)) == 30 and all(0.3 < z.count("1")/128 < 0.7 for z in nulls)
print("b  mode     AUC(seam string)  null AUC 5-95%   distinct |I| values")
for slide in (False, True):
    for b in (1,2,3,4,6,8,12):
        if slide and b == 1: continue
        k = kw(b, 128, slide); s = sig(X, **k)
        a = auc(s[:64], s[64:])
        na = [auc(*(lambda t:(t[:64],t[64:]))(sig(z, **k))) for z in nulls]
        print(f"{b:>2} {'slide' if slide else 'tile ':6} {a:8.3f}        [{np.percentile(na,5):.3f}, {np.percentile(na,95):.3f}]   {len(set(np.round(np.abs(s),6)))}")
