"""Rebuild paper figures/tables from retained evidence; never rerun benchmarks.

Run from any directory with a Python interpreter containing matplotlib.
All paths are relative to this script. Assertions fail closed on source drift.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import statistics as st

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'generated'
OUT.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', '/tmp/causalbool-paper-mpl')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/causalbool-paper-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

TEAL, ORANGE, INK, GREY = '#007F86', '#C86428', '#243340', '#77818D'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
    'text.color': INK, 'axes.labelcolor': INK, 'xtick.color': INK,
    'ytick.color': INK, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#CBD2D8', 'pdf.fonttype': 42, 'savefig.dpi': 180})
INPUTS = {}

def read(rel):
    p = ROOT / rel
    INPUTS[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text())

BASE = 'results/direct_index_v4_optimization_repair2/lead_review/'
d = read(BASE + 'final/runs.json')
prov = read(BASE + 'final/provenance.json')
audit = read(BASE + 'measurement_audit.json')
verification = read(BASE + 'verification/summary.json')
historical = read('results/comparison.json')
extra_manifest = read('results/direct_index_v4_optimization/baseline/extra_corpus_manifest.json')
assert d['acceptance_gates']['all_passed']['passed']
assert verification['status'] == 'PASS' and not verification['failures']
assert sum(r.get('tests', 0) for r in verification['records']) == 351
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

def gm(xs):
    return math.exp(st.mean(math.log(x) for x in xs))

serial = {p['program']: p['runs']['serial'][0] for p in historical['programs']}
scores = {}
for a in arms:
    scores[a] = gm(math.sqrt(serial[p]['cycles'] * serial[p]['scratch'] /
                             (metric(a, p, 'cycles') * metric(a, p, 'scratch'))) for p in programs)
    assert math.isclose(scores[a], d['analysis']['scores'][a]['combined_score'], rel_tol=1e-13)
for mode in ['bootstrap', 'full']:
    ratio = gm(median('frozen_' + mode, p) / median('candidate_' + mode, p) for p in programs)
    assert math.isclose(ratio, audit['speedups'][mode]['point'], rel_tol=1e-13)

# Recompute the generated-set score from its frozen serial control and raw rows.
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

def save(fig, name):
    fig.savefig(OUT / (name + '.pdf'), bbox_inches='tight', metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(OUT / (name + '.png'), bbox_inches='tight')
    plt.close(fig)

# Exact pedagogical example: displayed coordinates are x0,x1,x2,x3.
def expand(a, f, n=4):
    return {i for i in range(1 << n) if (i & (((1 << n) - 1) ^ f)) == a}
assert expand(1, 10) == {1, 3, 9, 11}
assert expand(1, 10) & expand(0, 7) == expand(1, 2) == {1, 3}
fig, ax = plt.subplots(figsize=(7.1, 2.1))
for y, (label, members, color) in enumerate([
    ('A: anchor 1, free mask 10', expand(1, 10), GREY),
    ('B: anchor 0, free mask 7', expand(0, 7), ORANGE),
    ('A ∩ B: anchor 1, free mask 2', expand(1, 2), TEAL)]):
    ax.scatter(range(16), [y]*16, s=95, color='#EDF1F3', zorder=1)
    ax.scatter(sorted(members), [y]*len(members), s=95, color=color, zorder=2)
ax.set_yticks(range(3), [x for x in ['A: 1 + {0, 2, 8, 10}', 'B: {0, …, 7}', 'A ∩ B: 1 + {0, 2}']])
ax.set_xticks(range(16)); ax.set_xlabel('Decision index (not a physical memory address)')
ax.invert_yaxis(); ax.set_ylim(2.6, -.6); ax.spines[['left', 'bottom']].set_visible(False)
ax.tick_params(length=0); fig.tight_layout(); save(fig, 'schema_example')

# Raw output components: lower is better. No score/runtimes conflated.
fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.2), sharey=True)
for ax, field, title in zip(axes, ['cycles', 'scratch'], ['Emitted cycles', 'Scratch words']):
    for i, p in enumerate(programs):
        c, b = metric('classical', p, field), metric('candidate_bootstrap', p, field)
        ax.plot([c, b], [i, i], color='#C7CDD3', lw=2)
        ax.scatter(c, i, color=ORANGE, marker='s', s=28, label='Classical' if i == 0 else None)
        ax.scatter(b, i, color=TEAL, s=29, label='Direct (both modes)' if i == 0 else None)
    ax.set_xlabel(title + ' · lower is better'); ax.grid(axis='x', alpha=.18)
axes[0].set_yticks(range(8), [p.replace('_', ' ') for p in programs]); axes[0].invert_yaxis()
axes[1].legend(loc='upper center', bbox_to_anchor=(.2, 1.22), ncol=2, frameon=False)
fig.tight_layout(); save(fig, 'output_quality')

fig, ax = plt.subplots(figsize=(7.1, 3.5))
styles = [('classical', ORANGE, 's', 'Classical'),
          ('frozen_bootstrap', GREY, 'v', 'v3 bootstrap'),
          ('candidate_bootstrap', TEAL, 'o', 'v4 bootstrap'),
          ('frozen_full', GREY, '^', 'v3 full'),
          ('candidate_full', INK, 'D', 'v4 full')]
for j, (a, color, marker, label) in enumerate(styles):
    ax.scatter([median(a, p)*1000 for p in programs], np.arange(8)+(j-2)*.12,
               color=color, marker=marker, label=label, s=25)
ax.set_xscale('log'); ax.set_yticks(range(8), [p.replace('_',' ') for p in programs]); ax.invert_yaxis()
ax.set_xlabel('Median compiler-call time (ms, logarithmic scale) · lower is better')
ax.grid(axis='x', alpha=.18); ax.legend(ncol=3, bbox_to_anchor=(.5,1.23),loc='upper center', frameon=False)
fig.tight_layout(); save(fig, 'compile_times')

# Show the optimizer ablation without hiding the 94 unchanged programs.
improved = sorted(p for p in extra_serial if
                  math.prod(extra_metrics['candidate_full'][p]) < math.prod(extra_metrics['candidate_bootstrap'][p]))
assert len(improved) == 6
assert all(math.prod(extra_metrics['candidate_full'][p]) <= math.prod(extra_metrics['candidate_bootstrap'][p])
           for p in extra_serial)
fig, ax = plt.subplots(figsize=(7.1, 2.8))
for i, p in enumerate(improved):
    before, after = extra_metrics['candidate_bootstrap'][p], extra_metrics['candidate_full'][p]
    reduction = 100 * (1 - math.prod(after) / math.prod(before))
    ax.plot([0, reduction], [i, i], color='#C7CDD3', lw=2)
    ax.scatter(reduction, i, s=32, color=TEAL)
    ax.annotate(f'{before[0]} × {before[1]} → {after[0]} × {after[1]}',
                (reduction, i), xytext=(7, 0), textcoords='offset points', va='center', fontsize=8)
ax.set_yticks(range(len(improved)), [p.replace('additional_', 'Seed ') for p in improved])
ax.invert_yaxis(); ax.set_xlim(0, 47)
ax.set_xlabel('Cycle × scratch product reduction (%) · higher is better')
ax.set_title('Joint optimization: 6 improved programs; 94 unchanged', fontsize=10)
ax.grid(axis='x', alpha=.18); fig.tight_layout(); save(fig, 'optimizer_ablation')

rounds = [read('results/direct_index_v4_optimization_repair/final/runs.json'),
          read('results/direct_index_v4_optimization_repair2/final/runs.json'), d]
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.6), sharey=True)
for ax, mode, target in zip(axes, ['bootstrap', 'full'], [1.2, 2.0]):
    for i, rd in enumerate(rounds):
        r = rd['analysis']['ratios'][mode + '_candidate_vs_frozen']
        x = r['geometric_mean_of_per_program_medians']; ci = r['paired_bootstrap_95']
        ax.errorbar(x,i,xerr=[[x-ci['low']],[ci['high']-x]],fmt='o',color=TEAL,capsize=4)
        ax.annotate(f'{x:.3f}×', (x,i), xytext=(0,9), textcoords='offset points', ha='center',fontsize=8)
    ax.axvline(target, color=ORANGE, ls='--', lw=1)
    ax.set_title(mode.capitalize()); ax.set_xlabel('v3 time / v4 time · higher is better')
    ax.set_ylim(2.5,-.55); ax.grid(axis='x',alpha=.15)
axes[0].set_yticks(range(3), ['Repair 1 worker', 'Repair 2 worker', 'Repair 2 lead'])
fig.tight_layout(); save(fig, 'run_variability')

# Analytic illustration, never presented as measured compiler scaling.
fig, ax = plt.subplots(figsize=(6.6, 2.3))
n = np.arange(1, 17)
ax.plot(n, 2.**(n-1), color=ORANGE, marker='.', label='Odd parity: exact flat cube cover')
ax.plot(n, np.ones_like(n), color=TEAL, label='Unconstrained family: one cube')
ax.set_yscale('log',base=2); ax.set_xticks([1,4,8,12,16])
ax.set_xlabel('Number of Boolean coordinates n'); ax.set_ylabel('Required cubes')
ax.legend(frameon=False); ax.grid(alpha=.15); fig.tight_layout(); save(fig, 'representation_limits')

def tex(s):
    return s.replace('_', r'\_')

quality_rows, timing_rows = [], []
for p in programs:
    vals = [serial[p]['cycles'], serial[p]['scratch']]
    vals += [metric(a,p,k) for a in ['classical','candidate_bootstrap'] for k in ['cycles','scratch']]
    quality_rows.append(tex(p) + ' & ' + ' & '.join(map(str, vals)) + r' \\')
    timing_rows.append(tex(p) + ' & ' + ' & '.join(f'{median(a,p)*1000:.4f}' for a in arms) + r' \\')
(OUT/'quality_rows.tex').write_text('\n'.join(quality_rows)+'\n')
(OUT/'timing_rows.tex').write_text('\n'.join(timing_rows)+'\n')
resource_rows=[]
for a in arms:
    vals=[st.median(r[f] for r in subset(a)) * scale for f,scale in
          [('compile_seconds',1000),('import_seconds',1000),('process_seconds',1000),('peak_rss_bytes',1/2**20)]]
    resource_rows.append(tex(a.replace('_',' '))+' & '+' & '.join(f'{v:.3f}' for v in vals)+r' \\')
(OUT/'resource_rows.tex').write_text('\n'.join(resource_rows)+'\n')
metrics={'public_scores': scores, 'extra_scores': d['extra_corpus']['score_distribution'],
    'public_improved_programs': sorted({r['program'] for r in rows if r['arm']=='candidate_full' and r['optimiser']['accepted']}),
    'extra_improved_programs': sorted({r['program'] for r in extra if r['arm']=='candidate_full' and r['optimiser']['accepted']}),
    'public_direct_over_classical_percent':100*(scores['candidate_full']/scores['classical']-1),
    'classical_relative_slowdown':{m:gm(median('candidate_'+m,p)/median('classical',p) for p in programs) for m in ['bootstrap','full']}}
assert len(metrics['extra_improved_programs']) == 6
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
(OUT/'input_manifest.json').write_text(json.dumps({'inputs_sha256': INPUTS,
    'candidate_export_sha256':prov['export_sha256'], 'frozen_export_sha256':prov['frozen_export_sha256'],
    'matplotlib':matplotlib.__version__, 'numpy':np.__version__,
    'checks':'351 recorded tests; exact timing memberships; public and generated score recomputation; speedup recomputation; production/export/protected hashes; example set algebra; six improved generated programs'},indent=2)+'\n')
print('PASS: evidence checks and six reproducible figure pairs; generated tables and manifest.')
