"""Rebuild every figure, table and cited value from retained evidence.

Never reruns a benchmark and never measures time. The only code it executes is
the compilers themselves, through ``worked_example.py``, on one public program
with a logical clock, so every figure of the worked example draws the actual
object that the real modules produce. Every number a figure shows is asserted
before rendering, and each figure's data is saved beside it as JSON.

Owners: this script owns figures and tables; ``phase2_evidence.Ledger`` owns
cited values; ``worked_example.py`` owns compiler execution. The colour palette
is read (not executed, not copied) from the 0xPARC figure module, which owns it.
"""
from pathlib import Path
import ast
import hashlib
import json
import math
import os
import re
import statistics as st
from collections import defaultdict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'generated'
OUT.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', '/tmp/causalbool-paper-mpl')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/causalbool-paper-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np
import phase2_evidence as pe
import worked_example as we

# ---------------------------------------------------------------------------
# Palette: owned by the 0xPARC figure module; read by parsing, never executed.
# ---------------------------------------------------------------------------
PALETTE_OWNER = ROOT.parent / '0xPARC-challenge/tools/paper_network_figures.py'


def _palette():
    tree = ast.parse(PALETTE_OWNER.read_text())
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
            names = [t.id for t in node.targets[0].elts] if isinstance(node.targets[0], ast.Tuple) else []
            for name, value in zip(names, node.value.elts):
                if isinstance(value, ast.Constant):
                    found[name] = value.value
    need = ('TEAL', 'ORANGE', 'BLUE', 'GREY', 'PALE', 'LIGHT', 'INK')
    missing = [n for n in need if n not in found]
    if missing:
        raise RuntimeError(f'palette owner lacks {missing}: {PALETTE_OWNER}')
    return {n: found[n] for n in need}


PAL = _palette()
TEAL, ORANGE, BLUE, GREY, PALE, LIGHT, INK = (PAL[k] for k in ('TEAL', 'ORANGE', 'BLUE', 'GREY', 'PALE', 'LIGHT', 'INK'))
SOFT = '#c7cdd3'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
    'text.color': INK, 'axes.labelcolor': INK, 'xtick.color': INK,
    'ytick.color': INK, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#CBD2D8', 'pdf.fonttype': 42, 'savefig.dpi': 180})
INPUTS = {}
FIGURE_CHECKS = {}
L = pe.Ledger()


def read(rel):
    p = ROOT / rel
    INPUTS[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text())


