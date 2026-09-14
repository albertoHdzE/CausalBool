import json
import re
import math
import random
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

# AUDIT04-D: src/ is placed on sys.path here once, and BOTH the BDM wrapper and
# the description-length owner are reached through it. A second path insertion
# for the owner would be a second way to find one thing.
_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.append(str(_SRC_DIR))

from integration.BDM_Wrapper import BDMWrapper


@lru_cache(maxsize=1)
def _gate_owner():
    """The declared Python owner of gate semantics (author decision 2026-09-06)."""
    _idsrc = _SRC_DIR.parent / "index-deconvolution" / "src"
    if str(_idsrc) not in sys.path:
        sys.path.insert(0, str(_idsrc))
    import causalbool

    return causalbool


GATE_LABELS = [
    "AND",
    "OR",
    "XOR",
    "NAND",
    "NOR",
    "XNOR",
    "NOT",
    "IMPLIES",
    "NIMPLIES",
    "MAJORITY",
    "KOFN",
    "CANALISING",
]


def log2_int(x: int) -> float:
    if x <= 0:
        return 0.0
    return float(math.log2(x))


def encode_node_cost(cm_row, gate: str, n: int) -> float:
    """Per-node description length in bits, delegated to the declared owner.

    AUDIT04-D. This used to carry its own copy of the cost model. Measured
    elementwise against ``src/description_lengths.node_description_cost`` before
    anything moved: **0 disagreements over 180 (n, degree, gate) cases**. Zero is
    drift, not a second concept, so it is collapsed rather than declared.

    Nothing was guarding it, and that is not hypothetical. The AUDIT03/R3.1 note
    this docstring replaces records that the copy HAD drifted before: the
    ``log2(n + 1)`` in-degree field was absent, so a decoder could not know how
    wide the input-set field was, the Kraft sum was ``n + 1`` rather than 1, and
    every DeltaD built from it was a difference of two invalid lengths. It was
    corrected by hand then, and nothing would have caught it happening again.

    The signature keeps ``cm_row`` because callers pass a connectivity row; the
    owner takes the degree, which is that row's sum.
    """
    from description_lengths import node_description_cost

    return node_description_cost(n, int(sum(cm_row)), gate)


def compute_description_length(cm, dynamic):
    n = len(dynamic)
    per_node = [
        encode_node_cost(cm[i], dynamic[i], n)
        for i in range(n)
    ]
    total_bits = float(sum(per_node))
    total_edges = int(sum(int(v) for row in cm for v in row))
    avg_per_node = total_bits / n if n > 0 else 0.0
    return {
        "D": total_bits,
        "per_node": per_node,
        "avg_per_node": avg_per_node,
        "components": n,
        "total_edges": total_edges,
    }


def randomize_network_degree_preserving(cm, n_swaps: int):
    n = len(cm)
    cm_rand = [list(row) for row in cm]
    edges = [(i, j) for i in range(n) for j in range(n) if cm_rand[i][j] == 1]
    if len(edges) < 2:
        return cm_rand
    for _ in range(n_swaps):
        if len(edges) < 2:
            break
        e1, e2 = random.sample(edges, 2)
        i1, j1 = e1
        i2, j2 = e2
        if i1 == j2 or i2 == j1 or i1 == i2 or j1 == j2:
            continue
        if cm_rand[i1][j2] == 1 or cm_rand[i2][j1] == 1:
            continue
        cm_rand[i1][j1] = 0
        cm_rand[i2][j2] = 0
        cm_rand[i1][j2] = 1
        cm_rand[i2][j1] = 1
        edges.remove(e1)
        edges.remove(e2)
        edges.append((i1, j2))
        edges.append((i2, j1))
    return cm_rand


def randomize_gate_assignments(dynamic):
    dynamic_rand = list(dynamic)
    random.shuffle(dynamic_rand)
    return dynamic_rand


