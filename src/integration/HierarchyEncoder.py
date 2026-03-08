import numpy as np
import networkx as nx
import math

class HierarchyEncoder:
    def __init__(self, adjacency_matrix):
        self.cm = np.array(adjacency_matrix)
        self.n = self.cm.shape[0]
        self.G = nx.from_numpy_array(self.cm, create_using=nx.DiGraph)
        
    def compute_cost(self, layers, feedback_edges):
        """
        Compute description length using a Layer-based Block Model.
        Cost = L(Layers) + L(Forward_Edges) + L(Feedback_Edges)
        """
        # 1. Cost to describe the layer assignment
        # N nodes, assigned to L layers.
        num_layers = len(layers)
        if num_layers == 0: 
            return 0
        
        # Simple encoding: each node needs log2(num_layers) bits
        layer_assignment_cost = self.n * math.log2(num_layers) if num_layers > 0 else 0
        
        # 2. Cost to describe edges
        # We model connections between layers as independent blocks.
        # Forward: Layer i -> Layer j (where j >= i, allowing self-loops/intra-layer if DAG logic permits, 
        # but typically Hierarchy means i -> j with j > i? 
        # Topological sort ensures j >= i (if we consider condensation). 
        # Intra-SCC edges are "feedback" in the strict sense of "Hierarchy = DAG of nodes"? 
        # No, HierarchyEncoder uses Condensation. 
        # Nodes in same SCC are in same layer. Edges within SCC are cycles.
        # So "Forward" means edges between DIFFERENT layers (scc_u != scc_v).
        # "Feedback" means edges within SCC or back-edges?
        # My compute_layers uses topo sort.
        # Edges (u,v):
        #   if layer_v > layer_u: Forward (Strict)
        #   if layer_v == layer_u: Intra-layer (Recurrent/Feedback)
        #   if layer_v < layer_u: Feedback (Back)
        # The previous code defined feedback as layer_v <= layer_u.
        
        # Let's group edges by (layer_u, layer_v)
        block_edges = {}
        for u, v in self.G.edges():
            lu = -1
            lv = -1
            # Find layers
            for l_idx, nodes in layers.items():
                if u in nodes: lu = l_idx
                if v in nodes: lv = l_idx
            
            if lu == -1 or lv == -1: continue # Should not happen
            
            pair = (lu, lv)
            block_edges[pair] = block_edges.get(pair, 0) + 1
            
        edge_encoding_cost = 0
        
        # Iterate over all possible pairs of layers (including self)
        # But wait, we only need to encode the blocks that HAVE edges? 
        # No, we must specify for EVERY pair (u,v) whether edges exist, or specify which blocks have edges.
        # Sparse block encoding:
        # Sum over all pairs (i, j): log2( Binom( |Li|*|Lj|, k_ij ) )
        
        layer_indices = sorted(layers.keys())
        for i in layer_indices:
            for j in layer_indices:
                # Max possible edges between layer i and j
                n_i = len(layers[i])
                n_j = len(layers[j])
                max_edges = n_i * n_j
                
                # Actual edges
                k = block_edges.get((i, j), 0)
                
                # Cost to specify k edges in this block
                if max_edges > 0:
                    # Using approx log2(nCk)
                    term = math.log2(math.comb(max_edges, k)) if k <= max_edges else 0
                    edge_encoding_cost += term
                    
        return layer_assignment_cost + edge_encoding_cost

    def run(self):
        layers, feedback_edges = self.compute_layers()
        cost = self.compute_cost(layers, feedback_edges)
        
        return {
            "layers": layers,
            "feedback_edges": feedback_edges,
            "hierarchy_cost": cost
        }

    def compute_layers(self):
        """
        Assign nodes to layers via topological sort of the condensation graph.
        Identify feedback edges.
        """
        # Get SCCs
        sccs = list(nx.strongly_connected_components(self.G))
        # Map node -> scc_index
        node_to_scc = {}
        for idx, comp in enumerate(sccs):
            for node in comp:
                node_to_scc[node] = idx
                
        # Condensation graph (DAG of SCCs)
        condensation = nx.condensation(self.G, scc=sccs)
        
        # Topological sort
        try:
            topo_order = list(nx.topological_sort(condensation))
        except nx.NetworkXUnfeasible:
            # Should not happen for condensation graph
            topo_order = list(range(len(sccs)))
            
        # Assign layer = index in topo order
        scc_to_layer = {scc_idx: layer_idx for layer_idx, scc_idx in enumerate(topo_order)}
        
        # Map node -> layer
        node_to_layer = {node: scc_to_layer[node_to_scc[node]] for node in range(self.n)}
        
        # Format layers output
        layers = {}
        for node, layer in node_to_layer.items():
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(node)
            
        # Identify feedback edges
        feedback_edges = []
        for u, v in self.G.edges():
            layer_u = node_to_layer[u]
            layer_v = node_to_layer[v]
            
            # Forward edge: layer_v > layer_u
            # Violation: layer_v <= layer_u
            if layer_v <= layer_u:
                feedback_edges.append((u, v))
                
        return layers, feedback_edges
