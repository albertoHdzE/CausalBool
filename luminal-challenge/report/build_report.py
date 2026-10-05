"""Build the challenge report from the paper's frozen evidence.

The report does not own a single measurement. Every number it cites is either an
entry of the paper's claim ledger (``paper/phase2_evidence.Ledger``), copied with
its source and field, or a value derived here from the same frozen rows through
the ledger's own loaders. The derived values are the few the report needs and the
paper does not cite: the cycle and scratch halves of the public score, win counts,
and the public compile times of the submitted configuration. The combined scores
recomputed here must equal the ledger's to 1e-12, or the build fails.

Figures of section 5 are snapshots of the paper's worked-example figures, which run
the real compilers on ``05_mixed_broadcast``; each copy's SHA-256 is recorded.

Sections 3 and 4 follow a second program, ``02_scalar_dual_chain`` (the running
example of notebook 00, section 2). ``build_example`` runs every compiler on it
through ``worked_example.explain_program`` (deterministic, on a logical clock, no
timing), asserts the live results equal the frozen public rows, replays each
compilation cycle by cycle, draws only with the renders owned by
``notebooks/viz.py``, and enters every number it states into the ledger as a
``computed`` entry whose source is ``generated/example.json``.

Steps: derive and write ``generated/values.tex`` and ``generated/claim_ledger.json``;
re-derive every pointer entry from disk (``verify_ledger``); reject any digit in
``report.tex`` that is neither a ledger value nor a constant of the challenge
specification; compile twice and reject warnings; check that every cited value
appears in the PDF text; write ``BUILD_VALIDATION.json``.

Run from the repository root:  venv/bin/python luminal-challenge/report/build_report.py
"""
from pathlib import Path
import collections
import hashlib
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
LUMINAL = HERE.parent
PAPER = LUMINAL / 'paper'
OUT = HERE / 'generated'
FIGURES = ('we_program', 'we_methods', 'we_pipeline')
sys.path.insert(0, str(PAPER))
sys.path.insert(0, str(LUMINAL / 'notebooks'))    # viz.py and trace.py, the render and replay owners
import phase2_evidence as pe  # noqa: E402
import worked_example as we  # noqa: E402
import machine  # noqa: E402  (on the path through worked_example)
import schema_index as si  # noqa: E402
import trace  # noqa: E402
import viz  # noqa: E402
assert hasattr(trace, 'replay'), 'stdlib trace shadowed the replay owner'

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


def _render(name, draw, *args, **kwargs):
    """Save one ``viz`` figure: the owner draws, this only writes the file."""
    plt.close('all')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)     # Agg's show() is a no-op
        draw(*args, **kwargs)
    fig = plt.gcf()
    path = OUT / f'{name}.pdf'
    fig.savefig(path, bbox_inches='tight', metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)
    return sha(path)


def _pattern(cube):
    """The cube's bit pattern as the owner prints it, lowest bit first."""
    return cube.label().split(':', 1)[1]


def _holders(query, addresses, life):
    """Each word an address query subtracted, mapped to the live value that holds it."""
    me = life[query['value']]
    held = {}
    for h in query['intervals'][1:]:
        for w in range(h['lo'], h['hi'] + 1):
            held[w] = next(v for v, a in addresses.items() if a == w and v != query['value']
                           and life[v][0] <= me[1] and me[0] <= life[v][1])
    return held


