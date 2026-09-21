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


def cover(column, n):
    """Return the exact schema cover of an output column, as anchor/offset pairs.

    A schema fixes some coordinates and leaves the rest free; it belongs to the
    cover when every one of its expansions is active.  Only maximal schemata are
    kept, so the cover is the compressed reading of the index set rather than a
    restatement of it.  This is the representation of Section S3.1: an anchor
    carried together with its own family of offsets.
    """
    active = {i for i, v in enumerate(column) if v}
    found = []
    for size in range(n + 1):
        for free in combinations(range(n), size):
            rest = [i for i in range(n) if i not in free]
            for assignment in range(1 << len(rest)):
                fixed = {i: (assignment >> k) & 1 for k, i in enumerate(rest)}
                anchor = sum(1 << i for i, bit in fixed.items() if bit)
                offsets = [sum(((j >> k) & 1) << i for k, i in enumerate(free))
                           for j in range(1 << size)]
                if not all(anchor + off in active for off in offsets):
                    continue
                pattern = ''.join('*' if i in free else str(fixed[i]) for i in range(n))
                found.append(dict(pattern=pattern, anchor=anchor, free=list(free),
                                  offsets=offsets, indices=[anchor + o for o in offsets]))
    maximal = sorted((s for s in found
                      if not any(other is not s and set(s['indices']) < set(other['indices'])
                                 for other in found)),
                     key=lambda s: s['anchor'])
    union = set().union(*(set(s['indices']) for s in maximal)) if maximal else set()
    if union != active:
        raise RuntimeError('schema cover does not reproduce the index set')
    return maximal


def arithmetic_cells():
    """Enumerate the stated relations and recover them, exactly as the compiler does.

    Nothing here names a gate.  The behaviours are the relations as written in
    ``boolean_arithmetic``; the names come back from the recovery and are only
    read for display.
    """
    from oxparc_challenge.boolean_arithmetic import full_adder_cell, _comparator_step

    def column(behaviour, n):
        return [behaviour([(i >> k) & 1 for k in range(n)]) for i in range(1 << n)]

    def comparator(bound_bit):
        def less(bits):
            l, e, x = bits
            return 1 if l or (e and not x and bound_bit) else 0
        return less

    cells = dict(
        adder_sum=dict(column=column(lambda b: sum(b) & 1, 3),
                       recovered=full_adder_cell()[0]),
        adder_carry=dict(column=column(lambda b: sum(b) >> 1, 3),
                         recovered=full_adder_cell()[1]),
        less_bound1=dict(column=column(comparator(1), 3),
                         recovered=_comparator_step(1)[0]),
        less_bound0=dict(column=column(comparator(0), 3),
                         recovered=_comparator_step(0)[0]))
    for name, cell in cells.items():
        cell['indices'] = [i for i, v in enumerate(cell['column']) if v]
        cell['essential'] = essential_variables(cell['column'], 3)
        cell['cover'] = cover(cell['column'], 3)
        if cell['essential'] != list(cell['recovered'].connected_inputs):
            raise RuntimeError(f'{name}: column dependence differs from the recovery')
    # The carry's index set is the three-input majority index set of Section S3.1.
    if cells['adder_carry']['indices'] != [3, 5, 6, 7]:
        raise RuntimeError('carry index set is not the majority index set')
    if cells['adder_carry']['recovered'].gate != 'MAJORITY':
        raise RuntimeError('carry was not recovered as MAJORITY')
    if cells['less_bound0']['essential'] != [0]:
        raise RuntimeError('the bound-zero comparison did not specialise')
    return cells