def save(fig, name, data, checks):
    """Write vector PDF, PNG preview and the figure's data, after its checks passed."""
    fig.savefig(OUT / (name + '.pdf'), bbox_inches='tight', metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(OUT / (name + '.png'), bbox_inches='tight')
    plt.close(fig)
    (OUT / (name + '.json')).write_text(json.dumps({'checks': checks, 'data': data}, indent=1, default=str) + '\n')
    FIGURE_CHECKS[name] = checks


def gm(xs):
    return math.exp(st.mean(math.log(x) for x in xs))


def tex(s):
    return str(s).replace('_', r'\_')


# ---------------------------------------------------------------------------
# Phase 1 evidence (the original direct-index compiler), checked as before.
# ---------------------------------------------------------------------------
BASE = 'results/direct_index_v4_optimization_repair2/lead_review/'
d = read(BASE + 'final/runs.json')
prov = read(BASE + 'final/provenance.json')
audit = read(BASE + 'measurement_audit.json')
verification = read(BASE + 'verification/summary.json')
comparison = read(BASE + 'comparison/runs.json')
historical = read('results/comparison.json')
extra_manifest = read('results/direct_index_v4_optimization/baseline/extra_corpus_manifest.json')
assert d['acceptance_gates']['all_passed']['passed']
assert verification['status'] == 'PASS' and not verification['failures']
assert sum(r.get('tests', 0) or 0 for r in verification['records']) == 351
for name, digest in prov['source_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    INPUTS[name] = digest
for name, digest in prov['protected_sha256'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    INPUTS[name] = digest
assert prov['export_sha256'] == 'd14bf39b450aaa5fe73c41a3236980e219089e527ae43007781d78e0059a5864'
assert hashlib.sha256((ROOT / '.build/direct_index/compiler.py').read_bytes()).hexdigest() == prov['export_sha256']
frozen_path = 'results/direct_index_v4_optimization/baseline/snapshot/compiler_frozen.py'
assert hashlib.sha256((ROOT / frozen_path).read_bytes()).hexdigest() == prov['frozen_export_sha256']
INPUTS[frozen_path] = prov['frozen_export_sha256']
programs = d['analysis']['programs']
arms = d['analysis']['arms']
rows = d['runs']
extra = d['extra_corpus']['runs']
for rr, pp, repeats in [(rows, programs, 15), (extra, d['extra_corpus']['analysis']['programs'], 3)]:
    expected = {(a, p, r) for a in arms for p in pp for r in range(repeats)}
    assert len(rr) == len(expected)
    assert {(r['arm'], r['program'], r['repeat']) for r in rr} == expected
    assert all(r['correctness'] == 'PASS' and r['exit_code'] == 0 and not r['timed_out'] for r in rr)
    for mode in ['bootstrap', 'full']:
        metric = lambda arm: {(r['program'], r['repeat']): (r['cycles'], r['scratch']) for r in rr if r['arm'] == arm}
        assert metric('frozen_' + mode) == metric('candidate_' + mode)


def subset(arm, program=None):
    return [r for r in rows if r['arm'] == arm and (program is None or r['program'] == program)]


def metric(arm, program, field):
    vals = {r[field] for r in subset(arm, program)}
    assert len(vals) == 1
    return vals.pop()


def median(arm, program, field='compile_seconds'):
    return st.median(r[field] for r in subset(arm, program))


serial = {p['program']: p['runs']['serial'][0] for p in historical['programs']}
scores = {}
for a in arms:
    scores[a] = gm(math.sqrt(serial[p]['cycles'] * serial[p]['scratch'] /
                             (metric(a, p, 'cycles') * metric(a, p, 'scratch'))) for p in programs)
    assert math.isclose(scores[a], d['analysis']['scores'][a]['combined_score'], rel_tol=1e-13)
for mode in ['bootstrap', 'full']:
    ratio = gm(median('frozen_' + mode, p) / median('candidate_' + mode, p) for p in programs)
    assert math.isclose(ratio, audit['speedups'][mode]['point'], rel_tol=1e-13)
extra_serial = {p['name']: p for p in extra_manifest['programs']}
extra_metrics = {}
for a in arms:
    extra_metrics[a] = {}
    for p in extra_serial:
        values = {(r['cycles'], r['scratch']) for r in extra if r['arm'] == a and r['program'] == p}
        assert len(values) == 1, (a, p)
        extra_metrics[a][p] = values.pop()
    score = gm(math.sqrt(extra_serial[p]['serial_cycles'] * extra_serial[p]['serial_scratch'] /
                         math.prod(extra_metrics[a][p])) for p in extra_serial)
    assert math.isclose(score, d['extra_corpus']['score_distribution'][a]['combined_score_geomean'], rel_tol=1e-13)
    accepted = sum(r.get('optimiser', {}).get('accepted', 0) for r in extra if r['arm'] == a)
    assert accepted == d['extra_corpus']['score_distribution'][a]['accepted_improvements']
improved = sorted(p for p in extra_serial if
                  math.prod(extra_metrics['candidate_full'][p]) < math.prod(extra_metrics['candidate_bootstrap'][p]))
assert len(improved) == 6
assert all(math.prod(extra_metrics['candidate_full'][p]) <= math.prod(extra_metrics['candidate_bootstrap'][p])
           for p in extra_serial)

F = BASE + 'final/runs.json'
L.ptr('pOneScore', F, ['analysis', 'scores', 'candidate_full', 'combined_score'], 'f6', claim='original direct, 8 public programs')
L.ptr('pOneClassical', F, ['analysis', 'scores', 'classical', 'combined_score'], 'f6')
L.computed('pOneGain', scores['candidate_full'] / scores['classical'] - 1, 'pct2', F,
           'analysis.scores candidate_full / classical - 1')
for arm, key in (('classical', 'Cl'), ('candidate_bootstrap', 'Boot'), ('candidate_full', 'Full')):
    L.ptr(f'pOneExtra{key}', F, ['extra_corpus', 'score_distribution', arm, 'combined_score_geomean'], 'f6')
L.ptr('pOneAccepted', F, ['extra_corpus', 'score_distribution', 'candidate_full', 'accepted_improvements'], 'int')
L.computed('pOneImproved', len(improved), 'int', F, 'extra_corpus runs: programs whose full product < bootstrap product')
L.computed('pOneExtraN', len(extra_serial), 'int', 'results/direct_index_v4_optimization/baseline/extra_corpus_manifest.json', 'len(programs)')
L.ptr('pOneSpeedFull', BASE + 'measurement_audit.json', ['speedups', 'full', 'point'], 'f3')
L.ptr('pOneSpeedFullLo', BASE + 'measurement_audit.json', ['speedups', 'full', 'low'], 'f3')
L.ptr('pOneSpeedFullHi', BASE + 'measurement_audit.json', ['speedups', 'full', 'high'], 'f3')
L.ptr('pOneSpeedBoot', BASE + 'measurement_audit.json', ['speedups', 'bootstrap', 'point'], 'f3')
L.ptr('pOneWorkerFull', 'results/direct_index_v4_optimization_repair2/final/runs.json',
      ['analysis', 'ratios', 'full_candidate_vs_frozen', 'geometric_mean_of_per_program_medians'], 'f3')
L.ptr('pOneWorkerBoot', 'results/direct_index_v4_optimization_repair2/final/runs.json',
      ['analysis', 'ratios', 'bootstrap_candidate_vs_frozen', 'geometric_mean_of_per_program_medians'], 'f3')
L.derived('pOneSlowBoot', 'classical_relative', 'f2', mode='bootstrap', claim='candidate/classical, geometric mean of per-program medians')
L.derived('pOneSlowFull', 'classical_relative', 'f1', mode='full')
L.derived('pOneTests', 'tests_total', 'int', source=BASE + 'verification/summary.json')
L.computed('pOneReps', 15, 'int', F, 'runs: repetitions per (arm, program), asserted')

# ---------------------------------------------------------------------------
# Programme evidence (rounds 1-3), the P1 feasibility table and the worked example.
# ---------------------------------------------------------------------------
pe.build_programme_ledger(L)
phase2_metrics = pe.generate()
W = we.compute()
WE_SRC = 'paper/generated/worked_example.json (worked_example.compute)'
(OUT / 'worked_example.json').write_text(json.dumps(W, indent=1, default=str) + '\n')
M = W['methods']
names = {'serial': 'Serial', 'starter': 'Starter', 'classical': 'Classical',
         'direct_phase1': 'Original direct', 'C1': 'C1'}
for key in names:
    for f in ('C', 'S', 'J'):
        L.computed(f'we{key.replace("_", "").capitalize()}{f}', M[key][f], 'int', WE_SRC, f'methods.{key}.{f}')
L.computed('weCapCcap', W['caps']['Ccap'], 'int', WE_SRC, 'caps.Ccap')
L.computed('weCapScap', W['caps']['Scap'], 'int', WE_SRC, 'caps.Scap')
L.computed('weCapLC', W['caps']['LC'], 'int', WE_SRC, 'caps.LC')
L.computed('weCapLS', W['caps']['LS'], 'int', WE_SRC, 'caps.LS')
L.computed('weCapJ', W['caps']['J0'], 'int', WE_SRC, 'caps.J0')
L.computed('weHorizon', W['horizon'], 'int', WE_SRC, 'horizon')
L.computed('weCatalogue', len(W['catalogue']), 'int', WE_SRC, 'len(catalogue)')
L.computed('weCombDeclared', W['combinations_declared'], 'int', WE_SRC, 'combinations_declared')
L.computed('weCombRoot', W['combinations_root'], 'int', WE_SRC, 'combinations_root')
L.computed('weRootCerts', len(W['root_certificates']), 'int', WE_SRC, 'len(root_certificates)')
L.computed('weChildCerts', len(W['child_certificates']), 'int', WE_SRC, 'len(child_certificates)')
L.computed('weEdges', W['edges_total'], 'int', WE_SRC, 'edges_total')
L.computed('weLooksR', W['child_edge_looks']['R0'], 'int', WE_SRC, 'child_edge_looks.R0')
L.computed('weLooksC', W['child_edge_looks']['C1'], 'int', WE_SRC, 'child_edge_looks.C1')
last = W['subtree'][-1]
L.computed('weSubChildren', last['children'], 'int', WE_SRC, 'subtree[-1].children')
L.computed('weSubR', last['looks_R0'], 'int', WE_SRC, 'subtree[-1].looks_R0')
L.computed('weSubC', last['looks_C1'], 'int', WE_SRC, 'subtree[-1].looks_C1')
L.computed('weSubCerts', last['certificates'], 'int', WE_SRC, 'subtree[-1].certificates')
L.computed('weSubRatio', last['looks_C1'] / last['looks_R0'], 'f2', WE_SRC, 'subtree[-1].looks_C1 / looks_R0')
L.computed('weEpochs', W['epochs']['count'], 'int', WE_SRC, 'epochs.count')
L.computed('weImprovements', len(W['epochs']['steps']), 'int', WE_SRC, 'len(epochs.steps)')
L.computed('weNodes', W['epochs']['nodes'], 'int', WE_SRC, 'epochs.nodes')
L.computed('weQueries', W['first_answer_queries']['queries'], 'int', WE_SRC, 'first_answer_queries.queries')
L.computed('weOps', len(W['operations']), 'int', WE_SRC, 'len(operations)')
for i, step in enumerate(W['epochs']['steps']):
    L.computed(f'weStep{"ABC"[i]}C', step['to'][0], 'int', WE_SRC, f'epochs.steps[{i}].to[0]')
    L.computed(f'weStep{"ABC"[i]}S', step['to'][1], 'int', WE_SRC, f'epochs.steps[{i}].to[1]')
S_ = W['scale']
L.computed('weScaleOps', S_['operations'], 'int', WE_SRC, 'scale.operations')
L.computed('weScaleFirstJ', S_['first_CSJ'][2], 'int', WE_SRC, 'scale.first_CSJ[2]')
L.computed('weScaleFinalJ', S_['final_CSJ'][2], 'int', WE_SRC, 'scale.final_CSJ[2]')
L.computed('weScaleNodes', S_['nodes'], 'int', WE_SRC, 'scale.nodes')
L.computed('weStarterScore', W['starter_public']['score'], 'f6', WE_SRC, 'starter_public.score (starter = serial on all 8)')
for seed in ('980183', '980026'):
    L.computed(f'weQone{seed}J', W['q1'][seed]['first_CSJ'][2], 'int', WE_SRC, f'q1.{seed}.first_CSJ[2]')
    L.computed(f'weQone{seed}C', W['q1'][seed]['first_CSJ'][0], 'int', WE_SRC, f'q1.{seed}.first_CSJ[0]')
    L.computed(f'weQone{seed}S', W['q1'][seed]['first_CSJ'][1], 'int', WE_SRC, f'q1.{seed}.first_CSJ[1]')
for tag, path in (('hCOne', 'research/third_round_candidate.py'), ('hRZero', 'research/efficiency_search.py'),
                  ('hExpCOne', 'results/phase2_structural_encoding/third_round_20260925_resume/exports/C1/compiler.py'),
                  ('hExpRZero', 'results/phase2_structural_encoding/third_round_20260925_resume/exports/R0/compiler.py'),
                  ('hPOne', '.build/direct_index/compiler.py')):
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    L.computed(tag, digest if tag == 'hCOne' else digest[:16], 'str', path, 'sha256 of file bytes')
assert L.value('hCOne') == we.C1_SHA

# Definitional machine constants, read from the challenge's own machine module.
MACH = '.reference/machine.py'
L.computed('mWords', we.machine.SCRATCH_WORDS, 'int', MACH, 'SCRATCH_WORDS')
L.computed('mVlen', we.machine.VLEN, 'int', MACH, 'VLEN')
L.computed('mBits', (we.machine.WORD_MASK + 1).bit_length() - 1, 'int', MACH, 'WORD_MASK bit width')
L.computed('mTwoSlot', we.machine.ENGINE_LIMITS['load'], 'int', MACH, 'ENGINE_LIMITS load/scalar/vector')
L.computed('mOneSlot', we.machine.ENGINE_LIMITS['store'], 'int', MACH, 'ENGINE_LIMITS store/flow')
assert {we.machine.ENGINE_LIMITS[e] for e in ('load', 'scalar', 'vector')} == {2}
assert {we.machine.ENGINE_LIMITS[e] for e in ('store', 'flow')} == {1}
L.computed('mPublic', len(W['starter_public']['programs']), 'int', '.reference/programs', 'number of public programs')

# Frozen compile times for the worked example (never measured here).
MB = 'mixed_broadcast'
for key, source, arm in (('weTimeSerial', BASE + 'comparison/runs.json', 'serial'),
                         ('weTimeClassical', BASE + 'final/runs.json', 'classical'),
                         ('weTimeDirect', BASE + 'final/runs.json', 'candidate_full')):
    raw = pe.DERIVATIONS['phase1_median_seconds'](source=source, arm=arm, program=MB)
    L._put(key, 1000 * raw, 'f3', {'kind': 'derived-ms', 'derivation': 'phase1_median_seconds',
                                    'arguments': {'source': source, 'arm': arm, 'program': MB},
                                    'source': source, 'claim': 'median compile-call milliseconds'})
for arm in ('R0', 'C1'):
    for mode, tag in (('wall:1.0', 'Full'), ('wall:0.01', 'Short')):
        raw = pe.DERIVATIONS['public_median_seconds'](program_sha=W['program_object_sha256'], arm=arm, mode=mode)
        L._put(f'weTime{arm}{tag}', 1000 * raw, 'f1', {'kind': 'derived-ms', 'derivation': 'public_median_seconds',
               'arguments': {'program_sha': W['program_object_sha256'], 'arm': arm, 'mode': mode},
               'source': pe.DERIVATION_SOURCES['public_median_seconds'], 'claim': f'median compile-call ms, {mode}'})
        for field in ('cycles', 'scratch'):
            L.derived(f'wePub{arm}{tag}{field}', 'public_row', 'int', program_sha=W['program_object_sha256'],
                      arm=arm, mode=mode, field=field)
    raw = pe.DERIVATIONS['public_median_seconds'](program_sha=W['program_object_sha256'], arm=arm, mode='wall:0.1')
    L._put(f'weTime{arm}', 1000 * raw, 'f1', {'kind': 'derived-ms', 'derivation': 'public_median_seconds',
                                              'arguments': {'program_sha': W['program_object_sha256'], 'arm': arm, 'mode': 'wall:0.1'},
                                              'source': pe.DERIVATION_SOURCES['public_median_seconds'],
                                              'claim': 'median compile-call milliseconds, 0.1 s allowance, 5 runs'})
    assert pe.DERIVATIONS['public_row'](program_sha=W['program_object_sha256'], arm=arm, mode='wall:0.1', field='J') == M['C1']['J']

# ---------------------------------------------------------------------------
# Figure helpers in the 0xPARC style
# ---------------------------------------------------------------------------
ENGINE_COLOUR = {'load': TEAL, 'vector': BLUE, 'scalar': GREY, 'store': ORANGE, 'flow': INK}


def node(ax, xy, label, *, colour=TEAL, size=850, light=False, font=10):
    ax.scatter(*xy, s=size, color=PALE if light else colour, edgecolor='white', linewidth=1.5, zorder=4)
    ax.text(*xy, label, ha='center', va='center', color=INK if light else 'white', fontsize=font, zorder=5)


def edge(ax, a, b, label=None, *, colour=GREY, radius=0, shift=(0, .15), shrink=17, lw=1.2):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=10,
                                 connectionstyle=f'arc3,rad={radius}', shrinkA=shrink, shrinkB=shrink,
                                 color=colour, lw=lw, zorder=2))
    if label:
        ax.text((a[0] + b[0]) / 2 + shift[0], (a[1] + b[1]) / 2 + shift[1], label, ha='center', va='center',
                fontsize=8.5, color=INK, bbox=dict(facecolor='white', edgecolor='none', pad=1), zorder=3)


def box(ax, xy, text, *, width=1.9, height=.9, colour=PALE, edgecolour=TEAL, font=8.5, textcolour=INK):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x - width / 2, y - height / 2), width, height,
                                boxstyle='round,pad=0.02,rounding_size=0.12', facecolor=colour,
                                edgecolor=edgecolour, lw=1.2, zorder=3))
    ax.text(x, y, text, ha='center', va='center', fontsize=font, color=textcolour, zorder=4)


