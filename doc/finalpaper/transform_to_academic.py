import os
import re

# Paths
BASE_DIR = "/Users/alberto/Documents/projects/CausalBoolIntegration/doc"
FINAL_DIR = os.path.join(BASE_DIR, "finalpaper")
SECTIONS_DIR = os.path.join(FINAL_DIR, "sections")

# Source files mapping to academic sections
SOURCES = {
    "introduction": "newIntPaper/bioProcessLev2.tex",  # Introduction / Motivation
    "theory": "newIntPaper/docProcess.tex",  # Theoretical Framework
    "methods": "newIntPaper/expProcess.tex", # Methods / Algorithms
    "results_structural": "newIntPaper/bioProcessLev3.tex", # Results: Structural Universality
    "results_hybrid": "newIntPaper/bioProcessLev5.tex", # Results: Hybrid Encoding
    "results_dynamics": "newIntPaper/bioProcessLev6.tex", # Results: Asynchronous Dynamics
    "results_semantic": "newIntPaper/bioProcessLev7.tex", # Results: Semantic Fidelity
    "discussion": "newIntPaper/Phase6_Closure_Report.md", # Discussion
}

def merge_bibliographies(source_bib, target_bib):
    """
    Merges entries from source_bib into target_bib if they don't exist in target_bib.
    """
    if not os.path.exists(source_bib):
        print(f"Source bib {source_bib} not found. Skipping merge.")
        return

    with open(target_bib, 'r') as f:
        target_content = f.read()

    with open(source_bib, 'r') as f:
        source_content = f.read()

    # Simple regex to find citation keys: @type{key,
    existing_keys = set(re.findall(r'@\w+\{([^,]+),', target_content))
    
    source_keys = re.findall(r'@\w+\{([^,]+),', source_content)
    
    # Find which keys are missing in target
    missing_keys = set(source_keys) - existing_keys
    
    if not missing_keys:
        print("No new citations to merge.")
        return

    print(f"Merging {len(missing_keys)} new citations from {source_bib}...")
    
    # Split source by @ at start of line
    entries = re.split(r'(?m)^@', source_content)
    
    with open(target_bib, 'a') as f:
        f.write('\n% Merged from newIntPaper/references.bib\n')
        for entry in entries:
            if not entry.strip(): continue
            
            # Extract key
            match = re.search(r'^\w+\{([^,]+),', entry)
            if match:
                key = match.group(1)
                if key in missing_keys:
                    f.write('@' + entry.strip() + '\n\n')

