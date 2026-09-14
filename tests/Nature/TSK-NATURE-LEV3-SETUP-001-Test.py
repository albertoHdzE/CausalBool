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
    """Both comparison measures on all three matrices.

    AUDIT04-F. This producer happens to run the single case that separates the
    two measures, and it used to report only one number per matrix.

    The checkerboard is the index-set length's worst case: it is a run-length
    code over each row's neighbour index set, and an alternating row costs n/2
    runs, its maximum, while its algorithmic content is nearly nil. So the
    index-set length is EXPECTED to call the checkerboard more expensive than a
    random matrix of the same density here -- a declared inversion, recorded
    beside `test_structured_families_against_matched_random`. BDM gets it right.

    Reporting one measure would have made this artefact say either "the method
    fails" or "the method passes", both of which are less true than the pair.
    The random comparator is drawn at p = 0.5, which matches the checkerboard's
    density exactly, so the comparison is on a common coordinate.
    """
    s1 = structured_adj(n)
    s2 = checker_adj(n)
    r = random_adj(n, 0.5)
    out = {"n": n, "measures": ["index_set_program_length", "bdm"]}
    for label, m in (("structured", s1), ("checker", s2), ("random", r)):
        enc = UniversalDv2Encoder(m).compute()
        out[f"dv2_{label}"] = float(enc["dv2"])          # retained key name
        out[f"index_set_{label}"] = float(enc["index_set_bits"])
        out[f"bdm_{label}"] = None if enc["bdm"] is None else float(enc["bdm"])
    return out

def main():
    res_dir = Path(__file__).resolve().parents[2] / "results" / "lev3"
    res_dir.mkdir(parents=True, exist_ok=True)
    out_path = res_dir / "setup001.json"
    results = []
    for n in [32, 48, 64]:
        results.append(run_comparison(n))
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    # AUDIT04-F. The verdict is stated PER MEASURE, and the chain case is
    # separated from the checkerboard case, because they are different claims
    # and folding them into one boolean is what hid the difference.
    #
    #   chain vs random     both measures must order it correctly.
    #   checker vs random   BDM must; the index-set length is DECLARED to fail,
    #                       for the reason in run_comparison's docstring.
    verdict = {}
    for measure in ("index_set", "bdm"):
        verdict[measure] = {
            "structured_below_random": all(
                x[f"{measure}_structured"] < x[f"{measure}_random"] for x in results),
            "checker_below_random": all(
                x[f"{measure}_checker"] < x[f"{measure}_random"] for x in results),
        }
    ok = (verdict["index_set"]["structured_below_random"]
          and verdict["bdm"]["structured_below_random"]
          and verdict["bdm"]["checker_below_random"])
    declared_inversion = not verdict["index_set"]["checker_below_random"]

    status_path = res_dir / "setup001_status.txt"
    with open(status_path, "w") as f:
        f.write("PASS\n" if ok else "FAIL\n")
        f.write(f"index_set  chain<random={verdict['index_set']['structured_below_random']}"
                f"  checker<random={verdict['index_set']['checker_below_random']}\n")
        f.write(f"bdm        chain<random={verdict['bdm']['structured_below_random']}"
                f"  checker<random={verdict['bdm']['checker_below_random']}\n")
        f.write("index-set checkerboard inversion: "
                f"{'PRESENT as declared' if declared_inversion else 'ABSENT -- the declaration is now stale'}\n")
    print("PASS" if ok else "FAIL")
    for measure in ("index_set", "bdm"):
        v = verdict[measure]
        print(f"  {measure:10s} chain<random={v['structured_below_random']}"
              f"  checker<random={v['checker_below_random']}")

if __name__ == "__main__":
    main()
