import os
import re

base_dir = "/Users/alberto/Documents/projects/CausalBoolIntegration"
source_tex = os.path.join(base_dir, "doc/finalpaper/together.tex")
output_tex = os.path.join(base_dir, "doc/finalpaper/together_full.tex")
new_int_paper_dir = os.path.join(base_dir, "doc/newIntPaper")
final_bib = os.path.join(base_dir, "doc/finalpaper/references.bib")
source_bib = os.path.join(base_dir, "doc/newIntPaper/references.bib")

# Mapping Section Title -> Filename
section_map = {
    "Bio-Process Log Level 2": "bioProcessLev2.tex",
    "Programme Plan: Universal Structural Compression": "bioPlanLev-3.md",
    "Bio Process Level 3 \\& 4": "bioProcessLev3.tex",
    "Contingency Plan Evaluation": "Contingency_Plan_Evaluation.md",
    "Contingency Activation Reformulation": "Contingency_Activation_Reformulation.md",
    "Programme Plan: Contingency Activation Reformulation": "bioPlanLev-4.md",
    "Programme Plan: Hybrid Encoding": "bioPlanLev-5.md",
    "Scientific Logbook: Hybrid Encoding": "bioProcessLev5.tex",
    "Programme Plan: Asynchronous Dynamics": "bioPlanLev-6.md",
    "Scientific Logbook: Asynchronous Basin Entropy": "bioProcessLev6.tex",
    "Phase 6 Closure Report": "Phase6_Closure_Report.md",
    "Level 7: Semantic Basin Fidelity": "bioPlanLev-7.md",
    "Scientific Logbook: Semantic Basin Fidelity": "bioProcessLev7.tex",
    "Bio-Process Log: Deterministic Causal Boolean Integration": "bioProcess.tex",
    "Supplementary Documentation": "docProcess.tex",
    "Experimental and Algorithmic Process": "expProcess.tex"
}

def clean_latex_body(content):
    # Extract body if present
    match = re.search(r'\\begin{document}(.*?)\\end{document}', content, re.DOTALL)
    if match:
        body = match.group(1)
    else:
        body = content

    # Remove maketitle, tableofcontents
    body = re.sub(r'\\maketitle', '', body)
    body = re.sub(r'\\tableofcontents', '', body)
    
    # Remove bibliography commands
    body = re.sub(r'\\bibliography\s*\{.*?\}', '', body, flags=re.DOTALL)
    body = re.sub(r'\\bibliographystyle\s*\{.*?\}', '', body, flags=re.DOTALL)
    
    # Remove thebibliography environment
    body = re.sub(r'\\begin{thebibliography}.*?\\end{thebibliography}', '', body, flags=re.DOTALL)
    
    # Fix image paths: remove 'figures/' prefix
    body = re.sub(r'\\includegraphics(\[.*?\])?\{figures/(.*?)\}', r'\\includegraphics\1{\2}', body)
    
    return body

def md_to_latex(content):
    # Split by code blocks to avoid escaping inside them
    parts = re.split(r'(```.*?```)', content, flags=re.DOTALL)
    new_parts = []
    
    for part in parts:
        if part.startswith('```'):
            # Code block: convert to verbatim
            code_content = part[3:-3]
            # Remove language identifier if present
            if '\n' in code_content:
                first_line = code_content.split('\n', 1)[0]
                if re.match(r'^\w+$', first_line.strip()):
                     code_content = code_content.split('\n', 1)[1]
            new_parts.append(f'\\begin{{verbatim}}{code_content}\\end{{verbatim}}')
        else:
            # Text content
            lines = part.split('\n')
            processed_lines = []
            in_list = False
            
            for line in lines:
                # Headers
                header_level = 0
                clean_line = line
                if line.startswith('# '): header_level = 1; clean_line = line[2:]
                elif line.startswith('## '): header_level = 2; clean_line = line[3:]
                elif line.startswith('### '): header_level = 3; clean_line = line[4:]
                
                # List
                is_list = False
                if line.strip().startswith('- ') or line.strip().startswith('* '):
                    is_list = True
                    clean_line = line.strip()[2:]
                
                # Images: ![caption](path)
                img_match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                if img_match:
                    if in_list:
                        processed_lines.append('\\end{itemize}')
                        in_list = False

                    caption = img_match.group(1)
                    path = img_match.group(2)
                    # Strip figures/
                    if path.startswith('figures/'):
                        path = path[8:]
                    
                    processed_lines.append('\\begin{figure}[H]')
                    processed_lines.append('\\centering')
                    processed_lines.append(f'\\includegraphics[width=0.8\\textwidth]{{{path}}}')
                    processed_lines.append(f'\\caption{{{caption}}}')
                    processed_lines.append('\\end{figure}')
                    continue

                # Escape content
                clean_line = clean_line.replace('&', '\\&')
                clean_line = clean_line.replace('%', '\\%')
                clean_line = clean_line.replace('$', '\\$')
                clean_line = clean_line.replace('#', '\\#')
                clean_line = clean_line.replace('_', '\\_')
                
                # Bold/Italic (simple regex)
                clean_line = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', clean_line)
                clean_line = re.sub(r'\*(.*?)\*', r'\\textit{\1}', clean_line)
                
                # Construct output
                if header_level == 1:
                    processed_lines.append(f'\\subsection{{{clean_line}}}')
                elif header_level == 2:
                    processed_lines.append(f'\\subsubsection{{{clean_line}}}')
                elif header_level == 3:
                    processed_lines.append(f'\\paragraph{{{clean_line}}}')
                elif is_list:
                    if not in_list:
                        processed_lines.append('\\begin{itemize}')
                        in_list = True
                    processed_lines.append(f'\\item {clean_line}')
                else:
                    if in_list and not line.strip(): # empty line ends list
                         processed_lines.append('\\end{itemize}')
                         in_list = False
                    
                    processed_lines.append(clean_line)
            
            if in_list:
                processed_lines.append('\\end{itemize}')
            
            new_parts.append('\n'.join(processed_lines))

    return ''.join(new_parts)

