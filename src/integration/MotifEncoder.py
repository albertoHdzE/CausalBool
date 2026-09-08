import numpy as np
import networkx as nx
from itertools import combinations
import math

class MotifEncoder:
    def __init__(self, adjacency_matrix):
        self.cm = np.array(adjacency_matrix)
        self.n = self.cm.shape[0]
        self.G = nx.from_numpy_array(self.cm, create_using=nx.DiGraph)
        
    def run(self):
        """
        Main execution method.
        """
        instances = self.find_motifs()
        motif_cost = self.compute_cost(instances)
        
        # Calculate residual cost (edges not in motifs)
        # 1. Identify all edges covered by motifs
        covered_edges = set()
        for m_type, motif_list in instances.items():
            for nodes in motif_list:
                subg = self.G.subgraph(nodes)
                for u, v in subg.edges():
                    covered_edges.add((u, v))
        
        # 2. Total edges
        all_edges = set(self.G.edges())
        
        # 3. Residual edges
        residual_edges = all_edges - covered_edges
        
        # 4. Residual cost: Simple edge list encoding
        # Each edge costs log2(N^2) = 2*log2(N)
        # Or log2(N*(N-1)) for directed without self-loops
        if self.n > 1:
            edge_cost_bits = math.log2(self.n * self.n)
        else:
            edge_cost_bits = 0
            
        residual_cost = len(residual_edges) * edge_cost_bits
        
        return {
            "instances": instances,
            "motif_cost": motif_cost,
            "residual_cost": residual_cost,
            "total_cost": motif_cost + residual_cost
        }

    # The DECLARED catalogue. compute_cost charges log2(len(MOTIF_CATALOGUE)) to
    # name a type, so this must be the set a decoder can read -- not the set that
    # happens to be non-empty in one network. Making the price depend on which
    # types occurred is the frequency coupling AUDIT04-E removed.
    MOTIF_CATALOGUE = ("FFL", "FeedbackLoop", "Other")

    def find_motifs(self):
        """
        Enumerate 3-node motifs.
        """
        instances = {name: [] for name in self.MOTIF_CATALOGUE}
        
        # Iterate over all 3-node combinations
        for nodes in combinations(range(self.n), 3):
            subg = self.G.subgraph(nodes)
            num_edges = subg.number_of_edges()
            
            if num_edges == 3:
                # Check for FFL vs Feedback
                if nx.is_directed_acyclic_graph(subg):
                    # FFL is a DAG with 3 edges (transitive triad)
                    instances["FFL"].append(nodes)
                else:
                    # Feedback loop (cycle of length 3)
                    # A cycle of 3 nodes with 3 edges is a feedback loop
                    # Need to verify it's a simple cycle
                    try:
                        cycles = list(nx.simple_cycles(subg))
                        if len(cycles) > 0 and len(cycles[0]) == 3:
                            instances["FeedbackLoop"].append(nodes)
                    except:
                        pass
                        
        return instances

    def compute_cost(self, instances):
        """Bits to write down every motif instance. NO FREQUENCY TERM.

        AUDIT04-E, author directive 2026-09-07: no Shannon quantity may serve as
        one of our complexity measures.

        WHAT THIS WAS:

            p = count / total_motifs
            type_entropy -= p * math.log2(p)        # Shannon
            return total_motifs * (location_cost + type_entropy)

        The docstring said "a description length cost based on motif FREQUENCY",
        which names the defect exactly. A frequency-weighted code is the cost
        under a distribution over an ENSEMBLE of networks; a description length
        is the cost of writing down THIS network. The difference is not
        cosmetic -- an entropy term makes the cost of a motif depend on how
        often OTHER motifs occur, so adding an unrelated motif elsewhere in the
        graph changes the price of this one.

        WHAT IT IS NOW. Naming one of K motif types costs log2(K) bits, exactly
        as the twelve-family gate catalogue charges log2(12) for a gate
        (src/description_lengths.py, node_description_cost). K is the size of
        the DECLARED catalogue, not the number of types that happen to appear,
        because a decoder must be able to read any catalogue member.

        Both remaining terms are enumerative code lengths -- bits to name one
        object among a counted set -- which is a length in a declared language
        and not a distributional quantity.
        """
        total_motifs = sum(len(v) for v in instances.values())
        if total_motifs == 0:
            return 0

        # WHERE: which 3 of n nodes carry this instance.
        location_cost = math.log2(math.comb(self.n, 3)) if self.n >= 3 else 0.0

        # WHICH: an index into the declared catalogue. Flat, frequency-free.
        catalogue_size = len(self.MOTIF_CATALOGUE)
        type_cost = math.log2(catalogue_size) if catalogue_size > 1 else 0.0

        # HOW MANY: self-delimiting, so the decoder knows when to stop reading.
        count_cost = 2.0 * math.log2(total_motifs + 1) + 1.0

        return count_cost + total_motifs * (location_cost + type_cost)
