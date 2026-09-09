import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
import networkx as nx
import sys

# Add src to path for local imports
SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
# Local imports
from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "bio" / "processed"
RESULTS_DIR   = Path(__file__).resolve().parents[2] / "results" / "bio"
NULL_STATS_FILE = RESULTS_DIR / "null_stats.json"

# AUDIT04 Phase 2: RESULTS_DIR.mkdir() ran here, at module level, so importing
# this module created results/bio/ as a side effect. Deferred to the point of
# writing, where it belongs.

class TimeoutException(Exception):
    pass

def signal_handler(signum, frame):
    raise TimeoutException("Time limit reached")

def load_cm(path: Path) -> Tuple[str, np.ndarray, List[str]]:
    with open(path, "r") as f:
        data = json.load(f)
    name  = data.get("name") or path.stem
    cm    = np.array(data.get("cm", []), dtype=int)
    nodes = data.get("nodes", [])
    if cm.size == 0 and nodes:
        # Fallback if edges exist (rare in processed)
        edges = data.get("edges", [])
        n     = len(nodes)
        cm    = np.zeros((n, n), dtype=int)
        idx   = {n: i for i, n in enumerate(nodes)}
        for s, t in edges:
            if s in idx and t in idx:
                cm[idx[s], idx[t]] = 1
    return name, cm, nodes

def er_edge_shuffle(cm: np.ndarray, allow_self_loops: bool = False, seed: int | None = None) -> np.ndarray:
    rng    = np.random.default_rng(seed)
    n      = cm.shape[0]
    E      = int(cm.sum())
    mask   = np.ones((n, n), dtype=bool)
    if not allow_self_loops:
        np.fill_diagonal(mask, False)
    positions = np.argwhere(mask)
    if E > len(positions):
        E = len(positions)
    chosen    = positions[rng.choice(len(positions), size=E, replace=False)]
    adj       = np.zeros_like(cm, dtype=int)
    for i, j in chosen:
        adj[i, j] = 1
    return adj

def degree_preserving_swap(cm: np.ndarray, nswap_factor: int = 10, seed: int | None = None) -> np.ndarray:
    G      = nx.from_numpy_array(cm, create_using=nx.DiGraph)
    E      = int(cm.sum())
    nswap  = max(1, nswap_factor * E)
    try:
        nx.directed_edge_swap(G, nswap=nswap, max_tries=100 * nswap, seed=seed)
    except (nx.NetworkXError, nx.NetworkXAlgorithmError):
        # Fallback: configuration model
        in_deg  = [d for _, d in G.in_degree()]
        out_deg = [d for _, d in G.out_degree()]
        try:
            G_conf = nx.directed_configuration_model(in_deg, out_deg, seed=seed)
            G      = nx.DiGraph(G_conf)  # collapse multiedges
        except Exception:
            # Final fallback: return original
            pass
    return nx.to_numpy_array(G).astype(int)

def gate_preserving_fanout(cm: np.ndarray, seed: int | None = None) -> np.ndarray:
    # Preserve per-row out-degree (fan-out). Randomly reassign targets per source.
    rng  = np.random.default_rng(seed)
    n    = cm.shape[0]
    adj  = np.zeros_like(cm, dtype=int)
    cols = np.arange(n)
    for i in range(n):
        k = int(cm[i].sum())
        if k == 0:
            continue
        choices = rng.choice(cols, size=k, replace=False)
        # Optionally avoid self loops similar to original structure
        if k < n and i in choices:
            # swap out self if present
            alt = rng.choice(cols[cols != i])
            choices[choices == i] = alt
        adj[i, choices] = 1
    return adj

def compute_dv2(cm: np.ndarray) -> float:
    enc = UniversalDv2Encoder(cm)
    res = enc.compute()
    return float(res["dv2"])


