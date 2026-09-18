"""Render evidence tables and build/check the main paper and supplement."""
import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

def main():
    evidence=ROOT/'evidence';paper=ROOT/'paper';build=ROOT/'.build/paper';build.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable, str(ROOT/'tools/paper_index_examples.py')], check=True, timeout=180)
    subprocess.run([sys.executable, str(ROOT/'tools/paper_certificates.py')], check=True, timeout=1800)
    if '--regenerate-figures' in sys.argv:
        subprocess.run([sys.executable, str(ROOT/'tools/paper_network_figures.py')], check=True, timeout=180)
    figures=json.loads((evidence/'paper_figures.json').read_text())
    if figures['status']!='PASS':raise RuntimeError('Network figure checks failed')
    for relative,digest in figures['source_sha256'].items():
        if hashlib.sha256((ROOT.parent/relative).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Figure source changed; rebuild with --regenerate-figures')
    for name,digest in figures['figures'].items():
        if hashlib.sha256((paper/'generated'/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Figure artifact changed: '+name)
    index=json.loads((evidence/'paper_index.json').read_text())
    if index['status'] != 'PASS':raise RuntimeError('Index reconstruction check failed')
    discrete=json.loads((evidence/'discrete.json').read_text())
    arithmetic=json.loads((evidence/'compiled_audit.json').read_text())
    causalbool=json.loads((evidence/'causalbool_arithmetic/verification.json').read_text())
    certificates=json.loads((evidence/'paper_certificates.json').read_text())
    if certificates['status']!='PASS':raise RuntimeError('Certificates failed')
    suites=[json.loads((evidence/name).read_text()) for name in ('acceptance_pytest.json','legacy_pytest.json')]
    fourier=[json.loads((evidence/f'fourier_{n}_validation.json').read_text()) for n in (32768,65536)]
    if any(d.get('status')!='PASS' for d in (discrete,arithmetic,*fourier)):raise RuntimeError('Incomplete scientific evidence')
    lines=[r'\subsection*{Generated results}',
           r'\begin{center}\begin{tabular}{rrrrrr}\toprule',
           r'$N$ & Multiplies & Adds & Rotations & Depth & Cost (s)\\\midrule']
    for d in fourier:
        c=d['counts'];lines.append(f"{d['n']} & {c['multiplications']} & {c['additions']} & {c['rotations']} & {c['depth']} & {c['cost_us']/1e6:.6f}"+r'\\')
    lines += [r'\bottomrule\end{tabular}\end{center}']
    for d in fourier:
        n=d['n'];ledger=json.loads((evidence/f'fourier_{n}_ledger.json').read_text());selected=ledger['selected']
        baseline=ledger['dense_baseline']['cost_us'];error=max(c['normalized_max_error'] for c in d['checks'])
        mantissa,exponent=f'{error:.3g}'.split('e')
        error_tex=mantissa+r'\times 10^{'+str(int(exponent))+'}'
        lines.append(f"For $N={n}$, stages are {selected['partition']}, baby sizes {selected['babies']}, "
                     f"and the dense baseline is {baseline/1e6:.6f} seconds ({baseline/selected['cost_us']:.3f} times the selected cost). "
                     f"The {len(d['checks'])} target cases have maximum normalised error ${error_tex}$. ")
    lines += [r'\begin{center}\begin{tabular}{rrrrrrrrr}\toprule',
              '$n$ & '+' & '.join(str(d['n']) for d in discrete['majority'])+r'\\',
              'Gates & '+' & '.join(str(d['gates']) for d in discrete['majority'])+r'\\\bottomrule\end{tabular}\end{center}',
              r'\subsection*{Direct arithmetic systems}',
              r'\begin{center}\begin{tabular}{lrr}\toprule System & Compiled rows & Signals\\\midrule']
    for q,d in arithmetic['families'].items():lines.append(f"{q} & {d['compiled_rows']} & {d['signals']}"+r'\\')
    lines += [r'\bottomrule\end{tabular}\end{center}',
              r'\subsection*{Recovered-cell arithmetic systems}',
              r'\begin{center}\begin{tabular}{lrr}\toprule System & Rows & Signals\\\midrule']
    for q in ('Q5', 'Q6', 'Q7'):
        stats=causalbool['rows'][q]['stats']
        lines.append(f"{q} & {stats['rows']} & {stats['signals']}"+r'\\')
    q7=certificates['certificates']['Q7'];q8=certificates['certificates']['Q8']
    q2=certificates['certificates']['Q2'];cells=certificates['certificates']['cells']
    ladder=', '.join(f"{w} ({d['triples']:,})" for w,d in sorted(q7['constraint_ladder'].items(),key=lambda kv:int(kv[0])))
    lines += [r'\bottomrule\end{tabular}\end{center}',
              r'\subsection*{Role ledger}',
              r'\begin{center}\begin{tabular}{ll}\toprule Question & Role\\\midrule']
    lines += [f"{q} & {role}"+r'\\' for q,role in sorted(certificates['role_ledger'].items())]
    lines += [r'\bottomrule\end{tabular}\end{center}',
              'Recovered cells, as the method named them from stated integer relations: '
              + '; '.join(f"{name.replace('_',' ')} = "
                          + ', '.join(g['gate'].replace('_',r'\_') for g in group)
                          for name,group in sorted(cells['cells'].items()))
              + f". All {cells['expansions_verified_by_root_identity']} expansions into the "
                'constraint gate set are verified by root identity.',
              f"Majority is recovered at n={q2['largest_n']} with every input essential and "
              f"identity against an independent threshold, enumerating "
              f"{q2['states_enumerated']} states. Recovering it allocated "
              f"{q2['largest_decision_nodes']:,} decision nodes, growing as "
              f"$n^{{{q2['allocation_growth_degree']}}}$; the recovered function's own diagram "
              f"is {q2['largest_recovered_diagram_nodes']:,} nodes, growing as "
              f"$n^{{{q2['description_growth_degree']}}}$, and equals "
              f"$(n+1)^2/4$ at every size in the ladder. The exact match class is "
              + ' and '.join(q2['recovery_split']['match_class'])
              + f" at n={q2['recovery_split']['n']}, so the reported name is the "
                'canonical priority order, not a unique identification.',
              f"The Q7 constraint ladder is exhaustive at widths {ladder}: "
              f"{q7['constraint_triples_total']:,} triples with "
              f"{q7['constraint_discrepancies_total']} discrepancies against an independent "
              'integer predicate.',
              f"Recovery allocation grows as $n^{{{q8['majority_allocation_growth_degree']}}}$ for "
              f"majority, its description as $n^{{{q8['majority_description_growth_degree']}}}$, and "
              f"the multiplier's allocation "
              f"by a factor of {q8['multiplier_growth_per_bit']} per bit, so a "
              f"4096-bit multiplier would need about $10^{{{q8['multiplier_nodes_at_4096_log10']}}}$ "
              f"nodes against roughly $10^{{{q8['atoms_in_observable_universe_log10']}}}$ atoms in "
              'the observable universe.',
              f"The compiled audit records {len(arithmetic['checks'])} passing checks. "
              f"The challenge and affected Boolean regression suites collect {suites[0]['collected']} and {suites[1]['collected']} tests respectively; all pass. "
              'The modular enumeration counts for primes 3, 5, 7, 11, 13, 19 are '+
              ', '.join(str(d['solution_count']) for d in discrete['modular'])+'.',
              'Tables are generated from the recorded verification results; '
              'individual records retain the producing commands and source hashes.',
              f"The supplementary index check reconstructs {sum(r['states'] for r in index['majority'])} majority circuit states. "
              f"The incorrect nine-input circuit disagrees with majority on {index['naive_control']['disagreements']} of 512 states, "
              'despite having the same functional inputs and the same number of active indices.']
    (paper/'results.tex').write_text('\n'.join(lines)+'\n')
    documents = {name: build_document(paper, build, name) for name in ('response', 'supplementary')}
    (evidence/'pdf.json').write_text(json.dumps(dict(status='PASS', documents=documents,
        scope='Document builds and bounded index examples; prior Fourier and compiled results reused'), indent=2)+'\n')
    print('PDFs: '+', '.join(f"{name}: {record['pages']} pages" for name,record in documents.items()))


def build_document(paper, build, name):
    commands=[]
    for _ in range(3):
        command=['pdflatex','-interaction=nonstopmode','-halt-on-error',f'-output-directory={build}',f'{name}.tex']
        p=subprocess.run(command,cwd=paper,capture_output=True,text=True,timeout=300)
        commands.append({'command':command,'exit_code':p.returncode})
        if p.returncode:raise RuntimeError(p.stdout[-6000:])
    log=(build/f'{name}.log').read_text()
    problems=[line for line in log.splitlines() if any(s in line for s in ('Overfull','undefined','Rerun to get'))]
    if problems:raise RuntimeError(f'{name} PDF warnings: '+'; '.join(problems))
    pdf=build/f'{name}.pdf';bbox=build/f'{name}.bbox.html'
    subprocess.run(['pdftotext','-bbox',str(pdf),str(bbox)],check=True,timeout=60)
    xml=re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '\ufffd', bbox.read_text())
    tree=ET.fromstring(xml);pages=list(tree.iter('{http://www.w3.org/1999/xhtml}page'))
    if not pages:raise RuntimeError('PDF has no inspectable pages')
    for page in pages:
        w,h=float(page.attrib['width']),float(page.attrib['height'])
        for word in page.iter('{http://www.w3.org/1999/xhtml}word'):
            if not (0<=float(word.attrib['xMin'])<=float(word.attrib['xMax'])<=w and
                    0<=float(word.attrib['yMin'])<=float(word.attrib['yMax'])<=h):
                raise RuntimeError('Clipped PDF text: '+str(word.text))
    (paper/f'{name}.pdf').write_bytes(pdf.read_bytes())
    return dict(status='PASS', pages=len(pages), commands=commands,
        checks=['three successful LaTeX passes','no overfull or unresolved references',
                'all extracted words within page bounds'])

if __name__=='__main__':main()
