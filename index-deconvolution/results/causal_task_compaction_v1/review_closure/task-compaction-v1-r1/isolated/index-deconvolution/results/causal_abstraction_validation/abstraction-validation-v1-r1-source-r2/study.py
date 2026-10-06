"""abstraction-validation-v1-r1 -- thin run-local orchestration of Tracks V, D and X.

Declarations follow the accepted corrected MODEL_AND_MAPS.md / DESIGN.md of
abstraction-design-v1-r1 and the binding addendum in
supervision/abstraction-design-v1-r1-closure/NEXT_CLAUDE.md, which takes precedence.

The fibre condition, induced maps, map comparison and supplied-map commutation are
owned by ``deconvolution`` (index-deconvolution/src).  Models come from their owners:
``ca_deconvolution.heterogeneous_eca_network`` (M1, M3), the ``causalbool.Network``
LUT gate (M2), ``bnet.parse_bnet`` (M4), ``reprogramming.knockout`` (knockouts) and
``causalbool.repertoire`` (one-step tables).  Nothing here re-implements them.
Import with PYTHONPATH=index-deconvolution/src (bare names).
"""
from __future__ import annotations

import hashlib
import math
import os

import bnet
import ca_deconvolution
import causalbool
import deconvolution
import reprogramming
from causalbool import Network
from deconvolution import canonical_partition, compare_induced, fibre_sizes, induced_map

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))
EGFR = "index-deconvolution/results/screen_identification/corpus/bio/egfr_signaling.bnet"
TAUS = (1, 2, 4, 8, 16)
WIDTHS = (2, 3, 4)
G_FUNCS = ("val", "par", "cnt", "or", "and")
F4_FUNCS = ("par", "or", "and")
MODEL_IDS = ("M1", "M2", "M3", "M4")
MODEL_N = {"M1": 8, "M2": 8, "M3": 8, "M4": 10}
OFFSETS = {"M1": 0, "M2": 675, "M3": 1350, "M4": 2025}
LOSSY_COARSE_FAMILIES = ("F1", "F2", "F4")   # F1 only for g != val
OWNER_MODULES = (causalbool, deconvolution, ca_deconvolution, reprogramming, bnet)


# --------------------------------------------------------------------------- models

def counter_network(n: int) -> Network:
    """M2: x -> x+1 mod 2**n as LUT nodes; f_i depends on bits 0..i."""
    C = [[1 if c <= i else 0 for c in range(n)] for i in range(n)]
    params = [{"table": [((y + 1) >> i) & 1 for y in range(2 ** (i + 1))]} for i in range(n)]
    return Network(n=n, C=C, gates=["LUT"] * n, params=params)


def build_network(model: str) -> Network:
    if model == "M1":
        return ca_deconvolution.heterogeneous_eca_network([150] * 8)
    if model == "M2":
        return counter_network(8)
    if model == "M3":
        return ca_deconvolution.heterogeneous_eca_network([30] * 8)
    if model == "M4":
        net, names = bnet.parse_bnet(os.path.join(ROOT, EGFR))
        if names != [f"v{i:03d}" for i in range(10)]:
            raise RuntimeError(f"unexpected M4 node order {names}")
        return net
    raise KeyError(model)


def step_table(net: Network) -> list[int]:
    """One-step map as integers (bit i = node i, LSB-first), from the owner repertoire."""
    return [sum(b << i for i, b in enumerate(row)) for row in causalbool.repertoire(net)]


def power(table: list[int], t: int) -> list[int]:
    out = list(range(len(table)))
    for _ in range(t):
        out = [table[y] for y in out]
    return out


# --------------------------------------------------------------------------- interventions

def track_d_q(n: int) -> list[dict]:
    """Declared Track-D Q in its declared order (size 5n+2)."""
    q = [{"op": "id", "j": None, "c": None}]
    q += [{"op": "reset", "j": j, "c": c} for j in range(n) for c in (0, 1)]
    q += [{"op": "flip", "j": j, "c": None} for j in range(n)]
    q += [{"op": "knockout", "j": j, "c": c} for j in range(n) for c in (0, 1)]
    q += [{"op": "tick", "j": None, "c": None}]
    return q


def q_name(q: dict) -> str:
    if q["op"] in ("id", "tick"):
        return q["op"]
    if q["op"] == "flip":
        return f"flip{q['j']}"
    if q["op"] == "block_reset":
        return f"breset{q['j']}_{q['c'][0]}{q['c'][1]}"
    return f"{q['op']}{q['j']}_{q['c']}"