def pattern(ax, rows, labels, width, font=9):
    """0xPARC matrix style: 1 teal, 0 light, free coordinate '*' pale orange."""
    data = np.array([[2 if c == '*' else int(c) for c in r] for r in rows])
    ax.imshow(data, cmap=ListedColormap([LIGHT, TEAL, '#ffead8']), vmin=0, vmax=2, aspect='auto',
              interpolation='nearest')
    for (r, c), v in np.ndenumerate(data):
        ax.text(c, r, '*' if v == 2 else str(v), ha='center', va='center',
                color='white' if v == 1 else (ORANGE if v == 2 else GREY), fontsize=font)
    ax.set_xticks(range(width), [f'x{i}' for i in range(width)])
    ax.set_yticks(range(len(labels)), labels)
    ax.tick_params(length=0)
    ax.set_xticks(np.arange(-.5, width, 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=1)
    ax.tick_params(which='minor', length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)


def cube_bits(n, anchor, free):
    return ''.join('*' if (free >> i) & 1 else str((anchor >> i) & 1) for i in range(n))


def members(n, anchor, free):
    return {i for i in range(1 << n) if (i & (((1 << n) - 1) ^ free)) == anchor}


# ---------------------------------------------------------------------------
# F1: the program as a network, and the machine it runs on
# ---------------------------------------------------------------------------
ops = W['operations']
edges = W['edges']
lat = {o['id']: o['latency'] for o in ops}
assert all(lag == lat[u] for u, v, lag in edges), 'edge lag must equal producer latency'
depth = {}
for o in ops:
    depth[o['id']] = max([depth[u] + 1 for u, v, _ in edges if v == o['id']], default=0)
layers = defaultdict(list)
for o in ops:
    layers[depth[o['id']]].append(o['id'])
pos = {}
for dd, members_ in layers.items():
    for k, i in enumerate(members_):
        pos[i] = (dd * 2.1, 1.3 * ((len(members_) - 1) / 2 - k))
fig = plt.figure(figsize=(10.6, 3.9))
grid = fig.add_gridspec(1, 2, width_ratios=[2.35, 1], wspace=.12)
ax = fig.add_subplot(grid[0, 0]); ax.axis('off')
ax.set_title(f'A. {W["program"]}: operations and their dependences', loc='left', fontsize=10.5)
def layer_gap(u, v):
    return depth[v] - depth[u]


for u, v, lag in edges:
    long_ = layer_gap(u, v) > 1
    edge(ax, pos[u], pos[v], f'{lag}', radius=-.32 if long_ else 0,
         shift=(0, .62) if long_ else (0, .16))
for o in ops:
    node(ax, pos[o['id']], str(o['id']), colour=ENGINE_COLOUR[o['engine']], size=780)
    ax.text(pos[o['id']][0], pos[o['id']][1] - .42, f"{o['op']}\n{o['writes']}", ha='center', va='top', fontsize=7.6)
ax.text(0, -2.55, 'Arrow labels: latency (cycles) before the consumer may issue.', fontsize=8, color=GREY)
ax.set(xlim=(-.6, 9.1), ylim=(-2.75, 2.3))
ax = fig.add_subplot(grid[0, 1])
limits = W['engine_limits']
engines = list(limits)
for r, e in enumerate(engines):
    for s in range(limits[e]):
        ax.add_patch(Rectangle((s, r - .38), .85, .76, facecolor=ENGINE_COLOUR[e], edgecolor='white'))
    used = [o for o in ops if o['engine'] == e]
    ax.text(2.2, r, f'{len(used)} op' + ('' if len(used) == 1 else 's') + ' in this program', va='center', fontsize=8)
ax.set_yticks(range(len(engines)), engines); ax.set_xticks([])
ax.set(xlim=(-.2, 5.2), ylim=(len(engines) - .5, -.5))
ax.set_title('B. Issue slots per cycle, by engine', loc='left', fontsize=10.5)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
save(fig, 'we_program', {'operations': ops, 'edges': edges, 'engine_limits': limits},
     {'edge_lags_equal_producer_latency': True, 'operations': len(ops), 'edges': len(edges)})

# ---------------------------------------------------------------------------
# F2: five methods, one program: schedules and scratch layouts
# ---------------------------------------------------------------------------
order = ['serial', 'starter', 'classical', 'direct_phase1', 'C1']
cmax = max(M[k]['C'] for k in order)
smax = max(M[k]['S'] for k in order)
fig, axes = plt.subplots(2, 5, figsize=(11.4, 5.6), gridspec_kw={'height_ratios': [1, 1.9], 'hspace': .32, 'wspace': .12})
checks = {}
widths = W['widths']
producers = W['producers']
for col, key in enumerate(order):
    m = M[key]
    times = {int(k): v for k, v in m['times'].items()}
    ax = axes[0, col]
    occupancy = defaultdict(list)
    for o in ops:
        occupancy[(o['engine'], times[o['id']])].append(o['id'])
    for (e, t), ids in occupancy.items():
        assert len(ids) <= limits[e], (key, e, t)
        r = engines.index(e)
        ax.add_patch(Rectangle((t - .45, r - .42), .9, .84, facecolor=ENGINE_COLOUR[e], edgecolor='white'))
        ax.text(t, r, ','.join(map(str, ids)), ha='center', va='center', color='white', fontsize=6.8)
    ax.set(xlim=(-.6, cmax - .4), ylim=(len(engines) - .5, -.5))
    ax.set_yticks(range(len(engines)), engines if col == 0 else [])
    ax.set_xticks(range(0, cmax, 2)); ax.tick_params(labelsize=7, length=0)
    ax.set_title(f"{names[key]}\nC = {m['C']}, S = {m['S']}, J = {m['J']}", fontsize=9)
    ax.grid(axis='x', alpha=.15)
    ax = axes[1, col]
    rects = []
    for v, (b, e_) in m['lifetimes'].items():
        a = m['addresses'][v]
        w_ = widths[v]
        rects.append((b, e_, a, a + w_))
        ax.add_patch(Rectangle((b - .45, a), e_ - b + .9, w_, facecolor=TEAL if w_ > 1 else ORANGE,
                               edgecolor='white', lw=.8, alpha=.95))
        if w_ > 1:
            ax.text((b + e_) / 2, a + w_ / 2, v, ha='center', va='center', fontsize=5.8, color='white',
                    rotation=0 if e_ - b >= 3 else 90)
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            b1, e1, a1, z1 = rects[i]; b2, e2, a2, z2 = rects[j]
            assert not (b1 <= e2 and b2 <= e1 and a1 < z2 and a2 < z1), (key, 'scratch overlap')
    assert max(r[3] for r in rects) == m['S']
    ax.axhline(m['S'], color=INK, lw=.8, ls='--')
    ax.set(xlim=(-.6, cmax + .4), ylim=(smax + 1, 0))
    ax.set_xticks(range(0, cmax + 1, 2))
    ax.set_xlabel('cycle', fontsize=8); ax.tick_params(labelsize=7)
    if col == 0:
        ax.set_ylabel('scratch word')
    else:
        ax.set_yticklabels([])
    checks[key] = {'C': m['C'], 'S': m['S'], 'J': m['J'], 'engine_capacity_respected': True,
                   'no_live_scratch_overlap': True}
    for f in ('C', 'S', 'J'):
        assert str(m[f]) == L.value(f'we{key.replace("_", "").capitalize()}{f}')
fig.text(.1, .015, 'Top: engine × cycle, operation identifiers in each issue slot. Bottom: each value occupies its words from '
         'its write cycle to its last read (teal: 8-word vectors; orange: scalars). Dashed line: footprint S.', fontsize=7.8)
save(fig, 'we_methods', {k: M[k] for k in order}, checks)

# ---------------------------------------------------------------------------
# F3: the index-set view of one cycle query and one address query
# ---------------------------------------------------------------------------
sq = W['schedule_queries'][2]           # operation 2 (load gate0): an engine-full cycle removed
aq = next(q for q in W['address_queries'] if q['value'] == 'vgate')
fig = plt.figure(figsize=(10.8, 5.0))
grid = fig.add_gridspec(2, 2, height_ratios=[1.35, .75], hspace=.55, wspace=.32)
panel_checks = {}
for col, (q, title, universe_hi, field) in enumerate(
        [(sq, 'A. When may operation 2 issue?', 16, 'cycle'),
         (aq, 'B. Where may the vector vgate live?', 32, 'address')]):
    n = q['cubes'][0][0]
    interval_cubes = [c for iv in q['intervals'][:1] for c in iv['cubes']]
    removed_cubes = [c for iv in q['intervals'][1:] for c in iv['cubes']]
    rows_ = [cube_bits(*c) for c in interval_cubes] + [cube_bits(*c) for c in removed_cubes] + [cube_bits(*c) for c in q['cubes']]
    labels = ([f'range  {q["intervals"][0]["lo"]}..{q["intervals"][0]["hi"]}'] * len(interval_cubes) +
              [f'occupied  {iv["lo"]}..{iv["hi"]}' for iv in q['intervals'][1:] for _ in iv['cubes']] +
              ['survivor'] * len(q['cubes']))
    ax = fig.add_subplot(grid[0, col])
    pattern(ax, rows_, labels, n, font=8)
    ax.set_title(title, loc='left', fontsize=10.5)
    lo, hi = q['intervals'][0]['lo'], q['intervals'][0]['hi']
    span = set(range(lo, hi + 1))
    covered = set().union(*(members(*c) for c in interval_cubes))
    assert covered == span, 'interval cover must be exact'
    survivors = set().union(*(members(*c) for c in q['cubes']))
    assert min(survivors) == q['chosen_index']
    assert survivors <= span
    ax = fig.add_subplot(grid[1, col])
    for i in range(universe_hi):
        state = 'chosen' if i == q['chosen_index'] else 'survivor' if i in survivors else 'removed' if i in span else 'outside'
        colour = {'chosen': INK, 'survivor': TEAL, 'removed': '#f0d5d5', 'outside': LIGHT}[state]
        ax.add_patch(Rectangle((i - .45, -.45), .9, .9, facecolor=colour, edgecolor='white'))
        if state == 'chosen':
            ax.text(i, 0, str(i), ha='center', va='center', color='white', fontsize=7)
    ax.set(xlim=(-.7, universe_hi - .3), ylim=(-.7, .7)); ax.set_yticks([])
    ax.set_xticks(range(0, universe_hi, 2 if universe_hi <= 16 else 4)); ax.tick_params(labelsize=7, length=0)
    ax.set_xlabel(f'{field}: teal survives, pink removed, black = smallest survivor', fontsize=7.8)
    for s in ax.spines.values():
        s.set_visible(False)
    panel_checks[title[:1]] = {'range': [lo, hi], 'survivors': sorted(survivors), 'chosen': q['chosen_index'],
                               'cover_exact': True}
assert sq['chosen_index'] == int(M['direct_phase1']['times']['2']) == int(W['first_answer']['times']['2'])
assert aq['decoded'] == W['first_answer']['addresses']['vgate']
save(fig, 'we_index_queries', {'schedule_query': sq, 'address_query': aq}, panel_checks)
L.computed('weQTop', W['schedule_queries'].index(sq), 'int', WE_SRC, 'index of the displayed schedule query (operation id)')
L.computed('weQTlo', sq['intervals'][0]['lo'], 'int', WE_SRC, 'schedule_queries[2].intervals[0].lo')
L.computed('weQThi', sq['intervals'][0]['hi'], 'int', WE_SRC, 'schedule_queries[2].intervals[0].hi')
L.computed('weQTchosen', sq['chosen_index'], 'int', WE_SRC, 'schedule_queries[2].chosen_index')
L.computed('weQTsurv', len(sq['cubes']), 'int', WE_SRC, 'len(schedule_queries[2].cubes)')
L.computed('weQAhi', aq['intervals'][0]['hi'], 'int', WE_SRC, 'address query vgate: range hi')
L.computed('weQAchosen', aq['decoded'], 'int', WE_SRC, 'address query vgate: decoded address')

# ---------------------------------------------------------------------------
# F4: the C1 pipeline on the worked example
# ---------------------------------------------------------------------------
caps = W['caps']
path = W['epochs']['path']
steps_ = W['epochs']['steps']
fig = plt.figure(figsize=(11.2, 7.4))
grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.35], width_ratios=[1.25, 1], hspace=.32, wspace=.22)
ax = fig.add_subplot(grid[0, :]); ax.axis('off')
ax.set_title('A. One epoch of C1 on the worked example, with the counts the real modules produce', loc='left', fontsize=10.5)
stage = [
    ((0, 0), f'First answer\nindex queries\n{path[0][0]} × {path[0][1]} = {path[0][0] * path[0][1]}'),
    ((2.25, 0), f'Catalogue\n{len(W["catalogue"])} windows'),
    ((4.5, 0), f'Product box\nC ≤ {caps["Ccap"]}, S ≤ {caps["Scap"]}'),
    ((6.75, 0), f'Propagation\n{W["combinations_declared"]:,}\n→ {W["combinations_root"]:,}\n{len(W["root_certificates"])} certificates'),
    ((9.0, 0), 'Exact search\ndepth-first,\nproduct bound'),
    ((11.25, 0), f'Validated\nimprovement\n{steps_[0]["to"][0]} × {steps_[0]["to"][1]}'),
]
for i, (xy, text) in enumerate(stage):
    box(ax, xy, text, width=1.95, height=1.25, colour=PALE if i not in (0, 5) else TEAL,
        textcolour=INK if i not in (0, 5) else 'white')
    if i:
        edge(ax, (stage[i - 1][0][0] + .98, 0), (xy[0] - .98, 0), shrink=2)
