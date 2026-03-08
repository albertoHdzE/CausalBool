import json
import os
import sys
import numpy as np
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))
from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

def structured_adj(n: int) -> np.ndarray:
    a = np.zeros((n, n), dtype=int)
    for i in range(n):
        a[i, i] = 1
        if i + 1 < n:
            a[i, i + 1] = 1
    return a

def checker_adj(n: int) -> np.ndarray:
    a = np.indices((n, n)).sum(axis=0) % 2
    return a.astype(int)

def random_adj(n: int, p: float = 0.5) -> np.ndarray:
    rng = np.random.default_rng(42)
    return (rng.random((n, n)) < p).astype(int)

def run_comparison(n: int) -> dict:
    s1 = structured_adj(n)
    s2 = checker_adj(n)
    r = random_adj(n, 0.5)
    enc_s1 = UniversalDv2Encoder(s1).compute()["dv2"]
    enc_s2 = UniversalDv2Encoder(s2).compute()["dv2"]
    enc_r = UniversalDv2Encoder(r).compute()["dv2"]
    return {"n": n, "dv2_structured": float(enc_s1), "dv2_checker": float(enc_s2), "dv2_random": float(enc_r)}

def main():
    res_dir = Path(__file__).resolve().parents[2] / "results" / "lev3"
    res_dir.mkdir(parents=True, exist_ok=True)
    out_path = res_dir / "setup001.json"
    results = []
    for n in [32, 48, 64]:
        results.append(run_comparison(n))
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    ok = all(x["dv2_structured"] < x["dv2_random"] and x["dv2_checker"] < x["dv2_random"] for x in results)
    status_path = res_dir / "setup001_status.txt"
    with open(status_path, "w") as f:
        f.write("PASS\n" if ok else "FAIL\n")
    print("PASS" if ok else "FAIL")

if __name__ == "__main__":
    main()
