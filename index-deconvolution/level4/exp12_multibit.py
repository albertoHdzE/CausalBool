"""exp12_multibit.py  (Level 4)

Discover, in an uncontrolled sequence, which candidate units carry structure under
several binarisations, and read the behaviour table of the surviving unit.

The pipeline is agnostic: it is handed a list of numeric sequences and knows
nothing about them.  For each it (1) forms several binarisations, (2) tests every
bit column for survival against a time-shuffle, and (3) for the surviving units
builds the one-dimensional behaviour table -- the identified process columns and
the compression the behaviour rule achieves.

Two controls run through the identical pipeline: a deterministic rule-110 cellular
automaton column (must survive and compress) and a pseudo-random column (must not).
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from finance import load_yahoo_close  # noqa: E402  (loader only; no analysis imported)
from binarise import binarisations, sign_bit, top_magnitude_bit  # noqa: E402
from unit_survival import survival_report  # noqa: E402
from occurrence_arithmetic import behaviour_table  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data")
RESULTS_DIR = os.path.join(ROOT, "results")


def load_sequences() -> dict[str, list[float]]:
    seqs = {}
    for f in sorted(os.listdir(DATA_DIR)):
        if not f.endswith(".json"):
            continue
        px = load_yahoo_close(os.path.join(DATA_DIR, f))
        seqs[f[:-5]] = [px[d] for d in sorted(px)]
    return seqs


def rule110_column(n: int, seed: int = 1) -> list[int]:
    rng = random.Random(seed)
    width = 32
    row = [rng.randint(0, 1) for _ in range(width)]
    col = []
    for _ in range(n):
        col.append(row[width // 2])
        nxt = []
        for i in range(width):
            l, c, r = row[(i - 1) % width], row[i], row[(i + 1) % width]
            nxt.append(1 if (l, c, r) in {(1, 1, 0), (1, 0, 1), (0, 1, 1),
                                          (0, 1, 0), (0, 0, 1)} else 0)
        row = nxt
    return col


def run(quiet: bool = False) -> dict:
    seqs = load_sequences()
    names = list(seqs)
    length = min(len(s) for s in seqs.values())

    # ---- per-unit survival across binarisations, pooled over sequences -------
    unit_z = {}   # (binarisation, bit) -> list of autocorr z across sequences
    unit_surv = {}
    for name in names:
        bn = binarisations(seqs[name], nbits=3)
        for bkey, cols in bn.items():
            for b, col in enumerate(cols):
                rep = survival_report(col, n_shuffle=150, seed=7)
                key = (bkey, b)
                unit_z.setdefault(key, []).append(rep["z"]["autocorr1"])
                unit_surv.setdefault(key, []).append(rep["survives"])

    pooled_units = []
    for key, zs in sorted(unit_z.items()):
        pooled_units.append({
            "binarisation": key[0], "bit": key[1],
            "mean_autocorr_z": statistics.mean(zs),
            "n_survive": sum(unit_surv[key]), "n": len(zs),
        })

    # ---- behaviour table of the volatility unit vs the sign unit -------------
    vol_tables, sign_tables = [], []
    for name in names:
        vol_tables.append(behaviour_table(top_magnitude_bit(seqs[name])))
        sign_tables.append(behaviour_table(sign_bit(seqs[name])))

    def agg(tables, field_path):
        vals = []
        for t in tables:
            node = t
            for k in field_path:
                node = node[k]
            vals.append(node)
        return statistics.mean(vals)

    vol_summary = {
        "persistence_excess": agg(vol_tables, ["persistence_excess"]),
        "hurst": agg(vol_tables, ["columns", "memory_hurst"]),
        "gain_bits": agg(vol_tables, ["compression", "gain_bits"]),
        "mean_run_obs": agg(vol_tables, ["run_length", "mean_run_of_ones"]),
        "mean_run_geom_pred": agg(vol_tables, ["run_length", "geometric_mean_run_pred"]),
    }
    sign_summary = {
        "persistence_excess": agg(sign_tables, ["persistence_excess"]),
        "hurst": agg(sign_tables, ["columns", "memory_hurst"]),
        "gain_bits": agg(sign_tables, ["compression", "gain_bits"]),
    }

    # ---- compression of the volatility rule, honestly vs its shuffle ---------
    # The two-state rule pays a fixed model cost; the fair test is whether it
    # compresses the real unit more than the same rule compresses its shuffle.
    rng_c = random.Random(19)
    comp_real, comp_shuf = [], []
    for name in names:
        col = top_magnitude_bit(seqs[name])
        comp_real.append(behaviour_table(col)["compression"]["gain_bits"])
        b = col[:]
        draws = []
        for _ in range(30):
            rng_c.shuffle(b)
            draws.append(behaviour_table(b)["compression"]["gain_bits"])
        comp_shuf.append(statistics.mean(draws))
    vol_summary["gain_bits_vs_shuffle"] = statistics.mean(
        r - s for r, s in zip(comp_real, comp_shuf))
    vol_summary["n_compress_above_shuffle"] = sum(
        1 for r, s in zip(comp_real, comp_shuf) if r > s)

    # ---- controls through the identical pipeline -----------------------------
    ca = rule110_column(length)
    rng = random.Random(3)
    rnd = [rng.randint(0, 1) for _ in range(length)]
    ca_rep = survival_report(ca, n_shuffle=150, seed=7)
    rnd_rep = survival_report(rnd, n_shuffle=150, seed=7)
    ca_table = behaviour_table(ca)
    rnd_table = behaviour_table(rnd)

    out = {
        "experiment": "multibit_unit_survival",
        "n_sequences": len(names), "length": length,
        "pooled_units": pooled_units,
        "volatility_unit": vol_summary,
        "sign_unit": sign_summary,
        "controls": {
            "rule110": {"survives": ca_rep["survives"], "autocorr_z": ca_rep["z"]["autocorr1"],
                        "gain_bits": ca_table["compression"]["gain_bits"]},
            "random": {"survives": rnd_rep["survives"], "autocorr_z": rnd_rep["z"]["autocorr1"],
                       "gain_bits": rnd_table["compression"]["gain_bits"]},
        },
    }

    if not quiet:
        print(f"sequences: {len(names)}, aligned length: {length}\n")
        print("=== unit survival across binarisations (pooled over sequences) ===")
        print(f"{'binarisation':12s} {'bit':>3s} {'mean autocorr z':>16s} {'survive/n':>12s}")
        for u in pooled_units:
            print(f"{u['binarisation']:12s} {u['bit']:>3d} {u['mean_autocorr_z']:>16.2f} "
                  f"{u['n_survive']:>6d}/{u['n']:<5d}")
        print("\n=== behaviour table: volatility unit vs sign unit (means) ===")
        print(f"  volatility: persistence excess p11-p = {vol_summary['persistence_excess']:+.3f}, "
              f"Hurst = {vol_summary['hurst']:.3f}, compression = {vol_summary['gain_bits']:.1f} bits")
        print(f"              mean run of ones obs = {vol_summary['mean_run_obs']:.2f}, "
              f"geometric-law prediction = {vol_summary['mean_run_geom_pred']:.2f}")
        print(f"              compression vs shuffle = {vol_summary['gain_bits_vs_shuffle']:+.1f} bits "
              f"({vol_summary['n_compress_above_shuffle']}/{len(names)} above shuffle)")
        print(f"  sign      : persistence excess p11-p = {sign_summary['persistence_excess']:+.3f}, "
              f"Hurst = {sign_summary['hurst']:.3f}, compression = {sign_summary['gain_bits']:.1f} bits")
        print("\n=== controls (identical pipeline) ===")
        print(f"  rule-110 : survives={ca_rep['survives']}, autocorr z={ca_rep['z']['autocorr1']:+.1f}, "
              f"compression={ca_table['compression']['gain_bits']:.1f} bits")
        print(f"  random   : survives={rnd_rep['survives']}, autocorr z={rnd_rep['z']['autocorr1']:+.1f}, "
              f"compression={rnd_table['compression']['gain_bits']:.1f} bits")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp12_multibit.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp12_multibit.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