ax.add_patch(FancyArrowPatch((11.25, -.65), (2.25, -.65), connectionstyle='arc3,rad=-0.18', arrowstyle='-|>',
                             mutation_scale=10, color=ORANGE, lw=1.3))
ax.text(6.75, -1.45, f'new epoch from the new incumbent: {W["epochs"]["count"]} epochs, {W["epochs"]["nodes"]:,} search nodes, '
        f'final {path[-1][0]} × {path[-1][1]} = {path[-1][0] * path[-1][1]}', ha='center', fontsize=8.5, color=ORANGE)
ax.set(xlim=(-1.1, 12.4), ylim=(-1.7, .8))
ax = fig.add_subplot(grid[1, 0])
cat = W['catalogue']
mat = np.zeros((len(cat), len(ops)))
for r, e in enumerate(cat):
    for o in e['window']:
        mat[r, o] = 1
ax.imshow(mat, cmap=ListedColormap([LIGHT, TEAL]), aspect='auto', interpolation='nearest')
ax.set_yticks(range(len(cat)), [f"{e['policy']}  r{e['radius']}" for e in cat], fontsize=7.5)
ax.set_xticks(range(len(ops)), [f't{o["id"]}' for o in ops], fontsize=7.5)
ax.set_xticks(np.arange(-.5, len(ops), 1), minor=True); ax.set_yticks(np.arange(-.5, len(cat), 1), minor=True)
ax.grid(which='minor', color='white', lw=1); ax.tick_params(which='both', length=0)
for s in ax.spines.values():
    s.set_visible(False)
k8 = next(i for i, e in enumerate(cat) if e['policy'] == 'k8_latest')
ax.add_patch(Rectangle((-.5, k8 - .5), len(ops), 1, fill=False, edgecolor=ORANGE, lw=2))
ax.set_title('B. The catalogue: which decisions each question reopens', loc='left', fontsize=10.5)
ax = fig.add_subplot(grid[1, 1])
cs = np.linspace(6, 20, 300)
J0 = caps['J0']
ax.plot(cs, J0 / cs, color=GREY, lw=1)
ax.text(19.6, J0 / 19.6 + .6, f'C × S = {J0}', fontsize=8, ha='right', color=GREY)
ax.add_patch(Rectangle((caps['LC'], caps['LS']), caps['Ccap'] - caps['LC'], caps['Scap'] - caps['LS'], facecolor=PALE,
                       edgecolor=TEAL, lw=1.2, ls='--', zorder=0))
ax.text(caps['Ccap'] - .15, caps['LS'] + .4, 'product box of k8_latest', ha='right', va='bottom', fontsize=7.8, color=TEAL)
xs, ys = zip(*path)
ax.plot(xs, ys, color=ORANGE, lw=1.4, marker='o', zorder=3)
for i, (x, y) in enumerate(path):
    ax.annotate(f'e{i}  {x}×{y}', (x, y), xytext=(6, -2 if i % 2 else 7), textcoords='offset points', fontsize=7.8)
ax.set(xlim=(6, 20), ylim=(4, 30), xlabel='cycles C', ylabel='scratch words S')
ax.set_title('C. The incumbent, epoch by epoch, in the (C, S) plane', loc='left', fontsize=10.5)
ax.grid(alpha=.15)
assert all(x * y < prev[0] * prev[1] for (x, y), prev in zip(path[1:], path[:-1])), 'each epoch strictly improves J'
assert caps['LC'] <= path[1][0] <= caps['Ccap'] and caps['LS'] <= path[1][1] <= caps['Scap']
save(fig, 'we_pipeline', {'catalogue': cat, 'caps': caps, 'path': path, 'steps': steps_,
                          'combinations': [W['combinations_declared'], W['combinations_root']]},
     {'strict_improvement_each_epoch': True, 'first_improvement_inside_product_box': True,
      'epochs': W['epochs']['count'], 'nodes': W['epochs']['nodes'],
      'trace_equal_R0_C1': W['epochs']['trace_sha256_R0'] == W['epochs']['trace_sha256_C1']})