def load_processed_bio_networks(base_dir: Path):
    processed_dir = base_dir / "data" / "bio" / "processed"
    networks = {}
    for path in processed_dir.glob("*.json"):
        with path.open() as f:
            net = json.load(f)
        if "cm" not in net or "gates" not in net or "nodes" not in net:
            continue
        name = net.get("name", path.stem)
        nodes = net["nodes"]
        cm = net["cm"]
        gates_map = net.get("gates", {})
        dynamic = []
        for node in nodes:
            gate_info = gates_map.get(node)
            if gate_info is None:
                dynamic.append("INPUT")
            else:
                dynamic.append(gate_info["gate"])
        networks[name] = {
            "cm": cm,
            "dynamic": dynamic,
        }
    return networks


def run_refined_null_experiment(
    base_dir: Path,
    n_random: int = 1000,
    seed: int | None = 1234,
):
    if seed is not None:
        random.seed(seed)
    networks = load_processed_bio_networks(base_dir)
    results = {}
    for name, net in networks.items():
        cm = net["cm"]
        dynamic = net["dynamic"]
        D_bio_res = compute_description_length(cm, dynamic)
        D_bio = D_bio_res["D"]
        E = D_bio_res["total_edges"]
        n_swaps = 100 * E
        random_values = []
        for _ in range(n_random):
            cm_rand = randomize_network_degree_preserving(cm, n_swaps)
            dyn_rand = randomize_gate_assignments(dynamic)
            D_rand_res = compute_description_length(cm_rand, dyn_rand)
            random_values.append(D_rand_res["D"])
        n = len(random_values)
        mean_rand = float(sum(random_values) / n)
        var = float(
            sum((v - mean_rand) ** 2 for v in random_values) / (n - 1)
        ) if n > 1 else 0.0
        std_rand = math.sqrt(var)
        fold_reduction = mean_rand / D_bio if D_bio > 0 else float("inf")
        less_equal = sum(
            1 for v in random_values if v <= D_bio
        )
        p_empirical = (less_equal + 1.0) / (n + 1.0)
        results[name] = {
            "n": D_bio_res["components"],
            "edges": E,
            "D_bio": D_bio,
            "D_rand_mean_refined": mean_rand,
            "D_rand_std_refined": std_rand,
            "fold_reduction_refined": fold_reduction,
            "n_random_refined": n,
            "p_empirical_refined": p_empirical,
        }
    out_dir = base_dir / "results" / "bio" / "metricks"
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "D_metrics_refined_null.json"
    with metrics_path.open("w") as f:
        json.dump(results, f, indent=2)
    return metrics_path


def load_refined_null_metrics(base_dir: Path):
    metrics_path = base_dir / "results" / "bio" / "metricks" / "D_metrics_refined_null.json"
    if not metrics_path.exists():
        raise FileNotFoundError(str(metrics_path))
    with metrics_path.open() as f:
        return json.load(f)


def load_repertoire_matrix(csv_path: Path):
    data = np.loadtxt(csv_path, delimiter=",", dtype=int)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    return data


def compute_bdm_for_repertoires(base_dir: Path, repertoire_dir: Path | None = None):
    if repertoire_dir is None:
        repertoire_dir = base_dir / "results" / "bio" / "repertoires"
    metrics = load_refined_null_metrics(base_dir)
    wrapper = BDMWrapper()
    results = {}
    for name, info in metrics.items():
        csv_path = repertoire_dir / f"{name}_repertoire.csv"
        if not csv_path.exists():
            continue
        matrix = load_repertoire_matrix(csv_path)
        bdm_info = wrapper.compute_bdm(matrix)
        results[name] = {
            "n": info.get("n"),
            "edges": info.get("edges"),
            "D_bio": info.get("D_bio"),
            "BDM_bio": bdm_info["bdm_value"],
        }
    out_dir = base_dir / "results" / "bio" / "metricks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "D_BDM_bio_metrics.json"
    with out_path.open("w") as f:
        json.dump(results, f, indent=2)
    return out_path


