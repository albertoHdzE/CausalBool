"""Build the challenge report from the paper's frozen evidence.

The report does not own a single measurement. Every number it cites is either an
entry of the paper's claim ledger (``paper/phase2_evidence.Ledger``), copied with
its source and field, or a value derived here from the same frozen rows through
the ledger's own loaders. The derived values are the few the report needs and the
paper does not cite: the cycle and scratch halves of the public score, win counts,
and the public compile times of the submitted configuration. The combined scores
recomputed here must equal the ledger's to 1e-12, or the build fails.

Figures are snapshots of the paper's worked-example figures, which run the real
compilers on ``05_mixed_broadcast``; each copy's SHA-256 is recorded.

Steps: derive and write ``generated/values.tex`` and ``generated/claim_ledger.json``;
re-derive every pointer entry from disk (``verify_ledger``); reject any digit in
``report.tex`` that is neither a ledger value nor a constant of the challenge
specification; compile twice and reject warnings; check that every cited value
appears in the PDF text; write ``BUILD_VALIDATION.json``.

Run from the repository root:  venv/bin/python luminal-challenge/report/build_report.py
"""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
LUMINAL = HERE.parent
PAPER = LUMINAL / 'paper'
OUT = HERE / 'generated'
FIGURES = ('we_program', 'we_methods', 'we_pipeline')
sys.path.insert(0, str(PAPER))
import phase2_evidence as pe  # noqa: E402

