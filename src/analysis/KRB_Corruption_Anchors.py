import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats


# AUDIT03 (monolithic-code): _repo_root, _paper_root and _paper_figures_dir
# were defined identically here and in three other production modules. One
# owner now; parity proven over 24 of 24 comparisons before this edit
# (audit/AUDIT03_R2_collapse/probe_paths_parity.py). Guarded by
# tools/check_single_engine.sh.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from causalbool_paths import repo_root as _repo_root  # noqa: E402
from causalbool_paths import paper_root as _paper_root  # noqa: E402
from causalbool_paths import paper_figures_dir as _paper_figures_dir  # noqa: E402


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _randomize_matrix_deg_preserve(cm: np.ndarray, n_swaps: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    cm = np.asarray(cm, dtype=int)
    out = cm.copy()
    rows, cols = np.nonzero(out)
    edges = list(zip(rows.tolist(), cols.tolist()))
    n_edges = len(edges)
    if n_edges < 2:
        return out

    attempts = 0
    max_attempts = int(n_swaps) * 20 + 2000
    swaps = 0
    while swaps < int(n_swaps) and attempts < max_attempts:
        attempts += 1
        i1, i2 = rng.choice(n_edges, size=2, replace=False)
        u, v = edges[int(i1)]
        x, y = edges[int(i2)]
        if u == y or x == v:
            continue
        if out[u, y] == 1 or out[x, v] == 1:
            continue
        out[u, v] = 0
        out[x, y] = 0
        out[u, y] = 1
        out[x, v] = 1
        edges[int(i1)] = (u, y)
        edges[int(i2)] = (x, v)
        swaps += 1
    return out


def _dv2(cm: np.ndarray) -> float:
    repo = _repo_root()
    sys.path.append(str(repo / "src"))
    from integration.Universal_D_v2_Encoder import UniversalDv2Encoder

    enc = UniversalDv2Encoder(cm.tolist())
    res = enc.compute()
    return float(res.get("dv2", 0.0))


def _default_node_to_genes(nodes: list[str]) -> dict[str, list[str]]:
    repo = _repo_root()
    sys.path.append(str(repo / "src"))
    from data.cancer_network_builder import CancerNetworkBuilder

    mp = CancerNetworkBuilder.default_node_to_genes_for_nodes(nodes)
    out = {}
    for k, vs in dict(mp).items():
        if k is None:
            continue
        kk = str(k)
        out[kk] = [str(v) for v in (vs or []) if str(v).strip()]
    return out


def _pair_index(patient_dir: Path) -> list[dict]:
    pairs = []
    tumors = {}
    normals = {}
    for p in sorted(patient_dir.glob("*.json")):
        n = p.name
        if n.endswith("_Tumor.json"):
            tumors[n.replace("_Tumor.json", "")] = p
        if n.endswith("_Normal.json"):
            normals[n.replace("_Normal.json", "")] = p
    keys = sorted(set(tumors.keys()) & set(normals.keys()))
    for k in keys:
        pairs.append({"patient_id": k, "tumor_path": str(tumors[k]), "normal_path": str(normals[k])})
    return pairs


def _perm_p_abs(x: np.ndarray, y: np.ndarray, n_perm: int, seed: int = 2026) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x = x[m]
    y = y[m]
    if len(x) < 3:
        return {"spearman_rho": float("nan"), "perm_p_abs": float("nan"), "n": int(len(x)), "null": []}
    obs = float(stats.spearmanr(x, y).statistic)
    rng = np.random.default_rng(int(seed))
    null = []
    for _ in range(int(n_perm)):
        yr = rng.permutation(y)
        null.append(float(stats.spearmanr(x, yr).statistic))
    null = np.asarray(null, dtype=float)
    null = null[np.isfinite(null)]
    p = float((np.sum(np.abs(null) >= abs(obs)) + 1.0) / (len(null) + 1.0)) if len(null) else float("nan")
    return {"spearman_rho": float(obs), "perm_p_abs": p, "n": int(len(x)), "null": null.tolist()}


def _perm_p_diff_topk(score: np.ndarray, dep: np.ndarray, k: int, n_perm: int, seed: int = 2026) -> dict:
    score = np.asarray(score, dtype=float)
    dep = np.asarray(dep, dtype=float)
    m = np.isfinite(score) & np.isfinite(dep)
    score = score[m]
    dep = dep[m]
    n = int(len(dep))
    k = int(min(int(k), max(1, n // 2)))
    if n < 4:
        return {"n": int(n), "k": int(k), "diff_top_minus_bottom": float("nan"), "perm_p": float("nan"), "null": []}
    order = np.argsort(score)[::-1]
    top = dep[order[:k]]
    bot = dep[order[-k:]]
    obs = float(np.mean(top) - np.mean(bot))
    rng = np.random.default_rng(int(seed))
    null = []
    for _ in range(int(n_perm)):
        dep_p = rng.permutation(dep)
        top_p = dep_p[order[:k]]
        bot_p = dep_p[order[-k:]]
        null.append(float(np.mean(top_p) - np.mean(bot_p)))
    null = np.asarray(null, dtype=float)
    null = null[np.isfinite(null)]
    p = float((np.sum(np.abs(null) >= abs(obs)) + 1.0) / (len(null) + 1.0)) if len(null) else float("nan")
    return {"n": int(n), "k": int(k), "diff_top_minus_bottom": float(obs), "perm_p": p, "null": null.tolist()}


def main() -> None:
    patient_dir = Path(os.getenv("KRB_PATIENT_DIR", "data/cancer/patients")).resolve()
    base_path = Path(os.getenv("KRB_BASE_NETWORK", "data/bio/processed/egfr_signaling.json")).resolve()
    out_prefix = Path(os.getenv("KRB_OUT_PREFIX", str(_paper_figures_dir() / "krb_corruption_anchor"))).resolve()
    null_samples = int(os.getenv("KRB_NULL_SAMPLES", "80") or "80")
    perm_n = int(os.getenv("KRB_PERM_N", "5000") or "5000")
    depmap_gene_mean = Path(os.getenv("KRB_DEPMAP_GENE_MEAN", "data/DepMap/CRISPRGeneEffect.csv.gene_mean.csv")).resolve()

    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    base = _load_json(base_path)
    nodes = list(base.get("nodes", []))
    base_cm = np.array(base.get("cm", []), dtype=int)
    if base_cm.ndim != 2 or base_cm.shape[0] != base_cm.shape[1] or len(nodes) != base_cm.shape[0]:
        raise ValueError("Base network must contain square 'cm' and matching 'nodes'.")

    pairs = _pair_index(patient_dir)
    if not pairs:
        raise FileNotFoundError(f"No tumor/normal pairs found under {patient_dir}")

    normal_d = _dv2(base_cm)

    rows = []
    node_removed_in = np.zeros(len(nodes), dtype=float)
    node_changed_any = np.zeros(len(nodes), dtype=float)

    for item in pairs:
        pid = item["patient_id"]
        tumor = _load_json(Path(item["tumor_path"]))
        normal = _load_json(Path(item["normal_path"]))
        cm_t = np.array(tumor.get("cm", []), dtype=int)
        cm_n = np.array(normal.get("cm", []), dtype=int)

        if cm_t.shape != base_cm.shape or cm_n.shape != base_cm.shape:
            continue

        d_t = _dv2(cm_t)
        d_n = _dv2(cm_n)

        diff = (cm_n != cm_t).astype(int)
        removed_in = np.maximum(0, cm_n - cm_t).sum(axis=0).astype(float)
        node_removed_in += removed_in
        node_changed_any += (diff.sum(axis=0) + diff.sum(axis=1) > 0).astype(float)

        n_swaps = int(cm_t.shape[0]) * 20
        d_null = []
        for j in range(int(null_samples)):
            cm_r = _randomize_matrix_deg_preserve(cm_t, n_swaps=n_swaps, seed=1000 + j * 7 + int(hash(pid) & 0xFFFF))
            d_null.append(_dv2(cm_r))
        d_null = np.asarray(d_null, dtype=float)
        d_null = d_null[np.isfinite(d_null)]
        d_null_mean = float(np.mean(d_null)) if len(d_null) else float("nan")

        rows.append(
            {
                "PatientID": str(pid),
                "D_normal": float(d_n),
                "D_tumor": float(d_t),
                "Delta_D": float(d_t - d_n),
                "D_tumor_null_mean": float(d_null_mean),
                "Delta_D_null_mean": float(d_null_mean - d_n) if np.isfinite(d_null_mean) else float("nan"),
            }
        )

    df = pd.DataFrame(rows)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["D_normal", "D_tumor", "Delta_D"]).copy()
    if len(df) < 5:
        raise RuntimeError("Not enough valid patient pairs to analyze.")

    t_obs = stats.ttest_rel(df["D_tumor"], df["D_normal"])
    delta = df["Delta_D"].to_numpy(dtype=float, copy=False)
    delta_null = df["Delta_D_null_mean"].to_numpy(dtype=float, copy=False)
    mask = np.isfinite(delta) & np.isfinite(delta_null)
    t_nc = stats.ttest_rel(delta[mask], delta_null[mask]) if np.sum(mask) >= 5 else None

    out_patient = out_prefix.as_posix() + "__patients.csv"
    df.to_csv(out_patient, index=False)

    node_df = pd.DataFrame(
        {
            "Gene": [str(x) for x in nodes],
            "incoming_edges_removed_total": node_removed_in.astype(float),
            "incoming_edges_removed_mean": (node_removed_in / float(len(pairs))).astype(float),
            "fraction_nodes_changed_any": (node_changed_any / float(len(pairs))).astype(float),
        }
    )

    dep = None
    if depmap_gene_mean.exists():
        dep = pd.read_csv(depmap_gene_mean)
        dep["Gene"] = dep["Gene"].astype(str)
        dep["Dependency"] = pd.to_numeric(dep["Dependency"], errors="coerce")
        dep["Gene_u"] = dep["Gene"].str.upper()

        node_to_genes = _default_node_to_genes([str(x) for x in nodes])
        gene_u_to_dep = dict(zip(dep["Gene_u"].astype(str), dep["Dependency"].astype(float)))

        mapped = []
        for node in node_df["Gene"].astype(str).tolist():
            gs = node_to_genes.get(node) or []
            vals = []
            for g in gs:
                v = gene_u_to_dep.get(str(g).upper())
                if v is None:
                    continue
                if np.isfinite(float(v)):
                    vals.append(float(v))
            mapped.append(
                {
                    "Gene": str(node),
                    "MappedGenes": ",".join([str(g) for g in gs]),
                    "DepMapDependency_mapped_max": float(np.max(vals)) if vals else float("nan"),
                    "DepMapDependency_mapped_mean": float(np.mean(vals)) if vals else float("nan"),
                }
            )
        node_df = node_df.merge(pd.DataFrame(mapped), on="Gene", how="left")

    anchor = _perm_p_abs(
        node_df["incoming_edges_removed_mean"].to_numpy(dtype=float, copy=False),
        node_df["DepMapDependency_mapped_max"].to_numpy(dtype=float, copy=False)
        if "DepMapDependency_mapped_max" in node_df.columns
        else np.full(len(node_df), np.nan),
        n_perm=perm_n,
        seed=2026,
    )
    anchor_diff = _perm_p_diff_topk(
        node_df["incoming_edges_removed_mean"].to_numpy(dtype=float, copy=False),
        node_df["DepMapDependency_mapped_max"].to_numpy(dtype=float, copy=False)
        if "DepMapDependency_mapped_max" in node_df.columns
        else np.full(len(node_df), np.nan),
        k=3,
        n_perm=perm_n,
        seed=2027,
    )

    node_df = node_df.sort_values(["incoming_edges_removed_mean"], ascending=False).reset_index(drop=True)
    out_node = out_prefix.as_posix() + "__node_anchor.csv"
    node_df.to_csv(out_node, index=False)

    fig1 = out_prefix.as_posix() + "__negative_control.png"
    plt.figure(figsize=(6.8, 4.2), dpi=200)
    plt.hist(df["Delta_D"].to_numpy(dtype=float), bins=25, alpha=0.75, label="Observed ΔD (tumor-normal)")
    if np.any(np.isfinite(df["Delta_D_null_mean"].to_numpy(dtype=float))):
        plt.hist(df["Delta_D_null_mean"].to_numpy(dtype=float), bins=25, alpha=0.55, label="Null ΔD (deg-preserved tumor)")
    plt.axvline(0, color="black", linestyle="--", linewidth=1.0)
    plt.xlabel("ΔD^(v2) (bits proxy)")
    plt.ylabel("Count")
    plt.title("KR-B paired corruption: observed vs degree-preserved null")
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig1)
    plt.close()

    fig2 = out_prefix.as_posix() + "__node_anchor.png"
    plt.figure(figsize=(7.8, 3.8), dpi=200)
    top = node_df.head(min(15, len(node_df))).copy()
    xs = np.arange(len(top))
    plt.bar(xs, top["incoming_edges_removed_mean"].to_numpy(dtype=float), color="#4C72B0", alpha=0.9)
    plt.xticks(xs, top["Gene"].astype(str).tolist(), rotation=35, ha="right")
    plt.ylabel("Mean incoming edges removed")
    title = "Node corruption footprint (mean incoming pruning)"
    if np.isfinite(anchor.get("spearman_rho", np.nan)):
        title += f" | Spearman ρ(depmap)={anchor['spearman_rho']:.3g}, p={anchor['perm_p_abs']:.3g}"
    plt.title(title)
    plt.tight_layout()
    plt.savefig(fig2)
    plt.close()

    out_json = out_prefix.as_posix() + "__summary.json"
    summary = {
        "run_id": "LEV8-2026-04-06-004",
        "timestamp": datetime.now().isoformat(),
        "inputs": {
            "patient_dir": str(patient_dir),
            "base_network": str(base_path),
            "depmap_gene_mean": str(depmap_gene_mean) if depmap_gene_mean.exists() else None,
        },
        "n_pairs": int(len(df)),
        "D_normal_base": float(normal_d),
        "stats": {
            "paired_t_test_D_tumor_vs_D_normal": {"t": float(t_obs.statistic), "p": float(t_obs.pvalue)},
            "paired_t_test_delta_obs_vs_delta_null": (
                {"t": float(t_nc.statistic), "p": float(t_nc.pvalue)} if t_nc is not None else None
            ),
            "anchor_spearman_depmap": anchor,
            "anchor_topk_depmap": anchor_diff,
        },
        "outputs": {
            "patients_csv": str(out_patient),
            "node_anchor_csv": str(out_node),
            "negative_control_plot": str(fig1),
            "node_anchor_plot": str(fig2),
        },
    }
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"[{datetime.now()}] Wrote {out_patient}")
    print(f"[{datetime.now()}] Wrote {out_node}")
    print(f"[{datetime.now()}] Wrote {fig1}")
    print(f"[{datetime.now()}] Wrote {fig2}")
    print(f"[{datetime.now()}] Wrote {out_json}")


if __name__ == "__main__":
    main()
