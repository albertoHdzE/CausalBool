"""Producer for protocol bdm_anatomy_v1 (index-deconvolution/protocols/bdm_anatomy_v1).

Every measure is imported from its owner: description_lengths (BDM, CTM, block code
parts, certified ECA code), ca_deconvolution / causalbool (ECA, two-rule rings, strict
deconvolution), hierarchy (HID-v1 archives and baseline codecs). This file defines
families, sampling, statistics and verdicts only.

    PYTHONPATH=index-deconvolution:src venv/bin/python \
        index-deconvolution/experiments/bdm_anatomy_run.py --freeze      # once, before any run
    ... bdm_anatomy_run.py --run-id a1 [--only H5] [--workers 24] --quiet
    ... bdm_anatomy_run.py --dev --quiet     # tiny sizes, development seeds, results/bdm_anatomy_v1_dev/

A confirmatory run refuses unless every frozen file hashes as in freeze.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve()
ID_ROOT = HERE.parents[1]                       # index-deconvolution/
REPO = ID_ROOT.parent
for _p in (str(REPO / "src"), str(ID_ROOT / "src"), str(ID_ROOT)):
    while _p in sys.path:
        sys.path.remove(_p)
for _p in (str(REPO / "src"), str(ID_ROOT / "src"), str(ID_ROOT)):
    sys.path.insert(0, _p)                      # ROOT first: a sibling repo ships "hierarchy"
sys.modules.pop("hierarchy", None)

import numpy as np  # noqa: E402

from description_lengths import (bdm_1d, bdm_1d_trace, bdm_2d, block_code_parts,  # noqa: E402
                                 certified_eca_code, ctm_1d)
from ca_deconvolution import deconvolve_ca, evolve_eca, heterogeneous_eca_network  # noqa: E402
from causalbool import Network, evolve_network, repertoire  # noqa: E402
from hierarchy.baselines import encode_baseline  # noqa: E402
from hierarchy.infer import FULL, infer  # noqa: E402

PROTOCOL_DIR = ID_ROOT / "protocols" / "bdm_anatomy_v1"
FREEZE = PROTOCOL_DIR / "freeze.json"
MASTER = 20261004
FROZEN_FILES = [
    PROTOCOL_DIR / "PROTOCOL.md", HERE,
    REPO / "src" / "description_lengths.py",
    ID_ROOT / "src" / "ca_deconvolution.py", ID_ROOT / "src" / "causalbool.py",
    ID_ROOT / "src" / "deconvolution.py",
] + sorted((ID_ROOT / "hierarchy").glob("*.py"))

QUIET = False


def log(*a):
    if not QUIET:
        print(*a, flush=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(*parts) -> int:
    key = "|".join(str(p) for p in (MASTER,) + parts)
    return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)


def rng(*parts) -> random.Random:
    return random.Random(seed(*parts))


# --- configuration -------------------------------------------------------------

CONFIRM = dict(
    T1=dict(lengths=[96, 384], blocks=[4, 8, 12], perms=1000, per_family=1),
    T2=dict(blocks=[4, 8, 12], ms=[1, 10, 100, 1000, 10000], seeds=5),
    H1=dict(lengths=[1200, 12000, 120000, 1200000], seeds=20, block=12),
    H2=dict(lengths=[64, 128, 256, 512, 1024, 2048, 4096], blocks=[2, 3, 4, 6, 8, 10, 12],
            seams=5, nulls=50, positions=128),
    H3=dict(rules=list(range(256)), seeds=5, width=64, rows=64, cells=100, boot=1000),
    H5=dict(lengths=[8, 12, 24, 48, 96, 384, 1536, 6144], blocks=[4, 8, 12], per_family=300,
            pairs=2000, flips=300, boot=1000),
    H6=dict(rules=list(range(256)), steps=[16, 32, 64, 128], seeds=5, width=64),
    H7=dict(per_arm=30, width=64, rows=64),
    DM=dict(m=[100, 1000, 10000], periods=list(range(2, 17)), blocks=list(range(2, 13)),
            length=2520, controls=10),
)
DEV = dict(
    T1=dict(lengths=[96], blocks=[4, 12], perms=20, per_family=1),
    T2=dict(blocks=[4, 8], ms=[1, 10, 100], seeds=2),
    H1=dict(lengths=[1200, 12000], seeds=2, block=12),
    H2=dict(lengths=[64, 256], blocks=[2, 8], seams=2, nulls=6, positions=16),
    H3=dict(rules=[30, 110, 4], seeds=1, width=64, rows=64, cells=12, boot=50),
    H5=dict(lengths=[12, 96], blocks=[4, 12], per_family=10, pairs=100, flips=20, boot=50),
    H6=dict(rules=[0, 30, 110], steps=[16, 32], seeds=1, width=64),
    H7=dict(per_arm=2, width=64, rows=64),
    DM=dict(m=[100], periods=[2, 9], blocks=[4, 9], length=2520, controls=2),
)
FAMILIES = ["eca_row", "eca_spacetime", "periodic", "biased_coin", "counter_or_shuffle",
            "bn_repertoire", "two_word"]
SIMPLE = [0, 4, 8, 32, 40, 128, 136, 160, 200, 204, 232, 255]
COMPLEX = [30, 45, 54, 60, 90, 105, 106, 110, 150]
BN_GATES = ["AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY"]


# --- families (protocol section 2) ---------------------------------------------

def bits_of(rows) -> str:
    return "".join("".join(map(str, r)) for r in rows)


def random_network(r: random.Random) -> Network:
    N = r.randint(3, 6)
    C = [[0] * N for _ in range(N)]
    gates, params = [], []
    for k in range(N):
        d = r.randint(1, min(3, N))
        for i in r.sample(range(N), d):
            C[k][i] = 1
        gates.append(r.choice(BN_GATES))
        params.append({})
    return Network(n=N, C=C, gates=gates, params=params)


def family(fid: str, n: int, r: random.Random) -> str:
    if fid == "eca_row":
        init = [r.randrange(2) for _ in range(n)]
        return bits_of([evolve_eca(r.randrange(256), init, 33)[-1]])
    if fid == "eca_spacetime":
        h = max(d for d in range(1, n + 1) if n % d == 0 and d * d <= n)
        w = n // h
        rule = r.randrange(256)
        return bits_of(evolve_eca(rule, [r.randrange(2) for _ in range(w)], h))
    if fid == "periodic":
        p = r.randint(1, min(24, n))
        unit = "".join(r.choice("01") for _ in range(p))
        return (unit * (n // p + 1))[:n]
    if fid == "biased_coin":
        q = r.uniform(0.02, 0.5)
        return "".join("1" if r.random() < q else "0" for _ in range(n))
    if fid == "counter_or_shuffle":
        k = r.randint(2, 8)
        start = r.randrange(2 ** k)
        words = [format((start + i) % 2 ** k, f"0{k}b") for i in range(n // k + 2)]
        if r.random() < 0.5:
            r.shuffle(words)
        return "".join(words)[:n]
    if fid == "bn_repertoire":
        out = ""
        while len(out) < n:
            out += bits_of(repertoire(random_network(r)))
        return out[:n]
    if fid == "two_word":
        b = r.randint(2, 12)
        m = n // b + 1
        if r.random() < 0.5:
            seq = [i % 2 for i in range(m)]
        else:
            seq = [r.randrange(2) for _ in range(m)]
        return "".join(("1" if x else "0") * b for x in seq)[:n]
    raise ValueError(fid)


def flip(s: str, i: int) -> str:
    return s[:i] + ("1" if s[i] == "0" else "0") + s[i + 1:]


# --- statistics ------------------------------------------------------------------

def spearman(a, b) -> float:
    from scipy.stats import spearmanr
    a, b = np.asarray(a, float), np.asarray(b, float)
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return 0.0
    return float(spearmanr(a, b).correlation)


def boot_ci(values_fn, n: int, B: int, tag) -> list[float]:
    g = np.random.default_rng(seed("boot", *tag))
    stats = [values_fn(g.integers(0, n, n)) for _ in range(B)]
    return [float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))]


def auc_right_gt_left(left, right) -> float:
    from scipy.stats import mannwhitneyu
    return float(mannwhitneyu(np.abs(right), np.abs(left)).statistic / (len(left) * len(right)))


def wilson(k: int, n: int) -> list[float]:
    if n == 0:
        raise ValueError("Wilson interval over zero cases")
    z, p = 1.959964, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [c - h, c + h]


def sgn(x: float) -> int:
    return 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)


# --- T1, T2, H1 ------------------------------------------------------------------

def run_T1(cfg):
    fails = checked = 0
    for fid in FAMILIES:
        for n in cfg["lengths"]:
            s = family(fid, n, rng("T1", fid, n))
            for b in cfg["blocks"]:
                assert n % b == 0
                base = bdm_1d(s, block=b)
                blocks = [s[i:i + b] for i in range(0, n, b)]
                r = rng("T1perm", fid, n, b)
                for _ in range(cfg["perms"]):
                    r.shuffle(blocks)
                    checked += 1
                    fails += abs(bdm_1d("".join(blocks), block=b) - base) >= 1e-9
    if checked == 0:
        raise RuntimeError("T1 checked zero cases")
    return {"checked": checked, "failures": int(fails), "supported": fails == 0}


def run_T2(cfg):
    rows, viol = [], 0
    for b in cfg["blocks"]:
        Cb = sum(ctm_1d(format(i, f"0{b}b")) for i in range(2 ** b))
        for m in cfg["ms"]:
            for k in range(cfg["seeds"]):
                r = rng("T2", b, m, k)
                s = "".join(r.choice("01") for _ in range(b * m))
                v, bound = bdm_1d(s, block=b), Cb + 2 ** b * math.log2(m)
                viol += v > bound + 1e-9
                rows.append({"block": b, "m": m, "seed": k, "bdm": v, "bound": bound})
    return {"rows": rows, "checked": len(rows), "violations": int(viol), "supported": viol == 0}


def _h1_job(args):
    N, k, b = args
    r = rng("H1", N, k)
    s = "".join(r.choice("01") for _ in range(N))
    p = block_code_parts(s, block=b)
    return {"N": N, "seed": k, **{x: p[x] for x in ("bdm", "dictionary_bits", "count_bits",
                                                     "arrangement_bits", "decodable_bits",
                                                     "m", "distinct")}}


def run_H1(cfg, pool):
    jobs = [(N, k, cfg["block"]) for N in cfg["lengths"] for k in range(cfg["seeds"])]
    rows = list(pool.map(_h1_job, jobs))
    mean = {N: float(np.mean([r["bdm"] / N for r in rows if r["N"] == N])) for N in cfg["lengths"]}
    dmean = {N: float(np.mean([r["decodable_bits"] / N for r in rows if r["N"] == N]))
             for N in cfg["lengths"]}
    Nmax = max(cfg["lengths"])
    a = max(mean.values()) / min(mean.values()) > 5
    b_ = mean[Nmax] < 0.2
    c = all(r["decodable_bits"] / r["N"] >= 0.95 for r in rows) and 1.0 <= dmean[Nmax] <= 1.2
    return {"rows": rows, "mean_bdm_per_bit": mean, "mean_decodable_per_bit": dmean,
            "criteria": {"a_ratio_gt_5": a, "b_bdm_per_bit_lt_0.2": b_,
                         "c_decodable_ge_0.95_and_in_1_1.2": c},
            "supported": bool(a and b_ and c)}


# --- H2 ----------------------------------------------------------------------------

def _h2_job(args):
    n, b, kind, k, P = args
    r = rng("H2", kind, n, b, k)
    half = n // 2
    if kind == "seam":
        p = r.choice([2, 3, 5])
        unit = "".join(r.choice("01") for _ in range(p))
        s = (unit * (half // p + 1))[:half] + "".join(r.choice("01") for _ in range(n - half))
    else:
        s = "".join(r.choice("01") for _ in range(n))
    kw = dict(block=b, remainder="recursive")
    base = bdm_1d(s, **kw)
    pr = rng("H2pos", kind, n, b, k)
    left = sorted(pr.sample(range(half), min(P, half)))
    right = sorted(pr.sample(range(half, n), min(P, n - half)))
    IL = [base - bdm_1d(flip(s, i), **kw) for i in left]
    IR = [base - bdm_1d(flip(s, i), **kw) for i in right]
    return {"n": n, "block": b, "kind": kind, "k": k, "auc": auc_right_gt_left(IL, IR)}


def run_H2(cfg, pool):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    jobs = [(n, b, kind, k, cfg["positions"]) for n in cfg["lengths"] for b in cfg["blocks"]
            for kind, K in (("seam", cfg["seams"]), ("null", cfg["nulls"])) for k in range(K)]
    out = list(pool.map(_h2_job, jobs, chunksize=4))
    cells = []
    for n in cfg["lengths"]:
        for b in cfg["blocks"]:
            seam = [o["auc"] for o in out if o["n"] == n and o["block"] == b and o["kind"] == "seam"]
            null = [o["auc"] for o in out if o["n"] == n and o["block"] == b and o["kind"] == "null"]
            lo, hi = np.percentile(null, [5, 95])
            med = float(np.median(seam))
            cells.append({"n": n, "block": b, "seam_aucs": seam, "seam_median": med,
                          "null_p5": float(lo), "null_p95": float(hi),
                          "null_aucs": null, "visible": bool(med < lo or med > hi),
                          "fill_ratio": (n / 2) / b / 2 ** b})
    y = np.array([c["visible"] for c in cells], int)
    res = {"cells": cells, "n_cells": len(cells), "n_visible": int(y.sum())}

    def loo_auc(X):
        if y.min() == y.max():
            return None
        pred = []
        for i in range(len(y)):
            m = np.arange(len(y)) != i
            if y[m].min() == y[m].max():
                pred.append(float(y[m][0]))
                continue
            lr = LogisticRegression(C=1000, solver="lbfgs").fit(X[m], y[m])
            pred.append(float(lr.predict_proba(X[i:i + 1])[0, 1]))
        return float(roc_auc_score(y, pred))
    X_fill = np.log2([[c["fill_ratio"]] for c in cells])
    res["loo_auc_fill"] = loo_auc(X_fill)
    res["loo_auc_block"] = loo_auc(np.log2([[c["block"]] for c in cells]))
    res["loo_auc_length"] = loo_auc(np.log2([[c["n"]] for c in cells]))
    if res["loo_auc_fill"] is None:
        res["verdict"] = "not_testable"
        res["supported"] = False
    else:
        res["supported"] = res["loo_auc_fill"] >= 0.9
        res["verdict"] = "supported" if res["supported"] else "not_supported"
    return res


# --- H3, H4 --------------------------------------------------------------------------

def _h3_job(args):
    rule, k, W, R, ncell = args
    r = rng("H3", rule, k)
    A = np.array(evolve_eca(rule, [r.randrange(2) for _ in range(W)], R))
    cells = [(r.randrange(R), r.randrange(W)) for _ in range(ncell)]
    D = np.zeros((ncell, 4))
    for dc in range(4):
        S = np.roll(A, dc, axis=1)
        base = bdm_2d(S)
        for q, (t, c) in enumerate(cells):
            T = S.copy()
            T[t, (c + dc) % W] ^= 1
            D[q, dc] = base - bdm_2d(T)
    flat = bits_of(A.tolist())
    proxy = 8 * len(encode_baseline(flat, "lzma")) / len(flat)
    return {"rule": rule, "seed": k, "delta": D.round(12).tolist(), "lzma_per_bit": proxy}


def run_H3_H4(cfg, pool):
    jobs = [(rule, k, cfg["width"], cfg["rows"], cfg["cells"]) for rule in cfg["rules"]
            for k in range(cfg["seeds"])]
    out = list(pool.map(_h3_job, jobs, chunksize=2))
    per_rule = {}
    excluded = 0
    for o in out:
        D = np.array(o["delta"])
        S = np.vectorize(sgn)(D)
        instab = float(np.mean([len(set(row)) > 1 for row in S]))
        groups = np.array_split(np.arange(len(D)), 4)
        gagree = float(np.mean([len({sgn(D[g, p].mean()) for p in range(4)}) == 1 for g in groups]))
        rhos = []
        for p in (1, 2, 3):
            if np.ptp(D[:, 0]) == 0 or np.ptp(D[:, p]) == 0:
                continue
            rhos.append(spearman(D[:, 0], D[:, p]))
        if not rhos:
            excluded += 1
        pr = per_rule.setdefault(o["rule"], {"instab": [], "group": [], "rank": [], "proxy": []})
        pr["instab"].append(instab)
        pr["group"].append(gagree)
        pr["proxy"].append(o["lzma_per_bit"])
        if rhos:
            pr["rank"].append(float(np.median(rhos)))
    rules = sorted(per_rule)
    inst = np.array([np.mean(per_rule[r]["instab"]) for r in rules])
    grp = np.array([np.mean(per_rule[r]["group"]) for r in rules])
    rank = np.array([np.mean(per_rule[r]["rank"]) if per_rule[r]["rank"] else np.nan for r in rules])
    prox = np.array([np.mean(per_rule[r]["proxy"]) for r in rules])
    ci = boot_ci(lambda idx: float(inst[idx].mean()), len(inst), cfg["boot"], ("H3",))
    rho_p = spearman(inst, prox)
    rho_ci = boot_ci(lambda idx: spearman(inst[idx], prox[idx]), len(inst), cfg["boot"], ("H3rho",))
    h4_rank = float(np.nanmedian(rank))
    return {
        "raw": out,
        "per_rule": [{"rule": r, "sign_instability": float(i), "group_agreement": float(g),
                      "rank_agreement": (None if np.isnan(k) else float(k)), "lzma_per_bit": float(p)}
                     for r, i, g, k, p in zip(rules, inst, grp, rank, prox)],
        "H3": {"mean_instability": float(inst.mean()), "ci95": ci,
               "spearman_instability_vs_lzma": rho_p, "spearman_ci95": rho_ci,
               "n_rules": len(rules), "supported": ci[0] > 0.10},
        "H4": {"median_group_agreement": float(np.median(grp)),
               "median_rank_agreement": h4_rank, "diagrams_constant_delta": excluded,
               "n_rules_with_rank": int(np.sum(~np.isnan(rank))),
               "supported": bool(np.median(grp) >= 0.95 and h4_rank < 0.5)},
    }


# --- H5 ----------------------------------------------------------------------------

MEAN_CTM = None


def _mean_ctm():
    global MEAN_CTM
    if MEAN_CTM is None:
        MEAN_CTM = {L: float(np.mean([ctm_1d(format(i, f"0{L}b")) for i in range(2 ** L)]))
                    for L in range(1, 13)}
    return MEAN_CTM


def measures(s: str, blocks) -> dict:
    mc = _mean_ctm()
    out = {"E3a_zlib": 8 * len(encode_baseline(s, "zlib")),
           "E3b_lzma": 8 * len(encode_baseline(s, "lzma")),
           "E4_hid": infer(s).archive_bits}
    for b in blocks:
        if len(s) < b:
            continue
        p = block_code_parts(s, block=b, remainder="recursive")
        m = p["m"]
        out[b] = {"bdm": p["bdm"],
                  "E0_block_entropy": sum(v * math.log2(m / v) for v in p["counts"].values()),
                  "E1_flat": sum(len(w) for w in p["counts"]) + p["count_bits"],
                  "E2_mean_ctm": sum(mc[len(w)] for w in p["counts"]) + p["count_bits"]}
    return out


def _h5_job(args):
    fid, n, j, blocks, flip_at = args
    s = family(fid, n, rng("H5", fid, n, j))
    res = {"family": fid, "n": n, "j": j, "orig": measures(s, blocks)}
    if flip_at is not None:
        res["flip_at"] = flip_at
        res["flipped"] = measures(flip(s, flip_at), blocks)
    return res


EMULATORS = ["E0_block_entropy", "E1_flat", "E2_mean_ctm", "E3a_zlib", "E3b_lzma", "E4_hid"]


def _emu(rec, b, e):
    return rec[b][e] if e.startswith(("E0", "E1", "E2")) else rec[e]


def run_H5(cfg, pool):
    jobs = []
    for n in cfg["lengths"]:
        total = len(FAMILIES) * cfg["per_family"]
        chosen = set(rng("H5flips", n).sample(range(total), min(cfg["flips"], total)))
        idx = 0
        for fid in FAMILIES:
            for j in range(cfg["per_family"]):
                fa = rng("H5flippos", n, fid, j).randrange(n) if idx in chosen else None
                jobs.append((fid, n, j, cfg["blocks"], fa))
                idx += 1
    log(f"H5: {len(jobs)} strings")
    out = list(pool.map(_h5_job, jobs, chunksize=8))
    regimes = []
    for n in cfg["lengths"]:
        recs = [o for o in out if o["n"] == n]
        for b in cfg["blocks"]:
            if n < b:
                continue
            bdm = np.array([o["orig"][b]["bdm"] for o in recs])
            pr = rng("H5pairs", n, b)
            pairs = [tuple(pr.sample(range(len(recs)), 2)) for _ in range(cfg["pairs"])]
            flips_ = [o for o in recs if "flipped" in o]
            row = {"n": n, "block": b, "strings": len(recs), "emulators": {}}
            for e in EMULATORS:
                v = np.array([_emu(o["orig"], b, e) for o in recs], float)
                rho = spearman(v, bdm)
                ci = ([0.0, 0.0] if np.ptp(v) == 0 else
                      boot_ci(lambda ix: spearman(v[ix], bdm[ix]), len(v), cfg["boot"], ("H5", n, b, e)))
                agree = tied = 0
                for i, k in pairs:
                    db = bdm[i] - bdm[k]
                    if abs(db) < 1e-9:
                        tied += 1
                        continue
                    agree += sgn(v[i] - v[k]) == sgn(db)
                d1 = agree / (len(pairs) - tied) if len(pairs) > tied else None
                d2n = sum(sgn(_emu(o["flipped"], b, e) - _emu(o["orig"], b, e))
                          == sgn(o["flipped"][b]["bdm"] - o["orig"][b]["bdm"]) for o in flips_)
                d2 = d2n / len(flips_) if flips_ else None
                dec = None if d1 is None or d2 is None else min(d1, d2)
                fam_rho = {fid: spearman([_emu(o["orig"], b, e) for o in recs if o["family"] == fid],
                                         [o["orig"][b]["bdm"] for o in recs if o["family"] == fid])
                           for fid in FAMILIES}
                row["emulators"][e] = {
                    "rho": rho, "rho_ci95": ci, "constant": bool(np.ptp(v) == 0),
                    "D1": d1, "D1_pairs_used": len(pairs) - tied, "D1_pairs_tied_bdm": tied,
                    "D2": d2, "D2_flips": len(flips_), "decision": dec,
                    "emulates": bool(ci[0] >= 0.95 and dec is not None and dec >= 0.95),
                    "rho_by_family": fam_rho}
            regimes.append(row)
    return {"regimes": regimes, "raw": out}


# --- H6 ----------------------------------------------------------------------------

def _h6_job(args):
    rule, steps, k, W = args
    r = rng("H6", rule, steps, k)
    init = [r.randrange(2) for _ in range(W)]
    A = evolve_eca(rule, init, steps)
    flat = bits_of(A)
    cert = certified_eca_code(rule, init, steps)
    return {"rule": rule, "steps": steps, "seed": k, "bdm": bdm_2d(np.array(A)),
            "certified": cert["certified_bits"], "rule_bits": cert["rule_bits"],
            "hid": infer(flat).archive_bits, "literal": len(flat)}


def run_H6(cfg, pool):
    jobs = [(rule, s, k, cfg["width"]) for rule in cfg["rules"] for s in cfg["steps"]
            for k in range(cfg["seeds"])]
    rows = list(pool.map(_h6_job, jobs, chunksize=4))
    by_steps = {}
    for s in cfg["steps"]:
        rr = [x for x in rows if x["steps"] == s]
        by_steps[s] = {"diagrams": len(rr),
                       "share_bdm_gt_certified": float(np.mean([x["bdm"] > x["certified"] for x in rr])),
                       "median_ratio_bdm_over_certified": float(np.median([x["bdm"] / x["certified"] for x in rr])),
                       "share_hid_lt_literal": float(np.mean([x["hid"] < x["literal"] for x in rr]))}
    slopes = []
    for rule in cfg["rules"]:
        xs = [x["steps"] for x in rows if x["rule"] == rule]
        ys = [x["bdm"] - x["certified"] for x in rows if x["rule"] == rule]
        slopes.append({"rule": rule, "slope": float(np.polyfit(xs, ys, 1)[0])})
    return {"rows": rows, "by_steps": by_steps, "slopes": slopes,
            "share_rules_positive_slope": float(np.mean([s["slope"] > 0 for s in slopes]))}


# --- H7 ----------------------------------------------------------------------------

def split_by_labels(labels) -> int:
    from collections import Counter
    W = len(labels)
    score = {}
    for k in range(1, W):
        L, R = labels[:k], labels[k:]
        score[k] = Counter(L).most_common(1)[0][1] + Counter(R).most_common(1)[0][1]
    best = max(score.values())
    tied = sorted(k for k, v in score.items() if v == best)
    return tied[(len(tied) - 1) // 2]


def split_cusum(profile) -> int:
    x = np.asarray(profile, float)
    W = len(x)
    score = {k: math.sqrt(k * (W - k) / W) * abs(x[:k].mean() - x[k:].mean()) for k in range(1, W)}
    best = max(score.values())
    tied = sorted(k for k, v in score.items() if abs(v - best) < 1e-12)
    return tied[(len(tied) - 1) // 2]


def _h7_job(args):
    arm, i, W, R = args
    r = rng("H7", arm, i)
    if arm == "A3":
        A, B = r.sample(COMPLEX, 2)
    else:
        A, B = r.choice(SIMPLE), r.choice(COMPLEX)
        if r.random() < 0.5:
            A, B = B, A
    boundary = 30 if arm == "A2" else 32
    rules = [A] * boundary + [B] * (W - boundary)
    D = evolve_network(heterogeneous_eca_network(rules), [r.randrange(2) for _ in range(W)], R)
    if arm == "A1":
        cells = r.sample(range(W * R), round(0.01 * W * R))
        D = [row[:] for row in D]
        for c in cells:
            D[c // W][c % W] ^= 1
    _, reports = deconvolve_ca([D], max_radius=1)
    labels = []
    for c, rep in enumerate(reports):
        offs = tuple(((s - c + W // 2) % W) - W // 2 for s in rep.support)
        labels.append((offs, tuple(rep.reduced_truth_table)))
    k_ours = split_by_labels(labels)
    M = np.array(D)
    base = bdm_2d(M)
    per_col = 1 if arm == "A4" else 16
    prof = []
    for c in range(W):
        rows_ = r.sample(range(R), per_col)
        vals = []
        for t in rows_:
            T = M.copy()
            T[t, c] ^= 1
            vals.append(abs(base - bdm_2d(T)))
        prof.append(float(np.mean(vals)))
    k_bdm = split_cusum(prof)
    return {"arm": arm, "i": i, "A": A, "B": B, "boundary": boundary, "k_ours": k_ours,
            "k_bdm": k_bdm, "ours_ok": abs(k_ours - boundary) <= 2,
            "bdm_ok": abs(k_bdm - boundary) <= 2, "profile": prof}


def run_H7(cfg, pool):
    arms = ["A0", "A1", "A2", "A3", "A4"]
    jobs = [(a, i, cfg["width"], cfg["rows"]) for a in arms for i in range(cfg["per_arm"])]
    rows = list(pool.map(_h7_job, jobs))
    summary = {}
    for a in arms:
        rr = [x for x in rows if x["arm"] == a]
        ko, kb = sum(x["ours_ok"] for x in rr), sum(x["bdm_ok"] for x in rr)
        both = sum(x["ours_ok"] == x["bdm_ok"] for x in rr)
        summary[a] = {"n": len(rr), "ours": ko / len(rr), "ours_ci95": wilson(ko, len(rr)),
                      "bdm": kb / len(rr), "bdm_ci95": wilson(kb, len(rr)),
                      "methods_agree": both / len(rr)}
    valid = summary["A0"]["ours"] >= 0.9 and summary["A0"]["bdm"] >= 0.9
    return {"rows": rows, "summary": summary, "baseline_valid": bool(valid)}


# --- demonstrations ----------------------------------------------------------------

def run_DM(cfg):
    out = {}
    dm1 = []
    for m in cfg["m"]:
        alt = "".join(("1" if i % 2 else "0") * 12 for i in range(m))
        seq = [0] * (m // 2) + [1] * (m - m // 2)
        rng("DM1", m).shuffle(seq)
        rnd = "".join(("1" if x else "0") * 12 for x in seq)
        pa, pr = block_code_parts(alt, block=12), block_code_parts(rnd, block=12)
        dm1.append({"m": m, "bdm_alternating": pa["bdm"], "bdm_random": pr["bdm"],
                    "arrangement_random": pr["arrangement_bits"],
                    "decodable_alternating": pa["decodable_bits"], "decodable_random": pr["decodable_bits"],
                    "literal": 12 * m})
    out["DM1"] = dm1
    words = [format(i, "012b") for i in range(4096)]
    sh = words[:]
    rng("DM2").shuffle(sh)
    pc, ps = block_code_parts("".join(words), block=12), block_code_parts("".join(sh), block=12)
    out["DM2"] = {"bdm_counter": pc["bdm"], "bdm_shuffle": ps["bdm"],
                  "decodable_counter": pc["decodable_bits"], "decodable_shuffle": ps["decodable_bits"],
                  "literal": 12 * 4096, "log2_4096_factorial": math.lgamma(4097) / math.log(2)}
    L = cfg["length"]
    grid = []
    for p in cfg["periods"]:
        ru = rng("DM3unit", p)                       # one generator per string (Amendment 2)
        unit = "".join(ru.choice("01") for _ in range(p))
        s = (unit * (L // p + 1))[:L]
        for b in cfg["blocks"]:
            ctrl = [bdm_1d((lambda rc: "".join(rc.choice("01") for _ in range(L)))(rng("DM3ctl", b, j)),
                           block=b, remainder="recursive") for j in range(cfg["controls"])]
            v = bdm_1d(s, block=b, remainder="recursive")
            grid.append({"period": p, "block": b, "bdm": v, "control_mean": float(np.mean(ctrl)),
                         "ratio": v / float(np.mean(ctrl))})
    out["DM3"] = grid
    x = "1111100000"
    out["DM4"] = {str(st): bdm_1d_trace(x, block=5, shift=st, remainder="drop" if st == 2 else "raise")
                  for st in (5, 2, 1)}
    return out


# --- driver --------------------------------------------------------------------------

def freeze():
    if FREEZE.exists():
        raise SystemExit(f"{FREEZE} exists; the protocol is already frozen")
    data = {"frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "files": {str(p.relative_to(REPO)): sha(p) for p in FROZEN_FILES},
            "hid_config_sha256": FULL.sha256()}
    FREEZE.write_text(json.dumps(data, indent=1) + "\n")
    print(f"frozen {len(data['files'])} files -> {FREEZE}")


def check_freeze() -> dict:
    if not FREEZE.exists():
        raise SystemExit("no freeze.json: run --freeze first")
    data = json.loads(FREEZE.read_text())
    bad = [f for f, h in data["files"].items() if sha(REPO / f) != h]
    now = {str(p.relative_to(REPO)) for p in FROZEN_FILES}
    if bad or now != set(data["files"]) or FULL.sha256() != data["hid_config_sha256"]:
        raise SystemExit(f"FREEZE MISMATCH, refusing to run: {bad or 'file set or HID config changed'}")
    return data


def write(d: Path, name: str, obj):
    (d / f"{name}.json").write_text(json.dumps(obj, default=str) + "\n")


def main():
    global QUIET
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--run-id")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 4))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    QUIET = a.quiet
    if a.freeze:
        return freeze()
    if a.dev:
        cfg, fz = DEV, {"dev": True}
        global MASTER
        MASTER = 1                       # development seeds never overlap the confirmatory ones
        d = ID_ROOT / "results" / "bdm_anatomy_v1_dev"
    else:
        if not a.run_id:
            raise SystemExit("--run-id is required for a confirmatory run")
        fz = check_freeze()
        cfg = CONFIRM
        d = ID_ROOT / "results" / "bdm_anatomy_v1" / a.run_id
    d.mkdir(parents=True, exist_ok=True)
    steps = a.only or ["DM", "T1", "T2", "H1", "H2", "H3", "H5", "H6", "H7"]
    run = {"run_id": a.run_id, "freeze": fz, "master_seed": MASTER, "workers": a.workers,
           "python": sys.version, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "timings": {}}
    with ProcessPoolExecutor(a.workers) as pool:
        for st in steps:
            t = time.time()
            if st == "DM":
                write(d, "DM", run_DM(cfg["DM"]))
            elif st == "T1":
                write(d, "T1", run_T1(cfg["T1"]))
            elif st == "T2":
                write(d, "T2", run_T2(cfg["T2"]))
            elif st == "H1":
                write(d, "H1", run_H1(cfg["H1"], pool))
            elif st == "H2":
                write(d, "H2", run_H2(cfg["H2"], pool))
            elif st == "H3":
                write(d, "H3_H4", run_H3_H4(cfg["H3"], pool))
            elif st == "H5":
                write(d, "H5", run_H5(cfg["H5"], pool))
            elif st == "H6":
                write(d, "H6", run_H6(cfg["H6"], pool))
            elif st == "H7":
                write(d, "H7", run_H7(cfg["H7"], pool))
            else:
                raise SystemExit(f"unknown step {st}")
            run["timings"][st] = round(time.time() - t, 1)
            print(f"{st}: done in {run['timings'][st]} s", flush=True)
    prev = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    prev.setdefault("timings", {}).update(run["timings"])
    run["timings"] = prev["timings"]
    write(d, "run", run)
    files = sorted(p for p in d.glob("*.json") if p.name != "run.json") + [d / "run.json"]
    (d / "MANIFEST.sha256").write_text("".join(f"{sha(p)}  {p.name}\n" for p in files))
    print(f"results -> {d}")


if __name__ == "__main__":
    main()
