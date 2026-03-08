
import json
import numpy as np
import zlib
import gzip
import bz2
import lzma
import os
import sys
from pybdm import BDM
from scipy.stats import entropy

# Add src path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def shannon_entropy(bitstring):
    """Computes Shannon entropy of the bitstring."""
    if len(bitstring) == 0:
        return 0.0
    p = np.sum(bitstring) / len(bitstring)
    if p == 0 or p == 1:
        return 0.0
    return -p * np.log2(p) - (1-p) * np.log2(1-p)

def compression_ratio(bitstring, method='gzip'):
    """
    Computes compression ratio: CompressedSize / OriginalSize.
    Lower is more compressible (simpler).
    """
    data = bytes(bitstring)
    if method == 'gzip':
        compressed = gzip.compress(data)
    elif method == 'bz2':
        compressed = bz2.compress(data)
    elif method == 'lzma':
        compressed = lzma.compress(data)
    elif method == 'zlib':
        compressed = zlib.compress(data)
    else:
        return 1.0
        
    return len(compressed) / len(data)

def main():
    print("Loading Truth Tables...")
    tt_data = load_json('data/bio/processed/truth_tables.json')
    
    # Initialize BDM
    bdm = BDM(ndim=1)
    
    # Load essentiality data for correlation
    networks = ["lambda_phage", "lac_operon", "yeast_cell_cycle", "tcell_activation"]
    essentiality_map = {}
    for net in networks:
        try:
            net_data = load_json(f'data/bio/processed/{net}.json')
            if 'essentiality' in net_data:
                essentiality_map[net] = net_data['essentiality']
        except:
            pass
            
    results = []
    
    print(f"{'Network':<20} | {'Gene':<10} | {'k':<3} | {'Len':<5} | {'Ent':<5} | {'BDM':<10} | {'Gzip':<6} | {'Ess':<3}")
    print("-" * 90)
    
    for net, genes in tt_data.items():
        ess_data = essentiality_map.get(net, {})
        
        for gene_entry in genes:
            gene = gene_entry['gene']
            k = gene_entry['k']
            tt = gene_entry['tt']
            
            if isinstance(tt, str): # Input, TooBig, MissingRule
                continue
                
            tt_arr = np.array(tt, dtype=int)
            length = len(tt_arr)
            
            # 1. Entropy
            ent = shannon_entropy(tt_arr)
            
            # 2. BDM
            # If length is very small, BDM might return 0 or error if dataset is not covered?
            # pybdm handles this usually.
            try:
                if length < 2:
                    val_bdm = 0
                else:
                    val_bdm = bdm.bdm(tt_arr)
            except Exception as e:
                # print(f"BDM Error {net}-{gene}: {e}")
                val_bdm = 0.0
                
            # 3. Compression (Gzip)
            # Gzip adds header overhead. For small strings it's useless.
            # But let's record it.
            # We compress the BYTES of 0s and 1s.
            comp_ratio = compression_ratio(tt_arr.tolist(), method='zlib') # zlib has less header than gzip
            
            is_essential = ess_data.get(gene, -1)
            
            results.append({
                'network': net,
                'gene': gene,
                'k': k,
                'len': length,
                'entropy': ent,
                'bdm': val_bdm,
                'comp_ratio': comp_ratio,
                'essential': is_essential
            })
            
            print(f"{net:<20} | {gene:<10} | {k:<3} | {length:<5} | {ent:<5.2f} | {val_bdm:<10.2f} | {comp_ratio:<6.2f} | {is_essential:<3}")

    # Analysis
    print("\n--- Analysis ---")
    
    # Filter valid essentiality
    valid_ess = [r for r in results if r['essential'] != -1]
    
    if valid_ess:
        # Concatenated Analysis
        print("\n--- Concatenated Complexity (Network Genome) ---")
        
        # Group by Network
        grouped = {}
        for r in valid_ess:
            net = r['network']
            if net not in grouped: grouped[net] = {'ess': [], 'non': []}
            if r['essential'] == 1:
                grouped[net]['ess'].extend(tt_data[net][next(i for i,x in enumerate(tt_data[net]) if x['gene'] == r['gene'])]['tt'])
            else:
                grouped[net]['non'].extend(tt_data[net][next(i for i,x in enumerate(tt_data[net]) if x['gene'] == r['gene'])]['tt'])
        
        print(f"{'Network':<20} | {'Ess(Len)':<8} | {'Ratio':<6} | {'BDM':<6} | {'<k>':<4} | {'Non(Len)':<8} | {'Ratio':<6} | {'BDM':<6} | {'<k>':<4}")
        print("-" * 100)
        
        for net, data in grouped.items():
            ess_bits = data['ess']
            non_bits = data['non']
            
            if not ess_bits or not non_bits:
                continue
                
            # Compress
            ess_ratio = compression_ratio(ess_bits, method='zlib')
            non_ratio = compression_ratio(non_bits, method='zlib')
            
            # Use BDM on concatenated string if long enough
            # We split into chunks for BDM if needed, pybdm handles it.
            try:
                # BDM usually returns total bits. Normalize by length.
                ess_bdm_val = bdm.bdm(np.array(ess_bits, dtype=int))
                non_bdm_val = bdm.bdm(np.array(non_bits, dtype=int))
                
                ess_bdm_density = ess_bdm_val / len(ess_bits)
                non_bdm_density = non_bdm_val / len(non_bits)
            except:
                ess_bdm_density = 0
                non_bdm_density = 0
            
            # Mean k
            # We need to re-scan to find k for these genes
            # This is inefficient but fine for small data
            ess_ks = [x['k'] for x in tt_data[net] if x['gene'] in [r['gene'] for r in valid_ess if r['essential']==1 and r['network']==net]]
            non_ks = [x['k'] for x in tt_data[net] if x['gene'] in [r['gene'] for r in valid_ess if r['essential']==0 and r['network']==net]]
            
            mean_k_ess = np.mean(ess_ks) if ess_ks else 0
            mean_k_non = np.mean(non_ks) if non_ks else 0
            
            print(f"{net:<20} | {len(ess_bits):<5} | {ess_ratio:<6.2f} | {ess_bdm_density:<6.2f} | {mean_k_ess:<4.1f} | {len(non_bits):<5} | {non_ratio:<6.2f} | {non_bdm_density:<6.2f} | {mean_k_non:<4.1f}")
            
        print("\nNote: Ratio > 1.0 means overhead. BDM Density ~ 1.0 is random, < 1.0 is simple.")

if __name__ == "__main__":
    main()