def clean_latex_content(content, section_name, downgrade_headers=0, remove_title_sections=False):
    # Remove preamble (everything before \begin{document})
    if "\\begin{document}" in content:
        match = re.search(r'\\begin{document}(.*?)\\end{document}', content, re.DOTALL)
        if match:
            content = match.group(1)
    
    # Remove maketitle, tableofcontents, abstract (unless it's the abstract section)
    content = re.sub(r'\\maketitle', '', content)
    content = re.sub(r'\\tableofcontents', '', content)
    content = re.sub(r'\\begin{abstract}.*?\\end{abstract}', '', content, flags=re.DOTALL)
    content = re.sub(r'\\date\{.*?\}', '', content)
    content = re.sub(r'\\author\{.*?\}', '', content)
    content = re.sub(r'\\title\{.*?\}', '', content)
    
    # Remove JIRA tickets (TSK-XXX, EPIC-XXX)
    content = re.sub(r'TSK-[A-Z]+-[A-Z]+-\d+', '', content)
    content = re.sub(r'EPIC-[A-Z]+-[A-Z]+', '', content)
    
    # Remove informal logbook headers and sections
    content = re.sub(r'\\section\{Bio-Process Log.*?\}', r'\\section{Introduction}', content)
    content = re.sub(r'\\section\{Programme Plan.*?\}', '', content)
    content = re.sub(r'\\section\{Artifacts\}', '', content)
    content = re.sub(r'\\section\*?\{Phase 3 Verification Log\}', '', content)
    
    # Rename Phases to Academic Sections
    content = re.sub(r'\\section\{Phase 1: Advanced Data Curation\}', r'\\section{Dataset Construction}', content)
    content = re.sub(r'\\section\{Phase 2: Metric Implementation\}', r'\\section{Structural Metrics}', content)
    content = re.sub(r'\\section\{Phase 3 Completion: (.*?)\}', r'\\subsection{\1}', content)
    content = re.sub(r'\\section\{Phase 5: Trade-Off.*?\}', r'\\subsection{The Edge of Chaos: Phase Transitions}', content)

    # Specific cleanups for Discussion (Phase 6 Report)
    if section_name == "discussion":
        content = re.sub(r'\\(sub)*section\{Phase 6 Closure Report.*?\}', '', content)
        content = re.sub(r'\\textbf\{Date:\}.*', '', content)
        content = re.sub(r'\\textbf\{Project:\}.*', '', content)
        content = re.sub(r'\\textbf\{Phase:\}.*', '', content)
        content = re.sub(r'\\subsection\{1\. Executive Summary\}', r'\\subsection{Summary of Findings}', content)
        content = re.sub(r'\\subsection\{2\. Key Metrics (\\&|&) Achievements\}', r'\\subsection{Validation of Theoretical Predictions}', content)
        content = re.sub(r'\\subsection\{3\. Deliverables\}', '', content)
        content = re.sub(r'\\subsection\{4\. Lessons Learned\}', r'\\subsection{Methodological Implications}', content)
        content = re.sub(r'\\subsection\{5\. Recommendations for Phase 7\}', r'\\subsection{Future Directions}', content)
        content = re.sub(r'\\subsection\{6\. Approval\}', '', content)
        content = re.sub(r'\\textbf\{Project Sponsor Sign-off:\}.*', '', content, flags=re.DOTALL)
        content = re.sub(r'\[ x \] Approved for Phase 7 Transition\.', '', content)

    # Remove specific jargon lines (metadata headers)
    content = re.sub(r'\\textbf{Owner}:.*', '', content)
    content = re.sub(r'\\textbf{Status}:.*', '', content)
    content = re.sub(r'\\textbf{Target}:.*', '', content)
    content = re.sub(r'\\textbf{Document ID}:.*', '', content)
    content = re.sub(r'\\textbf{Timestamp}:.*', '', content)
    content = re.sub(r'\\textbf{Verification Method}:.*', '', content)
    content = re.sub(r'\\textbf{Rationale}:.*', '', content)
    content = re.sub(r'\\textbf{Action}:.*', '', content)

    # Fix image paths: remove 'figures/' prefix
    content = re.sub(r'\\includegraphics(\[.*?\])?\{figures/(.*?)\}', r'\\includegraphics\1{\2}', content)
    
    # Remove bibliography commands (handled in main file)
    content = re.sub(r'\\bibliography\{.*?\}', '', content)
    content = re.sub(r'\\bibliographystyle\{.*?\}', '', content)
    content = re.sub(r'\\begin{thebibliography}.*?\\end{thebibliography}', '', content, flags=re.DOTALL)

    if remove_title_sections:
        content = re.sub(r'\\section\{Introduction\}', '', content)
        content = re.sub(r'\\section\*?\{Introduction\}', '', content)
        content = re.sub(r'\\section\{Abstract\}', '', content)

    # Downgrade headers (iterative)
    # 1 level: section -> subsection
    # 2 levels: section -> subsubsection
    if downgrade_headers > 0:
        for _ in range(downgrade_headers):
            # subsubsection -> paragraph
            content = re.sub(r'\\subsubsection\*?\{(.*?)\}', r'\\paragraph{\1}', content)
            # subsection -> subsubsection
            content = re.sub(r'\\subsection\*?\{(.*?)\}', r'\\subsubsection{\1}', content)
            # section -> subsection
            content = re.sub(r'\\section\*?\{(.*?)\}', r'\\subsection{\1}', content)


    # Replace jargon
    content = re.sub(r'\\texttt\{Integration.*?\}', 'the algorithmic framework', content)
    content = re.sub(r'\\texttt\{IndexSetNetwork.*?\}', 'the network model', content)
    content = re.sub(r'\\texttt\{NatureBDM.*?\}', 'the complexity algorithm', content)
    
    # Line-based processing for headers and cleaning
    lines = content.split('\n')
    new_lines = []
    in_protected_env = False
    protected_envs = ['tabular', 'array', 'align', 'align*', 'gather', 'gather*', 'split', 'multline', 'cases', 'pmatrix', 'bmatrix', 'vmatrix']
    
    for line in lines:
        # Track protected environments to preserve row endings
        if any(f'\\begin{{{env}}}' in line for env in protected_envs):
            in_protected_env = True
        if any(f'\\end{{{env}}}' in line for env in protected_envs):
            in_protected_env = False
            
        # Remove lines with script paths (jargon) and TSK identifiers
        if 'src/' in line or 'doc/' in line or 'results/' in line:
            # Exception for biblatex resource
            if 'addbibresource' not in line:
                continue
        if 'TSK-' in line or 'EPIC-' in line or 'PLAN-' in line:
            continue
            
        # Remove Log Jargon
        if 'Verification Log' in line or 'Artifacts' in line:
            continue
        if re.search(r'\\textbf\{(Timestamp|Status|Verification Method|Rationale|Action|Command|Input Dataset)(:?)\}\s*:?', line):
            continue
            
        # Replace specific jargon words
        line = re.sub(r'\\texttt\{Null\\_Generator\\_HPC\.py\}', 'the batch generation system', line)
        line = line.replace('Null\\_Generator\\_HPC.py', 'the batch generation system')
        line = line.replace('BioBridgeV2.m', 'the integration module')
        line = re.sub(r'\\texttt\{biomodels\\_', r'\\texttt{\\small BioModels:', line)
        line = line.replace('biomodels\\_', 'BioModels:')
        
        # Truncate long data lists
        if 'Places = [' in line and len(line) > 100:
            line = re.sub(r'Places = \[.*?\]', 'Places = [1, 2, ..., 393] (full list in supplementary material)', line)
        if 'ZerosBaseline = [' in line and len(line) > 100:
            line = re.sub(r'ZerosBaseline = \[.*?\]', 'ZerosBaseline = [1, 2, ..., 393] (full list in supplementary material)', line)
            
        # Fix TikZ node width
        if 'node at (3,-0.8) {Coverage:' in line:
            line = line.replace('node at (3,-0.8) {Coverage:', 'node[text width=12cm, align=center] at (3,-0.8) {Coverage:')
            
        # Fix parbox width
        line = line.replace('\\parbox{0.92\\linewidth}', '\\parbox{0.85\\linewidth}')
        line = line.replace('\\parbox{0.85\\linewidth}', '\\parbox{0.80\\linewidth}')

        # Add spaces in math lists to allow breaking
        line = line.replace(r'\mathrm{AND}, \mathrm{OR}', r'\mathrm{AND},\ \mathrm{OR}')
        line = line.replace(r'\text{AND},\text{OR}', r'\text{AND},\ \text{OR}')
        line = line.replace(r',\mathrm{', r',\ \mathrm{')
        line = line.replace(r',\text{', r',\ \text{')

        # Use display math for long formulas in Lemmas/Theorems
        line = line.replace(r'\(\mathcal{C}(cm, dynamic, params)=\mathcal{C}(cm_{\pi,\pi}, dynamic_{\pi}, params_{\pi})\)', r'\[\mathcal{C}(cm, dynamic, params)=\mathcal{C}(cm_{\pi,\pi}, dynamic_{\pi}, params_{\pi})\]')
        line = line.replace(r'\(\mathrm{Canon}=\langle d_i, I_c(i), \theta_i\rangle_{i=1}^n\)', r'\[\mathrm{Canon}=\langle d_i, I_c(i), \theta_i\rangle_{i=1}^n\]')
            
        # Remove raw Markdown table rows (starting with |) if any remain
        if line.strip().startswith('|'):
            continue
            
        # Remove trailing backslashes if not in protected env (fixes "There's no line here to end")
        if not in_protected_env:
            line = line.rstrip('\\')
            
        # Header escaping
        if re.match(r'^\s*\\(sub)*section\{', line):
            # Remove newlines in headers (replace \\ with space)
            line = re.sub(r'\\\\', ' ', line)
            
            # Escape & in headers if not already escaped
            line = re.sub(r'(?<!\\)&', r'\\&', line)
            
            # Fix double backslashes before & (e.g. \\& -> \&) if any remain
            line = line.replace(r'\\&', r'\&')
            
            # Escape _ if no math mode and not already escaped
            if '$' not in line:
                line = re.sub(r'(?<!\\)_', r'\\_', line)

        new_lines.append(line)
    content = '\n'.join(new_lines)

    return content

