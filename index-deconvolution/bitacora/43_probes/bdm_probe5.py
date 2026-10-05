import sys, random, math, numpy as np
from collections import Counter
sys.path.insert(0, "src")
from description_lengths import ctm_1d, bdm_1d
from scipy.stats import spearmanr
c12=[ctm_1d(format(i,"012b")) for i in range(4096)]
print(f"CTM over all 4096 12-bit words: min {min(c12):.2f} median {np.median(c12):.2f} max {max(c12):.2f}")
print("CTM(00)==CTM(11):", ctm_1d("00")==ctm_1d("11"), " CTM(01)==CTM(10):", ctm_1d("01")==ctm_1d("10"))
def eca_row_string(rule, seed, n=96, t=40):
    r=random.Random(seed); x=[r.randrange(2) for _ in range(n)]
    tab=[(rule>>k)&1 for k in range(8)]
    for _ in range(t): x=[tab[4*x[i-1]+2*x[i]+x[(i+1)%n]] for i in range(n)]
    return "".join(map(str,x))
rng=random.Random(5); S=[]
for j in range(600):
    kind=j%3
    if kind==0: S.append(eca_row_string(rng.randrange(256), j))
    elif kind==1:
        p=rng.randrange(1,24); u="".join(rng.choice("01") for _ in range(p)); S.append((u*96)[:96])
    else:
        q=rng.uniform(0.02,0.5); S.append("".join("1" if rng.random()<q else "0" for _ in range(96)))
B=np.array([bdm_1d(s,block=12) for s in S])
def e1(s,b=12):
    c=Counter(s[i:i+b] for i in range(0,len(s),b)); return b*len(c)+sum(math.log2(v) for v in c.values())
def e1ctm_mean(s,b=12):
    c=Counter(s[i:i+b] for i in range(0,len(s),b)); return np.mean(c12)*len(c)+sum(math.log2(v) for v in c.values())
E1=np.array([e1(s) for s in S]); E1m=np.array([e1ctm_mean(s) for s in S])
print(f"n={len(S)} strings of 96 bits (ECA rows / periodic / biased coins)")
print(f"Spearman(BDM_12, distinct-count code with flat 12 bits/word) = {spearmanr(B,E1).correlation:.4f}")
print(f"residual: BDM - (mean-CTM x distinct + sum log n): median {np.median(B-E1m):.2f}, 5-95% {np.percentile(B-E1m,[5,95]).round(2)} bits; BDM range {B.min():.1f}-{B.max():.1f}")