# ---------------------------------------------------------------------------
# F5: one propagation step, and the shared branch state
# ---------------------------------------------------------------------------
decl = {int(k): v for k, v in W['declared_domains'].items()}
root = {int(k): v for k, v in W['root_domains'].items()}
child = {int(k): v for k, v in W['child_domains'].items()}
dec_op, dec_val = W['child_decision']
L.computed('weChildOp', dec_op, 'int', WE_SRC, 'child_decision[0]')
L.computed('weChildVal', dec_val, 'int', WE_SRC, 'child_decision[1]')
L.computed('tQoneSeed', 980183, 'str', pe.T3 + 'stages/C_wall/rows.jsonl', 'seed with the largest J gap among the 1 s losses (named in REVIEW.md)')
root_reason = {}
for rule, u, v, lag, bound, removed in W['root_certificates']:
    for x in removed:
        root_reason[(v if rule == 'PL' else u, x)] = f'{rule}'
child_reason = {}
for rule, u, v, lag, bound, removed in W['child_certificates']:
    for x in removed:
        child_reason[(v if rule == 'PL' else u, x)] = f'{rule}'
fig = plt.figure(figsize=(11.8, 4.9))
grid = fig.add_gridspec(1, 3, width_ratios=[1.5, 1.25, .85], wspace=.28)
ax = fig.add_subplot(grid[0, 0])
tmax = max(max(v) for v in decl.values()) + 1
for r, op in enumerate(sorted(decl)):
    for t in range(tmax):
        if t not in decl[op]:
            colour, text, tc = 'white', '', GREY
        elif t not in root:
            colour, text, tc = LIGHT, '', GREY
        if t in decl[op] and t not in root[op]:
            colour, text, tc = LIGHT, root_reason.get((op, t), ''), GREY
        elif t in root[op] and op == dec_op and t == dec_val:
            colour, text, tc = INK, 'fix', 'white'
        elif t in root[op] and t not in child[op] and op == dec_op:
            colour, text, tc = '#f3d3bd', '', INK
        elif t in root[op] and t not in child[op]:
            colour, text, tc = ORANGE, child_reason.get((op, t), ''), 'white'
            assert (op, t) in child_reason, 'every child deletion carries a certificate'
        elif t in root[op]:
            colour, text, tc = TEAL, '', 'white'
        ax.add_patch(Rectangle((t - .45, r - .42), .9, .84, facecolor=colour,
                               edgecolor='#dde3e8' if colour == 'white' else 'white'))
        if text:
            ax.text(t, r, text, ha='center', va='center', fontsize=6.3, color=tc)
    assert set(child[op]) <= set(root[op]) <= set(decl[op])
ax.set(xlim=(-.6, tmax - .4), ylim=(len(decl) - .5, -.5))
ax.set_yticks(range(len(decl)), [f't{o}' for o in sorted(decl)]); ax.set_xticks(range(tmax))
ax.set_xlabel('issue cycle', fontsize=8); ax.tick_params(labelsize=7.5, length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title(f'A. Fix t{dec_op} = {dec_val}: what the child loses, and why', loc='left', fontsize=10.5)
ax.text(-.5, len(decl) + .55, 'grey: removed at the root (certificate PL);  teal: still open in the child;\n'
        'orange: removed in the child, labelled by its certificate;  black: the decision;  pale orange: excluded by it', fontsize=7.4, va='top')
ax = fig.add_subplot(grid[0, 1]); ax.axis('off')
looked = {tuple(e) for e in W['child_edges_looked_C1']}
for u, v, lag in W['propagator_edges']:
    colour = ORANGE if (u, v, lag) in looked else '#aab5bf'
    long_ = layer_gap(u, v) > 1
    edge(ax, pos[u], pos[v], f'{lag}', colour=colour, lw=2.2 if colour == ORANGE else 1,
         radius=-.32 if long_ else 0, shift=(0, .62) if long_ else (0, .22), shrink=11)
for o in ops:
    node(ax, pos[o['id']], str(o['id']), colour=INK if o['id'] in W['change_record'] else GREY, size=330, font=8.5)
ax.set(xlim=(-.6, 9.1), ylim=(-2.2, 2.3))
ax.set_title('B. Constraints re-examined', loc='left', fontsize=10.5)
ax.text(-.4, -1.95, f"R0 re-checks every edge: {W['child_edge_looks']['R0']} looks.\n"
        f"C1 looks only at the orange edges: {W['child_edge_looks']['C1']} looks.\n"
        f"Black nodes: the change record {W['change_record']}.", fontsize=8, va='top')
assert len(looked) == W['child_edge_looks']['C1'] and looked <= {tuple(e) for e in W['propagator_edges']}
ax = fig.add_subplot(grid[0, 2])
sub = W['subtree']
x = np.arange(len(sub))
ax.bar(x - .2, [s['looks_R0'] for s in sub], .4, color=GREY, label='R0')
ax.bar(x + .2, [s['looks_C1'] for s in sub], .4, color=TEAL, label='C1')
ax.set_yscale('log'); ax.set_xticks(x, [f"{s['children']:,}" for s in sub], fontsize=7.5)
ax.set_xlabel('children built both ways', fontsize=8); ax.set_ylabel('precedence-edge looks', fontsize=8)
ax.legend(frameon=False, fontsize=8, loc='upper left')
ax.set_title('C. A whole subtree', loc='left', fontsize=10.5)
ax.text(.02, -.2, 'identical domains and certificate\nstreams at every child (asserted)', transform=ax.transAxes, fontsize=7.6, va='top')
save(fig, 'we_shared_state', {'declared': decl, 'root': root, 'child': child, 'decision': [dec_op, dec_val],
                              'root_certificates': W['root_certificates'], 'child_certificates': W['child_certificates'],
                              'edges': W['propagator_edges'], 'looked_C1': sorted(looked), 'subtree': sub},
     {'child_subset_of_root_subset_of_declared': True, 'edge_looks': W['child_edge_looks'],
      'subtree_identical_certificates': True, 'notebook_04_cross_check': W['notebook_cross_check']})

# ---------------------------------------------------------------------------
# F6: every measured pair, each against its own control and gate
# ---------------------------------------------------------------------------
R1C = pe.R1 + 'COMPARISON.json'
r1 = pe._load(R1C)
r2 = pe._load(pe.R2 + 'COMPARISON.json')
a0 = pe._load(pe.A0RUN + 'COMPARISON.json')
c3 = pe._load(pe.T3 + 'COMPARISON.json')
a0_acc = next(e for e in a0['entries'] if e['budget_seconds'] == 0.1 and e['corpus'] == 'heldout' and e['control'] == 'accepted_budgeted')
a0_cl = next(e for e in a0['entries'] if e['budget_seconds'] == 0.1 and e['corpus'] == 'heldout' and e['control'] == 'classical')


def from_log(point, lo, hi):
    return math.exp(-point), math.exp(-hi), math.exp(-lo)


quality_rows = [
    ('C1 / R0', 'round 3, 200 fresh, 97.5%', (c3['quality_ratio'], *c3['intervals_97_5']['quality']), c3['gate']['wall_primary_J_ratio_upper_max']),
    ('cell_a4cat_dfs / heap A4', 'round 2, 200 fresh, 98.75%', (r2['candidate_endpoints']['cell_a4cat_heap']['J_ratio'], *r2['candidate_endpoints']['cell_a4cat_heap']['J_ratio_interval_98_75']), 0.98),
    ('repaired A4 / cap512_wider', 'round 2, 200 fresh, 95%', from_log(r2['primary']['estimate'], *r2['primary']['interval_95']), None),
    ('A4 / A0', 'round 1, 200 fresh, 98.33%', from_log(r1['primary']['contrasts']['A0_frozen_phase2']['point'], *r1['primary']['contrasts']['A0_frozen_phase2']['interval']), None),
    ('A4 / accepted optimiser', 'round 1, 200 fresh, 98.33%', from_log(r1['primary']['contrasts']['accepted_budgeted']['point'], *r1['primary']['contrasts']['accepted_budgeted']['interval']), None),
    ('A4 / classical', 'round 1, 200 fresh, 98.33%', from_log(r1['primary']['contrasts']['classical']['point'], *r1['primary']['contrasts']['classical']['interval']), None),
    ('A0 / accepted optimiser', 'Phase 2, 100 held-out, 95%', from_log(a0_acc['quality_log_control_over_candidate']['point_estimate'], *a0_acc['quality_log_control_over_candidate']['intervals']['0.025-0.975']), None),
    ('A0 / classical', 'Phase 2, 100 held-out, 95%', from_log(a0_cl['quality_log_control_over_candidate']['point_estimate'], *a0_cl['quality_log_control_over_candidate']['intervals']['0.025-0.975']), None),
]
rb = r1['runtime_primary_bonferroni']
cost_rows = [
    ('C1 / R0, fixed work', 'round 3, 200 fresh, 97.5%', (c3['cost_ratio'], *c3['intervals_97_5']['cost']), c3['gate']['fixed_work_compile_ratio_upper_max']),
    ('cell_a4cat_dfs / heap A4', 'round 2, 200 fresh, 98.75%', (r2['candidate_endpoints']['cell_a4cat_heap']['compile_ratio'], *r2['candidate_endpoints']['cell_a4cat_heap']['compile_ratio_interval_98_75']), None),
    ('A4 / accepted optimiser', 'round 1, 200 fresh, 98.33%', (rb['accepted_budgeted:compile_seconds']['geometric_ratio_candidate_over_control'], *rb['accepted_budgeted:compile_seconds']['interval_ratio']), None),
    ('A4 / A0', 'round 1, 200 fresh, 98.33%', (rb['A0_frozen_phase2:compile_seconds']['geometric_ratio_candidate_over_control'], *rb['A0_frozen_phase2:compile_seconds']['interval_ratio']), None),
    ('A4 / classical', 'round 1, 200 fresh, 98.33%', (rb['classical:compile_seconds']['geometric_ratio_candidate_over_control'], *rb['classical:compile_seconds']['interval_ratio']), None),
    ('A0 / classical', 'Phase 2, 100 held-out, 95%', (a0_cl['compile_candidate_over_control_ratio'], *a0_cl['runtime_ratio_intervals_candidate_over_control']['compile']['0.025-0.975']), None),
]
for rows_ in (quality_rows, cost_rows):
    for label, pop, (p, lo, hi), gate in rows_:
        assert lo <= p <= hi, label
        if gate is not None:
            # C1's gates were met; the round-2 practical target (0.98) was not: TARGET_NOT_REACHED.
            assert (hi <= gate) == label.startswith('C1'), (label, hi, gate)
fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4), gridspec_kw={'wspace': .95})
for ax, rows_, title, xlabel in ((axes[0], quality_rows, 'A. Output quality: J ratio, candidate / control',
                                  'J ratio (log scale); below 1: candidate better'),
                                 (axes[1], cost_rows, 'B. Compile time: candidate / control',
                                  'time ratio (log scale); below 1: candidate faster')):
    for i, (label, pop, (p, lo, hi), gate) in enumerate(rows_):
        colour = TEAL if label.startswith('C1') else BLUE
        ax.errorbar(p, i, xerr=[[p - lo], [hi - p]], fmt='o', color=colour, capsize=3, ms=4.5)
        if gate is not None:
            ax.plot([gate, gate], [i - .35, i + .35], color=ORANGE, lw=2)
            ax.text(gate, i - .42, 'gate' if label.startswith('C1') else 'target (missed)', color=ORANGE, fontsize=7, ha='center', va='bottom')
    ax.axvline(1, color=GREY, lw=.8, ls=':')
    ax.set_xscale('log')
    ax.set_yticks(range(len(rows_)), [f'{lab}\n{pop}' for lab, pop, *_ in rows_], fontsize=7.4)
    ax.invert_yaxis(); ax.set_xlabel(xlabel, fontsize=8); ax.grid(axis='x', alpha=.15)
    ax.set_title(title, loc='left', fontsize=10)
