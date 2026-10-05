import sys, math, random
sys.path.insert(0, "src")
from description_lengths import ctm_1d, bdm_1d
b=12
Z,O="0"*b,"1"*b
print("E2 two-word alphabet, block 12")
for m in (100,1000,10000):
    alt="".join(Z if i%2==0 else O for i in range(m))
    rng=random.Random(m); seq=[Z]*(m//2)+[O]*(m//2); rng.shuffle(seq); rnd="".join(seq)
    arr=math.lgamma(m+1)/math.log(2)-2*math.lgamma(m//2+1)/math.log(2)
    print(f" m={m:>6} len={m*b:>7} BDM(alternating)={bdm_1d(alt,block=b):.2f} BDM(random order)={bdm_1d(rnd,block=b):.2f} "
          f"bits to name the order log2 C(m,m/2)={arr:.1f}")
print("E3 every 12-bit word once")
W=[format(i,"012b") for i in range(4096)]
cnt="".join(W); rng=random.Random(3); P=W[:]; rng.shuffle(P); per="".join(P)
C12=sum(ctm_1d(w) for w in W)
print(f" len={len(cnt)} BDM(counter)={bdm_1d(cnt,block=12):.1f} BDM(random perm)={bdm_1d(per,block=12):.1f} C_12={C12:.1f} log2(4096!)={math.lgamma(4097)/math.log(2):.0f}")
print("E3b sliding (step1) on counter vs perm:", round(bdm_1d(cnt[:12*400],block=12,shift=1),1), round(bdm_1d(per[:12*400],block=12,shift=1),1))
print("E4 fair-coin strings, block 12: BDM / length, and the omitted order term")
for N in (1200,12000,120000,1200000):
    rng=random.Random(N); s="".join(rng.choice("01") for _ in range(N))
    blocks=[s[i:i+12] for i in range(0,N,12)]
    from collections import Counter
    c=Counter(blocks); m=len(blocks)
    arr=(math.lgamma(m+1)-sum(math.lgamma(v+1) for v in c.values()))/math.log(2)
    B=bdm_1d(s,block=12)
    print(f" N={N:>8} BDM={B:10.1f} BDM/N={B/N:.3f} order term={arr:10.1f} (BDM+order)/N={(B+arr)/N:.3f}")
