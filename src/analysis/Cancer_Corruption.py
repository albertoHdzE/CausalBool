
import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from integration.Universal_D_v2_Encoder import UniversalDv2Encoder
from data.cancer_network_builder import CancerNetworkBuilder

# Configuration
DATA_DIR = os.getenv("CANCER_DATA_DIR", "data/cancer/patients")
METADATA_PATH = os.getenv("CANCER_METADATA_PATH", "data/cancer/clinical_metadata.csv")
TCGA_INDEX_PATH = os.getenv("TCGA_INDEX_PATH", "")
OUTPUT_DIR = os.getenv("CANCER_OUTPUT_DIR", "results/cancer")
OUTPUT_BASENAME = os.getenv("CANCER_OUTPUT_BASENAME", "corruption_metrics.csv")
FIGURE_DIR = os.getenv("CANCER_FIGURE_DIR", "4ClaudeCode/claude-Nature/paper/figures")
TCGA_SWEEP_THRESHOLDS = os.getenv("TCGA_SWEEP_THRESHOLDS", "")
TCGA_COUNTS_ROOT = os.getenv("TCGA_COUNTS_ROOT", "data/cancer/tcga_paired")
TCGA_BASE_NETWORK_PATH = os.getenv("TCGA_BASE_NETWORK_PATH", "data/bio/processed/egfr_signaling.json")

# Ensure directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIGURE_DIR, exist_ok=True)

def load_network(path):
    with open(path, 'r') as f:
        return json.load(f)

def compute_d_v2(json_data):
    cm = json_data.get("cm")
    if not cm:
        return None
    encoder = UniversalDv2Encoder(cm)
    result = encoder.compute()
    return result["dv2"]

def load_tcga_pairs(index_path: str) -> pd.DataFrame:
    idx = pd.read_csv(index_path)
    rows = []
    for (project, patient_id), g in idx.groupby(["project", "patient_id"]):
        g = g.set_index("tissue_type")
        if "Normal" not in g.index or "Tumor" not in g.index:
            continue
        rows.append(
            {
                "project": project,
                "patient_id": patient_id,
                "normal_sample": str(g.loc["Normal", "sample_name"]),
                "tumor_sample": str(g.loc["Tumor", "sample_name"]),
                "mutation_count": int(g.loc["Tumor", "mutation_count"]),
            }
        )
    return pd.DataFrame(rows)

def compute_d_v2_from_cm(cm: np.ndarray) -> float:
    encoder = UniversalDv2Encoder(cm.astype(int, copy=False))
    result = encoder.compute()
    return float(result["dv2"])

def _read_counts_subset(path: str, gene_set: set, sample_cols: list) -> pd.DataFrame:
    usecols = ["gene_name", *sample_cols]
    chunks = pd.read_csv(path, usecols=usecols, chunksize=5000, low_memory=False)
    rows = []
    for chunk in chunks:
        sub = chunk[chunk["gene_name"].isin(gene_set)]
        if len(sub):
            rows.append(sub)
    if not rows:
        return pd.DataFrame(index=pd.Index([], name="gene_name"), columns=sample_cols, dtype=float)
    df = pd.concat(rows, axis=0, ignore_index=True)
    df = df.drop_duplicates(subset=["gene_name"], keep="first")
    df = df.set_index("gene_name")
    return df

def _node_expr(counts: pd.DataFrame, node_to_genes: dict, agg: str = "max") -> pd.DataFrame:
    out = {}
    for node, genes in node_to_genes.items():
        present = [g for g in genes if g in counts.index]
        if not present:
            out[node] = np.full(counts.shape[1], np.nan, dtype=float)
            continue
        block = counts.loc[present].to_numpy(dtype=float, copy=False)
        if agg == "max":
            out[node] = np.nanmax(block, axis=0)
        else:
            out[node] = np.nanmean(block, axis=0)
    return pd.DataFrame(out, index=counts.columns).T

def _mutate_cm(base_cm: np.ndarray, nodes: list, diff: pd.Series, thr: float) -> tuple:
    cm = np.array(base_cm, copy=True)
    mutated = 0
    for i, node in enumerate(nodes):
        d = float(diff.get(node, np.nan))
        if np.isnan(d):
            continue
        if d >= thr or d <= -thr:
            cm[i, :] = 0
            mutated += 1
    return cm, int(mutated)