class Model:
    """F tables of one model, cached per tau and intervention."""

    def __init__(self, model: str):
        self.id = model
        self.net = build_network(model)
        self.n = self.net.n
        self.N = 2 ** self.n
        self.F = step_table(self.net)
        self._pow: dict = {}
        self._ko: dict = {}

    def Ft(self, t: int) -> list[int]:
        if t not in self._pow:
            self._pow[t] = power(self.F, t)
        return self._pow[t]

    def ko_table(self, j: int, c: int) -> list[int]:
        if (j, c) not in self._ko:
            self._ko[(j, c)] = step_table(reprogramming.knockout(self.net, j, c))
        return self._ko[(j, c)]

    def q_table(self, q: dict, tau: int) -> list[int]:
        """F_q for macro step tau: boundary resets/flips F^tau o r_q; knockout (F_k)^tau;
        tick F^(tau+1); identity F^tau."""
        op, j, c = q["op"], q["j"], q["c"]
        Ft = self.Ft(tau)
        if op == "id":
            return Ft
        if op == "reset":
            m = ~(1 << j)
            return [Ft[(x & m) | (c << j)] for x in range(self.N)]
        if op == "block_reset":
            m = ~((1 << j) | (1 << (j + 1)))
            v = (c[0] << j) | (c[1] << (j + 1))
            return [Ft[(x & m) | v] for x in range(self.N)]
        if op == "flip":
            return [Ft[x ^ (1 << j)] for x in range(self.N)]
        if op == "knockout":
            return power(self.ko_table(j, c), tau)
        if op == "tick":
            return self.Ft(tau + 1)
        raise ValueError(op)


# --------------------------------------------------------------------------- candidate family A

def partition(w: int, o: int, n: int) -> list[tuple[int, int]]:
    """P(w, o, n) as (start, length) blocks; ragged head and tail kept."""
    blocks = [(0, o)] if o > 0 else []
    a = o
    while a < n:
        blocks.append((a, min(w, n - a)))
        a += w
    return blocks


def block_bits(x: int, a: int, ln: int) -> list[int]:
    return [(x >> (a + k)) & 1 for k in range(ln)]


def gfunc(g: str, bits: list[int]) -> int:
    if g == "val":
        return sum(b << k for k, b in enumerate(bits))
    if g == "par":
        return sum(bits) & 1
    if g == "cnt":
        return sum(bits)
    if g == "or":
        return int(any(bits))
    if g == "and":
        return int(all(bits))
    raise ValueError(g)


def candidates(n: int) -> list[dict]:
    """Family A in canonical id order (135 for n=8, 141 for n=10)."""
    out = []
    wo = [(w, o) for w in WIDTHS for o in range(w)]
    for w, o in wo:
        for g in G_FUNCS:
            out.append({"family": "F1", "w": w, "o": o, "g": g})
    for g in ("par", "cnt", "or", "and"):
        out.append({"family": "F2", "g": g})
    for w, o in wo:
        for b, (a, ln) in enumerate(partition(w, o, n)):
            out.append({"family": "F3", "w": w, "o": o, "block": b, "a": a, "len": ln})
    for w, o in wo:
        for g in F4_FUNCS:
            for o2 in (0, 1):
                out.append({"family": "F4", "w": w, "o": o, "g": g, "o2": o2})
    out.append({"family": "C", "g": "identity"})
    out.append({"family": "C", "g": "constant"})
    for k, c in enumerate(out):
        c["id"] = k
    return out


def alpha_value(cand: dict, x: int, n: int):
    """Natural macro value alpha(x) of a candidate (tuple or int)."""
    f = cand["family"]
    if f == "F1":
        return tuple(gfunc(cand["g"], block_bits(x, a, ln)) for a, ln in partition(cand["w"], cand["o"], n))
    if f == "F2":
        return gfunc(cand["g"], block_bits(x, 0, n))
    if f == "F3":
        return gfunc("val", block_bits(x, cand["a"], cand["len"]))
    if f == "F4":
        y = [gfunc(cand["g"], block_bits(x, a, ln)) for a, ln in partition(cand["w"], cand["o"], n)]
        return tuple(gfunc(cand["g"], y[a:a + ln]) for a, ln in partition(2, cand["o2"], len(y)))
    if cand["g"] == "identity":
        return x
    return 0