axes[0].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
axes[0].set_xticks([0.85, 0.9, 0.95, 1.0], ['0.85', '0.90', '0.95', '1.00'])
save(fig, 'results_forest', {'quality': quality_rows, 'cost': cost_rows},
     {'points_inside_intervals': True, 'C1_upper_bounds_below_gates': True,
      'round2_target_missed_as_recorded': r2['candidate_endpoints']['verdict'],
      'comparators_never_chained': 'each row is one measured pair from its own frozen file'})

# ---------------------------------------------------------------------------
# F7: per program, C1/R0 at equal work against the size of the search
# ---------------------------------------------------------------------------
fixed = pe._rows('C_fixed_work')
cohort = pe._load(pe.T3 + 'cohort/COHORT_CHECKED.json')['programs']
by = defaultdict(lambda: defaultdict(list))
nodes = {}
for r in fixed:
    by[r['seed']][r['arm_id']].append(r['compile_call_seconds'])
    nodes.setdefault(r['seed'], set()).add(r['nodes'])
assert all(len(v) == 1 for v in nodes.values()), 'equal work: node counts identical across arms and repetitions'
points = []
for seed, a in by.items():
    points.append((next(iter(nodes[seed])), st.median(a['C1']) / st.median(a['R0']), cohort[str(seed)]['family'], st.median(a['R0'])))
ratios = sorted(p[1] for p in points)
probe = pe._load(pe.REV + 'RECOMPUTE.json')['probes']['per_program_cost_ratio']
assert math.isclose(min(ratios), probe['min']) and math.isclose(max(ratios), probe['max'])
assert math.isclose(st.median(ratios), probe['median']) and sum(r > 1 for r in ratios) == probe['programs_C1_slower']
fam_colour = dict(zip(sorted({p[2] for p in points}), [TEAL, ORANGE, BLUE, GREY, INK]))
fig, ax = plt.subplots(figsize=(7.4, 4.0))
for fam, colour in fam_colour.items():
    xs = [max(p[0], .8) for p in points if p[2] == fam]
    ys = [p[1] for p in points if p[2] == fam]
    ax.scatter(xs, ys, s=16, color=colour, label=fam, alpha=.85)
ax.set_xscale('log'); ax.axhline(1, color=GREY, lw=.8, ls=':')
ax.axhline(c3['cost_ratio'], color=TEAL, lw=1, ls='--')
ax.text(1.0, c3['cost_ratio'] - .045, f"pooled estimate {c3['cost_ratio']:.3f}", fontsize=7.8, color=TEAL)
ax.set_xlabel('search nodes per compilation at equal work (identical for R0 and C1; zero drawn at 0.8)', fontsize=8)
ax.set_ylabel('C1 / R0 compile-call time\n(median of 5 each)', fontsize=8)
ax.legend(frameon=False, fontsize=7.5, ncol=5, loc='upper center', bbox_to_anchor=(.5, 1.13))
ax.grid(alpha=.15)
save(fig, 'results_per_program', {'points': points}, {'programs': len(points), 'min': min(ratios), 'max': max(ratios),
     'median': st.median(ratios), 'C1_slower': sum(r > 1 for r in ratios), 'equal_nodes_both_arms': True})

# ---------------------------------------------------------------------------
# F8: Q1, speed changes the path under a real clock
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(10.6, 3.8))
grid = fig.add_gridspec(1, 2, width_ratios=[1.15, 1], wspace=.3)
ax = fig.add_subplot(grid[0, 0])
wtl = []
for i, budget in enumerate(('0.01', '0.1', '1.0')):
    w_, t_, l_ = c3['descriptive'][f'wall:{budget}_W_T_L_C1']
    wtl.append((budget, w_, t_, l_))
    ax.barh(i, w_, color=TEAL); ax.barh(i, t_, left=w_, color=LIGHT); ax.barh(i, l_, left=w_ + t_, color=ORANGE)
    if w_ >= 60:
        ax.text(w_ / 2, i, str(w_), ha='center', va='center', color='white', fontsize=8)
    else:
        ax.text(w_ + 8, i - .3, f'{w_} better', ha='left', va='center', color=TEAL, fontsize=7.5)
    ax.text(w_ + t_ / 2, i, str(t_), ha='center', va='center', fontsize=8)
    ax.text(1000 + 12, i, f'{l_} worse', va='center', fontsize=8, color=ORANGE)
ax.set_yticks(range(3), [f'{b} s' for b in ('0.01', '0.1', '1.0')]); ax.invert_yaxis()
ax.set_xlim(0, 1130); ax.set_xlabel('paired runs (200 fresh programs × 5): C1 better / equal / worse than R0', fontsize=8)
ax.set_title('A. Wall-clock allowance: per-run outcome', loc='left', fontsize=10)
ax = fig.add_subplot(grid[0, 1])
seed = '980183'
first = W['q1'][seed]['first_CSJ']
end = {arm: (pe.d_wall_seed(int(seed), arm, 'cycles'), pe.d_wall_seed(int(seed), arm, 'scratch')) for arm in ('R0', 'C1')}
cs = np.linspace(18, 26, 200)
for J, colour in ((first[2], GREY), (end['R0'][0] * end['R0'][1], TEAL), (end['C1'][0] * end['C1'][1], ORANGE)):
    ax.plot(cs, J / cs, color=colour, lw=.8, ls=':')
ax.scatter(*first[:2], color=GREY, s=40, zorder=3); ax.annotate(f'first answer {first[0]}×{first[1]}', first[:2], xytext=(6, 4), textcoords='offset points', fontsize=8)
for arm, colour in (('R0', TEAL), ('C1', ORANGE)):
    ax.scatter(*end[arm], color=colour, s=46, zorder=3)
    ax.annotate(f'{arm}, 1 s: {end[arm][0]}×{end[arm][1]} = {end[arm][0] * end[arm][1]}', end[arm], xytext=(6, -3), textcoords='offset points', fontsize=8, color=colour)
ax.set(xlim=(18, 26), ylim=(28, 48), xlabel='cycles C', ylabel='scratch words S')
ax.set_title(f'B. Program {seed}: same start, different local optimum', loc='left', fontsize=10)
ax.grid(alpha=.15)
assert first[2] > end['C1'][0] * end['C1'][1] > end['R0'][0] * end['R0'][1]
save(fig, 'results_q1', {'wtl': wtl, 'seed': seed, 'first': first, 'end': end},
     {'wtl_sums_1000': all(w_ + t_ + l_ == 1000 for _, w_, t_, l_ in wtl),
      'repetitions_agree_per_arm': True, 'first_answer_program_hash_matches_frozen_rows': True})

# ---------------------------------------------------------------------------
# Supplementary figures: the ladder and the factorial; Phase 1 figures
# ---------------------------------------------------------------------------
ladder = [s for s in r1['ladder_unadjusted_95'] if s['budget'] == 0.1]
fac = pe._load(pe.R2 + 'FACTORIAL.json')['budgets']['0.1']['factorial']
fig, axes = plt.subplots(1, 2, figsize=(10.8, 3.3), gridspec_kw={'wspace': .75})
ax = axes[0]
lab = [s['step'].replace('_deadline_control', '').replace('_product_search', '').replace('_propagated_search', '')
       .replace('_multiscale_search', '').replace('_frozen_phase2', '').replace('->', ' → ') for s in ladder]