def escape_latex(text):
    # Escape LaTeX special characters
    chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
    }
    text = text.replace('&', r'\&')
    text = text.replace('%', r'\%')
    return text

def md_to_latex(content):
    # Simple MD to LaTeX conversion for the discussion section
    parts = re.split(r'(```.*?```)', content, flags=re.DOTALL)
    new_parts = []
    
    for part in parts:
        if part.startswith('```'):
            code_content = part[3:-3]
            if '\n' in code_content:
                first_line = code_content.split('\n', 1)[0]
                if re.match(r'^\w+$', first_line.strip()):
                     code_content = code_content.split('\n', 1)[1]
            new_parts.append(f'\\begin{{verbatim}}{code_content}\\end{{verbatim}}')
        else:
            lines = part.split('\n')
            processed_lines = []
            in_list = False
            
            for line in lines:
                # Skip Markdown tables (lines starting with |)
                if line.strip().startswith('|'):
                    continue
                    
                clean_line = line
                header_level = 0
                
                if line.startswith('# '): header_level = 1; clean_line = line[2:]
                elif line.startswith('## '): header_level = 2; clean_line = line[3:]
                elif line.startswith('### '): header_level = 3; clean_line = line[4:]
                
                is_list = False
                if line.strip().startswith('- ') or line.strip().startswith('* '):
                    is_list = True
                    clean_line = line.strip()[2:]
                
                # Escape special chars in the line (excluding macros we are about to add)
                clean_line = clean_line.replace('&', r'\&')
                
                # Bold/Italic
                clean_line = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', clean_line)
                clean_line = re.sub(r'\*(.*?)\*', r'\\textit{\1}', clean_line)
                
                # Inline code
                clean_line = re.sub(r'`(.*?)`', r'\\texttt{\1}', clean_line)
                
                if header_level == 1:
                    processed_lines.append(f'\\section{{{clean_line}}}')
                elif header_level == 2:
                    processed_lines.append(f'\\subsection{{{clean_line}}}')
                elif header_level == 3:
                    processed_lines.append(f'\\subsubsection{{{clean_line}}}')
                elif is_list:
                    if not in_list:
                        processed_lines.append('\\begin{itemize}')
                        in_list = True
                    processed_lines.append(f'\\item {clean_line}')
                else:
                    if in_list and not line.strip():
                         processed_lines.append('\\end{itemize}')
                         in_list = False
                    processed_lines.append(clean_line)
            
            if in_list:
                processed_lines.append('\\end{itemize}')
            
            new_parts.append('\n'.join(processed_lines))

    return ''.join(new_parts)

