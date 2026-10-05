"""screen_s0_corpus.py -- identification screen, step 1: freeze the corpus.

PROTOCOL_screen_identification.md sec.2.  Writes
results/screen_identification/corpus/{synthetic,bio}/*.{bnet,json} and
corpus/manifest.json with SHA-256 hashes, seeds and the per-tool load checks.

Synthetic: random_network(n, seed, max_arity=3, gate_pool="core") at
n in {10,15,20,30,50,100,200}, 5 seeds per n.  gate_pool "core" (the canonical
families minus CANALISING) is used because exact_query_representation, our S3a
arm, does not accept CANALISING; the choice is made here, once, for the whole
corpus so that every setting sees the same networks.

Biological: every file in data/bio/processed/ whose rules are Boolean (not
multivalued, not threshold) is converted to a Network through the owners
(parse_bnet for the infix syntax, LogicParser for the functional one), frozen as
.bnet by network_to_bnet, and admitted only if the forward map of EVERY tool
(ours, BoolNet, PyBoolNet, dd, Z3) agrees with causalbool.step on 64 pinned
random states, and parse_bnet(bnet) equals the network by canonical diagram
identity.  Up to 20 are selected by a fixed rule (below).

Usage: venv/bin/python index-deconvolution/experiments/screen_s0_corpus.py [--quiet]
"""

from __future__ import annotations

import ast
import glob
import json
import random
import re
import sys
import tempfile
import time
from pathlib import Path

from screen_common import (CORPUS, ROOT, canonical_names, log, network_to_json,
                           r_lib_prelude, run_r, sha256, tool_versions, write_json)

from causalbool import Network, step
from bnet import parse_bnet, network_to_bnet
from deconvolution import symbolic_manager, network_roots, verify_forward_symbolic
from network_generator import random_network

sys.path.insert(0, str(ROOT / "src" / "integration"))
from LogicParser import LogicParser  # noqa: E402

SIZES = [10, 15, 20, 30, 50, 100, 200]
SEEDS_PER_N = 5
MAX_ARITY = 3
GATE_POOL = "core"
N_CHECK_STATES = 64
STATE_SEED = 20260929
MAX_BIO = 20
MAX_BIO_INDEGREE = 12          # minimal_dnf (the owner) covers m <= 12
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NON_BOOLEAN = re.compile(r"theta|\b(EQ|LEQ|GEQ|LT|GT|NEQ)\(|[<>=]")


def synthetic_seed(n: int, s: int) -> int:
    return 1000 * n + s


# ---------------------------------------------------------------------------
# Biological models: data/bio/processed JSON -> Network (via the owners)
# ---------------------------------------------------------------------------

def _lit(v):
    return ast.literal_eval(v) if isinstance(v, str) else v


def network_from_processed(d: dict) -> tuple[Network, list[str], dict]:
    """Return (network, original node names, notes); raise ValueError to reject."""
    nodes = _lit(d.get("nodes"))
    logic = _lit(d.get("logic")) or {}
    if not nodes or not logic:
        raise ValueError("no Boolean logic in file")
    nodes = list(nodes)
    bad = [x for x in nodes if not _IDENT.fullmatch(str(x))]
    if bad:
        raise ValueError(f"node names not identifiers: {bad[:3]}")
    rules = {}
    no_rule = []
    for x in nodes:
        r = logic.get(x)
        if r is None or str(r).strip() in ("", "INPUT"):
            rules[x] = x                      # input node: holds its value
            if r is None:
                no_rule.append(x)
        else:
            rules[x] = str(r).strip()
    for x, r in rules.items():
        if _NON_BOOLEAN.search(r):
            raise ValueError(f"non-Boolean rule for {x}: {r[:60]}")
        # GINsim level notation: "X:1" is "X at level 1".  With no level >= 2
        # anywhere in the model every node is Boolean and X:1 is X; any
        # "X:2" or higher makes the model multivalued, which is rejected.
        if re.search(r":\s*([2-9]|\d\d)", r):
            raise ValueError(f"multivalued level in rule for {x}: {r[:60]}")
        r = re.sub(r"\b([A-Za-z_][A-Za-z0-9_]*):1\b", r"\1", r)
        r = {"TRUE": "1", "FALSE": "0", "True": "1", "False": "0"}.get(r, r)
        rules[x] = r
    lp = LogicParser()
    functional = any(lp._uses_functional_syntax(r) for r in rules.values())
    if not functional:
        with tempfile.NamedTemporaryFile("w", suffix=".bnet", delete=False) as f:
            for x in nodes:
                f.write(f"{x}, {rules[x]}\n")
        net, names = parse_bnet(f.name)
        if names != nodes:
            raise ValueError("parse_bnet changed node order")
    else:
        index = {x: i for i, x in enumerate(nodes)}
        n = len(nodes)
        C = [[0] * n for _ in range(n)]
        gates, params = ["FALSE"] * n, [dict() for _ in range(n)]
        for k, x in enumerate(nodes):
            ins = sorted({index[t] for t in _IDENT.findall(rules[x]) if t in index})
            m = len(ins)
            if m > MAX_BIO_INDEGREE:
                raise ValueError(f"in-degree {m} > {MAX_BIO_INDEGREE}")
            tab = lp.truth_table(rules[x], [nodes[i] for i in ins])  # MSB-first rows
            lsb = [0] * (2 ** m)
            for idx in range(2 ** m):
                y = sum(int(tab[idx, j]) << j for j in range(m))
                lsb[y] = int(tab[idx, m])
            for i in ins:
                C[k][i] = 1
            if m == 0:
                gates[k] = "TRUE" if lsb[0] else "FALSE"
            else:
                gates[k], params[k] = "LUT", {"table": lsb}
        net = Network(n=n, C=C, gates=gates, params=params)
    indeg = max(sum(r) for r in net.C)
    if indeg > MAX_BIO_INDEGREE:
        raise ValueError(f"in-degree {indeg} > {MAX_BIO_INDEGREE}")
    return net, nodes, {"syntax": "functional" if functional else "infix",
                        "nodes_without_rule": no_rule, "max_indegree": indeg}