def compute_d_bdm_correlation(base_dir: Path, repertoire_dir: Path | None = None):
    metrics_path = compute_bdm_for_repertoires(base_dir, repertoire_dir)
    with metrics_path.open() as f:
        data = json.load(f)
    pairs = []
    for name, info in data.items():
        d_val = info.get("D_bio")
        bdm_val = info.get("BDM_bio")
        if d_val is None or bdm_val is None:
            continue
        pairs.append((float(d_val), float(bdm_val)))
    if len(pairs) < 2:
        return None
    ds = [p[0] for p in pairs]
    bs = [p[1] for p in pairs]
    mean_d = sum(ds) / len(ds)
    mean_b = sum(bs) / len(bs)
    num = sum((d - mean_d) * (b - mean_b) for d, b in zip(ds, bs))
    den_d = sum((d - mean_d) ** 2 for d in ds)
    den_b = sum((b - mean_b) ** 2 for b in bs)
    if den_d <= 0 or den_b <= 0:
        corr = 0.0
    else:
        corr = num / math.sqrt(den_d * den_b)
    out_dir = base_dir / "results" / "bio" / "metricks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "D_BDM_correlation.json"
    payload = {
        "pairs": [
            {"D_bio": d, "BDM_bio": b}
            for d, b in pairs
        ],
        "pearson_correlation": corr,
    }
    with out_path.open("w") as f:
        json.dump(payload, f, indent=2)
    return out_path




# --- AUDIT02/P8: Boolean formula evaluator -----------------------------------
# Mirrors src/Packages/Integration/LogicEval.m. Scope measured over the corpus:
# 3,709 of 4,628 expressions (80.1%) are Boolean and evaluated exactly; 512
# multi-valued (X:k) and 407 threshold (GEQ/theta) expressions are REFUSED,
# returning None so the caller falls back rather than fabricating a value.
_LOGIC_WORDS = {"AND", "OR", "NOT", "TRUE", "FALSE"}


def logic_class(expr: str) -> str:
    if re.search(r"\b(GEQ|LEQ|LT|GT|EQ)\s*\(", expr):
        return "Threshold"
    if re.search(r"[A-Za-z_0-9\-]+:[0-9]", expr):
        return "MultiValued"
    return "Boolean"


def evaluate_logic(expr: str, state: dict):
    """Return 0/1, or None if the expression is refused or unbound."""
    if logic_class(expr) != "Boolean":
        return None
    out = []
    for tok in re.split(r"([&|!(),])", expr):
        t = tok.strip()
        if not t:
            continue
        if t == "&":
            out.append(" and ")
        elif t == "|":
            out.append(" or ")
        elif t == "!":
            out.append(" not ")
        elif t in "(),":
            out.append(t)
        else:
            u = t.upper()
            if u == "AND":
                out.append("__AND")
            elif u == "OR":
                out.append("__OR")
            elif u == "NOT":
                out.append("__NOT")
            elif u == "TRUE":
                out.append("True")
            elif u == "FALSE":
                out.append("False")
            else:
                if t not in state:
                    return None
                out.append(f"V[{t!r}]")
    env = {"__AND": lambda *a: all(a), "__OR": lambda *a: any(a),
           "__NOT": lambda a: not a, "V": state}
    try:
        return 1 if eval("".join(out), {"__builtins__": {}}, env) else 0
    except Exception:
        return None