def separation(x: float, xs: List[float]) -> Dict[str, float]:
    """How far a value beats an ensemble, in bits and in rank. No mean, no sd.

    Promoted from a closure inside `process_networks` on 2026-09-07 (AUDIT04-F)
    because SimplicityV2_Nature needs the same operator and was still computing
    a z-score. Two homes for one comparison is the defect the audit removes, so
    there is one definition and the other module imports it.

    gap_bits   min(nulls) - x. The WORST-CASE advantage: how much shorter the
               real object is than the single best null, not than their average.
               By the coding theorem m(x) ~ 2^-K(x), a gap of g bits IS a
               likelihood ratio of 2^g under the universal distribution, which
               is a per-instance statement needing no ensemble shape.
    exceed     #{null <= x}/n, the exact permutation tail, valid whatever the
               null looks like.
    best/med   order statistics, for scale.

    REFUSES on an empty ensemble: a comparison against nothing is not a pass.
    """
    if not xs:
        raise ValueError(
            "separation over an EMPTY null ensemble. A comparison "
            "against nothing is not a pass."
        )
    beaten = sum(1 for v in xs if v <= x)
    return {
        "gap_bits": float(min(xs) - x),
        "exceed": beaten / len(xs),
        "best_null": float(min(xs)),
        "median_null": float(np.median(xs)),
    }


def compute_both(cm: np.ndarray) -> Dict[str, float | None]:
    """Both comparison measures for one adjacency matrix, side by side.

    AUDIT04-F. The author's directive of 2026-09-07 names TWO measures, the
    index-set program length and BDM, and decision #96 forbids combining them
    into one number. So this returns both under their own names and every
    downstream statistic is computed twice, once per measure.

    The reason is measured rather than procedural: at n = 16, against 20 random
    matrices of identical edge count, the index-set length calls a checkerboard
    1050.5 bits versus 563.9 for random and column stripes 1050.5 versus 568.4,
    while BDM calls them 34.3 versus 489.9 and 34.2 versus 485.2. On the sparse
    families this experiment actually meets the index-set length is the better
    behaved of the two on a chain (random simpler in 14/200 draws, BDM 0/200).
    Neither dominates, so neither decides alone.
    """
    enc = UniversalDv2Encoder(cm)
    res = enc.compute()
    return {"index_set": float(res["index_set_bits"]), "bdm": res["bdm"]}

