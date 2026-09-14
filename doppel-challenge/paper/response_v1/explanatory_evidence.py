"""Illustrations from sealed ten-node records; no new network search.

Row BDM is a new illustrative measurement, separate from the released 2D BDM.
"""
from fractions import Fraction
import math
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import networkx as nx
import numpy as np
import pandas as pd
from pybdm import BDM
from pybdm.partitions import PartitionIgnore

TEAL, ORANGE, GREY = '#007f86', '#c86428', '#77818d'


def probability_map(record):
    rep = record['dynamics']['repertoire']
    return {x: Fraction(v['numerator'], v['denominator'])
            for x, v in zip(rep['support'], rep['probability_fractions'])}


def binary(x):
    """Node order x0,...,x9, not conventional MSB-first order."""
    return ''.join(str((x >> i) & 1) for i in range(10))


def extend_example(base, record, summary, assets, source, read, save, table, write_json):
    rep = record['dynamics']['repertoire']
    transitions = rep['transition_map']
    q = probability_map(record)
    cycle_sets = [set(c) for c in rep['attractor_cycles']]
    cycles = []
    for members in cycle_sets:
        ordered, x = [], min(members)
        while x not in ordered:
            ordered.append(x)
            x = transitions[x]
        assert x == ordered[0] and set(ordered) == members
        cycles.append(ordered)
    # Independent all-start trajectory check, including basin membership.
    basin_counts = [0] * len(cycles)
    for start in range(1024):
        seen, x = set(), start
        while x not in seen:
            seen.add(x)
            x = transitions[x]
        basin_counts[next(i for i, c in enumerate(cycle_sets) if x in c)] += 1
    assert basin_counts == rep['basin_sizes']
    for cycle, basin in zip(cycles, basin_counts):
        assert all(q[x] == Fraction(basin, 1024 * len(cycle)) for x in cycle)
    table('cycle_masses', ['Cycle', 'States', 'Basin size', 'Cycle probability', 'Each state'],
          [[f'G{i}', len(c), b, str(Fraction(b,1024)),
            str(Fraction(b,1024*len(c)))] for i, (c, b) in enumerate(zip(cycles, basin_counts))],
          'lrrrr')
    chosen = cycles[1]
    start = next(x for x in range(1024) if x not in q and transitions[x] in cycle_sets[1])
    shown = [start] + chosen
    repertoire_rows = [{'address': x, 'input_x0_to_x9': binary(x),
                        'output_y0_to_y9': binary(transitions[x]),
                        'next_address': transitions[x],
                        'cycle_phase': chosen.index(x) if x in chosen else None,
                        'long_run_probability': str(q.get(x, 0))} for x in shown]
    pd.DataFrame(repertoire_rows).to_csv(assets / 'cycle_repertoire.csv', index=False)
    fig = plt.figure(figsize=(10, 7.1), layout='constrained')
    grid = fig.add_gridspec(2, 2, height_ratios=[1.12, 1])
    ax = fig.add_subplot(grid[0, :]); ax.axis('off')
    ax.set_title('A. One row is one update; the output address selects the next row',
                 loc='left', fontsize=11)
    cells = [[r['address'], r['input_x0_to_x9'], r['output_y0_to_y9'],
              r['next_address'], 'transient' if r['cycle_phase'] is None else
              f"G1, phase {r['cycle_phase']}"] for r in repertoire_rows]
    tab = ax.table(cellText=cells, colLabels=['Address x', 'Input x0 … x9',
                   'Output y0 … y9', 'Next address F(x)', 'Cycle index'],
                   cellLoc='center', loc='center', colWidths=[.12,.24,.24,.18,.22])
    tab.auto_set_font_size(False); tab.set_fontsize(9); tab.scale(1, 1.35)
    for (row, col), cell in tab.get_celld().items():
        cell.set_edgecolor('white')
        cell.set_facecolor('#d9eef0' if row == 0 else '#fff1e3' if row == 1 else '#f3f6f8')
        if col == 3 and row > 1:
            cell.get_text().set_color(TEAL)
    ax = fig.add_subplot(grid[1, 0])
    graph = nx.DiGraph((x, transitions[x]) for x in chosen)
    pos = {x: (math.cos(math.pi/2-2*math.pi*i/8),
               math.sin(math.pi/2-2*math.pi*i/8)) for i,x in enumerate(chosen)}
    nx.draw_networkx(graph, pos, ax=ax, labels={x:f'{x}\nphase {i}' for i,x in enumerate(chosen)},
                     node_color='#d9eef0', node_size=1350, font_size=8.5,
                     edge_color=TEAL, arrowsize=18, connectionstyle='arc3,rad=0.08')
    ax.set_title('B. Follow the actual eight-step cycle', fontsize=11); ax.axis('off')
    ax.margins(.22)
    ax = fig.add_subplot(grid[1, 1])
    weights = [Fraction(b,1024) for b in basin_counts]
    ax.bar(range(4), [float(w) for w in weights], color=[GREY,TEAL,'#4666a5',ORANGE])
    for i,(c,b,w) in enumerate(zip(cycles,basin_counts,weights)):
        ax.text(i,float(w)+.015,f'{b}/1024\n{len(c)} state'+('s' if len(c)>1 else ''),
                ha='center',fontsize=9)
    ax.set(xticks=range(4),xticklabels=[f'G{i}' for i in range(4)],
           ylabel='Probability of reaching the cycle',ylim=(0,.59))
    ax.set_title('C. Divide cycle mass among its phases', fontsize=11)
    save(fig, 'cycles_repertoire')

    offsets = [s for s in range(1024) if s & ~351 == 0]
    positions = [512+s for s in offsets]
    matching = [x for x in positions if x & 1]
    assert len(positions) == 128 and len(matching) == 64
    assert all(transitions[x] & 1 for x in positions)
    assert all(transitions[x] & 3 == 3 for x in matching)
    full_pattern = [x for x in range(1024) if transitions[x] & 3 == 3]
    unfolded_pattern = sorted(a + s for a in [513,129,33,673]
                             for s in range(1024) if s & ~350 == 0)
    assert full_pattern == unfolded_pattern and len(full_pattern) == 256
    fig = plt.figure(figsize=(9.5, 4.4), layout='constrained')
    grid = fig.add_gridspec(1, 2, width_ratios=[1,1.2])
    ax = fig.add_subplot(grid[0,0]); ax.axis('off')
    ax.set_title('A. Keep one accepting branch of output 0', loc='left', fontsize=11)
    text = ('Fixed inputs: x5 = 0, x7 = 0, x9 = 1\n\n'
            'Decimal anchor: 512\n'
            'Free coordinates: 0, 1, 2, 3, 4, 6, 8\n\n'
            'Sumandos = [0 … 31] ∪ [64 … 95]\n'
            '                     ∪ [256 … 287] ∪ [320 … 351]\n\n'
            'Add each offset to 512: 128 addresses\n'
            'At every one of them, y0 = 1.\n\n'
            'Also require y1 = 1: fix x0 = 1.\n'
            'New anchor 513, free mask 350:\n'
            '64 addresses remain on this branch.')
    ax.text(0,.94,text,va='top',fontsize=10,linespacing=1.45)
    ax = fig.add_subplot(grid[0,1]); ax.axis('off')
    ax.set_title('B. Read the same addresses in the output table', loc='left', fontsize=11)
    addresses = [512,513,514,515,768,769,862,863]
    data = [[x-512,x,binary(transitions[x]),str(transitions[x]&1),
             str((transitions[x]>>1)&1)] for x in addresses]
    tab = ax.table(cellText=data, colLabels=['Offset','Address','Output y0 … y9','y0','y1'],
                   cellLoc='center',loc='center',colWidths=[.14,.16,.42,.14,.14])
    tab.auto_set_font_size(False);tab.set_fontsize(9);tab.scale(1,1.7)
    for (r,c),cell in tab.get_celld().items():
        cell.set_edgecolor('white')
        cell.set_facecolor('#d9eef0' if r==0 else '#ffead8' if addresses[r-1]&1 else '#f3f6f8')
    ax.text(.5,.06,'Selected rows; gaps are omitted.\nOrange rows satisfy (y0, y1) = (1, 1).',
            transform=ax.transAxes,ha='center',fontsize=9)
    save(fig,'schema_unfolding')

    # One complete ten-bit block per output row: no padding or ignored bits.
    row_estimator = BDM(ndim=1, shape=(10,), partition=PartitionIgnore)
    row_scores = {y: float(row_estimator.bdm(np.array([(y>>i)&1 for i in range(10)],
                                                   dtype=int))) for y in set(transitions)}
    row_data = [{'input_address': x, 'output_address': y, 'output_bits': binary(y),
                 'row_bdm': row_scores[y], 'network_program_bits': 325}
                for x,y in enumerate(transitions)]
    assert record['compression']['program_bit_length'] == 325
    pd.DataFrame(row_data).to_csv(assets/'row_complexity.csv',index=False)
    addresses = sorted(set([0, start, chosen[0], 512, 513, 1023]))
    table('row_complexity', ['Input $x$', 'Output $F_A(x)$', 'Output bits', 'Row BDM', '$L_A$ (bits)'],
          [[x,transitions[x],r'\texttt{'+binary(transitions[x])+'}',f'{row_scores[transitions[x]]:.3f}',325]
           for x in addresses], 'rrlrr')

    catalogue = next(c for c in summary['catalogues']
                     if c['base_id']==base['base_id'] and c['kind']=='EDGE_ADD')
    point_rows=[]
    for effect in catalogue['effects']:
        candidate = read(source/'main/networks'/f"{effect['network_sha256']}.json", sealed=True)
        p = probability_map(candidate)
        infinite = any(x not in q for x in p)
        kl = None if infinite else sum(float(v)*math.log(float(v/q[x])) for x,v in p.items())
        assert infinite == effect['infinite_kl']
        if not infinite:
            assert math.isclose(kl,effect['D_KL_nats'],abs_tol=1e-12)
        target = p.get(catalogue['target_state'], Fraction(0))
        linear = sum(v*Fraction(x.bit_count(),10) for x,v in p.items())
        point_rows.append({'perturbation_id':effect['perturbation_id'],
                           'network_sha256':effect['network_sha256'],'kl_nats':kl,
                           'infinite_kl':infinite, 'target_payoff':float(target),
                           'linear_payoff':float(linear),'program_bits':effect['program_bits'],
                           'bdm_matrix':effect['bdm'],'feasible_at_025':not infinite and kl<=.25})
    frame=pd.DataFrame(point_rows); assert len(frame)==74
    frame.to_csv(assets/'complexity_frontier.csv',index=False)
    finite=frame[~frame.infinite_kl]
    assert len(finite)==29 and frame.feasible_at_025.sum()==13
    for loss, metric in [('L_SINGLE_TARGET','target_payoff'),('L_LINEAR','linear_payoff')]:
        for saved in catalogue['sensitivity'][loss]:
            feasible = finite[finite.kl_nats <= saved['C']]
            assert len(feasible) == saved['n_feasible']
            assert math.isclose(feasible[metric].max(), saved['V_k_C'], abs_tol=1e-12)
    norm=Normalize(frame.program_bits.min(),frame.program_bits.max())
    fig,axes=plt.subplots(1,2,figsize=(9,4.1),layout='constrained')
    for ax,metric,title in zip(axes,['target_payoff','linear_payoff'],
                               ['A. Target-state payoff','B. Mean active-node payoff']):
        ax.scatter(finite.kl_nats,finite[metric],c=finite.program_bits,cmap='viridis',
                   norm=norm,s=60,edgecolors='white',linewidths=.4)
        ax.axvline(.25,color=ORANGE,ls='--',lw=1,label='Primary budget C = 0.25')
        baseline=float(q.get(catalogue['target_state'],0)) if metric=='target_payoff' else \
                 float(sum(v*Fraction(x.bit_count(),10) for x,v in q.items()))
        ax.scatter([0],[baseline],marker='*',c='black',s=110,label='Baseline (not a change)')
        ax.set(xlabel='Actual forward KL (nats)',ylabel='Expected payoff',title=title)
        ax.grid(alpha=.12)
    axes[0].legend(frameon=False,fontsize=7.5)
    fig.colorbar(ScalarMappable(norm=norm,cmap='viridis'),ax=axes,
                 label='Causal description length (bits)',shrink=.85)
    save(fig,'complexity_frontier')
    fig=plt.figure(figsize=(10,4.7),layout='constrained')
    for i,(metric,title) in enumerate([('target_payoff','A. Target-state payoff'),
                                       ('linear_payoff','B. Mean active-node payoff')]):
        ax=fig.add_subplot(1,2,i+1,projection='3d')
        for feasible,color,label in [(True,TEAL,'KL ≤ 0.25'),(False,ORANGE,'KL > 0.25')]:
            subset=finite[finite.feasible_at_025==feasible]
            ax.scatter(subset.kl_nats,subset[metric],subset.program_bits,
                       c=color,s=30,alpha=.9,label=label,depthshade=False)
        ax.set_title(title)
        ax.set_xlabel('Actual KL (nats)', labelpad=10, fontsize=9)
        ax.set_ylabel('Expected payoff', labelpad=14, fontsize=9)
        ax.text2D(.5, .91, 'Height: causal description length (bits)',
                  transform=ax.transAxes, ha='center', fontsize=9)
        ax.tick_params(labelsize=8)
        ax.view_init(elev=24,azim=-58)
        ax.set_box_aspect((1, 1, .8), zoom=.78)
    ax.legend(frameon=False,fontsize=8,loc='upper right')
    save(fig,'complexity_frontier_3d')
    details={'cycles_in_transition_order':cycles,'basin_sizes_recomputed':basin_counts,
             'cycle_probability_sum':str(sum(q.values())),
             'illustrated_transient':start,'schema_positions':len(positions),
             'branch_two_output_positions':len(matching),'full_two_output_positions':len(full_pattern),
             'row_bdm':{'implementation':'pybdm','version':'0.1.0','ndim':1,'shape':[10],
                        'partition':'PartitionIgnore','padding_bits':0,'discarded_bits':0,
                        'minimum':min(row_scores.values()),'maximum':max(row_scores.values()),
                        'distinct_outputs':len(row_scores),'rows':len(row_data)},
             'frontier_changes':len(frame),'finite_kl':len(finite),'infinite_kl':int(frame.infinite_kl.sum()),
             'feasible_at_025':int(frame.feasible_at_025.sum()),
             'complexity_range_feasible':[int(frame[frame.feasible_at_025].program_bits.min()),
                                          int(frame[frame.feasible_at_025].program_bits.max())]}
    write_json(assets/'explanatory_checks.json',details)
    return details
