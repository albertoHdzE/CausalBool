import sys, random, numpy as np
sys.path.insert(0, "src")
from description_lengths import bdm_2d
from scipy.stats import spearmanr
def eca(rule, w=64, t=64, seed=0):
    r = np.random.default_rng(seed); x = r.integers(0, 2, w); rows=[x]
    tab = [(rule >> k) & 1 for k in range(8)]
    for _ in range(t-1):
        x = np.array([tab[4*x[(i-1)%w] + 2*x[i] + x[(i+1)%w]] for i in range(w)]); rows.append(x)
    return np.array(rows)
rng = random.Random(7)
for rule in (30, 110, 90, 4):
    A = eca(rule); cells=[(rng.randrange(64), rng.randrange(64)) for _ in range(60)]
    D = np.zeros((60,4)); base=[]
    for dc in range(4):
        S = np.roll(A, dc, axis=1); b0 = bdm_2d(S); base.append(b0)
        for q,(r,c) in enumerate(cells):
            T = S.copy(); T[r, (c+dc)%64] ^= 1
            D[q,dc] = b0 - bdm_2d(T)
    unstable = np.mean([np.sign(d).min() != np.sign(d).max() for d in np.round(D,9)])
    rho = [spearmanr(D[:,0], D[:,k]).correlation for k in (1,2,3)]
    print(f"rule {rule:>3}: BDM of the unperturbed diagram over 4 phases {min(base):.0f}-{max(base):.0f}; "
          f"dBDM sign flips with phase for {unstable:.0%} of 60 cells; median range {np.median(np.ptp(D,1)):.1f} bits "
          f"vs median |dBDM| {np.median(np.abs(D)):.1f}; Spearman(cell ranking, phase0 vs 1..3) {np.round(rho,2)}")