# Constants stated by the challenge specification (README of the pinned revision),
# or structural numbers of LaTeX; they may appear as literal digits in prose.
SPEC_LITERALS = {'0', '1', '2', '3', '4', '5', '8', '16', '20', '32', '256'}
PROGRAM_STEMS = [s[:-5] for s in pe.EXPECTED_PROGRAMS]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geomean(xs):
    xs = list(xs)
    assert xs
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def build_ledger():
    paper = json.loads((PAPER / 'generated/claim_ledger.json').read_text())
    L = pe.Ledger()

    def copy(key):
        e = dict(paper[key])
        for k in ('key', 'raw', 'fmt', 'value'):
            e.pop(k)
        L._put(key, paper[key]['raw'], paper[key]['fmt'], e)
        return paper[key]['raw']

    for key in (
        # machine and allowances
        'mWords', 'mVlen', 'mPublic', 'bA', 'bB', 'bC', 'resident', 'sliceMs', 'sliceNodes',
        # public scores
        'rTwoPubClassical', 'tPubSixC1B', 'tPubSixC1A', 'pOneScore',
        # fresh populations against classical
        'tPrograms', 'rTwoDfsClRed', 'rTwoDfsClW', 'rTwoDfsClT', 'rTwoDfsClL',
        'rOneClRed', 'rOneClLo', 'rOneClHi', 'rOneClwins', 'rOneClties', 'rOneCllosses',
        'rOneClTime', 'lvOne',
        # C1 against R0
        'tCost', 'tCostLo', 'tCostHi', 'tQual', 'tQualLo', 'tQualHi', 'lvThree', 'tParityPairs',
        'tNodes', 'tWTLBW', 'tWTLBT', 'tWTLBL', 'tReps',
        # correctness
        'tAccPrograms', 'tAccCases', 'tExportRows',
        # worked example (computed by running the compilers; checked by the paper build)
        'weOps', 'weSerialC', 'weSerialS', 'weSerialJ', 'weClassicalC', 'weClassicalS', 'weClassicalJ',
        'weDirectphase1C', 'weDirectphase1S', 'weDirectphase1J', 'weC1C', 'weC1S', 'weC1J',
        'weStepAC', 'weStepAS', 'weStepBC', 'weStepBS', 'weStepCC', 'weStepCS',
        'weCatalogue', 'weCapLC', 'weCapLS', 'weCapCcap', 'weCapScap',
        'weCombDeclared', 'weCombRoot', 'weRootCerts', 'weEpochs', 'weNodes',
        'weTimeClassical', 'weQTop', 'weQTlo', 'weQThi', 'weQTchosen',
    ):
        copy(key)

    # Per-program public metrics from the frozen rows, through the ledger's loaders.
    pub2 = pe._load(pe.R2 + 'PUBLIC_SCORE.json')['scores']
    W = json.loads((PAPER / 'generated/worked_example.json').read_text())
    rows = {}
    for stem in PROGRAM_STEMS:
        p = stem.split('_', 1)[1]
        prog_sha = W['starter_public']['programs'][stem]['object_sha256']
        ser = pub2['serial'][p]
        reps = {tuple(x) for x in pub2['arms']['classical@None']['per_program_CSJ_by_repetition'][p]}
        assert len(reps) == 1, (p, reps)
        cl = list(reps.pop())
        c1 = [pe.d_public_row(prog_sha, 'C1', f'wall:{L.entries["bB"]["value"]}', f) for f in ('cycles', 'scratch', 'J')]
        assert W['starter_public']['programs'][stem]['serial'] == ser
        rows[p] = {'serial': ser, 'classical': cl[:2], 'C1': c1[:2], 'sha': prog_sha}

    def score(arm):
        cyc = geomean(rows[p]['serial'][0] / rows[p][arm][0] for p in rows)
        scr = geomean(rows[p]['serial'][1] / rows[p][arm][1] for p in rows)
        return cyc, scr, math.sqrt(cyc * scr)

    src = f'{pe.R2}PUBLIC_SCORE.json and {pe.T3}stages/C_public/rows.jsonl'
    for arm, tag, ledger_key in (('classical', 'Cl', 'rTwoPubClassical'), ('C1', 'COne', 'tPubSixC1B')):
        cyc, scr, comb = score(arm)
        assert abs(comb - L.entries[ledger_key]['raw']) < 1e-12, (arm, comb)
        L.computed(f'rpCyc{tag}', cyc, 'f3', src, f'{arm}: geometric mean of serial/cycles')
        L.computed(f'rpScr{tag}', scr, 'f3', src, f'{arm}: geometric mean of serial/scratch')
    L.computed('rpGainPct', 100 * (L.entries['tPubSixC1B']['raw'] / L.entries['rTwoPubClassical']['raw'] - 1),
               'f1', src, 'C1 score over classical score, percent')

    better = [p for p in rows if math.prod(rows[p]['C1']) < math.prod(rows[p]['classical'])]
    equal = [p for p in rows if math.prod(rows[p]['C1']) == math.prod(rows[p]['classical'])]
    worse = [p for p in rows if math.prod(rows[p]['C1']) > math.prod(rows[p]['classical'])]
    for key, v in (('rpBetter', len(better)), ('rpEqual', len(equal)), ('rpWorse', len(worse))):
        L.computed(key, v, 'int', src, 'public programs by J, C1 against classical')
    scr_better = sum(rows[p]['C1'][1] < rows[p]['classical'][1] for p in rows)
    cyc_better = sum(rows[p]['C1'][0] < rows[p]['classical'][0] for p in rows)
    cyc_worse = sum(rows[p]['C1'][0] > rows[p]['classical'][0] for p in rows)
    L.computed('rpScrBetter', scr_better, 'int', src, 'public programs with fewer scratch words than classical')
    L.computed('rpCycBetter', cyc_better, 'int', src, 'public programs with fewer cycles than classical')
    L.computed('rpCycWorse', cyc_worse, 'int', src, 'public programs with more cycles than classical')
    Jcl = geomean(math.prod(rows[p]['classical']) for p in rows)
    Jc1 = geomean(math.prod(rows[p]['C1']) for p in rows)
    L.computed('rpJRed', 100 * (1 - Jc1 / Jcl), 'f1', src, 'geometric-mean J, C1 below classical, percent')

    # Public compile times of the submitted configuration (C1 at the 0.1 s allowance).
    mode = f'wall:{L.entries["bB"]["value"]}'
    c1rows = [r for r in pe._rows('C_public') if r['arm_id'] == 'C1' and r['mode_key'] == mode]
    assert len(c1rows) == len(rows) * L.entries['tReps']['raw'], len(c1rows)
    assert {r['correctness'] for r in c1rows} == {'PASS'}
    L.computed('rpC1CallMed', 1000 * statistics.median(r['compile_call_seconds'] for r in c1rows), 'f1',
               f'{pe.T3}stages/C_public/rows.jsonl', f'C1 {mode}: median compile_call_seconds, ms')
    L.computed('rpC1ProcMax', max(r['process_seconds'] for r in c1rows), 'f3',
               f'{pe.T3}stages/C_public/rows.jsonl', f'C1 {mode}: maximum process_seconds')
    L.computed('rpC1Runs', len(c1rows), 'int', f'{pe.T3}stages/C_public/rows.jsonl', f'C1 {mode}: rows')
    base = 'results/direct_index_v4_optimization_repair2/lead_review/final/runs.json'
    cl_runs = [r for r in pe._load(base)['runs'] if r['arm'] == 'classical']
    L.computed('rpClCallMed', 1000 * statistics.median(r['compile_seconds'] for r in cl_runs), 'f3',
               base, 'classical: median compile_seconds over public programs, ms')

    for p, r in rows.items():
        key = p.replace('_', '')
        for arm, tag in (('serial', 'Ser'), ('classical', 'Cl'), ('C1', 'COne')):
            c, s = r[arm]
            L.computed(f'rpT{key}{tag}', f'{c}×{s}', 'str', src, f'{p}: {arm} C×S')
            L.computed(f'rpT{key}{tag}J', c * s, 'int', src, f'{p}: {arm} J')
    return L, rows