for i, s in enumerate(ladder):
    q = s['quality']
    ax.errorbar(q['point'], i, xerr=[[q['point'] - q['interval'][0]], [q['interval'][1] - q['point']]], fmt='o', color=BLUE, capsize=3)
    ax.text(0.085, i, f"×{s['compile']['geometric_ratio_candidate_over_control']:.2f} time", va='center', fontsize=7.8, color=GREY)
ax.axvline(0, color=GREY, lw=.8, ls=':'); ax.set_yticks(range(len(lab)), lab); ax.invert_yaxis()
ax.set_xlim(-0.01, 0.11)
ax.set_xlabel('mean log(J control / J candidate); positive: step lowers J', fontsize=8)
ax.set_title(f"A. Round 1 ladder, {ladder[0]['quality']['programs']} fresh programs, {ladder[0]['budget']} s, 95%", loc='left', fontsize=10)
ax = axes[1]
for i, (key, label) in enumerate((('catalog_effect_a4_minus_a3', 'catalogue: A4 − A3'),
                                  ('traversal_effect_heap_minus_dfs', 'traversal: heap − DFS'),
                                  ('interaction', 'interaction'))):
    e = fac[key]
    ax.errorbar(e['estimate'], i, xerr=[[e['estimate'] - e['interval_95'][0]], [e['interval_95'][1] - e['estimate']]], fmt='o', color=BLUE, capsize=3)
    assert e['interval_95'][0] <= e['estimate'] <= e['interval_95'][1]
ax.axvline(0, color=GREY, lw=.8, ls=':'); ax.set_yticks(range(3), ['catalogue: A4 − A3', 'traversal: heap − DFS', 'interaction']); ax.invert_yaxis()
ax.set_xlabel('difference in log J (negative: lower J)', fontsize=8)
ax.set_title(f"B. Round 2 factorial, {fac['programs']} development programs, {fac['budget_seconds']} s, 95%", loc='left', fontsize=10)
save(fig, 'supp_ladder_factorial', {'ladder': ladder, 'factorial': {k: fac[k] for k in ('catalog_effect_a4_minus_a3', 'traversal_effect_heap_minus_dfs', 'interaction')}},
     {'ladder_steps': len(ladder), 'factorial_catalogue_interval_excludes_zero': fac['catalog_effect_a4_minus_a3']['interval_95'][1] < 0,
      'traversal_interval_spans_zero': fac['traversal_effect_heap_minus_dfs']['interval_95'][0] < 0 < fac['traversal_effect_heap_minus_dfs']['interval_95'][1]})


def expand(a, f, n=4):
    return {i for i in range(1 << n) if (i & (((1 << n) - 1) ^ f)) == a}


assert expand(1, 10) == {1, 3, 9, 11}
assert expand(1, 10) & expand(0, 7) == expand(1, 2) == {1, 3}
fig, ax = plt.subplots(figsize=(7.1, 2.1))
for y, (label, mem, color) in enumerate([
        ('A', expand(1, 10), GREY), ('B', expand(0, 7), ORANGE), ('A ∩ B', expand(1, 2), TEAL)]):
    ax.scatter(range(16), [y] * 16, s=95, color='#EDF1F3', zorder=1)
    ax.scatter(sorted(mem), [y] * len(mem), s=95, color=color, zorder=2)
ax.set_yticks(range(3), ['A: 1 + {0, 2, 8, 10}', 'B: {0, …, 7}', 'A ∩ B: 1 + {0, 2}'])
ax.set_xticks(range(16)); ax.set_xlabel('Decision index (not a physical memory address)')
ax.invert_yaxis(); ax.set_ylim(2.6, -.6); ax.spines[['left', 'bottom']].set_visible(False)
ax.tick_params(length=0); fig.tight_layout()
L.computed('exAnchor', 1, 'int', 'generate_figures.py schema example', 'anchor')
L.computed('exFree', 10, 'int', 'generate_figures.py schema example', 'free mask')
L.computed('exMembers', ', '.join(str(x - 1) for x in sorted(expand(1, 10))), 'str', 'generate_figures.py schema example', 'members minus anchor')
L.computed('exRangeHi', 7, 'int', 'generate_figures.py schema example', 'interval upper end')
L.computed('exResult', ', '.join(str(x - 1) for x in sorted(expand(1, 2))), 'str', 'generate_figures.py schema example', 'intersection minus anchor')
save(fig, 'schema_example', {'A': sorted(expand(1, 10)), 'B': sorted(expand(0, 7)), 'AB': sorted(expand(1, 2))},
     {'intersection_equals_cube_1_2': True})

fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.2), sharey=True)
for ax, field, title in zip(axes, ['cycles', 'scratch'], ['Emitted cycles', 'Scratch words']):
    for i, p in enumerate(programs):
        c, b = metric('classical', p, field), metric('candidate_bootstrap', p, field)
        ax.plot([c, b], [i, i], color=SOFT, lw=2)
        ax.scatter(c, i, color=ORANGE, marker='s', s=28, label='Classical' if i == 0 else None)
        ax.scatter(b, i, color=TEAL, s=29, label='Original direct' if i == 0 else None)
    ax.set_xlabel(title + ' · lower is better'); ax.grid(axis='x', alpha=.18)
axes[0].set_yticks(range(8), [p.replace('_', ' ') for p in programs]); axes[0].invert_yaxis()
axes[1].legend(loc='upper center', bbox_to_anchor=(.2, 1.22), ncol=2, frameon=False)
fig.tight_layout()
save(fig, 'output_quality', {p: {a: [metric(a, p, 'cycles'), metric(a, p, 'scratch')] for a in ('classical', 'candidate_bootstrap')} for p in programs},
     {'public_rows_constant_across_repetitions': True})

fig, ax = plt.subplots(figsize=(7.1, 3.5))
styles = [('classical', ORANGE, 's', 'Classical'), ('frozen_bootstrap', GREY, 'v', 'v3 bootstrap'),
          ('candidate_bootstrap', TEAL, 'o', 'v4 bootstrap'), ('frozen_full', GREY, '^', 'v3 full'),
          ('candidate_full', INK, 'D', 'v4 full')]
for j, (a, color, marker, label) in enumerate(styles):
    ax.scatter([median(a, p) * 1000 for p in programs], np.arange(8) + (j - 2) * .12, color=color, marker=marker, label=label, s=25)
ax.set_xscale('log'); ax.set_yticks(range(8), [p.replace('_', ' ') for p in programs]); ax.invert_yaxis()
ax.set_xlabel('Median compiler-call time (ms, logarithmic scale) · lower is better')
ax.grid(axis='x', alpha=.18); ax.legend(ncol=3, bbox_to_anchor=(.5, 1.23), loc='upper center', frameon=False)
fig.tight_layout()
save(fig, 'compile_times', {a: {p: median(a, p) for p in programs} for a, *_ in styles}, {'repetitions_per_cell': 15})

fig, ax = plt.subplots(figsize=(7.1, 2.8))
for i, p in enumerate(improved):
    before, after = extra_metrics['candidate_bootstrap'][p], extra_metrics['candidate_full'][p]
    reduction = 100 * (1 - math.prod(after) / math.prod(before))
    ax.plot([0, reduction], [i, i], color=SOFT, lw=2)
    ax.scatter(reduction, i, s=32, color=TEAL)
    ax.annotate(f'{before[0]} × {before[1]} → {after[0]} × {after[1]}', (reduction, i), xytext=(7, 0),
                textcoords='offset points', va='center', fontsize=8)
ax.set_yticks(range(len(improved)), [p.replace('additional_', 'Seed ') for p in improved])
ax.invert_yaxis(); ax.set_xlim(0, 47)
ax.set_xlabel('Cycle × scratch product reduction (%) · higher is better')
ax.set_title(f'Joint optimisation: {len(improved)} improved programs; {len(extra_serial) - len(improved)} unchanged', fontsize=10)
ax.grid(axis='x', alpha=.18); fig.tight_layout()
save(fig, 'optimizer_ablation', {p: [extra_metrics['candidate_bootstrap'][p], extra_metrics['candidate_full'][p]] for p in improved},
     {'improved': len(improved), 'no_program_worsened': True})

rounds = [read('results/direct_index_v4_optimization_repair/final/runs.json'),
          read('results/direct_index_v4_optimization_repair2/final/runs.json'), d]
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.6), sharey=True)
for ax, mode, target in zip(axes, ['bootstrap', 'full'], [1.2, 2.0]):
    for i, rd in enumerate(rounds):
        r = rd['analysis']['ratios'][mode + '_candidate_vs_frozen']
        x = r['geometric_mean_of_per_program_medians']; ci = r['paired_bootstrap_95']
        ax.errorbar(x, i, xerr=[[x - ci['low']], [ci['high'] - x]], fmt='o', color=TEAL, capsize=4)
        ax.annotate(f'{x:.3f}×', (x, i), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=8)
    ax.axvline(target, color=ORANGE, ls='--', lw=1)
    ax.set_title(mode.capitalize()); ax.set_xlabel('v3 time / v4 time · higher is better')
    ax.set_ylim(2.5, -.55); ax.grid(axis='x', alpha=.15)
axes[0].set_yticks(range(3), ['Repair 1 worker', 'Repair 2 worker', 'Repair 2 lead'])
fig.tight_layout()
save(fig, 'run_variability', {}, {'runs': 3})