def cells_figure(cells):
    """Render what "the resulting behaviour" is, in the method's own representation."""
    names = ['$\\ell$', '$e$', '$x$']

    def note(ax, text, y=-.30):
        ax.text(0, y, text, transform=ax.transAxes, va='top', ha='left',
                fontsize=9.5, color=INK, linespacing=1.5)

    fig = plt.figure(figsize=(10.9, 7.3))
    grid = fig.add_gridspec(2, 2, hspace=1.12, wspace=.30,
                            height_ratios=[1.75, 1], width_ratios=[1, 1])

    ax = fig.add_subplot(grid[0, 0])
    rows = [[(i >> k) & 1 for k in range(3)] +
            [cells['adder_sum']['column'][i], cells['adder_carry']['column'][i]]
            for i in range(8)]
    matrix(ax, np.array(rows), ['$a$', '$b$', '$c_{\\mathrm{in}}$', 'sum', 'carry'],
           list(range(8)), font=10)
    ax.set_title('A. The behaviour handed over', loc='left', pad=14, fontsize=11)
    ax.set_ylabel('Input index $\\iota$')
    ax.axvline(2.5, color=GREY, lw=1.5)
    note(ax, 'The stated relation $a+b+c_{\\mathrm{in}}$, enumerated over its eight\n'
             'states. This table is the whole of the input: no circuit is supplied\n'
             'and no gate is named.', y=-.13)

    ax = fig.add_subplot(grid[0, 1])
    strips = np.array([[1 if i in cells['adder_sum']['indices'] else 0 for i in range(8)],
                       [1 if i in cells['adder_carry']['indices'] else 0 for i in range(8)]])
    matrix(ax, strips, list(range(8)), ['sum', 'carry'], font=10)
    ax.set_title('B. The same behaviour as an index set', loc='left', pad=14, fontsize=11)
    ax.set_xlabel('Index $\\iota=a+2b+4c_{\\mathrm{in}}$')
    carry = cells['adder_carry']
    patterns = ', '.join(s['pattern'] for s in carry['cover'])
    anchors = ', '.join(str(s['anchor']) for s in carry['cover'])
    note(ax, f"Only the positions of the ones are kept:  "
             f"sum $\\mathcal{{I}}$ = {{{', '.join(map(str, cells['adder_sum']['indices']))}}},  "
             f"carry $\\mathcal{{I}}$ = {{{', '.join(map(str, carry['indices']))}}}\n"
             f"The carry's set is covered exactly by {patterns}, with anchors {anchors}.\n"
             f"That is the three-input majority index set of Section S3.1,\n"
             f"reached here from arithmetic rather than from voting.", y=-.19)

    ax = fig.add_subplot(grid[1, 0])
    matrix(ax, strips[1:], list(range(8)), ['carry'], font=10)
    ax.set_title('C. Which coordinates the behaviour responds to', loc='left',
                 pad=26, fontsize=11)
    column = carry['column']
    lines = []
    for k, coordinate in enumerate(carry['essential']):
        low = next(x for x in range(8) if not (x >> coordinate) & 1
                   and column[x] != column[x ^ (1 << coordinate)])
        high = low ^ (1 << coordinate)
        ax.add_patch(FancyArrowPatch((low, -.55), (high, -.55), arrowstyle='<|-|>',
                                     mutation_scale=9, linewidth=1.15, color=ORANGE,
                                     clip_on=False, connectionstyle=f'arc3,rad={-.35 - .16 * k}',
                                     zorder=5))
        lines.append(f"flip $a$: $\\iota={low}\\to{high}$" if coordinate == 0 else
                     (f"flip $b$: $\\iota={low}\\to{high}$" if coordinate == 1 else
                      f"flip $c_{{\\mathrm{{in}}}}$: $\\iota={low}\\to{high}$"))
    ax.set_ylim(1.2, -1.9)
    note(ax, 'A single-bit flip that crosses the set makes that coordinate essential.\n'
             + ';  '.join(lines) + '\n'
             f"All three do, so the carry keeps all three inputs, and the restricted\n"
             f"behaviour is matched against the canonical family as {carry['recovered'].gate}.",
         y=-.55)

    ax = fig.add_subplot(grid[1, 1])
    one, zero = cells['less_bound1'], cells['less_bound0']
    strips = np.array([[1 if i in one['indices'] else 0 for i in range(8)],
                       [1 if i in zero['indices'] else 0 for i in range(8)]])
    matrix(ax, strips, list(range(8)), ['bound bit 1', 'bound bit 0'], font=10)
    ax.set_title('D. Where the behaviour is already specialised', loc='left',
                 pad=26, fontsize=11)
    ax.set_xlabel('Index $\\iota=\\ell+2e+4x$')
    schema = zero['cover'][0]
    free = ' and '.join(names[i] for i in schema['free'])
    note(ax, f"bound bit 1: $\\mathcal{{I}}$ = {{{', '.join(map(str, one['indices']))}}}, "
             f"essential {{{', '.join(names[i] for i in one['essential'])}}}\n"
             f"bound bit 0: $\\mathcal{{I}}$ = {{{', '.join(map(str, zero['indices']))}}}, "
             f"essential {{{', '.join(names[i] for i in zero['essential'])}}}\n"
             f"The lower set is the single schema {schema['pattern']}, anchor {schema['anchor']},\n"
             f"offsets {{{', '.join(map(str, schema['offsets']))}}}. {free} are free, so no flip of\n"
             f"either crosses the set, and the method returns the wire.", y=-.62)

    save(fig, 'arithmetic_cells')