def write_table(rows):
    lines = []
    for p in rows:
        key = p.replace('_', '')
        js = {arm: math.prod(rows[p][arm]) for arm in ('serial', 'classical', 'C1')}
        best = min(js.values())
        cells = [r'\texttt{' + p.replace('_', r'\_') + '}']
        cells += [r'\V{rpT' + key + tag + '}' for tag in ('Ser', 'Cl', 'COne')]
        for arm, tag in (('serial', 'Ser'), ('classical', 'Cl'), ('C1', 'COne')):
            v = r'\V{rpT' + key + tag + 'J}'
            cells.append(r'\textbf{' + v + '}' if js[arm] == best else v)
        lines.append(' & '.join(cells) + r' \\')
    (OUT / 'tab_public.tex').write_text('\n'.join(lines) + '\n')


def digit_guard(tex):
    body = tex.split(r'\begin{document}', 1)[1]
    body = re.sub(r'(?<!\\)%.*', '', body)
    body = body.split(r'\begin{thebibliography}', 1)[0]
    for pattern in (r'\\V\{[^}]*\}', r'\\(?:ref|label|eqref|cite|url|href|path|includegraphics)(?:\[[^\]]*\])?\{[^}]*\}',
                    r'\\texttt\{[^}]*\}', r'\\(?:vspace|hspace)\{[^}]*\}', r'\[[0-9.]+(?:pt|mm|em)\]',
                    r'\{[0-9.]*\\(?:linewidth|textwidth)\}', r'[0-9.]+(?:pt|mm|em)\b',
                    r'\\(?:cmidrule|multicolumn)(?:\([a-z]*\))?\{[^}]*\}'):
        body = re.sub(pattern, ' ', body)
    bad = sorted({m for m in re.findall(r'\d+(?:[.,]\d+)*', body) if m not in SPEC_LITERALS})
    if bad:
        raise SystemExit(f'hand-typed digits in report.tex (use \\V{{key}}): {bad}')


def main():
    OUT.mkdir(exist_ok=True)
    L, rows = build_ledger()
    pe.OUT = OUT          # the owner's writer targets its module-level OUT
    L.write()
    checked, total = pe.verify_ledger(OUT / 'claim_ledger.json')
    write_table(rows)

    figures = {}
    for name in FIGURES:
        src = PAPER / 'generated' / f'{name}.pdf'
        dst = OUT / f'{name}.pdf'
        shutil.copyfile(src, dst)
        figures[name] = sha(dst)

    tex = (HERE / 'report.tex').read_text()
    digit_guard(tex)
    cited = sorted(set(re.findall(r'\\V\{([^}]*)\}', tex + (OUT / 'tab_public.tex').read_text())))
    missing = [k for k in cited if k not in L.entries]
    if missing:
        raise SystemExit(f'undefined ledger keys: {missing}')

    for _ in range(2):
        run = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'report.tex'],
                             cwd=HERE, capture_output=True, text=True)
        if run.returncode:
            sys.stdout.write(run.stdout[-3000:])
            raise SystemExit('pdflatex failed')
    log = (HERE / 'report.log').read_text(errors='replace')
    problems = [l for l in log.splitlines() if re.search(r'Warning|Overfull|undefined', l)]
    if problems:
        raise SystemExit('LaTeX problems:\n' + '\n'.join(problems[:20]))

    text = subprocess.run(['pdftotext', '-layout', 'report.pdf', '-'], cwd=HERE,
                          capture_output=True, text=True, check=True).stdout
    flat = re.sub(r'\s+', ' ', text).replace('−', '-')
    absent = [k for k in cited if L.entries[k]['value'].replace('−', '-') not in flat]
    if absent:
        raise SystemExit(f'cited values absent from the PDF text: {absent}')

    validation = {
        'ledger_entries': len(L.entries), 'verified_from_disk': checked, 'ledger_total': total,
        'cited_keys': len(cited), 'cited_keys_found_in_pdf': len(cited) - len(absent),
        'figures_sha256': figures, 'report_tex_sha256': sha(HERE / 'report.tex'),
        'report_pdf_sha256': sha(HERE / 'report.pdf'),
        'paper_claim_ledger_sha256': sha(PAPER / 'generated/claim_ledger.json'),
    }
    (HERE / 'BUILD_VALIDATION.json').write_text(json.dumps(validation, indent=1) + '\n')
    print(f'PASS: {len(cited)} cited values, {checked} of {total} ledger entries re-derived from disk, '
          f'{len(figures)} figures, 0 LaTeX warnings')


if __name__ == '__main__':
    main()