def coordinates(cand: dict, n: int) -> dict:
    """bit j -> (k, p, k2): level-1 coordinate, local position, coarse coordinate."""
    f = cand["family"]
    out = {}
    if f in ("F1", "F3", "F4"):
        blocks = partition(cand["w"], cand["o"], n)
        lvl2 = partition(2, cand.get("o2", 0), len(blocks)) if f == "F4" else None
        for j in range(n):
            k = next(b for b, (a, ln) in enumerate(blocks) if a <= j < a + ln)
            p = j - blocks[k][0]
            if f == "F3" and k != cand["block"]:
                out[j] = ("out", j, "out")
                continue
            k2 = next(i for i, (a, ln) in enumerate(lvl2) if a <= k < a + ln) if f == "F4" else k
            out[j] = (k, p, k2)
    elif f == "F2" or cand["g"] == "constant":
        out = {j: (0, j, 0) for j in range(n)}
    else:
        out = {j: (j, 0, j) for j in range(n)}
    return out


def has_coarse(cand: dict) -> list[str]:
    if cand["family"] == "F3":
        return ["H-OUT"]
    if cand["family"] in LOSSY_COARSE_FAMILIES and cand.get("g") != "val":
        return ["H-COARSE"]
    return []


# --------------------------------------------------------------------------- beta schemes

def beta_fine(q: dict, coord: dict):
    if q["op"] == "id":
        return ("id",)
    if q["op"] == "tick":
        return ("tick",)
    k, p, _ = coord[q["j"]]
    return (q["op"], k, p, q["c"])


def beta_coarse(q: dict, coord: dict):
    if q["op"] in ("id", "tick"):
        return (q["op"],)
    return (q["op"], coord[q["j"]][2], q["c"])


def beta_out(q: dict, coord: dict):
    if q["op"] in ("reset", "flip", "knockout") and coord[q["j"]][0] == "out":
        return ("id",)
    return beta_fine(q, coord)


SCHEMES = {"H-COARSE": beta_coarse, "H-OUT": beta_out}


def classes(Q: list[dict], coord: dict, beta) -> list[list[int]]:
    """Classes as lists of q indices in declared order; first member is the representative."""
    groups: dict = {}
    for i, q in enumerate(Q):
        groups.setdefault(beta(q, coord), []).append(i)
    return sorted(groups.values(), key=lambda m: m[0])


# --------------------------------------------------------------------------- decision tables

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"


def check_status(s) -> str:
    if s not in (PASS, FAIL, UNKNOWN):
        raise ValueError(f"INVALID evidence status {s!r}")
    return s


def primary_status(e2: str, e3: dict, id_index: int = 0) -> dict:
    """Addendum rule 1: total primary status from E2 and E3 (q index -> status)."""
    e2 = check_status(e2)
    stats = {q: check_status(s) for q, s in e3.items()}
    nonid = {q: s for q, s in stats.items() if q != id_index}
    any_fail = any(s == FAIL for s in stats.values())
    nonid_fail = any(s == FAIL for s in nonid.values())
    nonid_pass = any(s == PASS for s in nonid.values())
    any_unknown = e2 == UNKNOWN or any(s == UNKNOWN for s in stats.values())
    lower_bound = False
    if e2 == FAIL:
        st = "AUT-FAIL"
    elif e2 == UNKNOWN:
        st = "NOT-FULL-INCOMPLETE" if nonid_fail else "INCOMPLETE"
    elif nonid_pass and any_fail:
        st, lower_bound = "RESTRICTED", any_unknown
    elif nonid and all(s == FAIL for s in nonid.values()):
        st = "AUT-ONLY"
    elif any_fail and not nonid_pass and any_unknown:
        st = "NOT-FULL-INCOMPLETE"
    elif not any_fail and any_unknown:
        st = "INCOMPLETE"
    else:
        st = "FULL"
    return {"status": st, "q_prime_lower_bound": lower_bound}


def is_control(n_macro, N: int):
    """From complete E1 only; missing E1 gives None (never inferred)."""
    if n_macro is None:
        return None
    return n_macro in (1, N)


def display_label(status: str, control) -> str:
    """CONTROL only for complete, valid control rows; a theorem failure is CHECKER-INVALID."""
    if control is True:
        if status == "FULL":
            return "CONTROL"
        if status in ("AUT-FAIL", "RESTRICTED", "AUT-ONLY", "NOT-FULL-INCOMPLETE"):
            return "CHECKER-INVALID"
    return status