def capacities_figure(rows, schemas):
    """Show the method's forward, inverse, compression, and query capacities."""
    column = [r['output'] for r in rows]
    connected = essential_variables(column, 5)
    if connected != list(range(5)):
        raise RuntimeError('Capacity figure requires all five functional inputs')

    pairs = []
    for bit in range(5):
        zero = next(x for x in range(32)
                    if not (x & (1 << bit)) and column[x] != column[x | (1 << bit)])
        pairs.append((bit, zero, zero | (1 << bit), column[zero], column[zero | (1 << bit)]))

    fig = plt.figure(figsize=(11.5, 8.8))
    grid = fig.add_gridspec(2, 2, hspace=.48, wspace=.32,
                            height_ratios=[1.08, 1], width_ratios=[1.08, 1])

    # A complete repertoire is the exact object consumed by deconvolution.
    ax = fig.add_subplot(grid[0, 0])
    data = np.array([r['inputs'] + [r['output']] for r in rows])
    ax.imshow(data, cmap=ListedColormap([LIGHT, TEAL]), vmin=0, vmax=1,
              aspect='auto', interpolation='nearest')
    ax.set_title('A. Exact repertoire supplied to the inverse', loc='left', pad=14)
    ax.set_xticks(range(6), [f'$x_{i}$' for i in range(5)] + ['$y$'])
    ax.set_yticks(range(0, 32, 4), range(0, 32, 4))
    ax.set_ylabel('Input index (LSB first)')
    ax.set_xlabel('Inputs and output')
    ax.axvline(4.5, color=GREY, lw=1.2)
    ax.set_xticks(np.arange(-.5, 6, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 32, 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=.7)
    ax.tick_params(which='minor', length=0)
    ax.text(5.55, 15.5, '$2^5$ rows', rotation=90, va='center', ha='left',
            color=GREY, fontsize=9)

    # Essential-variable detection is an exact paired perturbation test.
    ax = fig.add_subplot(grid[0, 1])
    ax.axis('off')
    ax.set_title('B. Perturbation isolates an output condition', loc='left', pad=14)
    ax.text(0, .91, r'Compare $y[x]$ with $y[x\oplus2^i]$ within the integrated repertoire.',
            transform=ax.transAxes, fontsize=10, color=INK)
    headings = ['bit', '$x$', r'$x\oplus2^i$', 'y', "$y'$\n(change)"]
    cells = [[bit, zero, one, y0, f'{y1}']
             for bit, zero, one, y0, y1 in pairs]
    table = ax.table(cellText=cells, colLabels=headings, cellLoc='center',
                     bbox=[0, .28, 1, .52], colWidths=[.13, .21, .25, .13, .28])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('white')
        cell.set_facecolor(PALE if r == 0 else LIGHT)
        cell.set_text_props(color=INK)
    ax.text(.5, .16, r'$I_c=$ nodes with an output-changing witness',
            transform=ax.transAxes, ha='center', fontsize=10.5, color=TEAL,
            fontweight='bold')
    ax.text(.5, .07, 'Here every coordinate has a witnessed output change.',
            transform=ax.transAxes, ha='center', fontsize=9, color=GREY)

    # The schema view makes the lossless description explicit.
    ax = fig.add_subplot(grid[1, 0])
    ax.axis('off')
    ax.set_title('C. Lossless description of a pattern', loc='left', pad=14)
    ax.text(0, .9, 'Output-one states are grouped by fixed bits and\ndon\'t-care positions.',
            transform=ax.transAxes, va='top', fontsize=10, color=INK)
    shown = [s['pattern'] for s in schemas]
    ax.text(.02, .61, '\n'.join(shown[:5]), transform=ax.transAxes,
            va='top', family='monospace', fontsize=10.5, color=TEAL,
            linespacing=1.35)
    ax.text(.26, .61, '\n'.join(shown[5:]), transform=ax.transAxes,
            va='top', family='monospace', fontsize=10.5, color=TEAL,
            linespacing=1.35)
    ax.text(.55, .61, r'$111**:\quad P=1+2+4=7$', transform=ax.transAxes,
            va='top', fontsize=10, color=INK)
    ax.text(.55, .43, r'$S=\{0,8,16,24\}$', transform=ax.transAxes,
            va='top', fontsize=10, color=ORANGE)
    ax.text(.55, .26, r'$\mathrm{Dec}(P,S)=\{7,15,23,31\}$',
            transform=ax.transAxes, va='top', fontsize=10, color=INK)
    ax.text(.55, .09, 'schema union = exact on-set\n(16 output-one indices)',
            transform=ax.transAxes, va='top', fontsize=9.5, color=TEAL,
            fontweight='bold')

    # Recovered function supports exact replay and deterministic queries.
    ax = fig.add_subplot(grid[1, 1])
    ax.axis('off')
    ax.set_title('D. Reconstruct, replay, and answer queries', loc='left', pad=14)

    def box(x, y, w, h, label, *, fill=PALE, text_colour=INK, size=9.5):
        ax.add_patch(Rectangle((x, y), w, h, transform=ax.transAxes,
                               facecolor=fill, edgecolor=TEAL, linewidth=1.2,
                               joinstyle='round'))
        ax.text(x + w / 2, y + h / 2, label, transform=ax.transAxes,
                ha='center', va='center', fontsize=size, color=text_colour)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), transform=ax.transAxes,
                                     arrowstyle='-|>', mutation_scale=11,
                                     linewidth=1.1, color=GREY))

    box(.03, .66, .25, .17, 'union of node sets\n+ dynamical condition')
    box(.38, .66, .23, .17, 'exact pattern\nor decoder', fill='#ffead8')
    box(.71, .66, .25, .17, 'integrated\nsystem model')
    arrow(.28, .745, .38, .745)
    arrow(.61, .745, .71, .745)
    ax.text(.5, .53, 'independent forward replay', transform=ax.transAxes,
            ha='center', fontsize=9, color=GREY)
    arrow(.835, .66, .835, .37)
    box(.55, .16, .42, .17, 'whole supplied repertoire\nreproduced exactly',
        fill=PALE, text_colour=TEAL, size=9.5)
    box(.03, .16, .42, .17, 'query or counterfactual\ninput  →  deterministic output',
        fill='#ffead8', text_colour=INK, size=9.5)
    arrow(.24, .33, .24, .52)
    ax.text(.24, .42, 'evaluate', transform=ax.transAxes, ha='center',
            fontsize=8.5, color=GREY)
    ax.text(.03, .05, 'The guarantee is exact within the stated model and data domain;',
            transform=ax.transAxes, fontsize=8.5, color=GREY)
    ax.text(.03, .005, 'it is not a claim of minimal K or unique hidden wiring.',
            transform=ax.transAxes, fontsize=8.5, color=GREY)

    fig.text(.5, .965,
             'Index deconvolution: from integrated behaviour to exact conditioned patterns',
             ha='center', va='top', fontsize=12, color=INK, fontweight='bold')
    save(fig, 'index_deconvolution_capacities')