# ---------------------------------------------------------------------------
# Forward-map load checks, one per tool
# ---------------------------------------------------------------------------

def check_states(n: int, key: str) -> list[list[int]]:
    rng = random.Random(f"{STATE_SEED}:{key}")
    return [[rng.randint(0, 1) for _ in range(n)] for _ in range(N_CHECK_STATES)]


def pyboolnet_successors(bnet_text: str, names, states):
    from pyboolnet.file_exchange import bnet2primes
    from pyboolnet.state_transition_graphs import successor_synchronous
    body = "\n".join(bnet_text.splitlines()[1:])        # PyBoolNet takes no header
    primes = bnet2primes(body)
    out = []
    for s in states:
        nxt = successor_synchronous(primes, {nm: s[i] for i, nm in enumerate(names)})
        out.append([int(nxt[nm]) for nm in names])
    return out


def _rules(bnet_text: str):
    return [ln.split(",", 1)[1].strip() for ln in bnet_text.splitlines()[1:]]


def dd_successors(bnet_text: str, names, states):
    from dd.autoref import BDD
    m = BDD()
    m.declare(*names)
    roots = [m.add_expr(r.replace("0", "FALSE") if r == "0" else
                        ("TRUE" if r == "1" else r)) for r in _rules(bnet_text)]
    return [[int(m.let({nm: bool(s[i]) for i, nm in enumerate(names)}, u) == m.true)
             for u in roots] for s in states]


def z3_successors(bnet_text: str, names, states):
    import z3
    env = {nm: z3.Bool(nm) for nm in names}
    exprs = [z3.BoolVal(r == "1") if r in ("0", "1")
             else eval(r.replace("!", "~"), {"__builtins__": {}}, env)  # noqa: S307
             for r in _rules(bnet_text)]
    out = []
    for s in states:
        sub = [(env[nm], z3.BoolVal(bool(s[i]))) for i, nm in enumerate(names)]
        out.append([int(z3.is_true(z3.simplify(z3.substitute(e, *sub)))) for e in exprs])
    return out


def boolnet_successors(jobs: list[tuple[str, str, str]]) -> dict:
    """jobs: (bnet_path, states_csv, out_csv).  One R process for all."""
    listing = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False)
    for j in jobs:
        listing.write("\t".join(j) + "\n")
    listing.close()
    code = r_lib_prelude() + f'''
jobs <- read.table("{listing.name}", sep="\\t", stringsAsFactors=FALSE)
for (r in seq_len(nrow(jobs))) {{
  res <- tryCatch({{
    net <- loadNetwork(jobs[r,1])
    S <- as.matrix(read.csv(jobs[r,2], header=FALSE))
    O <- t(apply(S, 1, function(s) stateTransition(net, as.integer(s), type="synchronous")))
    write.table(O, jobs[r,3], sep=",", row.names=FALSE, col.names=FALSE)
    "ok"
  }}, error=function(e) conditionMessage(e))
  cat(jobs[r,1], "\\t", res, "\\n", sep="")
}}'''
    proc = run_r(code, timeout=3600)
    status = {}
    for ln in proc.stdout.splitlines():
        if "\t" in ln:
            p, res = ln.split("\t", 1)
            status[p] = res.strip()
    if not status:
        raise RuntimeError(f"BoolNet batch failed: {proc.stderr[-2000:]}")
    return status