def main():
    print(f"[{datetime.now()}] Starting Cancer Corruption Analysis...")
    results = []
    plot_prefix = os.path.splitext(str(OUTPUT_BASENAME))[0]

    if TCGA_INDEX_PATH:
        if TCGA_SWEEP_THRESHOLDS:
            base = load_network(TCGA_BASE_NETWORK_PATH)
            nodes = list(base.get("nodes", []))
            base_cm = np.array(base.get("cm", []), dtype=int)
            d_normal = compute_d_v2_from_cm(base_cm)

            node_to_genes = CancerNetworkBuilder.default_node_to_genes_for_nodes(nodes)
            node_to_genes = {k: list(v) for k, v in dict(node_to_genes).items() if k in set(nodes)}
            gene_set = set()
            for genes in node_to_genes.values():
                for g in genes:
                    if g:
                        gene_set.add(str(g))

            thresholds = [float(x) for x in str(TCGA_SWEEP_THRESHOLDS).split(",") if str(x).strip()]
            idx = pd.read_csv(TCGA_INDEX_PATH)
            pairs = load_tcga_pairs(TCGA_INDEX_PATH)
            if len(pairs) == 0:
                print(f"[{datetime.now()}] No paired tumor/normal cases found; sweep requires paired index.")
                return

            by_project = {}
            for project, g in idx.groupby("project"):
                tumors = g[g["tissue_type"] == "Tumor"]["sample_name"].tolist()
                normals = g[g["tissue_type"] == "Normal"]["sample_name"].tolist()
                by_project[project] = {"tumor_cols": tumors, "normal_cols": normals}

            cache = {}
            for project, spec in by_project.items():
                tumor_csv = os.path.join(TCGA_COUNTS_ROOT, project, "processed", "counts_tumor.csv")
                normal_csv = os.path.join(TCGA_COUNTS_ROOT, project, "processed", "counts_normal.csv")
                if not os.path.exists(tumor_csv) or not os.path.exists(normal_csv):
                    continue

                ct = _read_counts_subset(tumor_csv, gene_set, spec["tumor_cols"])
                cn = _read_counts_subset(normal_csv, gene_set, spec["normal_cols"])
                xt = np.log2(ct + 1.0)
                xn = np.log2(cn + 1.0)
                node_t = _node_expr(xt, node_to_genes, agg="max")
                node_n = _node_expr(xn, node_to_genes, agg="max")
                baseline = node_n.median(axis=1, skipna=True)
                cache[project] = {"node_t": node_t, "baseline": baseline}

            sweep_rows = []
            for thr in thresholds:
                for _, row in pairs.iterrows():
                    project = row["project"]
                    pid = row["patient_id"]
                    tumor_sample = row["tumor_sample"]
                    normal_sample = row["normal_sample"]
                    if project not in cache:
                        continue
                    node_t = cache[project]["node_t"]
                    baseline = cache[project]["baseline"]
                    if tumor_sample not in node_t.columns:
                        continue
                    diff = node_t[tumor_sample] - baseline
                    cm_t, mut = _mutate_cm(base_cm, nodes, diff, thr)
                    d_tumor = compute_d_v2_from_cm(cm_t)
                    sweep_rows.append(
                        {
                            "threshold": float(thr),
                            "project": project,
                            "patient_id": pid,
                            "normal_sample": normal_sample,
                            "tumor_sample": tumor_sample,
                            "mutation_count": int(mut),
                            "n_nodes": int(len(nodes)),
                            "edges_normal": int(base_cm.sum()),
                            "edges_tumor": int(cm_t.sum()),
                            "D_normal": float(d_normal),
                            "D_tumor": float(d_tumor),
                            "Delta_D": float(d_tumor - d_normal),
                        }
                    )

            sweep_df = pd.DataFrame(sweep_rows)
            sweep_path = os.path.join(OUTPUT_DIR, f"{plot_prefix}__tcga_paired_sweep.csv")
            sweep_df.to_csv(sweep_path, index=False)
            print(f"[{datetime.now()}] Sweep results saved to {sweep_path}")

            sum_rows = []
            for (thr, project), g in sweep_df.groupby(["threshold", "project"]):
                delta = g["Delta_D"].to_numpy(dtype=float, copy=False)
                t = stats.ttest_1samp(delta, popmean=0.0, nan_policy="omit")
                if len(g) >= 3:
                    r, p = stats.pearsonr(g["mutation_count"].to_numpy(dtype=float), delta)
                else:
                    r, p = np.nan, np.nan
                sum_rows.append(
                    {
                        "threshold": float(thr),
                        "project": str(project),
                        "n_pairs": int(len(g)),
                        "mean_D_normal": float(g["D_normal"].mean()),
                        "mean_D_tumor": float(g["D_tumor"].mean()),
                        "mean_Delta_D": float(delta.mean()),
                        "std_Delta_D": float(delta.std(ddof=1)) if len(delta) > 1 else 0.0,
                        "t_test_vs0_t": float(t.statistic) if np.isfinite(t.statistic) else np.nan,
                        "t_test_vs0_p": float(t.pvalue) if np.isfinite(t.pvalue) else np.nan,
                        "corr_mutcount_delta_r": float(r) if np.isfinite(r) else np.nan,
                        "corr_mutcount_delta_p": float(p) if np.isfinite(p) else np.nan,
                    }
                )

            sweep_summary = pd.DataFrame(sum_rows).sort_values(["threshold", "mean_Delta_D"])
            sweep_summary_path = os.path.join(OUTPUT_DIR, f"{plot_prefix}__tcga_paired_sweep_summary.csv")
            sweep_summary.to_csv(sweep_summary_path, index=False)
            print(f"[{datetime.now()}] Sweep summary saved to {sweep_summary_path}")

            plt.figure(figsize=(7, 4))
            agg = sweep_df.groupby("threshold")["Delta_D"].agg(["mean", "std", "count"]).reset_index()
            plt.errorbar(agg["threshold"], agg["mean"], yerr=agg["std"], fmt="-o", color="firebrick")
            plt.axhline(0, color="black", linewidth=1)
            plt.xlabel("log2 fold-change threshold")
            plt.ylabel("Mean ΔD (tumor − normal; D_v2 units)")
            plt.title("Paired TCGA corruption robustness vs threshold")
            plt.tight_layout()
            plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__tcga_sweep_mean_delta_d.png"), dpi=300)
            plt.close()

            plt.figure(figsize=(7, 4))
            corrs = []
            for thr, g in sweep_df.groupby("threshold"):
                x = g["mutation_count"].to_numpy(dtype=float)
                y = g["Delta_D"].to_numpy(dtype=float)
                if len(g) >= 3:
                    r, p = stats.pearsonr(x, y)
                else:
                    r, p = np.nan, np.nan
                corrs.append({"threshold": float(thr), "r": float(r) if np.isfinite(r) else np.nan, "p": float(p) if np.isfinite(p) else np.nan})
            cdf = pd.DataFrame(corrs).sort_values("threshold")
            plt.plot(cdf["threshold"], cdf["r"], "-o", color="navy")
            plt.axhline(0, color="black", linewidth=1)
            plt.xlabel("log2 fold-change threshold")
            plt.ylabel("Pearson r(ΔD, mutation_count)")
            plt.title("ΔD–mutation_count coupling vs threshold")
            plt.tight_layout()
            plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__tcga_sweep_corr_vs_thr.png"), dpi=300)
            plt.close()

            print(f"[{datetime.now()}] Sweep plots saved to {FIGURE_DIR}")
            return

        idx = pd.read_csv(TCGA_INDEX_PATH)
        pairs = load_tcga_pairs(TCGA_INDEX_PATH)

        if len(pairs) > 0:
            print(f"[{datetime.now()}] Processing {len(pairs)} TCGA tumor/normal pairs...")

            for _, row in pairs.iterrows():
                project = row["project"]
                pid = row["patient_id"]
                normal_path = os.path.join(DATA_DIR, project, f"{pid}_Normal.json")
                tumor_path = os.path.join(DATA_DIR, project, f"{pid}_Tumor.json")
                if not os.path.exists(normal_path) or not os.path.exists(tumor_path):
                    normal_path = os.path.join(DATA_DIR, f"{pid}_Normal.json")
                    tumor_path = os.path.join(DATA_DIR, f"{pid}_Tumor.json")
                if not os.path.exists(normal_path) or not os.path.exists(tumor_path):
                    print(f"Warning: Missing files for {project} {pid}")
                    continue

                normal_data = load_network(normal_path)
                tumor_data = load_network(tumor_path)

                cm_n = np.array(normal_data.get("cm", []))
                cm_t = np.array(tumor_data.get("cm", []))
                d_normal = compute_d_v2(normal_data)
                d_tumor = compute_d_v2(tumor_data)

                results.append(
                    {
                        "project": project,
                        "patient_id": pid,
                        "normal_sample": row["normal_sample"],
                        "tumor_sample": row["tumor_sample"],
                        "mutation_count": int(row["mutation_count"]),
                        "n_nodes": int(cm_n.shape[0]) if cm_n.ndim == 2 else 0,
                        "edges_normal": int(cm_n.sum()) if cm_n.size else 0,
                        "edges_tumor": int(cm_t.sum()) if cm_t.size else 0,
                        "D_normal": d_normal,
                        "D_tumor": d_tumor,
                        "Delta_D": d_tumor - d_normal,
                    }
                )

            results_df = pd.DataFrame(results)
            results_path = os.path.join(OUTPUT_DIR, OUTPUT_BASENAME)
            results_df.to_csv(results_path, index=False)
            print(f"[{datetime.now()}] Results saved to {results_path}")

            if len(results_df) < 2:
                print(f"[{datetime.now()}] Not enough paired samples for statistical tests.")
                return

            t_stat, p_val = stats.ttest_rel(results_df["D_tumor"], results_df["D_normal"])
            corr, p_corr = stats.pearsonr(results_df["Delta_D"], results_df["mutation_count"])
            print(f"\nStatistical Summary:")
            print(f"  Mean D_normal: {results_df['D_normal'].mean():.2f}")
            print(f"  Mean D_tumor:  {results_df['D_tumor'].mean():.2f}")
            print(f"  Mean Delta_D:  {results_df['Delta_D'].mean():.2f}")
            print(f"  Paired t-test: t={t_stat:.2f}, p={p_val:.2e}")
            print(f"  Correlation (Delta_D vs mutation_count): r={corr:.2f}, p={p_corr:.2e}")

            per_project_rows = []
            for project, g in results_df.groupby("project"):
                delta = g["Delta_D"].to_numpy(dtype=float, copy=False)
                t0 = stats.ttest_1samp(delta, popmean=0.0, nan_policy="omit")
                tp = stats.ttest_rel(g["D_tumor"], g["D_normal"], nan_policy="omit")
                if len(g) >= 3:
                    r, p = stats.pearsonr(g["mutation_count"].to_numpy(dtype=float), delta)
                else:
                    r, p = np.nan, np.nan
                per_project_rows.append(
                    {
                        "project": str(project),
                        "n_pairs": int(len(g)),
                        "mean_D_normal": float(g["D_normal"].mean()),
                        "mean_D_tumor": float(g["D_tumor"].mean()),
                        "mean_Delta_D": float(g["Delta_D"].mean()),
                        "std_Delta_D": float(g["Delta_D"].std(ddof=1)) if len(g) > 1 else 0.0,
                        "paired_t_t": float(tp.statistic) if np.isfinite(tp.statistic) else np.nan,
                        "paired_t_p": float(tp.pvalue) if np.isfinite(tp.pvalue) else np.nan,
                        "t_test_vs0_t": float(t0.statistic) if np.isfinite(t0.statistic) else np.nan,
                        "t_test_vs0_p": float(t0.pvalue) if np.isfinite(t0.pvalue) else np.nan,
                        "corr_mutcount_delta_r": float(r) if np.isfinite(r) else np.nan,
                        "corr_mutcount_delta_p": float(p) if np.isfinite(p) else np.nan,
                    }
                )
            per_project_df = pd.DataFrame(per_project_rows).sort_values("mean_Delta_D")
            per_project_path = os.path.join(OUTPUT_DIR, f"{plot_prefix}__tcga_paired_per_project_summary.csv")
            per_project_df.to_csv(per_project_path, index=False)
            print(f"[{datetime.now()}] Per-project summary saved to {per_project_path}")

            plt.figure(figsize=(10, 6))
            sns.histplot(results_df["Delta_D"], kde=True, color="firebrick")
            plt.axvline(0, color="k", linestyle="--")
            plt.title("Distribution of Algorithmic Corruption ($\\Delta D$) — Paired TCGA")
            plt.xlabel("$\\Delta D = D_{tumor} - D_{normal}$ (bits)")
            plt.tight_layout()
            plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__tcga_delta_d_dist.png"), dpi=300)
            plt.close()

            plt.figure(figsize=(10, 6))
            sns.scatterplot(data=results_df, x="Delta_D", y="mutation_count", hue="project", palette="viridis")
            sns.regplot(data=results_df, x="Delta_D", y="mutation_count", scatter=False, color="gray")
            plt.title(f"Algorithmic Corruption vs Mutation Proxy (r={corr:.2f}) — Paired TCGA")
            plt.xlabel("$\\Delta D$ (structural information loss)")
            plt.ylabel("mutation_count (thresholded nodes)")
            plt.tight_layout()
            plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__tcga_mutcount_corr.png"), dpi=300)
            plt.close()

            plt.figure(figsize=(10, 6))
            order = results_df.groupby("project")["Delta_D"].mean().sort_values().index.tolist()
            sns.boxplot(data=results_df, x="project", y="Delta_D", order=order, color="lightgray")
            sns.stripplot(data=results_df, x="project", y="Delta_D", order=order, color="black", alpha=0.6, size=3)
            plt.axhline(0, color="k", linestyle="--", linewidth=1)
            plt.title("Algorithmic Corruption by Project — Paired TCGA")
            plt.xlabel("")
            plt.ylabel("$\\Delta D$ (bits)")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__delta_d_by_project.png"), dpi=300)
            plt.close()

            plt.figure(figsize=(10, 6))
            sns.scatterplot(data=results_df, x="D_normal", y="D_tumor", hue="project", palette="viridis")
            mn = float(min(results_df["D_normal"].min(), results_df["D_tumor"].min()))
            mx = float(max(results_df["D_normal"].max(), results_df["D_tumor"].max()))
            plt.plot([mn, mx], [mn, mx], linestyle="--", color="gray", linewidth=1)
            plt.title("Paired $D_{tumor}$ vs $D_{normal}$ — TCGA")
            plt.xlabel("$D_{normal}$ (bits)")
            plt.ylabel("$D_{tumor}$ (bits)")
            plt.tight_layout()
            plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__tcga_dv2_tumor_vs_normal.png"), dpi=300)
            plt.close()

            print(f"[{datetime.now()}] Plots saved to {FIGURE_DIR}")
            return

        print(f"[{datetime.now()}] No paired tumor/normal cases found; computing per-sample D_v2.")
        for _, row in idx.iterrows():
            project = row["project"]
            pid = row["patient_id"]
            tissue_type = row["tissue_type"]
            sample_name = row["sample_name"]
            mutation_count = int(row["mutation_count"])

            path = os.path.join(DATA_DIR, project, f"{pid}_{tissue_type}.json")
            if not os.path.exists(path):
                path = os.path.join(DATA_DIR, f"{pid}_{tissue_type}.json")
            if not os.path.exists(path):
                print(f"Warning: Missing file for {project} {pid} {tissue_type}")
                continue

            data = load_network(path)
            cm = np.array(data.get("cm", []))
            d = compute_d_v2(data)

            results.append(
                {
                    "project": project,
                    "patient_id": pid,
                    "tissue_type": tissue_type,
                    "sample_name": sample_name,
                    "mutation_count": mutation_count,
                    "n_nodes": int(cm.shape[0]) if cm.ndim == 2 else 0,
                    "n_edges": int(cm.sum()) if cm.size else 0,
                    "D_v2": d,
                }
            )

        results_df = pd.DataFrame(results)
        results_path = os.path.join(OUTPUT_DIR, OUTPUT_BASENAME)
        results_df.to_csv(results_path, index=False)
        print(f"[{datetime.now()}] Results saved to {results_path}")

        normals = results_df[results_df["tissue_type"] == "Normal"]["D_v2"].dropna()
        tumors = results_df[results_df["tissue_type"] == "Tumor"]["D_v2"].dropna()

        if len(normals) >= 2 and len(tumors) >= 2:
            t_stat, p_val = stats.ttest_ind(normals, tumors, equal_var=False)
            print(f"\nStatistical Summary:")
            print(f"  Mean D_normal: {normals.mean():.2f}")
            print(f"  Mean D_tumor:  {tumors.mean():.2f}")
            print(f"  Welch t-test:  t={t_stat:.2f}, p={p_val:.2e}")
        else:
            print(f"[{datetime.now()}] Not enough samples for tumor/normal comparison.")

        tumor_df = results_df[results_df["tissue_type"] == "Tumor"].dropna(subset=["D_v2", "mutation_count"])
        if len(tumor_df) >= 3:
            corr, p_corr = stats.pearsonr(tumor_df["D_v2"], tumor_df["mutation_count"])
            print(f"  Correlation (D_v2 vs mutation_count) [tumor]: r={corr:.2f}, p={p_corr:.2e}")

        plt.figure(figsize=(10, 6))
        sns.boxplot(data=results_df, x="tissue_type", y="D_v2", color="lightgray")
        sns.stripplot(data=results_df, x="tissue_type", y="D_v2", hue="project", dodge=True, size=3)
        plt.title("D_v2 by tissue type — TCGA pilot")
        plt.xlabel("")
        plt.ylabel("D_v2 (bits)")
        plt.legend([], [], frameon=False)
        plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__tcga_dv2_by_tissue.png"))

        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=tumor_df, x="mutation_count", y="D_v2", hue="project", palette="viridis")
        sns.regplot(data=tumor_df, x="mutation_count", y="D_v2", scatter=False, color="gray")
        plt.title("Tumor D_v2 vs mutation proxy — TCGA pilot")
        plt.xlabel("mutation_count (thresholded nodes)")
        plt.ylabel("D_v2 (bits)")
        plt.savefig(os.path.join(FIGURE_DIR, f"{plot_prefix}__tcga_tumor_dv2_mutcount.png"))

        print(f"[{datetime.now()}] Plots saved to {FIGURE_DIR}")
        return

    df = pd.read_csv(METADATA_PATH)
    print(f"[{datetime.now()}] Processing {len(df)} patients...")

    for _, row in df.iterrows():
        pid = row["PatientID"]
        normal_path = os.path.join(DATA_DIR, f"{pid}_Normal.json")
        tumor_path = os.path.join(DATA_DIR, f"{pid}_Tumor.json")

        if not os.path.exists(normal_path) or not os.path.exists(tumor_path):
            print(f"Warning: Missing files for {pid}")
            continue

        normal_data = load_network(normal_path)
        tumor_data = load_network(tumor_path)

        d_normal = compute_d_v2(normal_data)
        d_tumor = compute_d_v2(tumor_data)

        delta_d = d_tumor - d_normal

        results.append(
            {
                "PatientID": pid,
                "Subtype": row["Subtype"],
                "SurvivalDays": row["SurvivalDays"],
                "MutationCount": row["MutationCount"],
                "D_normal": d_normal,
                "D_tumor": d_tumor,
                "Delta_D": delta_d,
            }
        )

    results_df = pd.DataFrame(results)

    results_path = os.path.join(OUTPUT_DIR, OUTPUT_BASENAME)
    results_df.to_csv(results_path, index=False)
    print(f"[{datetime.now()}] Results saved to {results_path}")

    t_stat, p_val = stats.ttest_rel(results_df["D_normal"], results_df["D_tumor"])
    print(f"\nStatistical Summary:")
    print(f"  Mean D_normal: {results_df['D_normal'].mean():.2f}")
    print(f"  Mean D_tumor:  {results_df['D_tumor'].mean():.2f}")
    print(f"  Mean Delta_D:  {results_df['Delta_D'].mean():.2f}")
    print(f"  Paired t-test: t={t_stat:.2f}, p={p_val:.2e}")

    corr, p_corr = stats.pearsonr(results_df["Delta_D"], results_df["SurvivalDays"])
    print(f"  Correlation (Delta_D vs Survival): r={corr:.2f}, p={p_corr:.2e}")

    plt.figure(figsize=(10, 6))
    sns.histplot(results_df["Delta_D"], kde=True, color="firebrick")
    plt.axvline(0, color="k", linestyle="--")
    plt.title("Distribution of Algorithmic Corruption ($\\Delta D$)")
    plt.xlabel("$\\Delta D = D_{tumor} - D_{normal}$ (Bits)")
    plt.savefig(os.path.join(FIGURE_DIR, "cancer_delta_d_dist.png"))

    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=results_df, x="Delta_D", y="SurvivalDays", hue="Subtype", palette="viridis")
    sns.regplot(data=results_df, x="Delta_D", y="SurvivalDays", scatter=False, color="gray")
    plt.title(f"Algorithmic Corruption vs Survival (r={corr:.2f})")
    plt.xlabel("$\\Delta D$ (Structural Information Loss)")
    plt.ylabel("Survival (Days)")
    plt.savefig(os.path.join(FIGURE_DIR, "cancer_survival_corr.png"))

    print(f"[{datetime.now()}] Plots saved to {FIGURE_DIR}")

if __name__ == "__main__":
    main()