def apply_gate(gate: str, inputs, params):
    """Evaluate a gate. The twelve families are delegated to the owner.

    AUDIT04-D. This carried its own copy of the twelve-family catalogue.
    Measured elementwise against ``index-deconvolution/src/causalbool.apply_gate``
    before anything moved: **0 disagreements over 168 (gate, input) cases**.
    Zero is drift, so the twelve are delegated rather than declared.

    It was the only ``def apply_gate`` under ``src/`` -- an experiment module
    serving as the de facto gate owner for the whole source tree, with nothing
    guarding it. It was briefly INVISIBLE to the guard as well: crediting this
    file for importing ``description_lengths`` cleared its gate flag, because the
    ledger listed the description-length owner among the gate owner's references.
    That cross-concept credit is now removed.

    INPUT and IDENTITY are NOT delegated and are not gate families. They are
    corpus sentinels meaning "this node holds its value", particular to the
    biological networks this module reads, and the owner has no such notion.
    Keeping only what is particular here is the rule; inventing them in the owner
    would put a corpus artefact into the gate catalogue.
    """
    if gate in ("INPUT", "IDENTITY"):
        if not inputs:
            # AUDIT02/P1: the caller already handles the empty case by holding
            # the node's value, so reaching here means the caller changed. A
            # silent 0 would be indistinguishable from a legitimate FALSE.
            raise ValueError(f"{gate} with no inputs must be resolved by the caller")
        return inputs[0]
    return int(_gate_owner().apply_gate(gate, list(inputs), params or {}))


def generate_repertoire_for_network(net):
    """Exhaustive output repertoire.

    AUDIT02/P8: the node's Boolean FORMULA in net["logic"] is now preferred over
    its classification label in net["gates"]. The label alone left CUSTOM,
    IDENTITY, INPUT and unlisted nodes -- 76.4% of node instances across the
    corpus -- evaluated by a fallthrough that silently returned 0.

    Formulas are evaluated against the full NAMED state, because 466 of the
    corpus formulas reference their own node (the cm omits self-edges).
    Multi-valued and threshold expressions are refused by evaluate_logic and
    fall back to the label, surfacing rather than being fabricated.
    """
    nodes = net["nodes"]
    # Not read, but the subscript asserts the key is present, so a network
    # missing its connectivity matrix fails here rather than much later with a
    # confusing error. Kept deliberately.
    cm = net["cm"]    # noqa: F841
    gates = net["gates"]
    logic = net.get("logic") or {}
    n = len(nodes)
    name_to_idx = {name: i for i, name in enumerate(nodes)}
    outputs = []
    for state_int in range(2 ** n):
        x = [(state_int >> i) & 1 for i in range(n)]
        named = {nm: x[j] for j, nm in enumerate(nodes)}
        y = [0] * n
        for i, node in enumerate(nodes):
            expr = logic.get(node)
            # "INPUT" is a sentinel for a free source node: it holds its value.
            if isinstance(expr, str) and expr.strip().upper() == "INPUT":
                y[i] = x[i]
                continue
            if isinstance(expr, str):
                v = evaluate_logic(expr, named)
                if v is not None:
                    y[i] = v
                    continue
            gate_info = gates.get(node)
            if gate_info is None:
                y[i] = x[i]
                continue
            gate = gate_info["gate"]
            input_names = gate_info.get("inputs", [])
            inputs = [x[name_to_idx[name]] for name in input_names]
            params = gate_info.get("parameters", {})
            if gate in ("INPUT", "IDENTITY") and not inputs:
                y[i] = x[i]
                continue
            y[i] = apply_gate(gate, inputs, params)
        outputs.append(y)
    return np.array(outputs, dtype=int)


def generate_bio_repertoires(base_dir: Path):
    processed_dir = base_dir / "data" / "bio" / "processed"
    repertoire_dir = base_dir / "results" / "bio" / "repertoires"
    repertoire_dir.mkdir(parents=True, exist_ok=True)
    for path in processed_dir.glob("*.json"):
        with path.open() as f:
            net = json.load(f)
        if "cm" not in net or "gates" not in net or "nodes" not in net:
            continue
        name = net.get("name", path.stem)
        matrix = generate_repertoire_for_network(net)
        out_path = repertoire_dir / f"{name}_repertoire.csv"
        np.savetxt(out_path, matrix, fmt="%d", delimiter=",")
    return repertoire_dir


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[2]
    run_refined_null_experiment(base)
