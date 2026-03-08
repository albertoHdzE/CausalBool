import xml.etree.ElementTree as ET
from pathlib import Path
import re

class GINMLParser:
    """
    Parses GINsim GINML files (XML format) into a standardized dictionary.
    """
    
    def parse_file(self, file_path: Path) -> dict:
        """
        Parses a GINML file and returns a dictionary with:
        - nodes: list of node IDs
        - edges: list of dicts {source, target, type}
        - logic: dict mapping node_id -> boolean expression string (for value 1)
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # GINML root is usually <gxl><graph>...
            graph = root.find("graph")
            if graph is None:
                # Try finding graph with namespace or just check if root is graph
                if root.tag == "graph":
                    graph = root
                else:
                    # Sometimes namespaced
                    graph = root.find("{http://www.gupro.de/GXL/gxl-1.0.dtd}graph") # Example namespace, checking wildcards is harder with ET
                    if graph is None:
                        # Fallback: search all children
                        for child in root:
                            if child.tag.endswith("graph"):
                                graph = child
                                break
            
            if graph is None:
                print(f"Error parsing {file_path.name}: No <graph> element found.")
                return None

            nodes = []
            edges = []
            logic = {}
            
            # Parse Nodes
            for node in graph.findall("node"):
                node_id = node.get("id")
                max_val = int(node.get("maxvalue", "1"))
                
                # Check if Boolean (maxvalue=1)
                # If maxvalue > 1, we might skip or log warning.
                # For now, we process them but logic extraction will assume value 1.
                
                nodes.append(node_id)
                
                # Logic
                # GINML stores logic as <value val="1"><exp str="..."/></value>
                # Sometimes multiple values. We focus on val="1" for Boolean activation.
                val_1 = None
                for val in node.findall("value"):
                    if val.get("val") == "1":
                        val_1 = val
                        break
                
                if val_1 is not None:
                    exp = val_1.find("exp")
                    if exp is not None:
                        logic_str = exp.get("str")
                        logic[node_id] = logic_str
                else:
                    # If no rule for 1, maybe it's an input or defaults to 0
                    pass

            # Parse Edges
            for edge in graph.findall("edge"):
                source = edge.get("from")
                target = edge.get("to")
                sign = edge.get("sign", "unknown")
                
                edge_type = "unknown"
                if "positive" in sign or "activation" in sign:
                    edge_type = "activation"
                elif "negative" in sign or "inhibition" in sign:
                    edge_type = "inhibition"
                elif "dual" in sign:
                    edge_type = "dual"
                
                edges.append({
                    "source": source,
                    "target": target,
                    "type": edge_type
                })
                
            return {
                    "name": file_path.stem,
                    "nodes": nodes,
                    "edges": edges,
                    "logic": logic,
                    "meta": {
                        "source_type": "GINML",
                        "file_name": file_path.name
                    }
                }
            
        except Exception as e:
            print(f"Exception parsing GINML {file_path.name}: {e}")
            return None