def generate_sections():
    # Merge bibliographies
    source_bib = os.path.join(BASE_DIR, 'newIntPaper', 'references.bib')
    target_bib = os.path.join(FINAL_DIR, 'references.bib')
    merge_bibliographies(source_bib, target_bib)

    # Define processing rules per section
    # format: (source_key, downgrade_levels, remove_title)
    processing_rules = {
        "introduction": ("introduction", 0, True),  # Keep structure, remove 'Introduction' header
        "theory": ("theory", 1, False), # Downgrade all headers (Theory is main section)
        "methods": ("methods", 1, False), # Downgrade all headers
        "results_structural": ("results_structural", 2, False), # section -> subsubsection
        "results_hybrid": ("results_hybrid", 2, False),
        "results_dynamics": ("results_dynamics", 2, False),
        "results_semantic": ("results_semantic", 2, False),
        "discussion": ("discussion", 0, False), # Discussion is top level in md, becomes subsection in latex
    }

    for dest_key, (src_key, downgrade, remove_title) in processing_rules.items():
        rel_path = SOURCES[src_key]
        src_path = os.path.join(BASE_DIR, rel_path)
        dest_path = os.path.join(SECTIONS_DIR, f"{dest_key}.tex")
        
        if not os.path.exists(src_path):
            print(f"Warning: Source not found: {src_path}")
            continue
            
        with open(src_path, 'r') as f:
            content = f.read()
            
        if src_path.endswith('.md'):
            content = md_to_latex(content)
        
        content = clean_latex_content(content, dest_key, downgrade_headers=downgrade, remove_title_sections=remove_title)
        
        with open(dest_path, 'w') as f:
            f.write(content)
        print(f"Generated {dest_path}")

def create_abstract():
    abstract_content = r"""
\begin{abstract}
\noindent We present a unifying framework for Deterministic Causal Boolean Integration in gene regulatory networks (GRNs), demonstrating that biological complexity emerges from simple algorithmic principles at the "edge of chaos." By decoupling structural complexity (mechanistic description length, $D$) from behavioral complexity (Block Decomposition Method, BDM), we reveal a universal phase transition where biological networks minimize algorithmic cost while maximizing semantic fidelity. Analyzing a curated "Tri-Phylum" dataset of 231 networks, we show that essential genes act as low-entropy "load-bearing pillars" of the epigenetic landscape. Our results unify structural universality, asynchronous dynamics, and hybrid encoding into a coherent theory of biological information processing, with direct applications to synthetic biology and precision oncology.
\end{abstract}
"""
    with open(os.path.join(SECTIONS_DIR, "abstract.tex"), 'w') as f:
        f.write(abstract_content)
    print("Generated abstract.tex")

if __name__ == "__main__":
    create_abstract()
    generate_sections()