def deduplicate_bib(file_path):
    print(f"Deduplicating bibliography: {file_path}")
    if not os.path.exists(file_path):
        print(f"Warning: Bibliography file not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    # Split by @ at start of line
    # Add a newline at start to ensure first entry matches if it starts at line 0
    raw_entries = re.split(r'\n@', '\n' + content)
    
    unique_entries = {}
    
    for raw in raw_entries:
        if not raw.strip():
            continue
        
        # Re-add the @
        entry_str = '@' + raw.strip()
        
        # Extract key
        match = re.match(r'@\w+\s*\{\s*([^,]+),', entry_str)
        if match:
            key = match.group(1).strip()
            if key in unique_entries:
                print(f"Duplicate key found: {key}")
            else:
                unique_entries[key] = entry_str
        else:
            # Maybe a comment or preamble, usually safe to ignore or keep?
            # If it's a comment, we might lose it. But for BibTeX, usually fine.
            print(f"Skipping non-entry block: {entry_str[:50]}...")
            
    with open(file_path, 'w') as f:
        for key, entry in unique_entries.items():
            f.write(entry + "\n\n")
    
    print(f"Deduplication complete. {len(unique_entries)} unique entries.")

def merge_bibliographies():
    print("Merging bibliographies...")
    
    if os.path.exists(source_bib):
        with open(source_bib, 'r') as f:
            source_content = f.read()
        
        # Always read current final_bib to append
        current_final = ""
        if os.path.exists(final_bib):
            with open(final_bib, 'r') as f:
                current_final = f.read()
            
        # Append source to final
        merged_content = current_final + "\n" + source_content
        
        with open(final_bib, 'w') as f:
            f.write(merged_content)
                
        deduplicate_bib(final_bib)
    else:
        print(f"Warning: Source bibliography not found: {source_bib}")

def process():
    merge_bibliographies()
    
    with open(source_tex, 'r') as f:
        lines = f.readlines()
    
    final_lines = []
    
    # Graphicspath injection
    final_lines.append("\\graphicspath{{../../newIntPaper/figures/}{../newIntPaper/figures/}{figures/}}\n")

    # Sort keys by length descending
    sorted_keys = sorted(section_map.keys(), key=len, reverse=True)
    
    # Pre-inject some useful packages
    final_lines.append("\\usepackage{tikz}\n")
    final_lines.append("\\usepackage{float}\n")
    final_lines.append("\\usepackage{caption}\n")
    final_lines.append("\\usepackage{subcaption}\n")
    final_lines.append("\\usepackage{amssymb}\n")

    for line in lines:
        # Fix natbib
        if "\\usepackage{natbib}" in line:
            final_lines.append("\\usepackage[numbers]{natbib}\n")
            continue

        # Detect section
        sec_match = re.search(r'\\section{(.*?)}', line)
        if sec_match:
            full_title = sec_match.group(1)
            current_section = None
            
            # Find best match in map
            for key in sorted_keys:
                if key in full_title:
                    current_section = key
                    break
            
            final_lines.append(line)
            
            if current_section:
                filename = section_map[current_section]
                filepath = os.path.join(new_int_paper_dir, filename)
                
                if os.path.exists(filepath):
                    print(f"Injecting {filename} into section {full_title}")
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    if filename.endswith('.tex'):
                        content = clean_latex_body(content)
                    elif filename.endswith('.md'):
                        content = md_to_latex(content)
                    
                    final_lines.append(content + "\n")
                else:
                    print(f"Warning: {filename} not found for section {full_title}")
            continue

        # Skip placeholder text if we injected content
        if "The PDF content from" in line or "The content from" in line:
            continue
            
        # Skip invalid inputs
        if "\\input{" in line and ".md}" in line:
            continue
            
        # Skip recursive inputs
        if "\\makeatletter" in line or "\\IfFileExists{\\jobname.aux}" in line or "\\makeatother" in line:
            continue
            
        final_lines.append(line)

    with open(output_tex, 'w') as f:
        f.writelines(final_lines)
    
    print(f"Written to {output_tex}")

if __name__ == "__main__":
    process()
