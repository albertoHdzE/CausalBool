import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional

class SBMLParser:
    """
    Parses SBML-qual files to extract Boolean network structure.
    """
    
    def __init__(self):
        self.namespaces = {
            'sbml': 'http://www.sbml.org/sbml/level3/version1/core',
            'qual': 'http://www.sbml.org/sbml/level3/version1/qual/version1',
            'mathml': 'http://www.w3.org/1998/Math/MathML'
        }
        # Sometimes namespaces differ slightly (level/version), so we might need to be flexible or strip namespaces.
    
    def parse_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Handle namespaces by stripping them or using the map
            # For simplicity in this implementation, we'll try to find elements ignoring namespace if possible
            # or use the defined ones.
            
            model = root.find('.//{http://www.sbml.org/sbml/level3/version1/core}model')
            if model is None:
                # Try without namespace or find any model
                model = root.find('model')
                if model is None:
                    # Try searching all children
                    for child in root:
                        if child.tag.endswith('model'):
                            model = child
                            break
            
            if model is None:
                print(f"Error: No model element found in {file_path.name}")
                return None
                
            model_id = model.get('id')
            if not model_id or model_id in ["model_id", "model", "Model"]:
                model_id = file_path.stem
            
            # 1. Extract Nodes (Qualitative Species)
            nodes = []
            species_list = model.find('.//{http://www.sbml.org/sbml/level3/version1/qual/version1}listOfQualitativeSpecies')
            if species_list is None:
                # Try finding by tag name ending with...
                for elem in model.iter():
                    if elem.tag.endswith('listOfQualitativeSpecies'):
                        species_list = elem
                        break
            
            if species_list is not None:
                for sp in species_list:
                    sp_id = sp.get('{http://www.sbml.org/sbml/level3/version1/qual/version1}id') or sp.get('id')
                    if sp_id:
                        nodes.append(sp_id)
            
            if not nodes:
                print(f"Warning: No qualitative species found in {file_path.name}")
                return None
                
            # 2. Extract Transitions (Logic)
            logic = {}
            transitions_list = model.find('.//{http://www.sbml.org/sbml/level3/version1/qual/version1}listOfTransitions')
            if transitions_list is None:
                 for elem in model.iter():
                    if elem.tag.endswith('listOfTransitions'):
                        transitions_list = elem
                        break
            
            if transitions_list is not None:
                for trans in transitions_list:
                    # Get output species
                    output_list = trans.find('.//{http://www.sbml.org/sbml/level3/version1/qual/version1}listOfOutputs')
                    if output_list is None:
                        for elem in trans:
                            if elem.tag.endswith('listOfOutputs'):
                                output_list = elem
                                break
                    
                    target = None
                    if output_list is not None:
                        for out in output_list:
                            # Assuming single output for boolean rule usually
                            target = out.get('{http://www.sbml.org/sbml/level3/version1/qual/version1}qualitativeSpecies') or out.get('qualitativeSpecies')
                            break # Just take the first one
                    
                    if not target:
                        continue
                        
                    # Get Function Terms
                    func_terms = trans.findall('.//{http://www.sbml.org/sbml/level3/version1/qual/version1}functionTerm')
                    if not func_terms:
                         # try finding generic
                         for elem in trans:
                             if elem.tag.endswith('functionTerm'):
                                 func_terms.append(elem)
                    
                    # We need to construct the logic string.
                    # Usually SBML-qual defines a defaultTerm (usually 0) and functionTerms (if condition -> result).
                    # For Boolean, usually result is 1.
                    # So the rule is OR(term1_condition, term2_condition, ...) where result=1.
                    
                    or_terms = []
                    
                    for term in func_terms:
                        result_level = term.get('{http://www.sbml.org/sbml/level3/version1/qual/version1}resultLevel') or term.get('resultLevel')
                        if result_level != '1':
                            continue # We only care about what makes it 1 (True)
                            
                        # Parse MathML condition
                        math = term.find('.//{http://www.w3.org/1998/Math/MathML}math')
                        if math is None:
                             for elem in term:
                                 if elem.tag.endswith('math'):
                                     math = elem
                                     break
                        
                        if math is not None:
                            # Parse MathML to boolean string
                            condition = self._parse_mathml(math)
                            if condition:
                                or_terms.append(condition)
                                
                    if or_terms:
                        if len(or_terms) == 1:
                            logic[target] = or_terms[0]
                        else:
                            logic[target] = f"OR({', '.join(or_terms)})"
                    else:
                        # Check default term, maybe it's 1?
                        default_term = trans.find('.//{http://www.sbml.org/sbml/level3/version1/qual/version1}defaultTerm')
                        if default_term is None:
                            for elem in trans:
                                if elem.tag.endswith('defaultTerm'):
                                    default_term = elem
                                    break
                        
                        if default_term is not None:
                            res = default_term.get('{http://www.sbml.org/sbml/level3/version1/qual/version1}resultLevel') or default_term.get('resultLevel')
                            if res == '1':
                                logic[target] = "TRUE" # Constant 1
                            else:
                                logic[target] = "FALSE" # Constant 0 (implicit if no rule makes it 1)

            # Assign FALSE/INPUT to nodes without rules
            for node in nodes:
                if node not in logic:
                    logic[node] = "INPUT" # Assume input if no transition targets it? 
                    # Or maybe it's just constant 0.
                    # For now, let's mark as INPUT to be safe, GRNLoader handles it.

            return {
                "name": model_id,
                "nodes": nodes,
                "logic": logic,
                "source": "BioModels",
                "description": f"Imported from {file_path.name}"
            }
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _parse_mathml(self, element) -> str:
        # Simple recursive MathML parser for Boolean logic
        # Supported tags: apply, and, or, not, eq, ci (identifier), cn (number), true, false
        
        # Find the first child usually (the operator or value)
        # But <math> usually contains one <apply> or <ci>
        
        if element.tag.endswith('math'):
            if len(element) > 0:
                return self._parse_mathml(element[0])
            return ""

        tag = element.tag.split('}')[-1] # strip namespace
        
        if tag == 'apply':
            children = list(element)
            if not children:
                return ""
            op_elem = children[0]
            op = op_elem.tag.split('}')[-1]
            args = [self._parse_mathml(c) for c in children[1:]]
            
            if op == 'and':
                return f"AND({', '.join(args)})"
            elif op == 'or':
                return f"OR({', '.join(args)})"
            elif op == 'not':
                return f"NOT({args[0]})"
            elif op == 'eq':
                # Equality, e.g. A == 1
                # If checking if A is 1, return A. If A is 0, return NOT(A).
                # args[0] is variable, args[1] is value
                var = args[0]
                val = args[1]
                if val == '1':
                    return var
                elif val == '0':
                    return f"NOT({var})"
                else:
                    return f"EQ({var}, {val})"
            elif op == 'geq' or op == 'gt':
                 # Threshold logic: A >= 1 -> A
                 var = args[0]
                 val = args[1]
                 if val == '1' or val == '0': # Simple boolean assumption
                     return var
                 return f"{op.upper()}({var}, {val})"
            else:
                return f"{op.upper()}({', '.join(args)})"
                
        elif tag == 'ci':
            return element.text.strip()
        elif tag == 'cn':
            return element.text.strip()
        elif tag == 'true':
            return "TRUE"
        elif tag == 'false':
            return "FALSE"
            
        return ""

if __name__ == "__main__":
    # Test on a file
    import sys
    if len(sys.argv) > 1:
        parser = SBMLParser()
        res = parser.parse_file(Path(sys.argv[1]))
        import json
        print(json.dumps(res, indent=2))
