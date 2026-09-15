"""Draw the actual five-input circuit and its exact repertoire and schemata."""
from pathlib import Path
from itertools import combinations
import csv
import hashlib
import importlib.metadata
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'paper/generated'
ASSETS.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.build/mplcache'))
os.environ.setdefault('XDG_CACHE_HOME', str(ROOT / '.build/fontcache'))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT.parent / 'index-deconvolution/src'))
from oxparc_challenge.boolean import build_majority, evaluate_boolean, BooleanCircuit
from deconvolution import essential_variables
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np

TEAL, ORANGE, BLUE, GREY = '#007f86', '#c86428', '#4666a5', '#77818d'
PALE, LIGHT, INK = '#d8eef0', '#f2f5f7', '#243340'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.labelcolor': INK, 'text.color': INK, 'pdf.fonttype': 42,
    'savefig.dpi': 180})


def save(fig, name):
    fig.savefig(ASSETS / f'{name}.pdf', bbox_inches='tight')
    fig.savefig(ASSETS / f'{name}.png', bbox_inches='tight')
    plt.close(fig)


def matrix(ax, data, columns, row_labels, *, star=False, font=9):
    colours = [LIGHT, TEAL, '#ffead8'] if star else [LIGHT, TEAL]
    ax.imshow(data, cmap=ListedColormap(colours), vmin=0, vmax=2 if star else 1,
              aspect='auto', interpolation='nearest')
    for (r, c), value in np.ndenumerate(data):
        ax.text(c, r, '*' if value == 2 else str(value), ha='center', va='center',
                color='white' if value == 1 else (ORANGE if value == 2 else GREY), fontsize=font)
    ax.set_xticks(range(len(columns)), columns)
    ax.set_yticks(range(len(row_labels)), row_labels)
    ax.tick_params(length=0)
    ax.set_xticks(np.arange(-.5, len(columns), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(row_labels), 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=1)
    ax.tick_params(which='minor', length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)


def derive():
    circuit = build_majority(5)
    all_outputs = BooleanCircuit(5, circuit.gates, tuple(range(5, 12)))
    rows = []
    for index in range(32):
        bits = [(index >> i) & 1 for i in range(5)]
        gates = evaluate_boolean(all_outputs, bits)
        if gates[-1] != int(sum(bits) >= 3):
            raise RuntimeError('Worked circuit differs from majority')
        rows.append(dict(index=index, inputs=bits, gates=gates, output=gates[-1]))
    column = [r['output'] for r in rows]
    if essential_variables(column, 5) != list(range(5)):
        raise RuntimeError('Worked functional-input recovery failed')
    schemas = []
    for fixed in combinations(range(5), 3):
        free = [i for i in range(5) if i not in fixed]
        anchor = sum(1 << i for i in fixed)
        offsets = [sum(((j >> k) & 1) << i for k, i in enumerate(free)) for j in range(4)]
        indices = [anchor + offset for offset in offsets]
        if not all(column[i] for i in indices):
            raise RuntimeError('Schema includes an inactive state')
        schemas.append(dict(pattern=''.join('1' if i in fixed else '*' for i in range(5)),
                            anchor=anchor, free=free, offsets=offsets, indices=indices))
    active = {r['index'] for r in rows if r['output']}
    expanded = set().union(*(set(s['indices']) for s in schemas))
    if expanded != active or len(expanded) != 16 or schemas[0]['indices'] != [7, 15, 23, 31]:
        raise RuntimeError('Exact schema union failed')
    # Every input has a boundary pair; retain them to reproduce dependence.
    pairs = []
    for bit in range(5):
        lo = next(x for x in range(32) if not (x & (1 << bit)) and column[x] != column[x | (1 << bit)])
        pairs.append(dict(input=bit, zero_state=lo, one_state=lo | (1 << bit)))
    if rows[6]['output'] != 0 or rows[7]['output'] != 1:
        raise RuntimeError('Displayed perturbation pair failed')
    with (ASSETS/'worked_repertoire.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['index']+[f'x{i}' for i in range(5)]+[f'g{i}' for i in range(7)]+['output'])
        for r in rows:
            writer.writerow([r['index']]+r['inputs']+r['gates']+[r['output']])
    data = dict(status='PASS', circuit=json.loads(circuit.to_json()), rows=rows,
                schemas=schemas, active_indices=sorted(active), functional_inputs=list(range(5)),
                dependence_pairs=pairs, checks=['all 32 states equal the independent threshold',
                    'every schema expands to active indices only', 'schema union equals the exact repertoire',
                    'five functional inputs recovered', 'all displayed internal signals evaluated from circuit'])
    (ASSETS/'worked_network.json').write_text(json.dumps(data, indent=2)+'\n')
    return circuit, rows, schemas


def network_figure(circuit, rows):
    fig = plt.figure(figsize=(11.5, 7.2))
    grid = fig.add_gridspec(2, 2, height_ratios=[3.7, 1.4], width_ratios=[1.12, 1],
                           hspace=.55, wspace=.28)
    ax = fig.add_subplot(grid[0, 0])
    ax.set_title('A. Follow the actual majority circuit', loc='left', pad=16)
    pos = {i: (0, 4-i) for i in range(5)}
    pos.update({5:(1.7,4), 7:(1.7,2), 9:(1.7,0), 6:(3.4,4), 8:(3.4,2), 10:(3.4,0), 11:(5.1,2)})
    for g, gate in enumerate(circuit.gates):
        target = 5+g
        for ref in gate.operands:
            long = pos[target][0]-pos[ref][0] > 2
            # The long input wires arc around first-layer gates.
            rad = .25 if long else 0
            if long and pos[ref][1] < pos[target][1]:
                rad = -.25
            ax.add_patch(FancyArrowPatch(pos[ref], pos[target], arrowstyle='-|>',
                mutation_scale=11, linewidth=1.05, color=GREY, alpha=.85,
                connectionstyle=f'arc3,rad={rad}', shrinkA=14, shrinkB=16, zorder=1))
    for ref, (x,y) in pos.items():
        ax.scatter([x], [y], s=530 if ref < 5 else 650,
                   c=[PALE if ref < 5 else TEAL], edgecolors='white', linewidth=1.5, zorder=3)
        label = f'$x_{ref}$' if ref < 5 else f'$g_{ref-5}$'
        ax.text(x,y,label,ha='center',va='center',color=INK if ref<5 else 'white', zorder=4, fontsize=12)
    ax.text(5.1,1.45,'output',ha='center',fontsize=9)
    ax.text(2.5,-.8,'Every gate returns the majority of its three incoming wires.',ha='center',fontsize=9)
    ax.set(xlim=(-.5,5.7),ylim=(-.95,4.6));ax.axis('off')
    ax = fig.add_subplot(grid[0, 1])
    data = np.zeros((7, 11), dtype=int)
    for g, gate in enumerate(circuit.gates):
        data[g, list(gate.operands)] = 1
    matrix(ax, data, [f'$x_{i}$' for i in range(5)]+[f'$g_{i}$' for i in range(6)],
           [f'$g_{i}$' for i in range(7)], font=10)
    ax.set_title('B. Read one target row',loc='left',pad=16)
    ax.set_xlabel('Source input or gate');ax.set_ylabel('Target gate')
    ax.axvline(4.5, color=GREY, lw=1)
    ax = fig.add_subplot(grid[1, :]);ax.axis('off')
    ax.set_title('C. The same input pattern can contain different internal gate states',loc='left',pad=15)
    selected = [rows[i] for i in (7,15,23,31)]
    headings=['Index',r'Input $x_0\ldots x_4$']+[f'$g_{i}$' for i in range(7)]+['Output']
    cells=[[r['index'], ''.join(map(str,r['inputs']))]+r['gates']+[r['output']] for r in selected]
    table=ax.table(cellText=cells,colLabels=headings,cellLoc='center',bbox=[0,0,1,1],
                   colWidths=[.07,.23]+[.08]*7+[.1])
    table.auto_set_font_size(False);table.set_fontsize(10)
    for (r,c),cell in table.get_celld().items():
        cell.set_edgecolor('white')
        cell.set_facecolor(PALE if r==0 else ('#ffead8' if c in (1,9) else LIGHT))
        cell.set_text_props(color=INK)
    save(fig,'majority_network')


def patterns_figure(rows, schemas):
    fig = plt.figure(figsize=(11.5, 8.7))
    grid=fig.add_gridspec(2,2,width_ratios=[1,1.15],height_ratios=[1.25,1],hspace=.55,wspace=.5)
    ax=fig.add_subplot(grid[0,0])
    data=np.array([[1 if c=='1' else 2 for c in s['pattern']] for s in schemas])
    matrix(ax,data,[f'$x_{i}$' for i in range(5)],[s['pattern'] for s in schemas],star=True,font=11)
    ax.set_title('A. Ten patterns cover every output-one state',loc='left',pad=18,fontsize=11)
    ax.set_ylabel('Fixed ones and free positions')
    ax.add_patch(Rectangle((-.5,-.5),5,1,fill=False,edgecolor=ORANGE,lw=2.4))
    ax=fig.add_subplot(grid[:,1])
    data=np.array([r['inputs']+[r['output']] for r in rows])
    matrix(ax,data,[f'$x_{i}$' for i in range(5)]+['$y$'],list(range(32)),font=10)
    ax.set_title('B. Expand into the complete repertoire',loc='left',pad=18,fontsize=11)
    ax.set_ylabel('Input index');ax.axvline(4.5,color=GREY,lw=1.5)
    for index in schemas[0]['indices']:
        ax.add_patch(Rectangle((-.5,index-.5),6,1,fill=False,edgecolor=ORANGE,lw=2))
    ax=fig.add_subplot(grid[1,0]);ax.axis('off')
    ax.set_title('C. Unfold one pattern and test one input',loc='left',pad=18,fontsize=11)
    lines=[('Pattern 111** fixes three ones.',INK),
           ('Anchor: 1 + 2 + 4 = 7',INK),
           ('Free positions: 3 and 4',INK),
           ('Offsets: {0, 8, 16, 24}',INK),
           ('Indices: {7, 15, 23, 31}',ORANGE),
           ('The four orange rows all have y = 1.',INK),
           ('',INK),
           ('Flip only input 0 at the boundary:',INK),
           ('01100  →  11100',TEAL),
           ('index 6, y = 0  →  index 7, y = 1',INK),
           ('Input 0 matters to the function.',INK)]
    for i,(line,colour) in enumerate(lines):
        ax.text(0,1-i*.096,line,transform=ax.transAxes,va='top',fontsize=10.5,color=colour)
    save(fig,'majority_patterns')


def main():
    circuit,rows,schemas=derive()
    network_figure(circuit,rows)
    patterns_figure(rows,schemas)
    from paper_operation_figures import generate
    generate()
    sources=[Path(__file__), ROOT/'src/oxparc_challenge/boolean.py',
             ROOT.parent/'index-deconvolution/src/deconvolution.py',
             ROOT.parent/'index-deconvolution/src/causalbool.py',
             ROOT/'paper/requirements-figures.lock',
             ROOT/'tools/paper_operation_figures.py',
             ROOT/'src/oxparc_challenge/fourier.py',
             ROOT/'src/oxparc_challenge/fourier_search.py',
             ROOT/'evidence/fourier_32768_ledger.json',
             ROOT/'evidence/fourier_65536_ledger.json']
    report=dict(status='PASS',states=32, gates=7, schemas=10, active_indices=16,
        environment=dict(python=sys.version, dependencies={
            line.split('==')[0]:importlib.metadata.version(line.split('==')[0])
            for line in (ROOT/'paper/requirements-figures.lock').read_text().splitlines()}),
        source_sha256={str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        figures={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ASSETS.iterdir() if p.is_file()})
    (ROOT/'evidence/paper_figures.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Network figures: 7 emitted gates, all 32 states, 10 exact schemata; PASS')


if __name__ == '__main__':
    main()
