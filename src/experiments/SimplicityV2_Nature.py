import json
import os
import sys
import numpy as np
import networkx as nx
import glob

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from experiments.Null_Generator_HPC import compute_both, separation
from integration.HierarchyEncoder import HierarchyEncoder
from integration.MotifEncoder import MotifEncoder
from pipeline.Contingency_Monitor import ContingencyMonitor
from stats.Bayes_Factor_Calculator import BayesFactorCalculator
# ComplexityScaler no longer imported: its only use here was
# compute_scaling_exponent, retired in AUDIT04-E (a program length has no
# block size, so D(b) ~ b^alpha is not a question this measure can answer).

def load_network(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

def adjacency_from_edges(nodes, edges):
    n = len(nodes)
    node_map = {name: i for i, name in enumerate(nodes)}
    adj = np.zeros((n, n), dtype=int)
    for src, tgt in edges:
        if src in node_map and tgt in node_map:
            adj[node_map[src], node_map[tgt]] = 1
    return adj

def summarise(results):
    """Aggregate per-network separations into the monitor's inputs. AUDIT04-F.

    Extracted from `main` so that the only part of this script carrying logic
    can be tested; the rest is I/O and orchestration.

    Summarised by ORDER STATISTICS and reported PER MEASURE. No z-scores: the
    monitor refuses `z_score_deg` and requires gap_bits/exceed, and this script
    was the last caller still speaking the retired language, which is how it
    went unnoticed when AUDIT04-E moved Null_Generator_HPC.

    A median gap says how large the typical advantage is in bits; a median
    exceed says where the real network sits in its own null ensemble. Neither
    needs the ensemble to have a shape, which is exactly what the z-score got
    wrong on the degenerate and heavy-tailed nulls.

    `None` is returned for any BDM figure with no measurements behind it --
    networks below pybdm's 4x4 partition floor have no BDM -- rather than 0.0,
    which the monitor would read as a real measurement of no advantage.
    """
    gaps_index = [r['index_set']['gap_bits'] for r in results]
    exceeds_index = [r['index_set']['exceed'] for r in results]
    gaps_bdm = [r['bdm']['gap_bits'] for r in results if r.get('bdm')]
    exceeds_bdm = [r['bdm']['exceed'] for r in results if r.get('bdm')]

    d_bio_vals = [r['D_index_set'] for r in results]
    d_null_vals = [r['index_set']['median_null'] for r in results]
    mean_d_bio = float(np.mean(d_bio_vals))
    mean_d_null = float(np.mean(d_null_vals))
    # AER: efficiency ratio (null / bio). Above 1.0 means the real network is
    # the shorter of the two, against the MEDIAN null rather than the mean.
    aer = mean_d_null / mean_d_bio if mean_d_bio > 0 else 1.0

    # AUDIT04-E: every per-network alpha_diff is None, so there is nothing to
    # average. Reported as None so the monitor receives "not measured" rather
    # than a fabricated 0.0 it would read as a real scaling agreement.
    alphas = [r['alpha_diff'] for r in results if r.get('alpha_diff') is not None]

    return {
        'gap_bits_deg': float(np.median(gaps_index)),
        'exceed_deg': float(np.median(exceeds_index)),
        'gap_bits_bdm': float(np.median(gaps_bdm)) if gaps_bdm else None,
        'exceed_bdm': float(np.median(exceeds_bdm)) if exceeds_bdm else None,
        'gaps_index': gaps_index,
        'aer': aer,
        'scaling_diff': float(np.mean(alphas)) if alphas else None,
        'n': len(results),
        'beats_every_null_index': sum(1 for e in exceeds_index if e == 0.0),
        'beats_every_null_bdm': sum(1 for e in exceeds_bdm if e == 0.0),
    }


def main():
    print("------------------------------------------------")
    print("   Nature Protocol: Simplicity V2 (Real Data)   ")
    print("------------------------------------------------")

    # 1. Load BDM Results (Behavioural Coordinate)
    bdm_path = os.path.join(os.path.dirname(__file__), '../../results/bio/bdm_nature.json')
    if not os.path.exists(bdm_path):
        print(f"Error: BDM results not found at {bdm_path}")
        return

    with open(bdm_path, 'r') as f:
        bdm_data = json.load(f)
    
    # Create lookup for BDM data
    bdm_lookup = {item['network']: item for item in bdm_data}
    
    # 2. Process Networks for Structural Complexity (D_v2)
    processed_dir = os.path.join(os.path.dirname(__file__), '../../data/bio/processed')
    network_files = glob.glob(os.path.join(processed_dir, "*.json"))
    
    results = []
    
    # Limit to first 30 for Contingency Checkpoint (avoid stalling on large networks)
    print("Running on first 30 networks for Level 4 Contingency Checkpoint...")
    for net_file in network_files[:30]:
        net_name = os.path.basename(net_file).replace('.json', '')
        
        # Skip non-networks
        if net_name in ['gate_histogram', 'truth_tables', 'nature_dataset']:
            continue
            
        print(f" > Processing: {net_name}")
        
        # Load Network Data
        net_data = load_network(net_file)
        nodes = net_data.get('nodes', [])
        
        if not nodes:
            print("   [Skipping] No nodes found.")
            continue
            
        # Prefer using CM (Adjacency Matrix) directly
        if 'cm' in net_data:
            adj = np.array(net_data['cm'])
            # Ensure it's square and matches nodes
            if adj.shape[0] != len(nodes):
                print(f"   [Warning] CM shape {adj.shape} mismatch with nodes {len(nodes)}")
                continue
            num_edges = int(np.sum(adj))
        else:
            # Fallback to edges list if available (and is a list)
            edges = net_data.get('edges', [])
            if isinstance(edges, list):
                adj = adjacency_from_edges(nodes, edges)
                num_edges = len(edges)
            else:
                print("   [Error] No valid CM or Edges list found.")
                continue
        
        # Calculate D_v2 (Structural Complexity)
        # 1. Hierarchy Cost
        h_enc = HierarchyEncoder(adj)
        h_res = h_enc.run()
        L_hier = h_res['hierarchy_cost']
        
        # 2. Motif Cost
        m_enc = MotifEncoder(adj)
        m_res = m_enc.run()
        L_motif = m_res['total_cost']
        
        # AUDIT04-F: `min(L_hier, L_motif)` IS THE FORBIDDEN HYBRID.
        #
        # Author decision #96 (2026-09-03) rejected "the cheaper of two
        # encodings with a selector bit" and required ONE explicit, clean
        # algorithmic measure. This line computed exactly that construction and
        # called it D_v2, and it survived the AUDIT04-E sweep because it never
        # went through Universal_D_v2_Encoder at all -- the sweep repointed the
        # encoder, and this file had its own arithmetic.
        #
        # It is also not even a valid code: taking a minimum without paying the
        # selector bit is not a description length, because a decoder handed the
        # number cannot know which scheme produced it.
        #
        # The two declared measures replace it. The two encoder costs are kept
        # as DIAGNOSTICS under their own names, which is what they always were.
        both = compute_both(adj)
        D_index_set = both["index_set"]
        D_bdm = both["bdm"]
        cheaper_encoder = "Hierarchy" if L_hier < L_motif else "Motif"
        
        # AUDIT04-E: the Level-4 scaling exponent is GONE, not zero.
        #
        # It fitted D(b) ~ b^alpha over block sizes, which is meaningful only for
        # a block-decomposed measure. D_v2 was retired to the index-set program
        # length, which has no block size, so the sweep returned Alpha 0.0000 for
        # every network and compute_scaling_exponent now raises.
        #
        # `None` rather than 0.0 on purpose: 0.0 is a legitimate value of a
        # scaling exponent, so writing it here would put a fabricated
        # measurement into a tracked artefact. None says "not measured".
        alpha_bio = None

        # 3. Generate Null Models
        n_nulls = 10
        null_index_scores = []
        null_bdm_scores = []
        
        # Degree-preserving randomization
        # Using networkx directed_edge_swap is robust but slow for many swaps.
        # Alternatively configuration model.
        # Let's use configuration model for strong null.
        in_degrees = [d for n, d in nx.from_numpy_array(adj, create_using=nx.DiGraph).in_degree()]
        out_degrees = [d for n, d in nx.from_numpy_array(adj, create_using=nx.DiGraph).out_degree()]
        
        print(f"   > Generating {n_nulls} null models...", end='', flush=True)
        
        for _ in range(n_nulls):
            # Generate random directed graph with same degree sequence
            # nx.directed_configuration_model can create parallel edges/loops.
            # We want simple graphs if possible, but biological networks have loops.
            # We should try to remove parallel edges to match simple graph constraint if original is simple.
            try:
                G_null = nx.directed_configuration_model(in_degrees, out_degrees, create_using=nx.DiGraph, seed=None)
                # Remove parallel edges (collapse to simple)
                G_null = nx.DiGraph(G_null) 
                # Note: this alters degree distribution slightly if many collisions.
                # For small N it's significant. 
                # Better approach: 10*E swaps.
                
                # Let's use double_edge_swap on the original graph copy
                G_swap = nx.from_numpy_array(adj, create_using=nx.DiGraph)
                nswap = 10 * num_edges
                try:
                    nx.directed_edge_swap(G_swap, nswap=nswap, max_tries=100*nswap)
                except nx.NetworkXError:
                    # Fallback for very small/dense graphs where swaps fail
                    pass
                
                adj_null = nx.to_numpy_array(G_swap)
                
            except Exception:
                # Fallback to Erdos-Renyi if degree preserving fails hard (should not happen often)
                adj_null = np.random.randint(0, 2, adj.shape)
            
            # AUDIT04-F: both declared measures for the null, same as for the
            # real network. The `min(h_null, m_null)` hybrid is gone here too.
            nb = compute_both(adj_null.astype(int))
            null_index_scores.append(nb["index_set"])
            if nb["bdm"] is not None:
                null_bdm_scores.append(nb["bdm"])
            
            # AUDIT04-E: no scaling exponent for the nulls either, same reason.
            # null_alphas stays empty and the summary below reports it as
            # unavailable rather than averaging an empty list to 0.0.

        print(" Done.")
        
        # 4. Separation, per measure. AUDIT04-F.
        #
        # The z-score `(mu - x) / sd` was still here after AUDIT04-E replaced it
        # in Null_Generator_HPC: it rescales a quantity in BITS by the standard
        # deviation of an ensemble, which discards the information the length
        # already carries. Measured on three nulls where the real network beat
        # 0 of 1000 in every case -- identical evidence -- it read 5.07 / 0.00 /
        # 0.31 and would have falsified two of them.
        #
        # `separation` is IMPORTED from Null_Generator_HPC rather than rewritten
        # here; one comparison, one definition.
        sep_index = separation(D_index_set, null_index_scores)
        sep_bdm = (separation(D_bdm, null_bdm_scores)
                   if D_bdm is not None and null_bdm_scores else None)

        # Get Behavioural BDM
        bdm_info = bdm_lookup.get(net_name, {})
        avg_bdm = bdm_info.get('avg_bdm', 0)
        category = bdm_info.get('category', 'Unknown')

        # Scaling stats: UNAVAILABLE, not zero (AUDIT04-E). `np.mean([])` would
        # have produced 0.0 with a RuntimeWarning and written it to a tracked
        # artefact as though it were measured.
        alpha_diff = None

        print(f"   index-set: {D_index_set:.2f} bits | structural BDM: "
              f"{'n/a' if D_bdm is None else format(D_bdm, '.2f')} | "
              f"behavioural BDM: {avg_bdm:.2f}")
        print(f"   index-set vs nulls: gap {sep_index['gap_bits']:.2f} bits, "
              f"{sep_index['exceed']:.1%} of nulls at least as short")
        if sep_bdm is not None:
            print(f"   BDM       vs nulls: gap {sep_bdm['gap_bits']:.2f} bits, "
                  f"{sep_bdm['exceed']:.1%} of nulls at least as short")
        print("   Alpha: NOT MEASURED — the block-size scaling exponent does not "
              "exist for a program length (AUDIT04-E)")
        
        results.append({
            "network": net_name,
            "category": category,
            "measures": ["index_set_program_length", "bdm"],
            "D_index_set": D_index_set,
            "D_bdm": D_bdm,
            "index_set": sep_index,
            "bdm": sep_bdm,
            # Diagnostics, not measures. `cheaper_encoder` records which of the
            # two encoder costs was smaller; it is NOT used to select a value.
            "L_hierarchy": L_hier,
            "L_motif": L_motif,
            "cheaper_encoder": cheaper_encoder,
            "avg_bdm": avg_bdm,
            "nodes": len(nodes),
            "edges": num_edges,
            "alpha_bio": alpha_bio,
            "alpha_diff": alpha_diff
        })
        
    # 3. Save Combined Results
    out_path = os.path.join(os.path.dirname(__file__), '../../results/bio/simplicity_v2_real.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f">> SUCCESS. Saved {len(results)} network profiles to {out_path}")
    print("------------------------------------------------")

    # 4. Level 4 Contingency Check
    print("Running Level 4 Contingency Check...")
    
    # Aggregate Metrics
    if not results:
        print("No results to analyze.")
        return

    summary = summarise(results)
    median_gap_index = summary['gap_bits_deg']
    median_exceed_index = summary['exceed_deg']
    median_gap_bdm = summary['gap_bits_bdm']
    median_exceed_bdm = summary['exceed_bdm']
    gaps_index = summary['gaps_index']
    aer = summary['aer']
    mean_alpha_diff = summary['scaling_diff']
    
    # Bayes Factor: Test if Z-scores come from N(0,1) (Null Hypothesis)
    # H0: Z ~ N(0,1) (Bio is Random)
    # H1: Z ~ N(mu, sigma) (Bio is Distinct)
    # Note: BayesFactorCalculator expects data, null_mean, null_std
    # AUDIT04-F: the Bayes factor now runs on the GAP IN BITS against a null of
    # zero advantage, not on z-scores. The quantity being tested is the same
    # ("is the real network distinguishable from its nulls?") but the input is
    # the algorithmic gap rather than a rescaling of it.
    #
    # A standard deviation appears here and that is legitimate: this is a
    # STATISTICAL TEST, in the same category as the mutual information in
    # Mutual_Information_Analyzer. The directive forbids Shannon and
    # distributional summaries as our MEASURES; it does not forbid statistics
    # computed on top of them. What it forbade in particular -- a z-score
    # DECIDING falsification -- is now done by gap and exceed in the monitor.
    sd_gap = float(np.std(gaps_index)) or 1.0
    bf_res = BayesFactorCalculator.calculate_bayes_factor(gaps_index, 0.0, sd_gap)
    bf01 = bf_res['BF01'] # Evidence for H0 (Randomness)
    
    # DepMap Correlation
    depmap_stats_path = os.path.join(os.path.dirname(__file__), '../../results/cancer/depmap_stats.json')
    if os.path.exists(depmap_stats_path):
        with open(depmap_stats_path, 'r') as f:
            depmap_stats = json.load(f)
        rho = depmap_stats.get('rho', 0.0)
        mi = depmap_stats.get('mi_bits', 0.0)
    else:
        print("Warning: DepMap stats not found. Using defaults.")
        rho = 0.0
        mi = 0.0
    
    metrics = {
        'gap_bits_deg': median_gap_index,
        'exceed_deg': median_exceed_index,
        'gap_bits_bdm': median_gap_bdm,
        'exceed_bdm': median_exceed_bdm,
        'bayes_factor_01': bf01,
        'rho_depmap': rho,
        'mi_depmap_bits': mi,
        'aer': aer,
        'scaling_diff': mean_alpha_diff
    }
    
    monitor_res = ContingencyMonitor.evaluate_checkpoint(metrics)
    
    print(f"Action Code: {monitor_res['action_code']}")
    print(f"Reason: {monitor_res['reason']}")
    
    # Save Report
    report_path = os.path.join(os.path.dirname(__file__), '../../results/bio/Contingency_Report.md')
    with open(report_path, 'w') as f:
        f.write(monitor_res['report_content'])
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    main()