def run_status(harness_error: bool, invalid: bool, incomplete: bool) -> str:
    if harness_error:
        return "FAILED-RUN"
    if invalid:
        return "CHECKER-INVALID"
    if incomplete:
        return "INCOMPLETE"
    return "COMPLETE"


def evaluate_classes(cls: list[list[int]], maps: dict, present: set, sizes: dict, N: int) -> dict:
    """Coarse-hypothesis outcome. ``maps``: q -> induced map or None (record present);
    ``present``: q indices with a record. Representative = first member; never substituted.

    Record availability (does a record exist?) and member existence (does its own
    induced map exist?) are tracked independently of comparison evaluability.  A
    known structural failure outranks missing evidence; missing evidence, including
    an absent singleton representative, never yields COARSE-NO-HOLDOUT or COARSE-HOLDS.
    ``availability`` units: ``missing_records`` = distinct q indices with no record;
    ``missing_comparisons`` = representative-member comparisons not made for want of a
    record (equal to ``counts["MISSING"]``; a singleton contributes none).
    """
    rows = []
    intended = inspected = evaluable = macro_mis = micro_mis = 0
    counts = {"DISAGREE": 0, "REP-NOEXIST": 0, "MEMBER-NOEXIST": 0, "MISSING": 0}
    missing_records = set()
    for members in cls:
        rep = members[0]
        intended += (len(members) - 1) * N
        if rep not in present:
            rep_state = "MISSING"
            missing_records.add(rep)
        elif maps[rep] is None:
            rep_state = "REP-NOEXIST"
            counts["REP-NOEXIST"] += 1
        else:
            rep_state = "OK"
        out = []
        for m in members[1:]:
            own = None if m not in present else (PASS if maps[m] is not None else FAIL)
            if m not in present:
                missing_records.add(m)
                res = {"q": m, "outcome": "MISSING", "own_e3": own, "reason": "record absent",
                       "macro_disagreements": None, "micro_mismatches": None, "witness_macro": None}
                counts["MISSING"] += 1
            elif rep_state == "MISSING":
                if maps[m] is None:
                    res = {"q": m, "outcome": "MEMBER-NOEXIST", "own_e3": own,
                           "reason": "member has no induced map; representative record absent",
                           "macro_disagreements": None, "micro_mismatches": None, "witness_macro": None}
                    counts["MEMBER-NOEXIST"] += 1
                else:
                    res = {"q": m, "outcome": "MISSING", "own_e3": own, "reason": "representative record absent",
                           "macro_disagreements": None, "micro_mismatches": None, "witness_macro": None}
                counts["MISSING"] += 1
            else:
                inspected += N
                if rep_state == "REP-NOEXIST":
                    res = {"q": m, "own_e3": own, **compare_induced(None, maps[m], sizes)}
                elif maps[m] is None:
                    res = {"q": m, "outcome": "MEMBER-NOEXIST", "own_e3": own, "reason": "member has no induced map",
                           "macro_disagreements": None, "micro_mismatches": None, "witness_macro": None}
                    counts["MEMBER-NOEXIST"] += 1
                else:
                    evaluable += N
                    res = {"q": m, "own_e3": own, **compare_induced(maps[rep], maps[m], sizes)}
                    macro_mis += res["macro_disagreements"]
                    micro_mis += res["micro_mismatches"]
                    if res["outcome"] == "DISAGREE":
                        counts["DISAGREE"] += 1
            out.append(res)
        rows.append({"rep": rep, "rep_state": rep_state, "members": out})
    if counts["DISAGREE"]:
        label = "COARSE-DISAGREE"
    elif counts["REP-NOEXIST"] or counts["MEMBER-NOEXIST"]:
        label = "COARSE-STRUCT-FAIL"
    elif counts["MISSING"] or missing_records:
        label = "COARSE-INCOMPLETE"
    elif all(len(m) == 1 for m in cls):
        label = "COARSE-NO-HOLDOUT"
    else:
        label = "COARSE-HOLDS"
    return {"label": label, "classes": rows, "n_classes": len(cls), "counts": counts,
            "pairs_intended": intended, "pairs_inspected": inspected, "pairs_evaluable": evaluable,
            "macro_state_disagreements": macro_mis, "micro_state_pair_mismatches": micro_mis,
            "availability": {"missing_records": len(missing_records),
                             "missing_comparisons": counts["MISSING"]}}


# --------------------------------------------------------------------------- one D row

def row_id(model: str, cand_id: int, tau: int) -> int:
    return OFFSETS[model] + 5 * cand_id + TAUS.index(tau)