def forward_checks(net: Network, names: list[str], bnet_path: Path, key: str) -> dict:
    text = bnet_path.read_text()
    states = check_states(net.n, key)
    truth = [step(net, s) for s in states]
    res = {}
    # ours: the file round-trips to the same function, over all 2**n states
    parsed, pnames = parse_bnet(str(bnet_path))
    mgr = symbolic_manager(net.n)
    vf = verify_forward_symbolic(mgr, network_roots(mgr, net), parsed)
    res["ours_parse_bnet_identity"] = bool(vf["exact"] and pnames == names)
    for tool, fn in (("pyboolnet", pyboolnet_successors), ("dd", dd_successors),
                     ("z3", z3_successors)):
        try:
            res[tool] = fn(text, names, states) == truth
        except Exception as exc:  # noqa: BLE001
            res[tool] = f"error: {type(exc).__name__}: {str(exc)[:120]}"
    return res, states, truth


# ---------------------------------------------------------------------------

def main() -> None:
    t0 = time.time()
    (CORPUS / "synthetic").mkdir(parents=True, exist_ok=True)
    (CORPUS / "bio").mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="screen_corpus_"))
    entries, rejected, pending_r = [], [], []

    # synthetic -------------------------------------------------------------
    for n in SIZES:
        for s in range(SEEDS_PER_N):
            seed = synthetic_seed(n, s)
            net = random_network(n, seed, max_arity=MAX_ARITY, gate_pool=GATE_POOL)
            names = canonical_names(n)
            stem = f"synthetic/n{n:03d}_s{s}"
            (CORPUS / f"{stem}.json").write_text(json.dumps(network_to_json(net)))
            (CORPUS / f"{stem}.bnet").write_text(network_to_bnet(net, names))
            chk, states, truth = forward_checks(net, names, CORPUS / f"{stem}.bnet", stem)
            entries.append({"id": stem, "kind": "synthetic", "n": n, "seed": seed,
                            "generator": f"random_network(n, seed, max_arity={MAX_ARITY}, gate_pool='{GATE_POOL}')",
                            "network_json": f"{stem}.json", "bnet": f"{stem}.bnet",
                            "max_indegree": max(sum(r) for r in net.C),
                            "gates": sorted(set(net.gates)), "checks": chk})
            pending_r.append((stem, states, truth))
            log("synthetic", stem, chk)

    # biological candidates -------------------------------------------------
    files = sorted(glob.glob(str(ROOT / "data/bio/processed/*.json")))
    candidates = []
    seen_hash = {}
    for f in files:
        name = Path(f).stem
        try:
            d = json.load(open(f))
            if not isinstance(d, dict) or "nodes" not in d:
                raise ValueError("not a network file")
            net, orig_names, notes = network_from_processed(d)
        except Exception as exc:  # noqa: BLE001
            rejected.append({"file": Path(f).name, "stage": "convert",
                             "reason": f"{type(exc).__name__}: {str(exc)[:160]}"})
            continue
        names = canonical_names(net.n)
        text = network_to_bnet(net, names)
        h = __import__("hashlib").sha256(text.encode()).hexdigest()
        if h in seen_hash:
            rejected.append({"file": Path(f).name, "stage": "dedup",
                             "reason": f"identical network to {seen_hash[h]}"})
            continue
        seen_hash[h] = Path(f).name
        stem = f"bio/{name}"
        (CORPUS / f"{stem}.json").write_text(json.dumps(network_to_json(net)))
        (CORPUS / f"{stem}.bnet").write_text(text)
        chk, states, truth = forward_checks(net, names, CORPUS / f"{stem}.bnet", stem)
        candidates.append({"id": stem, "kind": "bio", "n": net.n, "source_file":
                           f"data/bio/processed/{Path(f).name}",
                           "source_sha256": sha256(Path(f)), "source": d.get("source"),
                           "node_names": orig_names, "network_json": f"{stem}.json",
                           "bnet": f"{stem}.bnet", **notes, "checks": chk})
        pending_r.append((stem, states, truth))
        log("bio", stem, net.n, chk)

    # BoolNet: one R process for every file ---------------------------------
    jobs, truths = [], {}
    for stem, states, truth in pending_r:
        sp = work / (stem.replace("/", "__") + "_states.csv")
        op = work / (stem.replace("/", "__") + "_out.csv")
        sp.write_text("\n".join(",".join(map(str, s)) for s in states) + "\n")
        jobs.append((str(CORPUS / f"{stem}.bnet"), str(sp), str(op)))
        truths[str(CORPUS / f"{stem}.bnet")] = (op, truth)
    status = boolnet_successors(jobs)
    by_id = {e["id"]: e for e in entries + candidates}
    for stem, _, _ in pending_r:
        bp = str(CORPUS / f"{stem}.bnet")
        op, truth = truths[bp]
        st = status.get(bp, "no output")
        if st == "ok":
            got = [[int(v) for v in ln.split(",")] for ln in op.read_text().split()]
            by_id[stem]["checks"]["boolnet"] = got == truth
        else:
            by_id[stem]["checks"]["boolnet"] = f"error: {st[:160]}"

    def all_ok(e):
        return all(v is True for v in e["checks"].values())

    # biological selection rule (fixed before any measurement) --------------
    # Admit candidates that load in every tool; if more than MAX_BIO remain,
    # take MAX_BIO spread evenly over the list sorted by (n, id), always
    # keeping the smallest and the largest.
    ok_bio = sorted([c for c in candidates if all_ok(c)], key=lambda c: (c["n"], c["id"]))
    for c in candidates:
        if not all_ok(c):
            rejected.append({"file": Path(c["source_file"]).name, "stage": "tool_load",
                             "reason": json.dumps(c["checks"])[:300]})
    if len(ok_bio) > MAX_BIO:
        L = len(ok_bio)
        picks = sorted({round(i * (L - 1) / (MAX_BIO - 1)) for i in range(MAX_BIO)})
        chosen = [ok_bio[i] for i in picks]
    else:
        chosen = ok_bio
    chosen_ids = {c["id"] for c in chosen}
    for c in candidates:
        if c["id"] not in chosen_ids:
            for suffix in (".json", ".bnet"):
                (CORPUS / f"{c['id']}{suffix}").unlink(missing_ok=True)

    final = []
    for e in entries + chosen:
        e["network_sha256"] = sha256(CORPUS / e["network_json"])
        e["bnet_sha256"] = sha256(CORPUS / e["bnet"])
        final.append(e)

    syn_ok = sum(all_ok(e) for e in entries)
    manifest = {
        "protocol": "index-deconvolution/PROTOCOL_screen_identification.md (frozen at dcc1d59e)",
        "script": "index-deconvolution/experiments/screen_s0_corpus.py",
        "created_unix": int(time.time()),
        "tool_versions": tool_versions(),
        "synthetic": {"sizes": SIZES, "seeds_per_n": SEEDS_PER_N,
                      "seed_rule": "seed = 1000*n + s, s = 0..4",
                      "max_arity": MAX_ARITY, "gate_pool": GATE_POOL,
                      "count": len(entries), "all_tools_load": syn_ok},
        "bio": {"files_scanned": len(files), "converted": len(candidates),
                "load_in_every_tool": len(ok_bio), "selected": len(chosen),
                "selection_rule": f"sorted by (n, id); if more than {MAX_BIO}, indices round(i*(L-1)/{MAX_BIO - 1})"},
        "load_check": f"forward map of each tool == causalbool.step on {N_CHECK_STATES} pinned random states (seed '{STATE_SEED}:<id>'); ours: parse_bnet(bnet) == network by canonical diagram identity over all 2^n states",
        "entries": final,
        "rejected": rejected,
        "elapsed_s": round(time.time() - t0, 1),
    }
    write_json(CORPUS / "manifest.json", manifest)
    print(f"synthetic: {syn_ok}/{len(entries)} load in every tool")
    print(f"bio: scanned {len(files)}, converted {len(candidates)}, "
          f"load in every tool {len(ok_bio)}, selected {len(chosen)} "
          f"(n: {[c['n'] for c in chosen]})")
    print(f"rejected by stage: " + json.dumps(
        {s: sum(r['stage'] == s for r in rejected) for s in ('convert', 'dedup', 'tool_load')}))


if __name__ == "__main__":
    main()
