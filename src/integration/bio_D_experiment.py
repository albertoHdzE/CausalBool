import json
import math
import random
import sys
from pathlib import Path

import numpy as np

try:
    from integration.BDM_Wrapper import BDMWrapper
except ModuleNotFoundError:
    src_dir = Path(__file__).resolve().parents[1]
    if str(src_dir) not in sys.path:
        sys.path.append(str(src_dir))
    from integration.BDM_Wrapper import BDMWrapper


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
    d = int(sum(cm_row))
    k = len(GATE_LABELS)
    cost = 0.0
    cost += log2_int(k)
    if 0 <= d <= n:
        binom = math.comb(n, d)
    else:
        binom = 1
    cost += log2_int(max(1, binom))
    if gate == "KOFN":
        cost += log2_int(d + 1) + 1.0
    elif gate == "CANALISING":
        cost += log2_int(n) + 2.0
    elif gate == "IMPLIES" or gate == "NIMPLIES":
        cost += log2_int(max(1, d * (d - 1)))
    elif gate == "NOT":
        cost += log2_int(max(1, d))
    elif gate in ("MAJORITY", "XOR", "XNOR"):
        cost += 1.0
    else:
        cost += 1.0
    return cost


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


def apply_gate(gate: str, inputs, params):
    if gate == "INPUT":
        return inputs[0] if len(inputs) > 0 else 0
    if gate == "IDENTITY":
        return inputs[0] if len(inputs) > 0 else 0
    if gate == "NOT":
        return 0 if inputs[0] == 1 else 1
    if gate == "AND":
        return 1 if all(inputs) else 0
    if gate == "OR":
        return 1 if any(inputs) else 0
    if gate == "CANALISING":
        idx = params.get("canalisingIndex", 1) - 1
        val = params.get("canalisingValue", 1)
        out = params.get("canalisedOutput", 1)
        if 0 <= idx < len(inputs) and inputs[idx] == val:
            return out
        fallback = [v for i, v in enumerate(inputs) if i != idx]
        return 1 if any(fallback) else 0
    return 0


def generate_repertoire_for_network(net):
    nodes = net["nodes"]
    cm = net["cm"]
    gates = net["gates"]
    n = len(nodes)
    name_to_idx = {name: i for i, name in enumerate(nodes)}
    outputs = []
    for state_int in range(2 ** n):
        x = [(state_int >> i) & 1 for i in range(n)]
        y = [0] * n
        for i, node in enumerate(nodes):
            gate_info = gates.get(node)
            if gate_info is None:
                y[i] = x[i]
                continue
            gate = gate_info["gate"]
            input_names = gate_info.get("inputs", [])
            inputs = [x[name_to_idx[name]] for name in input_names]
            params = gate_info.get("parameters", {})
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