def audit_rows() -> list[int]:
    """Addendum rule 4: r_j = 10 j + (j mod 5), j = 0..272."""
    return [10 * j + (j % 5) for j in range(273)]


def evaluate_row(model: Model, cand: dict, tau: int) -> dict:
    n, N = model.n, model.N
    Q = track_d_q(n)
    canon = canonical_partition([alpha_value(cand, x, n) for x in range(N)])
    sizes = fibre_sizes(canon)
    n_macro = len(sizes)
    maps, e3, wit = {}, {}, {}
    for i, q in enumerate(Q):
        Fq = model.q_table(q, tau)
        G, w = induced_map(canon, [canon[y] for y in Fq])
        maps[i] = G
        e3[i] = PASS if G is not None else FAIL
        wit[i] = list(w) if w else None
    e2 = e3[0]                       # F_{q_id} = F^tau: E2 is the q_id fibre check
    st = primary_status(e2, e3)
    ctl = is_control(n_macro, N)
    coord = coordinates(cand, n)
    fine = classes(Q, coord, beta_fine)
    coarse = {}
    for scheme in has_coarse(cand):
        coarse[scheme] = evaluate_classes(classes(Q, coord, SCHEMES[scheme]), maps, set(range(len(Q))), sizes, N)
    return {
        "row": row_id(model.id, cand["id"], tau), "model": model.id, "cand_id": cand["id"],
        "candidate": {k: v for k, v in cand.items() if k != "id"}, "tau": tau,
        "E1": {"n_macro": n_macro, "log2_n_macro": round(math.log2(n_macro), 12),
               "fibre_min": min(sizes.values()), "fibre_max": max(sizes.values())},
        "is_control": ctl,
        "E2": {"status": e2, "witness": wit[0]},
        "E3": [[i, e3[i], wit[i]] for i in range(len(Q))],
        "Q_prime": [i for i in range(len(Q)) if e3[i] == PASS],
        "n_Q": len(Q), "status": st["status"], "q_prime_lower_bound": st["q_prime_lower_bound"],
        "display": display_label(st["status"], ctl),
        "beta_fine_all_singletons": all(len(c) == 1 for c in fine),
        "coarse": coarse,
        "coverage": {"declared_pairs": len(Q) * N, "checked_pairs": len(Q) * N},
        "partition_sha": hashlib.sha256(",".join(map(str, canon)).encode()).hexdigest()[:16],
    }


def verify_row_witnesses(model: Model, cand: dict, row: dict) -> int:
    """Independently re-check every stored fibre and macro witness from the tables."""
    n, N = model.n, model.N
    Q = track_d_q(n)
    canon = canonical_partition([alpha_value(cand, x, n) for x in range(N)])
    checked = 0
    for i, st, w in row["E3"]:
        if st == FAIL:
            Fq = model.q_table(Q[i], row["tau"])
            x, x2 = w
            assert x < x2 and canon[x] == canon[x2] and canon[Fq[x]] != canon[Fq[x2]], (row["row"], i)
            members: dict = {}
            for z in range(N):
                members.setdefault(canon[z], []).append(z)
            # lexicographic minimality: every fibre whose least member is below x is
            # image-constant; x is its fibre's least member; nothing in (x, x2) separates
            for fib in members.values():
                imgs = {canon[Fq[z]] for z in fib}
                if fib[0] < x:
                    assert len(imgs) == 1, (row["row"], i, fib[0])
            assert members[canon[x]][0] == x, (row["row"], i)
            assert all(canon[Fq[z]] == canon[Fq[x]] for z in members[canon[x]] if x < z < x2), (row["row"], i)
            checked += 1
    for sch in row["coarse"].values():
        for c in sch["classes"]:
            for m in c["members"]:
                if m["outcome"] == "DISAGREE":
                    y = m["witness_macro"]
                    Fr, Fm = model.q_table(Q[c["rep"]], row["tau"]), model.q_table(Q[m["q"]], row["tau"])
                    xs = [x for x in range(N) if canon[x] == y]
                    assert canon[Fr[xs[0]]] != canon[Fm[xs[0]]], (row["row"], m["q"])
                    assert all(canon[Fr[x]] == canon[Fm[x]] for x in range(N) if canon[x] < y), (row["row"], m["q"])
                    checked += 1
    return checked


def import_origins() -> dict:
    return {m.__name__: os.path.relpath(m.__file__, ROOT) for m in OWNER_MODULES}