def main():
    circuit,rows,schemas=derive()
    network_figure(circuit,rows)
    patterns_figure(rows,schemas)
    cells = arithmetic_cells()
    cells_figure(cells)
    capacities_figure(rows, schemas)
    from paper_operation_figures import generate
    generate()
    sources=[Path(__file__), ROOT/'src/oxparc_challenge/boolean.py',
             ROOT/'src/oxparc_challenge/boolean_arithmetic.py',
             ROOT.parent/'index-deconvolution/src/deconvolution.py',
             ROOT.parent/'index-deconvolution/src/causalbool.py',
             ROOT/'paper/requirements-figures.lock',
             ROOT/'tools/paper_operation_figures.py',
             ROOT/'src/oxparc_challenge/fourier.py',
             ROOT/'src/oxparc_challenge/fourier_search.py',
             ROOT/'evidence/fourier_32768_ledger.json',
             ROOT/'evidence/fourier_65536_ledger.json']
    report=dict(status='PASS',states=32, gates=7, schemas=10, active_indices=16,
        arithmetic_cells={name:dict(indices=c['indices'], essential=c['essential'],
            gate=c['recovered'].gate, cover=[s['pattern'] for s in c['cover']])
            for name,c in cells.items()},
        environment=dict(python=sys.version, dependencies={
            line.split('==')[0]:importlib.metadata.version(line.split('==')[0])
            for line in (ROOT/'paper/requirements-figures.lock').read_text().splitlines()}),
        source_sha256={str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        figures={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ASSETS.iterdir() if p.is_file()})
    (ROOT/'evidence/paper_figures.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Network figures: 7 emitted gates, all 32 states, 10 exact schemata; PASS')


if __name__ == '__main__':
    main()
