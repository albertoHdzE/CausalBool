import xml.etree.ElementTree as ET
from pathlib import Path

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
            # AUDIT03-C. `max_val` used to be parsed and thrown away, under a
            # comment conceding the problem: "we might skip or log warning. For
            # now, we process them but logic extraction will assume value 1."
            #
            # That approximation is not small. Measured BY THIS PARSER over all
            # 178 files in data/bio/raw, which all parse:
            #   582 of 5882 nodes (9.9 per cent) declare maxvalue > 1;
            #   108 of 178 files (60.7 per cent) contain at least one;
            #   304 nodes actually carry higher-level rules that are DISCARDED.
            # (A grep over data/ gives 668/6198 because it also counts elements
            # that are not <node>; the figures above are what is parsed.)
            #
            # GINML gives a multi-valued node a SEPARATE rule per level, so
            # keeping only val="1" keeps the condition for reaching level >= 1
            # and discards the rest of its dynamics. The model then enters the
            # corpus looking Boolean, and nothing downstream could tell that it
            # is not.
            #
            # The parse is deliberately NOT refused -- these models are still
            # usable as a Boolean approximation, and refusing would silently
            # shrink the corpus by 61 per cent of its GINML files. Instead the
            # approximation is made visible and countable.
            node_max_values = {}
            multivalued_nodes = []
            discarded_value_rules = {}

            # Parse Nodes
            for node in graph.findall("node"):
                node_id = node.get("id")
                max_val = int(node.get("maxvalue", "1"))
                node_max_values[node_id] = max_val
                if max_val > 1:
                    multivalued_nodes.append(node_id)

                nodes.append(node_id)

                # GINML stores logic as <value val="N"><exp str="..."/></value>,
                # one element per level. We keep val="1" as the Boolean
                # activation condition and RECORD the levels dropped.
                val_1 = None
                dropped = []
                for val in node.findall("value"):
                    v = val.get("val")
                    if v == "1":
                        val_1 = val
                    elif v not in (None, "0"):
                        dropped.append(v)

                if dropped:
                    discarded_value_rules[node_id] = sorted(dropped)

                if val_1 is not None:
                    exp = val_1.find("exp")
                    if exp is not None:
                        logic_str = exp.get("str")
                        logic[node_id] = logic_str
                else:
                    # If no rule for 1, maybe it's an input or defaults to 0
                    pass

            # Warn ONCE per file, not once per node: a per-node warning over
            # this corpus would print 668 lines and be ignored.
            if multivalued_nodes:
                print(f"WARNING {file_path.name}: {len(multivalued_nodes)} of "
                      f"{len(nodes)} nodes are multi-valued (maxvalue > 1); "
                      f"binarised to the val=\"1\" rule. "
                      f"{len(discarded_value_rules)} node(s) had higher-level "
                      f"rules discarded.")

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
                    "node_max_values": node_max_values,
                    "meta": {
                        "source_type": "GINML",
                        "file_name": file_path.name,
                        # Everything a consumer needs to decide whether this
                        # model is safe for a Boolean analysis, without
                        # re-reading the XML.
                        "is_multivalued": bool(multivalued_nodes),
                        "multivalued_nodes": multivalued_nodes,
                        "n_multivalued": len(multivalued_nodes),
                        "discarded_value_rules": discarded_value_rules,
                        "binarisation": ("val=1 rule kept; higher levels dropped"
                                         if multivalued_nodes else "none needed"),
                    }
                }
            
        except Exception as e:
            print(f"Exception parsing GINML {file_path.name}: {e}")
            return None
