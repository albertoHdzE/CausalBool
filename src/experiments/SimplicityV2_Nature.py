import json
import os
import sys
import numpy as np
import networkx as nx
import glob

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from integration.HierarchyEncoder import HierarchyEncoder
from integration.MotifEncoder import MotifEncoder
from pipeline.Contingency_Monitor import ContingencyMonitor
from stats.Bayes_Factor_Calculator import BayesFactorCalculator
from complexity.Scaling_LZ_Tools import ComplexityScaler

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
            print(f"   [Skipping] No nodes found.")
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
                print(f"   [Error] No valid CM or Edges list found.")
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
        
        # D_v2 is the minimum of encoding schemes
        D_v2 = min(L_hier, L_motif)
        encoding_type = "Hierarchy" if L_hier < L_motif else "Motif"
        
        # Compute Scaling Exponent for Bio (Level 4 Check)
        scaling_res = ComplexityScaler.compute_scaling_exponent(adj)
        alpha_bio = scaling_res['alpha'] if scaling_res else 0.0

        # 3. Generate Null Models
        n_nulls = 10
        null_Dv2_scores = []
        null_alphas = []
        
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
                
            except Exception as e:
                # Fallback to Erdos-Renyi if degree preserving fails hard (should not happen often)
                adj_null = np.random.randint(0, 2, adj.shape)
            
            # Compute D_v2 for Null
            h_null = HierarchyEncoder(adj_null).run()['hierarchy_cost']
            m_null = MotifEncoder(adj_null).run()['total_cost']
            null_Dv2_scores.append(min(h_null, m_null))
            
            # Compute Scaling for Null
            s_res = ComplexityScaler.compute_scaling_exponent(adj_null)
            if s_res:
                null_alphas.append(s_res['alpha'])
            
        print(" Done.")
        
        # 4. Compute Z-Score
        mu_null = np.mean(null_Dv2_scores)
        sigma_null = np.std(null_Dv2_scores)
        
        if sigma_null > 0:
            z_score = (mu_null - D_v2) / sigma_null
        else:
            z_score = 0.0
            
        # Get Behavioural BDM
        bdm_info = bdm_lookup.get(net_name, {})
        avg_bdm = bdm_info.get('avg_bdm', 0)
        category = bdm_info.get('category', 'Unknown')

        # Scaling Stats
        null_alpha_mean = np.mean(null_alphas) if null_alphas else 0.0
        alpha_diff = abs(alpha_bio - null_alpha_mean)
        
        print(f"   D_v2: {D_v2:.2f} ({encoding_type}) | BDM: {avg_bdm:.2f}")
        print(f"   Null Mean: {mu_null:.2f} | Z-Score: {z_score:.2f}")
        print(f"   Alpha(Bio): {alpha_bio:.2f} | Alpha(Null): {null_alpha_mean:.2f} | Diff: {alpha_diff:.2f}")
        
        results.append({
            "network": net_name,
            "category": category,
            "D_v2": D_v2,
            "L_hierarchy": L_hier,
            "L_motif": L_motif,
            "encoding_used": encoding_type,
            "avg_bdm": avg_bdm,
            "nodes": len(nodes),
            "edges": num_edges,
            "null_mean": mu_null,
            "null_std": sigma_null,
            "z_score": z_score,
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

    # Extract Z-scores
    z_scores = [r['z_score'] for r in results]
    mean_z = np.mean(z_scores)
    
    # Extract D values for AER
    d_bio_vals = [r['D_v2'] for r in results]
    d_null_vals = [r['null_mean'] for r in results]
    mean_d_bio = np.mean(d_bio_vals)
    mean_d_null = np.mean(d_null_vals)
    
    # AER: Efficiency Ratio (Null / Bio) -> If > 1.0, Bio is simpler (more efficient)
    aer = mean_d_null / mean_d_bio if mean_d_bio > 0 else 1.0
    
    # Scaling Diff
    mean_alpha_diff = np.mean([r['alpha_diff'] for r in results])
    
    # Bayes Factor: Test if Z-scores come from N(0,1) (Null Hypothesis)
    # H0: Z ~ N(0,1) (Bio is Random)
    # H1: Z ~ N(mu, sigma) (Bio is Distinct)
    # Note: BayesFactorCalculator expects data, null_mean, null_std
    bf_res = BayesFactorCalculator.calculate_bayes_factor(z_scores, 0.0, 1.0)
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
        'z_score_deg': mean_z,
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