fig, ax = plt.subplots(figsize=(6.6, 2.3))
n = np.arange(1, 17)
ax.plot(n, 2. ** (n - 1), color=ORANGE, marker='.', label='Odd parity: exact flat cube cover')
ax.plot(n, np.ones_like(n), color=TEAL, label='Unconstrained family: one cube')
ax.set_yscale('log', base=2); ax.set_xticks([1, 4, 8, 12, 16])
ax.set_xlabel('Number of Boolean coordinates n'); ax.set_ylabel('Required cubes')
ax.legend(frameon=False); ax.grid(alpha=.15); fig.tight_layout()
save(fig, 'representation_limits', {}, {'analytic': True})

# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def cell(key, raw, fmt, source, field):
    L.computed(key, raw, fmt, source, field)
    return L.value(key)


PS2 = pe.R2 + 'PUBLIC_SCORE.json'
pub2 = pe._load(PS2)['scores']
pub_rows = [
    ('Serial', 'yardstick', '--', cell('tabPubSerial', 1.0, 'f6', 'definition', 'score of serial against itself')),
    ('Starter', 'provided start', '--', L.value('weStarterScore')),
    ('Classical', 'external benchmark', '--', L.value('rTwoPubClassical')),
    ('Original direct (Phase 1)', 'our first version', 'default', L.value('pOneScore')),
    ('A0, structural encoding', 'our second version', f"{L.value('bB')} s", L.value('aZeroPub')),
    ('A4 (round one)', 'intermediate', f"{L.value('bB')} s", L.value('rOnePubAfour')),
    ('\\texttt{cap512\\_wider}', 'earlier optimiser', f"{L.value('bB')} s", L.value('rTwoPubCap')),
    ('\\texttt{cell\\_a4cat\\_dfs} (round two)', 'intermediate', f"{L.value('bB')} s", L.value('rTwoPubDfs')),
    ('R0', 'accepted baseline', f"{L.value('bA')} s", L.value('tPubSixR0A')),
    ('R0', '', f"{L.value('bB')} s and {L.value('bC')} s", L.value('tPubSixR0B')),
    ('C1', 'final proposal', f"{L.value('bA')} s", L.value('tPubSixC1A')),
    ('C1', '', f"{L.value('bB')} s and {L.value('bC')} s", L.value('tPubSixC1B')),
]
assert L.value('tPubSixR0B') == L.value('tPubSixR0C') and L.value('tPubSixC1B') == L.value('tPubSixC1C')
assert L.value('pOneScore') == L.value('rTwoPubDirect')
(OUT / 'tab_public.tex').write_text('\n'.join(' & '.join(r) + r' \\' for r in pub_rows) + '\n')

name_by_sha = {v['object_sha256']: k for k, v in W['starter_public']['programs'].items()}
short = lambda s: s.split('_', 1)[1]
perprog = []
for stem in sorted(W['starter_public']['programs']):
    p = short(stem)
    sha = W['starter_public']['programs'][stem]['object_sha256']
    ser = pub2['serial'][p]
    cl = pub2['arms']['classical@None']['per_program_CSJ_by_repetition'][p][0]
    di = pub2['arms']['accepted_bootstrap@None']['per_program_CSJ_by_repetition'][p][0]
    dfs = pub2['arms']['cell_a4cat_dfs@0.1']['per_program_CSJ_by_repetition'][p][0]
    c1 = [pe.d_public_row(sha, 'C1', 'wall:0.1', f) for f in ('cycles', 'scratch', 'J')]
    r0_ = [pe.d_public_row(sha, 'R0', 'wall:0.1', f) for f in ('cycles', 'scratch', 'J')]
    assert c1 == r0_ and W['starter_public']['programs'][stem]['serial'] == ser
    for arm_rows in (pub2['arms']['classical@None'], pub2['arms']['accepted_bootstrap@None'], pub2['arms']['cell_a4cat_dfs@0.1']):
        assert len({tuple(x) for x in arm_rows['per_program_CSJ_by_repetition'][p]}) == 1
    key = p.replace('_', '').replace('0', '')
    vals = [f'{ser[0]}×{ser[1]}', f'{cl[0]}×{cl[1]}', f'{di[0]}×{di[1]}', f'{c1[0]}×{c1[1]}', str(c1[2])]
    for tag, v in zip(('Ser', 'Cl', 'Di', 'COne', 'J'), vals):
        L.computed(f'tabPP{key}{tag}', v, 'str', f'{PS2} and {pe.T3}stages/C_public/rows.jsonl', f'{p}: {tag}')
    best = min(ser[0] * ser[1], cl[2], di[2], c1[2])
    perprog.append(tex(p) + ' & ' + ' & '.join(vals[:4]) + ' & ' + ' & '.join(
        (r'\textbf{' + str(j) + '}' if j == best else str(j)) for j in (ser[0] * ser[1], cl[2], di[2], c1[2])) + r' \\')
(OUT / 'tab_perprogram.tex').write_text('\n'.join(perprog) + '\n')

worked = []
mech = {
    'serial': 'fixed rule: one operation per bundle, a fresh address per value',
    'starter': 'fixed rule: the same as serial on this program',
    'classical': 'greedy priorities (critical path, first fit); never revisits a decision',
    'direct_phase1': 'every cycle and address is the smallest member of a queried cover; the four-operation optimiser finds nothing',
    'C1': 'reopens related windows, confines each to its product box, propagates with certificates and searches exactly',
}
def n_runs(source, arm):
    return len([r for r in pe._load(source)['runs'] if r['arm'] == arm and r['program'] == MB])


n_c1 = len([r for r in pe._rows('C_public') if r['program_sha256'] == W['program_object_sha256']
            and r['arm_id'] == 'C1' and r['mode_key'] == 'wall:1.0'])
time_key = {'serial': ('weTimeSerial', f"ms, median of {n_runs(BASE + 'comparison/runs.json', 'serial')}"),
            'starter': (None, 'not measured'),
            'classical': ('weTimeClassical', f"ms, median of {n_runs(BASE + 'final/runs.json', 'classical')}"),
            'direct_phase1': ('weTimeDirect', f"ms, median of {n_runs(BASE + 'final/runs.json', 'candidate_full')}"),
            'C1': ('weTimeC1Full', f"ms, median of {n_c1}; completes its pass within the {L.value('bC')} s allowance")}
for key in order:
    m = M[key]
    tk, note = time_key[key]
    t = (L.value(tk) + ' ' + note) if tk else note
    worked.append(f"{names[key]} & {m['C']} & {m['S']} & {m['J']} & {t} & {mech[key]}" + r' \\')
(OUT / 'tab_worked.tex').write_text('\n'.join(worked) + '\n')

ledger_rows = []
for k, e in sorted(L.entries.items()):
    src = e.get('source', '')
    field = e.get('field') if e['kind'] == 'pointer' else e.get('derivation', e.get('field', ''))
    if isinstance(field, list):
        field = '/'.join(map(str, field))
    val = e['value'].replace('\N{MINUS SIGN}', '-').replace('×', 'x')
    src_s = str(src).replace('results/phase2_structural_encoding/', 'p2/').replace(' ', '')
    field_s = str(field)[:60].replace('{', '(').replace('}', ')').replace(' ', '')
    field_s = re.sub(r'[^A-Za-z0-9/._():,=+@\-\[\]]', '', field_s)
    ledger_rows.append(r'\texttt{\seqsplit{' + k + r'}} & \texttt{\seqsplit{' + val.replace(' ', '') + r'}} & \path{'
                       + src_s + r'} & \path{' + field_s + r'} \\')
(OUT / 'tab_ledger.tex').write_text('\n'.join(ledger_rows) + '\n')
md = ['| key | value | source file | field or derivation | claim context |', '|---|---|---|---|---|']
for k, e in sorted(L.entries.items()):
    field = e.get('field') if e['kind'] == 'pointer' else e.get('derivation', e.get('field', ''))
    if isinstance(field, list):
        field = '/'.join(map(str, field))
    md.append(f"| `{k}` | {e['value']} | `{e.get('source', '')}` | `{field}` | {e.get('claim', '')} |")
(OUT / 'claim_table.md').write_text('# Claim ledger (generated; do not edit)\n\n' + '\n'.join(md) + '\n')

L.write()
checked, total = pe.verify_ledger()
INPUTS['paper/phase2_evidence.py'] = hashlib.sha256((HERE / 'phase2_evidence.py').read_bytes()).hexdigest()
INPUTS['paper/worked_example.py'] = hashlib.sha256((HERE / 'worked_example.py').read_bytes()).hexdigest()
INPUTS['palette_owner:' + str(PALETTE_OWNER.relative_to(ROOT.parent))] = hashlib.sha256(PALETTE_OWNER.read_bytes()).hexdigest()
INPUTS.update(phase2_metrics['source_sha256'])
INPUTS.update(phase2_metrics['raw_artifact_sha256_verified_against_p1_summary'])
for e in L.entries.values():
    src = e.get('source', '')
    if isinstance(src, str) and (ROOT / src).is_file():
        INPUTS[src] = hashlib.sha256((ROOT / src).read_bytes()).hexdigest()
(OUT / 'metrics.json').write_text(json.dumps({'public_scores_phase1': scores, 'improved_generated_programs': improved}, indent=2) + '\n')
(OUT / 'input_manifest.json').write_text(json.dumps({
    'inputs_sha256': dict(sorted(INPUTS.items())), 'palette': PAL, 'matplotlib': matplotlib.__version__,
    'numpy': np.__version__, 'figure_checks': FIGURE_CHECKS,
    'ledger': {'entries': total, 'reverified_from_disk': checked,
               'computed_by_generators': total - checked}}, indent=2, default=str) + '\n')
print(f'PASS: {len(FIGURE_CHECKS)} checked figures; ledger {total} values, {checked} re-derived from disk; tables written.')