def load_existing_results(out_file: Path | None = None) -> List[Dict[str, Any]]:
    """Load the in-memory list from `out_file` (or NULL_STATS_FILE).

    The subsample runs (H1.1) keep their own files so the main 231-network
    artefact is not touched. The default is unchanged.
    """
    target = out_file if out_file is not None else NULL_STATS_FILE
    if target.exists():
        try:
            with open(target, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_results(results: List[Dict[str, Any]], out_file: Path | None = None):
    """Write the in-memory list to `out_file` (or NULL_STATS_FILE).

    Created here rather than at import; see the note beside RESULTS_DIR.
    When `out_file` is given, the parent directory is created if missing, so
    a per-subsample run writes to its own file without disturbing the main
    231-network artefact. The default behaviour is unchanged.
    """
    target = out_file if out_file is not None else NULL_STATS_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write to avoid corruption
    temp_file = target.with_suffix(".tmp")
    with open(temp_file, "w") as f:
        json.dump(results, f, indent=2)
    temp_file.replace(target)

def process_networks(
    max_networks: int = 200,
    nulls_per_type: int = 1000,
    allow_self_loops: bool = False,
    seed: int | None = 42,
    time_limit_sec: int | None = None,
    subsample_name: str | None = None,
) -> List[Dict]:
    """Run the null generator.

    When `subsample_name` is set, the run writes to
    `results/bio/null_stats_{subsample_name}.json` instead of the main
    `null_stats.json` artefact, and the resume logic reads from the same
    file. The first `max_networks` files in alphabetical order are taken
    (the existing selection rule), so passing `max_networks=30` and
    `subsample_name="h1_30"` reproduces the H1.1 subsample exactly.
    """
    if subsample_name is not None:
        out_file = RESULTS_DIR / f"null_stats_{subsample_name}.json"
    else:
        out_file = NULL_STATS_FILE

    start_time = time.time()

    # Load existing results (Resume capability) from the run's own file.
    results = load_existing_results(out_file)
    processed_names = {r["network"] for r in results}
    
    # Load all potential files
    files = sorted([p for p in PROCESSED_DIR.glob("*.json") if p.name not in {"gate_histogram.json", "truth_tables.json"}])
    
    print(f"Loaded {len(results)} existing results. Found {len(files)} total network files.")
    
    count = 0
    
    try:
        for path in files:
            if count >= max_networks:
                break
                
            name, cm, nodes = load_cm(path)
            
            # Skip if already processed with sufficient nulls
            if name in processed_names:
                # Check if existing result has enough nulls
                existing_entry = next((r for r in results if r["network"] == name), None)
                if existing_entry and existing_entry.get("nulls_per_type", 0) >= nulls_per_type:
                    print(f"Skipping {name} (already has {existing_entry['nulls_per_type']} nulls)")
                    continue
                else:
                    print(f"Reprocessing {name} (requested {nulls_per_type} nulls, found {existing_entry.get('nulls_per_type', 0)})")
                    # Remove old entry to avoid duplicates
                    results = [r for r in results if r["network"] != name]

            # Validation filters
            if cm.size == 0 or cm.shape[0] != cm.shape[1]:
                continue
            n = cm.shape[0]
            if n < 5 or n > 100:
                continue

            # Check time limit
            if time_limit_sec and (time.time() - start_time > time_limit_sec):
                print(f"Time limit of {time_limit_sec}s reached. Stopping gracefully.")
                break

            print(f"[{len(results)+1}] Processing {name}: n={n}, E={int(cm.sum())}")
            
            bio = compute_both(cm)
            D_bio = bio["index_set"]
            null_scores: Dict[str, Dict[str, List[float]]] = {
                m: {"er": [], "deg": [], "gate": []} for m in ("index_set", "bdm")
            }

            for k in range(nulls_per_type):
                # Check time limit inside inner loop for very slow networks
                if time_limit_sec and (time.time() - start_time > time_limit_sec):
                     raise TimeoutException("Time limit reached inside loop")

                s = None if seed is None else seed + k
                # ER edge-shuffle
                cm_er   = er_edge_shuffle(cm, allow_self_loops=allow_self_loops, seed=s)
                # Degree-preserving
                cm_deg  = degree_preserving_swap(cm, nswap_factor=10, seed=s)
                # Gate-preserving (fanout)
                cm_gate = gate_preserving_fanout(cm, seed=s)
                for kind, cm_null in (("er", cm_er), ("deg", cm_deg), ("gate", cm_gate)):
                    both = compute_both(cm_null)
                    for m in ("index_set", "bdm"):
                        if both[m] is not None:
                            null_scores[m][kind].append(float(both[m]))

            # AUDIT04-E, author directive 2026-09-07: the z-score is replaced.
            #
            # It was `(mu - x) / sd`, which rescales a quantity in BITS by the
            # standard deviation of an ensemble. That is a distributional
            # summary wrapped around an algorithmic length, and it destroys
            # information the length already carries. Measured on three nulls
            # where bio beats 0 of 1000 in EVERY case -- identical evidence:
            #
            #   gaussian null       z = 5.07  pass      gap  8.8 bits  rank 0/1000
            #   DEGENERATE null     z = 0.00  FALSIFY   gap 50.0 bits  rank 0/1000
            #   heavy-tailed null   z = 0.31  FALSIFY   gap 20.0 bits  rank 0/1000
            #
            # The degenerate case is the old code's own `if sd > 0 else 0.0`
            # branch: every null 50 bits LONGER than bio, and it returned "no
            # evidence". The fat tail inflates sd and falsifies a real result.
            # The gap and the rank are unmoved by either.
            #
            # WHAT REPLACES IT, all algorithmic or distribution-free:
            #
            #   gap       D(best null) - D(bio), in bits. The WORST-CASE
            #             advantage: how much shorter bio is than the single
            #             best null, not than their average. By the coding
            #             theorem m(x) ~ 2^-K(x), a gap of g bits IS a
            #             likelihood ratio of 2^g under the universal
            #             distribution -- a per-instance statement needing no
            #             ensemble shape.
            #   exceed    #{null <= bio} / n. Distribution-free: the exact
            #             permutation-test tail, valid whatever the null looks
            #             like.
            #   best/med  order statistics, for scale. No mean, no sd.
            # AUDIT04-F: the separation is computed ONCE PER MEASURE. The top
            # level keys (`er`/`deg`/`gate`) keep carrying the index-set result
            # so that artefacts and readers written before this change resolve
            # unchanged; `bdm` holds the same three separations computed from
            # BDM, and nothing merges the two.
            entry = {
                "network": name,
                "nodes": len(nodes),
                "n": n,
                "E": int(cm.sum()),
                "D_bio": D_bio,
                "measure": "index_set_program_length",
                "measures": ["index_set_program_length", "bdm"],
                "D_bio_bdm": bio["bdm"],
                "nulls_per_type": nulls_per_type,
                "timestamp": time.time()
            }
            for kind in ("er", "deg", "gate"):
                entry[kind] = separation(D_bio, null_scores["index_set"][kind])
            if bio["bdm"] is None:
                entry["bdm"] = None
                entry["bdm_unavailable"] = (
                    f"n={n} is below pybdm's 4x4 partition floor; unmeasured, not zero")
            else:
                entry["bdm"] = {
                    kind: separation(float(bio["bdm"]), null_scores["bdm"][kind])
                    for kind in ("er", "deg", "gate")
                }
            results.append(entry)
            save_results(results, out_file) # Checkpoint after each network
            count += 1

    except TimeoutException:
        print("Time limit reached. Saving progress...")
    except KeyboardInterrupt:
        print("Interrupted! Saving progress...")
    finally:
        save_results(results, out_file)

    return results

def main():
    parser = argparse.ArgumentParser(description="Massive Null Model Generator with Checkpointing")
    parser.add_argument("--networks", type=int, default=200, help="Max networks to process")
    parser.add_argument("--nulls", type=int, default=1000, help="Nulls per type per network")
    parser.add_argument("--time_limit", type=int, default=None, help="Time limit in seconds (soft stop)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--subsample", type=str, default=None,
                        help="If set, write to null_stats_{subsample}.json instead of null_stats.json")

    args = parser.parse_args()

    print("=== Phase 3: Massive Null Model Generation ===")
    print(f"Configuration: Max Networks={args.networks}, Nulls={args.nulls}, Time Limit={args.time_limit}s, Subsample={args.subsample}")

    results = process_networks(
        max_networks=args.networks,
        nulls_per_type=args.nulls,
        allow_self_loops=False,
        seed=args.seed,
        time_limit_sec=args.time_limit,
        subsample_name=args.subsample,
    )
    
    print(f"Total processed so far: {len(results)}")
    
    # Global summary
    if results:
        # AUDIT04-E: summarised by ORDER STATISTICS and a count, not by a mean.
        # A mean of z-scores was a summary of a summary. The median gap says how
        # large the typical advantage is in bits; `separating` counts how many
        # networks beat EVERY null outright, which is the claim itself rather
        # than a proxy for it.
        def _col(kind: str, field: str, measure: str = "index_set") -> List[float]:
            if measure == "index_set":
                return [r[kind][field] for r in results if kind in r]
            return [r["bdm"][kind][field] for r in results
                    if isinstance(r.get("bdm"), dict) and kind in r["bdm"]]

        def _col_gap_to_median(kind: str, measure: str = "index_set") -> List[float]:
            # gap_to_median = D(median null) - D(bio). Per-record, so we
            # derive it from median_null and D_bio here rather than asking
            # the artefact to store it.
            D_key = "D_bio_bdm" if measure == "bdm" else "D_bio"
            if measure == "bdm":
                return [r["bdm"][kind]["median_null"] - r[D_key] for r in results
                        if isinstance(r.get("bdm"), dict)]
            return [r[kind]["median_null"] - r[D_key] for r in results if kind in r]

        def _block(kind: str, measure: str) -> Dict[str, Any]:
            # AUDIT04-H (H1.2): the summary now publishes FIVE statistics per
            # measure × null, three of them new and two retained. The retained
            # ones — `median_gap_bits` (the gap to the SINGLE BEST null, i.e.
            # the worst-case advantage) and `separating_at_exceed_0` (the
            # count of networks with `exceed == 0`) — are unchanged. The new
            # ones — `median_gap_to_median_null`, `n_bio_lt_median_null`,
            # and `median_exceed` — do not move with the null count.
            gaps_best  = _col(kind, "gap_bits", measure)
            gap_med    = _col_gap_to_median(kind, measure)
            exc        = _col(kind, "exceed", measure)
            return {
                "median_gap_bits": float(np.median(gaps_best)) if gaps_best else None,
                "min_gap_bits":    float(min(gaps_best)) if gaps_best else None,
                "median_gap_to_median_null": float(np.median(gap_med)) if gap_med else None,
                "n_bio_lt_median_null":      int(sum(1 for g in gap_med if g > 0)) if gap_med else 0,
                "median_exceed":             float(np.median(exc)) if exc else None,
                "separating_at_exceed_0":          int(sum(1 for e in exc if e == 0.0)) if exc else 0,
                "separating_at_exceed_lt_0.05":    int(sum(1 for e in exc if e < 0.05)) if exc else 0,
                "n": len(gaps_best),
            }

        summary: Dict[str, Any] = {
            "count": len(results),
            "measure": "index_set_program_length",
            "measures": ["index_set_program_length", "bdm"],
            "comparison": "gap_bits = D(best null) - D(bio); exceed = #{null <= bio}/n",
        }
        for kind in ("er", "deg", "gate"):
            summary[kind] = _block(kind, "index_set")
        # AUDIT04-F: BDM's own summary, under its own key. Two measures reported,
        # never averaged; where they disagree the disagreement is the result.
        summary["bdm"] = {kind: _block(kind, "bdm") for kind in ("er", "deg", "gate")}
        summary["agreement"] = {
            kind: {
                "both_separate": sum(
                    1 for r in results
                    if kind in r and isinstance(r.get("bdm"), dict)
                    and r[kind]["exceed"] < 0.05 and r["bdm"][kind]["exceed"] < 0.05),
                "disagree": sum(
                    1 for r in results
                    if kind in r and isinstance(r.get("bdm"), dict)
                    and (r[kind]["exceed"] < 0.05) != (r["bdm"][kind]["exceed"] < 0.05)),
                "n": sum(1 for r in results
                         if kind in r and isinstance(r.get("bdm"), dict)),
            }
            for kind in ("er", "deg", "gate")
        }
        # The module-level mkdir was removed (it ran on import); every write
        # site must now guarantee the directory itself.
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        if args.subsample is not None:
            summary_path = RESULTS_DIR / f"null_summary_{args.subsample}.json"
        else:
            summary_path = RESULTS_DIR / "null_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        for measure in ("index_set", "bdm"):
            print(f"  -- {measure} --")
            for kind in ("er", "deg", "gate"):
                s = summary[kind] if measure == "index_set" else summary["bdm"][kind]
                if s["n"]:
                    # AUDIT04-H (H1.2): three comparators now published.
                    # The "worst-case advantage" is the gap to the best null.
                    # The "median-null gap" is the gap to the median null.
                    # The "exceed==0" count is the worst-case indicator.
                    print(f"  {kind:5s} worst-case adv {s['median_gap_bits']:8.2f} bits · "
                          f"med-null gap {s['median_gap_to_median_null']:7.2f} · "
                          f"med exceed {s['median_exceed']:.3f} · "
                          f"beats EVERY null {s['separating_at_exceed_0']}/{s['n']} · "
                          f"shorter than median null {s['n_bio_lt_median_null']}/{s['n']}")
        for kind in ("er", "deg", "gate"):
            a = summary["agreement"][kind]
            if a["n"]:
                print(f"  {kind:5s} both measures separate {a['both_separate']}/{a['n']} · "
                      f"they DISAGREE on {a['disagree']}/{a['n']}")

if __name__ == "__main__":
    main()
