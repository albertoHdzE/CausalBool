import re
from pathlib import Path
from typing import Dict, List, Any, Optional

class BNetParser:
    """
    Parses .bnet files (PyBoolNet format) to extract Boolean network structure.
    Format:
    targets, factors
    Gene1, formula1
    Gene2, formula2
    ...
    """
    
    def __init__(self):
        pass
        
    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.parse_string(content, file_path.stem)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_string(self, content: str, model_name: str) -> Optional[Dict[str, Any]]:
        lines = content.strip().splitlines()
        nodes = []
        rules = {}
        
        # First pass: collect nodes
        for line in lines:
            line = line.strip()
            if not line or line.startswith("targets,"):
                continue
            
            # Split by first comma
            parts = line.split(",", 1)
            if len(parts) != 2:
                continue
            
            node = parts[0].strip()
            formula = parts[1].strip()
            nodes.append(node)
            rules[node] = formula
            
        if not nodes:
            return None
            
        # Second pass: extract edges
        edges = []
        
        # Regex to find tokens that might be nodes
        # We match words and check if they are in the node list
        # This handles cases where a substring might match (e.g. Gene1 vs Gene10)
        # by matching word boundaries or sorting nodes by length desc
        
        # Better approach: Use regex for words \b\w+\b and check intersection with nodes set
        node_set = set(nodes)
        
        for target, formula in rules.items():
            # Find all potential identifiers
            tokens = re.findall(r'[a-zA-Z0-9_]+', formula)
            
            # Filter tokens that are valid nodes
            sources = set(tokens) & node_set
            
            for source in sources:
                # Naive sign detection: check if "!" immediately precedes the source
                # This is not perfect for complex clauses but sufficient for dependency graph
                # For exact logic, we need a full parser, but for now we just need the graph structure
                
                # Check for negative regulation
                # Look for !source in formula
                # We need to be careful about substrings (e.g. !Gene1 matching !Gene10)
                # Use regex with boundary
                is_negative = bool(re.search(r'!\s*\b' + re.escape(source) + r'\b', formula))
                
                edge_type = "inhibition" if is_negative else "activation"
                # Note: "activation" is default if not explicitly negative. 
                # Complex logic might have both or neither clear.
                # For structural analysis, existence of edge is key.
                
                edges.append({
                    "source": source,
                    "target": target,
                    "type": edge_type
                })
                
        return {
            "name": model_name,
            "nodes": nodes,
            "edges": edges,
            "rules": rules # Store raw rules for potential future use
        }