def build_example(L, rows):
    """The running example of sections 3 and 4: every compiler on one small program.

    Executes the compilers deterministically through ``worked_example.explain_program``
    (the paper's owner of compiler execution), replays each compilation cycle by cycle
    through ``notebooks/trace.py`` (which checks itself against the validator), and
    draws only with the renders owned by ``notebooks/viz.py``. Nothing is timed.
    """
    D, comps = we.explain_program()
    (OUT / 'example.json').write_text(json.dumps(D, indent=1, default=str) + '\n')
    src = 'report/generated/example.json (worked_example.explain_program)'
    M = D['methods']
    assert (M['first']['C'], M['first']['S']) == (M['C1']['C'], M['C1']['S'])
    stem = D['program'].split('_', 1)[1]
    assert rows[stem]['classical'] == [M['classical']['C'], M['classical']['S']], 'live classical != frozen'
    assert rows[stem]['C1'] == [M['C1']['C'], M['C1']['S']], 'live C1 at fixed work != frozen C1 at 0.1 s'
    assert rows[stem]['serial'] == [M['serial']['C'], M['serial']['S']]
    ops = D['operations']

    def put(key, raw, fmt, field, claim=''):
        L.computed(key, raw, fmt, src, field, claim)

    put('exOps', len(ops), 'int', 'operations', 'operations in the example')
    put('exValues', len(M['C1']['addresses']), 'int', 'methods/C1/addresses', 'values needing a word')
    for arm, tag in (('serial', 'Ser'), ('classical', 'Cl'), ('C1', 'Ours')):
        for f in ('C', 'S', 'J'):
            put(f'ex{tag}{f}', M[arm][f], 'int', f'methods/{arm}/{f}')
    put('exRatioCl', M['classical']['J'] / M['C1']['J'], 'f3', 'methods', 'J classical / J ours')
    put('exRatioSer', M['serial']['J'] / M['C1']['J'], 'f1', 'methods', 'J serial / J ours')

    # Peak number of live values, and the cycles of the two stores, for classical and ours.
    for arm, tag in (('classical', 'Cl'), ('C1', 'Ours')):
        life = M[arm]['lifetimes']
        live = [sum(a <= c <= b for a, b in life.values()) for c in range(M[arm]['C'])]
        peak = max(live)
        assert peak == M[arm]['S'], (arm, peak)          # scalars: footprint == peak live
        put(f'ex{tag}PeakCycle', live.index(peak), 'int', f'methods/{arm}/lifetimes', 'first cycle at the peak')
        stores = sorted(M[arm]['times'][str(o['id'])] for o in ops if o['engine'] == 'store')
        put(f'ex{tag}StoreA', stores[0], 'int', f'methods/{arm}/times')
        put(f'ex{tag}StoreB', stores[1], 'int', f'methods/{arm}/times')
    put('exSerLast', M['serial']['C'] - 1, 'int', 'methods/serial/C', 'last serial cycle')

    # The classical ready queue of cycle 0: every load has the same priority; fan-out breaks the tie.
    steps, _ = trace.replay_list_schedule(
        machine.load_program(LUMINAL / f'.reference/programs/{D["program"]}.json'))
    first_queue = steps[0].queue
    assert len({e.priority for e in first_queue}) == 1
    put('exClPrio', first_queue[0].priority, 'int', 'trace.replay_list_schedule/steps[0]', 'load priority')

    # Step 1: one query per operation, one per value.
    tq = D['schedule_queries']
    put('exTimeBits', D['time_width'], 'int', 'time_width')
    put('exHorizon', D['horizon'], 'int', 'horizon')
    put('exAddrBits', D['address_width'], 'int', 'address_width')
    put('exQueries', len(tq) + len(D['address_queries']), 'int', 'schedule_queries+address_queries')
    k = 2                                               # load c0: the first query with a full cycle
    q = tq[k]
    interval = q['intervals'][0]
    before = [si.Cube(*c) for c in interval['cubes']]
    after = [si.Cube(*c) for c in q['cubes']]
    blocked = sorted({m for c in before for m in c.members()} - set(q['members']))
    assert blocked == [0] and q['chosen_index'] == 1 and ops[k]['op'] == 'load'
    put('exQhi', interval['hi'], 'int', f'schedule_queries/{k}/intervals/0/hi')
    for i, c in enumerate(before):
        put(f'exQb{"ABC"[i]}', _pattern(c), 'str', f'schedule_queries/{k}/intervals/0/cubes/{i}')
    for i, c in enumerate(after):
        put(f'exQa{"ABCD"[i]}', _pattern(c), 'str', f'schedule_queries/{k}/cubes/{i}')
    assert len(before) == 3 and len(after) == 4
    field_t = si.Field('t', 0, D['time_width'])

    # The notation: horizon = sum of latencies; each window ends at the sum before it.
    lat = [o['latency'] for o in ops]
    assert D['horizon'] == sum(lat)
    assert [x['intervals'][0]['hi'] for x in tq[:4]] == [sum(lat[:i]) for i in range(4)]
    put('exLatSum', '+'.join(map(str, lat)), 'str', 'operations/latency', 'latencies, summed to the horizon')
    put('exHorizonLast', D['horizon'] - 1, 'int', 'horizon', 'last cycle any schedule can need')
    put('exCodeMax', (1 << D['time_width']) - 1, 'int', 'time_width', 'largest code of the time field')
    put('exWinD', tq[3]['intervals'][0]['hi'], 'int', 'schedule_queries/3/intervals/0/hi')
    put('exQlen', interval['hi'] - interval['lo'] + 1, 'int', f'schedule_queries/{k}/intervals/0')
    put('exMaxCover', max(len(x['cubes']) for x in tq), 'int', 'schedule_queries/*/cubes', 'largest cover')
    anchors = sorted(c.anchor for c in after)
    assert min(anchors) == q['chosen_index']
    put('exQanchors', ', '.join(map(str, anchors[:-1])) + f' and {anchors[-1]}', 'str',
        f'schedule_queries/{k}/cubes/*/anchor')
    code = lambda v: ''.join(str((v >> i) & 1) for i in range(D['time_width']))
    owner = lambda cover, v: next((_pattern(c) for c in cover if c.contains(v)), None)
    crow = []
    for v in range(interval['lo'], interval['hi'] + 1):
        gone = owner(after, v) is None
        crow.append(f"{v} & \\texttt{{{code(v)}}} & \\texttt{{{owner(before, v)}}} & "
                    + (r"\emph{removed: engine full}" if gone else f"\\texttt{{{owner(after, v)}}}")
                    + r" \\")
    (OUT / 'tab_example_codes.tex').write_text('\n'.join(crow) + '\n')

    # The address query of d0: two overlapping values hold the two lowest words.
    aq = next(x for x in D['address_queries'] if x['value'] == 'd0')
    window, held = aq['intervals'][0], aq['intervals'][1:]
    put('exAhi', window['hi'], 'int', 'address_queries[d0]/intervals/0/hi')
    put('exAchosen', aq['decoded'], 'int', 'address_queries[d0]/decoded')
    assert [h['lo'] for h in held] == [0, 1] and aq['decoded'] == 2

    # Steps 2 to 5: the reopen round.
    R = D['reopen']
    Q = R['questions']
    box = [x for x in Q if x['status'] == 'NO_STRICT_IMPROVEMENT']
    root = [x for x in Q if x['status'] == 'UNSAT' and x['nodes'] == 0]
    searched = [x for x in Q if x['nodes'] > 0]
    assert len(box) + len(root) + len(searched) == len(Q) and not R['improvements']
    assert all(x['status'] == 'UNSAT' for x in searched)
    put('exCatalogue', len(Q), 'int', 'reopen/questions')
    put('exBoxClosed', len(box), 'int', 'reopen/questions[status=NO_STRICT_IMPROVEMENT]')
    put('exRootClosed', len(root), 'int', 'reopen/questions[UNSAT, nodes=0]')
    put('exSearched', len(searched), 'int', 'reopen/questions[nodes>0]')
    put('exNodes', R['nodes'], 'int', 'reopen/nodes')
    put('exEpochs', R['epochs'], 'int', 'reopen/epochs')
    put('exCerts', R['certificates'], 'int', 'reopen/certificates', 'propagation certificates emitted')
    whole = next(x for x in Q if x['policy'] == 'whole_program')
    put('exWholeNodes', whole['nodes'], 'int', 'reopen/questions[whole_program]/nodes')
    for tag, x in (('Box', box[0]), ('Whole', whole)):
        for i, f in enumerate(('LC', 'LS', 'Ccap', 'Scap')):
            put(f'ex{tag}{f}', x['caps'][i], 'int', f'reopen/questions[{x["policy"]}]/caps/{i}')
    put('exBoxPolicy', box[0]['policy'].replace('_', ' '), 'str', 'reopen/questions/policy')
    O = D['optimum']
    assert O['schedules_below_J0'] == 0 and O['J'] == M['C1']['J'] and O['J0'] == M['C1']['J']
    put('exOptSchedules', O['schedules'], 'int', 'optimum/schedules', 'legal schedules enumerated')
    put('exOptCmax', O['c_max'], 'int', 'optimum/c_max')
    put('exOptJm', O['J0'] - 1, 'int', 'optimum/J0', 'J0 - 1')

    # The program itself, one numbered line per operation (line number = operation id).
    program = machine.load_program(LUMINAL / f'.reference/programs/{D["program"]}.json')
    symbol = {'mul': '*', 'add': '+', 'xor': r'\^{}'}
    readers = collections.Counter(a for o in program['operations'] for a in o.get('args') or [])
    lines = []
    for o, info in zip(program['operations'], ops):
        name = lambda v: v.replace('_', r'\_')
        if o['op'] == 'load':
            code = f"{o['dest']} = load {o['buffer']}[{o['offset']}]"
            note = f"one word from buffer \\texttt{{{o['buffer']}}} (latency {info['latency']})"
        elif o['op'] == 'store':
            code = f"{o['buffer']}[{o['offset']}] = {name(o['args'][0])}"
            note = 'one store slot per cycle'
        else:
            code = f"{name(o['dest'])} = {name(o['args'][0])} {symbol[o['op']]} {name(o['args'][1])}"
            note = ('shared by both chains ' if readers[o['dest']] > 1 else '') + f"(latency {info['latency']})"
        lines.append(f"{o['id']} & \\texttt{{{code}}} & \\emph{{{note}}} \\\\")
    (OUT / 'tab_example_program.tex').write_text('\n'.join(lines) + '\n')

    # Tables of Step 1, generated (digits come from the run, not the author).
    trow = []
    for op, x in zip(ops, tq):
        iv = x['intervals'][0]
        full = sorted({m for c in iv['cubes'] for m in si.Cube(*c).members()} - set(x['members']))
        pats = ', '.join(r'\texttt{' + _pattern(si.Cube(*c)) + '}' for c in x['cubes'])
        trow.append(f"{op['id']} & \\texttt{{{op['op']}}} & [{iv['lo']},\\,{iv['hi']}] & {pats} & "
                    f"{', '.join(map(str, full)) or '--'} & \\textbf{{{field_t.decode(x['chosen_index'])}}} \\\\")
    (OUT / 'tab_example_times.tex').write_text('\n'.join(trow) + '\n')
    arow, life = [], M['C1']['lifetimes']
    tt = lambda v: r'\texttt{' + v.replace('_', r'\_') + '}'
    for x in D['address_queries']:
        held = _holders(x, M['C1']['addresses'], life)
        taken = ', '.join(f'{w} ({tt(v)})' for w, v in sorted(held.items()))
        a, b = life[x['value']]
        arow.append(f"{tt(x['value'])} & [{a},\\,{b}] & [0,\\,{x['intervals'][0]['hi']}] & "
                    f"{taken or '--'} & \\textbf{{{x['decoded']}}} \\\\")
    (OUT / 'tab_example_addresses.tex').write_text('\n'.join(arow) + '\n')

    # Figures, each drawn by its owner in viz.py.
    program = machine.load_program(LUMINAL / f'.reference/programs/{D["program"]}.json')
    case = program['cases'][0]
    figs = {}
    for arm, label in (('serial', 'serial'), ('classical', 'classical'), ('C1', 'ours')):
        states = trace.replay(program, comps[arm], case)
        figs[f'ex_trace_{label}'] = _render(
            f'ex_trace_{label}', viz.show_execution_trace, program, comps[arm], states,
            f"{label}: C = {M[arm]['C']} cycles, S = {M[arm]['S']} words, J = {M[arm]['J']}")
    figs['ex_classical_queue'] = _render('ex_classical_queue', viz.show_list_schedule, steps,
                                         'classical: the ready queue of every cycle')
    figs['ex_cube_anatomy'] = _render('ex_cube_anatomy', viz.show_cube_anatomy, after[0],
                                      'one cube of the example, taken apart')
    field = si.Field('t', 0, D['time_width'])
    figs['ex_query_before'] = _render('ex_query_before', viz.show_cover_blocks, before, field, 0, interval['hi'],
                                      f"op {k}: cycles [0, {interval['hi']}] as {len(before)} cubes")
    figs['ex_query_after'] = _render('ex_query_after', viz.show_cover_blocks, after, field, 0, interval['hi'],
                                     f"minus the full cycle {blocked[0]}: {len(after)} cubes, minimum {q['chosen_index']}",
                                     excluded=blocked, chosen=q['chosen_index'])
    span = range(M['C1']['C'] + 1)
    trows = []
    for op, x in zip(ops, tq):
        iv = x['intervals'][0]
        asked = [c for c in span if c <= iv['hi']]      # the row ends where the query's window ends
        reasons = {c: ('wait' if c < iv['lo'] else 'full') for c in asked}
        trows.append((f"op{op['id']} {op['op']}", asked, [c for c in asked if c in x['members']],
                      reasons, field.decode(x['chosen_index'])))
    figs['ex_step1_times'] = _render('ex_step1_times', viz.show_domain_filtering, trows,
                                     'Step 1, when: each operation takes the smallest surviving cycle')
    words = range(M['classical']['S'])
    arows = []
    for x in D['address_queries']:
        iv = x['intervals'][0]
        kept = {m for c in x['cubes'] for m in si.Cube(*c).members()}
        held = _holders(x, M['C1']['addresses'], life)
        asked = [w for w in words if w <= iv['hi']]
        reasons = {w: held.get(w, '') for w in asked}
        arows.append((f"{x['value']} {tuple(life[x['value']])}", asked, [w for w in asked if w in kept],
                      reasons, x['decoded']))
    figs['ex_step1_addresses'] = _render('ex_step1_addresses', viz.show_domain_filtering, arows,
                                         'Step 1, where: each value takes the lowest word no live value holds')
    verdict = {id(x): 'box empty' for x in box}
    verdict.update({id(x): 'no at root' for x in root})
    verdict.update({id(x): f"searched, {x['nodes']} nodes" for x in searched})
    figs['ex_catalogue'] = _render(
        'ex_catalogue', viz.show_window_catalog,
        [(f"{x['policy']} r{x['radius']}: {verdict[id(x)]}", x['window']) for x in Q], len(ops),
        f"{len(Q)} questions, no strict improvement")
    caps = dict(zip(('LC', 'LS', 'Ccap', 'Scap'), whole['caps']))
    figs['ex_plane'] = _render(
        'ex_plane', viz.show_objective_plane, (M['C1']['C'], M['C1']['S']),
        'the incumbent and every point that would beat it',
        points=[('classical', (M['classical']['C'], M['classical']['S']))],
        caps=caps, c_range=(1, M['classical']['C'] + 3), s_range=(1, M['classical']['S'] + 4))
    return figs


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
    example_figures = build_example(L, rows)
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
    figures.update(example_figures)
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
