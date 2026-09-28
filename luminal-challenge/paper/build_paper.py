"""Regenerate both manuscripts from retained evidence and refuse anything unverified.

Steps: regenerate figures, tables and the value ledger (which runs the worked
example through the real compilers and re-derives every ledger entry from disk);
guard the LaTeX sources against hand-typed numbers and forbidden content; build
the supplementary and main documents twice so cross-document references resolve;
reject LaTeX warnings, undefined references and overfull boxes; check that every
ledger value cited in the sources appears in the PDF text; write
BUILD_VALIDATION.json. No compiler is timed and no benchmark is rerun.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'
BUILD.mkdir(exist_ok=True)
DOCS = ['supplementary', 'main']


def run(command, log_name):
    with (BUILD / log_name).open('w') as stream:
        result = subprocess.run(command, cwd=HERE, stdout=stream, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f'{command[0]} exited {result.returncode}; see build/{log_name}')
    return {'command': command, 'exit_code': result.returncode, 'log': f'build/{log_name}'}


# ---------------------------------------------------------------------------
# Source guards
# ---------------------------------------------------------------------------
# Identifiers and structural words that contain digits but are not cited numbers.
ALLOWED = [
    r'\b(?:C1|R0|A[0-4]|E[12]|Q[1-3]|S\d)\b',
    r'\b(?:Phase|phase|round|Round|Rounds|rounds)[~ ]\d\b',
    r'\bnotebook[~ ]0?\d\b', r'\bSHA-256\b', r'\b(?:19|20)\d\d\b',
]
STRIP = [
    r'(?<!\\)%.*', r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',
    r'\\begin\{verbatim\}.*?\\end\{verbatim\}',
    r'\\V\{[^}]*\}', r'\\(?:ref|label|cite|input|tableinput|path|url|texttt|externaldocument|includegraphics'
    r'|renewcommand|cmidrule|multicolumn|begin|end)\*?(?:\[[^\]]*\])?(?:\([^)]*\))?\{[^}]*\}(?:\{[^}]*\})?',
    r'p\{[\d.]+mm\}', r'\\\w+',
]
MATH = r'\$[^$]*\$|\\\[.*?\\\]|\\begin\{equation\}.*?\\end\{equation\}'
FORBIDDEN = {
    'retracted kernel median 2.3948': r'2\.3948',
    'wrong C1 hash 5ccbaaa3': r'5ccbaaa3',
    'Shannon or entropy wording': r'(?i)shannon|entrop',
    'deconvolution construction detail': r'(?i)sumando|decimal anchor|Dec\(|schema expansion',
    'unqualified "identical decisions"': r'identical decisions(?![^.]{0,80}equal work)',
    'runtime superiority over classical': r'(?i)faster (?:to compile )?than (?:the )?classical',
    'the 0.827 registration used as a verdict': r'0\.827(?!\d)',
}


def body_of(tex):
    return tex.split(r'\begin{document}', 1)[1]


def hand_typed_numbers(name, tex):
    body = body_of(tex)
    maths = re.findall(MATH, body, flags=re.S)
    problems = []
    for m in maths:
        stripped = re.sub(r'\\V\{[^}]*\}|\\ref\{[^}]*\}|\\mathrm\{[^}]*\}|\\operatorname\{[^}]*\}', '', m)
        for token in re.findall(r'\d+(?:\.\d+)?', stripped):
            if token not in {'0', '1', '2'}:
                problems.append((name, 'math', token, m[:60]))
    text = re.sub(MATH, ' ', body, flags=re.S)
    for pattern in STRIP:
        text = re.sub(pattern, ' ', text, flags=re.S)
    for pattern in ALLOWED:
        text = re.sub(pattern, ' ', text)
    for line in text.splitlines():
        for token in re.findall(r'\d+(?:[.,]\d+)*', line):
            problems.append((name, 'text', token, line.strip()[:80]))
    return problems


def forbidden(name, text):
    hits = []
    flat = re.sub(r'\s+', ' ', text)
    for label, pattern in FORBIDDEN.items():
        for m in re.finditer(pattern, flat):
            hits.append((name, label, flat[max(0, m.start() - 50):m.end() + 50]))
    return hits


commands = [run([sys.executable, 'generate_figures.py'], 'figures.log')]
sources = {d: (HERE / f'{d}.tex').read_text() for d in DOCS}
generated_tables = {p.name: p.read_text() for p in (HERE / 'generated').glob('tab_*.tex')}
numbers = [p for d, t in sources.items() for p in hand_typed_numbers(d, t)]
if numbers:
    raise RuntimeError('Hand-typed numbers in the manuscript sources:\n' +
                       '\n'.join(f'{d} [{k}] {tok!r}: {ctx}' for d, k, tok, ctx in numbers))
hits = [h for d, t in sources.items() for h in forbidden(d, body_of(t))]
hits += [h for n, t in generated_tables.items() if n != 'tab_ledger.tex' for h in forbidden(n, t)]
if hits:
    raise RuntimeError('Forbidden content:\n' + '\n'.join(f'{d}: {label}: ...{ctx}...' for d, label, ctx in hits))

# ---------------------------------------------------------------------------
# LaTeX: two passes over both documents for cross-document references
# ---------------------------------------------------------------------------
for round_ in (1, 2):
    for doc in DOCS:
        commands.append(run(['latexmk', '-pdf', '-g' if round_ == 2 else '-pdf', '-interaction=nonstopmode',
                             '-halt-on-error', '-outdir=build', f'{doc}.tex'], f'latexmk_{doc}_{round_}.log'))
issues = {}
for doc in DOCS:
    log = (BUILD / f'{doc}.log').read_text(errors='replace')
    found = re.findall(r'^.*(?:Overfull|undefined|multiply defined|LaTeX Warning:|Package .* Warning:|Error).*$',
                       log, flags=re.MULTILINE)
    found = [f for f in found if 'Package hyperref Warning: Token not allowed' not in f]
    if found:
        issues[doc] = found
if issues:
    raise RuntimeError('Resolve LaTeX issues before delivering the PDF:\n' + json.dumps(issues, indent=1))
for doc in DOCS:
    shutil.copyfile(BUILD / f'{doc}.pdf', HERE / f'{doc}.pdf')

# ---------------------------------------------------------------------------
# PDF content checks
# ---------------------------------------------------------------------------
ledger = json.loads((HERE / 'generated/claim_ledger.json').read_text())
pdf_text = {}
for doc in DOCS:
    out = subprocess.run(['pdftotext', '-layout', str(HERE / f'{doc}.pdf'), '-'], capture_output=True, text=True, check=True)
    pdf_text[doc] = out.stdout
flat_pdf = {d: re.sub(r'\s+', '', t).replace('\N{MINUS SIGN}', '-') for d, t in pdf_text.items()}
used = {d: sorted(set(re.findall(r'\\V\{([^}]*)\}', sources[d]))) for d in DOCS}
missing_keys = {d: [k for k in keys if k not in ledger] for d, keys in used.items()}
if any(missing_keys.values()):
    raise RuntimeError(f'Ledger keys cited but not defined: {missing_keys}')
absent = {}
for d, keys in used.items():
    gone = [k for k in keys if re.sub(r'\s+', '', ledger[k]['value']).replace('\N{MINUS SIGN}', '-') not in flat_pdf[d]]
    if gone:
        absent[d] = gone
if absent:
    raise RuntimeError(f'Ledger values cited in the source but not found in the PDF text: {absent}')
pdf_forbidden = [h for d, t in pdf_text.items() for h in forbidden(d, t.split('References')[0])]
if pdf_forbidden:
    raise RuntimeError('Forbidden content in PDF text:\n' + '\n'.join(map(str, pdf_forbidden)))
pages = {}
for doc in DOCS:
    info = subprocess.run(['pdfinfo', str(HERE / f'{doc}.pdf')], capture_output=True, text=True, check=True).stdout
    pages[doc] = int(re.search(r'Pages:\s+(\d+)', info).group(1))

manifest = json.loads((HERE / 'generated/input_manifest.json').read_text())
artifacts = [HERE / p for p in ('main.tex', 'supplementary.tex', 'main.pdf', 'supplementary.pdf', 'generate_figures.py',
                                'phase2_evidence.py', 'worked_example.py', 'build_paper.py')]
artifacts += sorted((HERE / 'generated').iterdir())
report = {
    'status': 'PASS', 'commands': commands, 'pages': pages,
    'latex_warnings_or_overfull_boxes': issues,
    'hand_typed_numbers_in_sources': 0, 'forbidden_content_hits': 0,
    'ledger_values': len(ledger), 'ledger_reverified_from_disk': manifest['ledger']['reverified_from_disk'],
    'ledger_keys_cited': {d: len(k) for d, k in used.items()},
    'ledger_values_found_in_pdf': {d: len(k) for d, k in used.items()},
    'figures_checked': sorted(manifest['figure_checks']),
    'artifacts_sha256': {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in artifacts if p.is_file()},
    'scope': 'Paper regeneration, evidence re-derivation and a deterministic run of the compilers on one public '
             'program; no timing, no new benchmark, no peer review.',
}
(HERE / 'BUILD_VALIDATION.json').write_text(json.dumps(report, indent=2) + '\n')
print(f"PASS: main.pdf ({pages['main']} pp) and supplementary.pdf ({pages['supplementary']} pp); "
      f"{len(ledger)} ledger values, {sum(len(k) for k in used.values())} cited and found in the PDFs; "
      f"{len(manifest['figure_checks'])} checked figures; 0 hand-typed numbers; 0 forbidden hits.")
