"""Derive manuscript evidence and figures from the two released studies."""
from __future__ import annotations

import hashlib
import json
import math
import os
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / 'results'
SOURCE = RESULTS / 'joint_degree5_final_replication_v1'
FINAL = RESULTS / 'joint_degree5_final_replication_analysis_v1'
PREVIOUS = RESULTS / 'joint_degree5_final_analysis_v1'
ASSETS = HERE / 'generated'
ASSETS.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(ASSETS / '.mplcache'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import networkx as nx
import numpy as np
import pandas as pd

from doppel_challenge.adapters import Network, repertoire
from doppel_challenge.records import compute_sha256, scientific_digest
from doppel_challenge.repertoire_program import (
    compile_repertoire_program, compile_schema_program, deserialize_program,
    export_output_schemata, iter_output_rows, program_metadata, serialize_program,
)

TEAL, ORANGE, BLUE, GREY = '#007f86', '#c86428', '#4666a5', '#77818d'
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.titleweight': 'medium', 'axes.labelcolor': '#243340',
    'text.color': '#243340', 'pdf.fonttype': 42, 'savefig.dpi': 180,
})
INPUTS = {}
SOURCE_DRIFT = []


def raw_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path, sealed=False):
    obj = json.loads(path.read_text())
    INPUTS[str(path.relative_to(ROOT.parent))] = raw_hash(path)
    if sealed:
        assert obj['sha256'] == compute_sha256(obj), path
        assert obj['scientific_digest'] == scientific_digest(obj), path
    return obj


def check_release(folder):
    rel = read(folder / 'release.json', sealed=True)
    assert rel['release_ready'] and not rel['errors']
    for name, digest in rel['artifact_hashes'].items():
        assert raw_hash(folder / name) == digest, name
    for name, digest in rel['source_hashes'].items():
        current = raw_hash(ROOT.parent / name)
        if current != digest:
            # Historical notebooks have sealed executed snapshots. Use those
            # snapshots, and report later working-copy edits explicitly.
            assert folder == PREVIOUS and name in {
                'doppel-challenge/notebooks/01_exact_n8_walkthrough.ipynb',
                'doppel-challenge/notebooks/02-pre-analysis.ipynb'}, name
            snapshot = Path(name).stem + '.executed.ipynb'
            assert snapshot in rel['artifact_hashes']
            SOURCE_DRIFT.append({'path': name, 'release_source_sha256': digest,
                'current_sha256': current, 'used_snapshot': str((folder / snapshot).relative_to(ROOT.parent)),
                'snapshot_sha256': rel['artifact_hashes'][snapshot]})
    return rel


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')


def save(fig, name):
    fig.savefig(ASSETS / f'{name}.pdf', bbox_inches='tight')
    fig.savefig(ASSETS / f'{name}.png', bbox_inches='tight')
    plt.close(fig)


def table(name, headings, rows, columns):
    text = '\\begin{tabular}{' + columns + '}\n\\toprule\n'
    text += ' & '.join(headings) + ' \\\\\n\\midrule\n'
    text += ''.join(' & '.join(map(str, row)) + ' \\\\\n' for row in rows)
    text += '\\bottomrule\n\\end{tabular}\n'
    (ASSETS / f'{name}.tex').write_text(text)


def submasks(mask):
    values, current = [], mask
    while True:
        values.append(current)
        if current == 0:
            return sorted(values)
        current = (current - 1) & mask


def worked_example(manifest):
    base = next(b for b in manifest['bases'] if b['base_id'] == 'ring_n10_s1000')
    record = read(SOURCE / 'main/networks' / f"{base['network_sha256']}.json", sealed=True)
    spec = base['network']
    net = Network(n=10, C=spec['cm'], gates=spec['dyn'], params=spec['params'])
    programme = compile_repertoire_program(net)
    metadata = program_metadata(programme)
    assert metadata['canonical_program_sha256'] == record['compression']['canonical_program_sha256']
    payload = serialize_program(programme)
    assert payload.hex() == record['compression']['payload_hex']
    restored = deserialize_program(payload, n=10)
    rows = list(iter_output_rows(restored))
    assert rows == repertoire(net)
    transitions = [sum(bit << j for j, bit in enumerate(row)) for row in rows]
    assert transitions == record['dynamics']['repertoire']['transition_map']
    schemata = [export_output_schemata(programme, j) for j in range(10)]
    assert serialize_program(compile_schema_program(10, schemata)) == payload
    schema_rows = []
    for j, cubes in enumerate(schemata):
        positions = []
        for anchor, mask in cubes:
            offsets = submasks(mask)
            assert anchor & mask == 0
            positions.extend(anchor + s for s in offsets)
            schema_rows.append({'output': j, 'anchor': anchor, 'free_mask': mask,
                                'offset_count': len(offsets)})
        assert len(positions) == len(set(positions))
        assert sorted(positions) == [i for i, row in enumerate(rows) if row[j]]
    rep = record['dynamics']['repertoire']
    assert sum(Fraction(p['numerator'], p['denominator']) for p in rep['probability_fractions']) == 1
    pd.DataFrame(rows, columns=[f'y{j}' for j in range(10)]).to_csv(ASSETS / 'worked_output.csv', index_label='address')
    pd.DataFrame(schema_rows).to_csv(ASSETS / 'worked_schemata.csv', index=False)
    pd.DataFrame(programme.nodes, columns=['coordinate', 'zero', 'one'],
                 index=range(2, 2+len(programme.nodes))).to_csv(ASSETS / 'worked_decisions.csv', index_label='reference')
    write_json(ASSETS / 'worked_network.json', spec)
    write_json(ASSETS / 'worked_programme.json', {
        **metadata, 'payload_hex': payload.hex(), 'outputs': programme.outputs,
        'nodes': programme.nodes, 'schemata': schemata,
    })
    table('schemas', ['Output', 'Gate', 'Decimal anchors and free masks', 'One positions'],
          [[j, spec['dyn'][j], ', '.join(f'({a}, {m})' for a, m in cubes),
            sum(1 << m.bit_count() for a, m in cubes)] for j, cubes in enumerate(schemata)], 'rlp{8cm}r')
    table('decisions', ['Reference', 'Coordinate', 'Zero child', 'One child'],
          [[i+2, *node] for i, node in enumerate(programme.nodes)], 'rrrr')
    table('worked_lengths', ['Field', 'Logical bits'], [
        ['Node-count code', metadata['decision_count_bits']],
        ['Decision records', metadata['decision_record_bits']],
        ['Ordered output references', metadata['output_reference_bits']],
        ['Total programme', metadata['program_bit_length']],
        ['Raw ordered output', metadata['raw_bit_length']],
        ['Byte padding (separate)', metadata['padding_bits']],
    ], 'lr')
    fig = plt.figure(figsize=(8.2, 5.9), layout='constrained')
    grid = fig.add_gridspec(2, 2, height_ratios=[1, .28])
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, :])]
    graph = nx.DiGraph()
    graph.add_nodes_from(range(10))
    graph.add_edges_from((source, target) for target, row in enumerate(net.C) for source, bit in enumerate(row) if bit)
    nx.draw_networkx(graph, nx.circular_layout(graph), ax=axes[0], node_color='#d9eef0',
                     edge_color=GREY, node_size=440, arrowsize=12, font_size=10,
                     connectionstyle='arc3,rad=0.08', width=1.1)
    axes[0].set_title('A. Follow source → target'); axes[0].axis('off')
    axes[1].imshow(net.C, cmap=ListedColormap(['#f3f6f8', TEAL]), vmin=0, vmax=1)
    axes[1].set(xticks=range(10), yticks=range(10), xlabel='Source node', ylabel='Target node', title='B. Read one target row')
    for j, row in enumerate(net.C):
        for i, bit in enumerate(row):
            axes[1].text(i, j, str(bit), ha='center', va='center', fontsize=9.5, color='white' if bit else '#8593a0')
    axes[2].axis('off'); axes[2].set_title('C. Apply the corresponding gate in this dynamics vector', fontsize=10)
    tab = axes[2].table(cellText=[['Node',*range(10)], ['Gate',*spec['dyn']]],
                         loc='center', cellLoc='center')
    tab.auto_set_font_size(False); tab.set_fontsize(8); tab.scale(1, 1.6)
    for (r, c), cell in tab.get_celld().items():
        cell.set_edgecolor('white'); cell.set_facecolor('#d9eef0' if r == 0 else '#f3f6f8')
    save(fig, 'network')

    fig, ax = plt.subplots(figsize=(8.5, 4.8), layout='constrained')
    pos = {6:(0,3), 4:(-1.15,2), 5:(1.15,2), 2:(-1.15,1), 3:(1.15,1), 0:(-1.15,0), 1:(1.15,0)}
    branch_graph = nx.DiGraph(); branch_graph.add_nodes_from(pos)
    for ref in [6,4,5,2,3]:
        coord, zero, one = programme.nodes[ref-2]
        for value, child in [(0,zero),(1,one)]:
            nx.draw_networkx_edges(nx.DiGraph([(ref,child)]), pos, ax=ax,
                 edgelist=[(ref,child)], node_size=1600, arrowsize=18,
                 edge_color=GREY if value == 0 else TEAL,
                 style='dashed' if value == 0 else 'solid', width=1.6,
                 connectionstyle='arc3,rad=0.04')
    nx.draw_networkx_nodes(branch_graph, pos, ax=ax, node_color=['#d9eef0']*5+['#e7ebef','#ffdfc4'], node_size=1600)
    labels = {r:f'r{r}: x{programme.nodes[r-2][0]}?' for r in [6,4,5,2,3]}
    labels.update({0:'0',1:'1'});nx.draw_networkx_labels(branch_graph,pos,labels,ax=ax,font_size=10)
    ax.plot([], [], '--', color=GREY,label='Coordinate is 0');ax.plot([], [], color=TEAL,label='Coordinate is 1')
    ax.legend(loc='upper left',frameon=False,fontsize=9)
    ax.set_title('Output 0: three parity tests, shared continuations')
    ax.set_xlim(-2.6,2.5); ax.set_ylim(-.45,3.45); ax.axis('off')
    save(fig, 'decision_graph')
    return base, record, metadata


def result_figures(networks, groups, comparison, correlations):
    lengths = networks.groupby('n').agg(networks=('n','size'), raw_bits=('raw_bits','first'),
        program_min=('program_bits','min'), program_median=('program_bits','median'),
        program_max=('program_bits','max'), median_bdm=('bdm','median'))
    assert len(networks) == 106789 and (networks.program_bits < networks.raw_bits).all()
    lengths.to_csv(ASSETS / 'lengths.csv')
    table('lengths', ['$N$', 'Networks', 'Raw bits', 'Programme bits: min / median / max', 'BDM median'],
          [[n, f'{int(r.networks):,}', f'{int(r.raw_bits):,}',
            f'{int(r.program_min)} / {int(r.program_median)} / {int(r.program_max)}', f'{r.median_bdm:.2f}']
           for n,r in lengths.iterrows()], 'rrrrr')
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.8), layout='constrained')
    xx = np.arange(3)
    axes[0].bar(xx-.18, lengths.raw_bits, .36, color=GREY, label='Raw binary table')
    axes[0].bar(xx+.18, lengths.program_median, .36, color=TEAL, label='Median programme')
    for i, (_,r) in enumerate(lengths.iterrows()):
        axes[0].text(i-.18,r.raw_bits*1.13,f'{int(r.raw_bits):,}',ha='center',fontsize=9)
        axes[0].text(i+.18,r.program_median*1.13,f'{int(r.program_median)}',ha='center',fontsize=9)
    axes[0].set(yscale='log',ylim=(80,150000),xticks=xx,xticklabels=['8','10','12'],
                xlabel='Number of nodes',ylabel='Bits (logarithmic scale)',title='A. How long is the exact description?')
    axes[0].legend(frameon=False,fontsize=9)
    bp=axes[1].boxplot([networks.loc[networks.n==n,'bdm'] for n in [8,10,12]],
                       tick_labels=['8','10','12'],showfliers=False,patch_artist=True,
                       medianprops={'color':ORANGE,'linewidth':2})
    for box in bp['boxes']:box.set_facecolor('#dce4f2')
    axes[1].set(xlabel='Number of nodes',ylabel='BDM estimate (BDM units)',title='B. What does the block estimate report?')
    save(fig,'lengths_bdm')
    fig, axes = plt.subplots(1, 3, figsize=(8.5, 5.8), sharey=True, layout='constrained')
    key = [('hub',8),('hub',10),('hub',12),('modular',8),('modular',10),('modular',12),
           ('ring',8),('ring',10),('ring',12),('sparse_random',8),('sparse_random',10),('sparse_random',12)]
    for ax,metric,title in zip(axes,['delta_program_bits','delta_bdm','total_variation'],
             ['Programme change (bits)','BDM change (BDM units)','Long-run total variation']):
        for kind,colour,offset in [('EDGE_ADD',TEAL,-.15),('EDGE_REMOVE',ORANGE,.15)]:
            rs=[groups[(groups.family==f)&(groups.n==n)&(groups.kind==kind)].iloc[0] for f,n in key]
            means=np.array([r[f'mean_{metric}'] for r in rs])
            lo=np.array([r[f'{metric}_lo95'] for r in rs]);hi=np.array([r[f'{metric}_hi95'] for r in rs])
            ax.errorbar(means,np.arange(12)+offset,xerr=[means-lo,hi-means],fmt='o',markersize=4,
                         color=colour,capsize=2,label='Add an edge' if kind=='EDGE_ADD' else 'Remove an edge')
        ax.axvline(0,color=GREY,lw=.7);ax.set_title(title,fontsize=9);ax.grid(axis='y',alpha=.12)
    axes[0].set_yticks(range(12),[f'{f.replace("sparse_random","Sparse random").title()}, N={n}' for f,n in key])
    axes[0].invert_yaxis()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9, ncol=2, loc='outside lower center')
    save(fig,'effects')
    table('strata', ['Family', '$N$', 'Change', r'$L/|R|$ (\%)', '$\\Delta L$', '$\\Delta$BDM', 'TV'],
      [[r.family.replace('_',' '),r.n,'Add' if r.kind=='EDGE_ADD' else 'Remove',
        f'{100*r.mean_program_ratio:.2f}',f'{r.mean_delta_program_bits:.2f}',
        f'{r.mean_delta_bdm:.2f}',f'{r.mean_total_variation:.3f}'] for r in groups.itertuples()], 'lrlrrrr')
    table('replication', ['Quantity', 'Smallest change', 'Largest change'],
      [[label,f'{scale*comparison[col].min():.3f}',f'{scale*comparison[col].max():.3f}']
       for col,label,scale in [('change_mean_program_ratio','Programme/raw (percentage points)',100),
            ('change_mean_delta_program_bits','Programme effect (bits)',1),
            ('change_mean_delta_bdm','BDM effect (BDM units)',1),
            ('change_mean_total_variation','Total variation effect',1)]], 'lrr')
    return lengths.reset_index().to_dict('records')


def frontier_evidence(summary, base, record):
    rows=[]
    for cat in summary['catalogues']:
        for loss, points in cat['sensitivity'].items():
            for p in points:
                assert p['V_k_C'] is None or p['V_k_C'] <= p['upper_bound'] + 1e-9
                rows.append({**{k:cat[k] for k in ['base_id','family','n','kind']},'loss':loss,**p})
    frame=pd.DataFrame(rows);assert len(frame)==19200
    frame.to_csv(ASSETS/'frontiers.csv',index=False)
    primary=frame[frame.C==.25]
    counts=primary.groupby(['kind','loss']).agg(catalogues=('base_id','size'),
                         with_feasible_change=('V_k_C','count')).reset_index()
    counts['without_feasible_change']=counts.catalogues-counts.with_feasible_change
    counts.to_csv(ASSETS/'frontier_coverage.csv',index=False)
    table('frontier_coverage',['Change','Payoff','Catalogues','Feasible','No feasible change'],
      [['Add' if r.kind=='EDGE_ADD' else 'Remove', 'Target' if r.loss=='L_SINGLE_TARGET' else 'Linear',
        r.catalogues,r.with_feasible_change,r.without_feasible_change] for r in counts.itertuples()], 'llrrr')
    cat=next(c for c in summary['catalogues'] if c['base_id']==base['base_id'] and c['kind']=='EDGE_ADD')
    points=cat['sensitivity']['L_LINEAR']
    table('worked_frontier',['KL budget','Feasible changes','Best payoff','Saved upper bound'],
          [[p['C'],p['n_feasible'],f"{p['V_k_C']:.6f}",f"{p['upper_bound']:.6f}"] for p in points], 'rrrr')
    fig,axes=plt.subplots(1,2,figsize=(8.5,3.6),layout='constrained')
    for ax,loss,title in zip(axes,['L_SINGLE_TARGET','L_LINEAR'],['A. Payoff at the target state','B. Mean active-node payoff']):
        ps=cat['sensitivity'][loss];x=[p['C'] for p in ps]
        ax.plot(x,[p['upper_bound'] for p in ps],'o--',color=ORANGE,label='Saved relaxation upper bound')
        ax.plot(x,[p['V_k_C'] for p in ps],'s-',color=TEAL,label='Best admissible edge addition')
        ax.set(xlabel='KL budget (nats)',ylabel='Expected payoff',title=title);ax.grid(alpha=.12)
    axes[0].legend(frameon=False,fontsize=8)
    save(fig,'frontier')
    best=next(p for p in points if p['C']==.25)
    selected=next(e for e in cat['effects'] if e['perturbation_id']==best['best_perturbation_id'])
    best_record=read(SOURCE/'main/networks'/f"{selected['network_sha256']}.json",sealed=True)
    q=record['dynamics']['repertoire'];p=best_record['dynamics']['repertoire']
    qmap={x:Fraction(v['numerator'],v['denominator']) for x,v in zip(q['support'],q['probability_fractions'])}
    pmap={x:Fraction(v['numerator'],v['denominator']) for x,v in zip(p['support'],p['probability_fractions'])}
    expected=sum(prob*Fraction(x.bit_count(),10) for x,prob in pmap.items())
    assert math.isclose(float(expected),best['V_k_C'],abs_tol=1e-12)
    computed_kl=sum(float(prob)*math.log(float(prob/qmap[x])) for x,prob in pmap.items())
    assert math.isclose(computed_kl,best['best_D_KL_nats'],abs_tol=1e-12)
    pd.DataFrame([{'state':x,'q_exact':str(qmap.get(x,0)),'p_exact':str(pmap.get(x,0))}
                   for x in sorted(qmap.keys()|pmap.keys())]).to_csv(ASSETS/'worked_distributions.csv',index=False)
    return {'primary_coverage':counts.to_dict('records'),'worked_best':best,
            'worked_best_exact_payoff':str(expected),'worked_kl_recomputed':computed_kl}


def main():
    previous=check_release(PREVIOUS);release=check_release(FINAL)
    manifest=read(SOURCE/'main_manifest.json',sealed=True)
    summary=read(SOURCE/'main/summary.json',sealed=True)
    assert summary['sha256']==release['source']['main_summary_sha256']
    assert manifest['sha256']==release['source']['main_manifest_sha256']
    networks=pd.read_csv(FINAL/'network_metrics.csv')
    groups=pd.read_csv(FINAL/'group_summary.csv')
    comparison=pd.read_csv(FINAL/'comparison_with_previous.csv')
    correlations=pd.read_csv(FINAL/'base_correlations.csv')
    base,record,metadata=worked_example(manifest)
    from explanatory_evidence import extend_example
    explanatory = extend_example(base, record, summary, ASSETS, SOURCE,
                                 read, save, table, write_json)
    lengths=result_figures(networks,groups,comparison,correlations)
    frontier=frontier_evidence(summary,base,record)
    write_json(HERE/'evidence.json',{'input_hashes':INPUTS,
      'previous_release_sha256':previous['sha256'],'replication_release_sha256':release['sha256'],
      'working_copy_notebook_differences':SOURCE_DRIFT,
      'checks':{'release_artifacts_match':True,'current_release_sources_match':not SOURCE_DRIFT,
          'historical_executed_notebook_snapshots_match':True,
          'worked_output_bits_checked':10240,'worked_schema_rebuild_identical':True,
          'worked_all_schema_positions_checked':True,'worked_probability_sum_exact':True,
          'frontier_upper_bound_checks':19200,'all_main_programmes_shorter_than_raw':True},
      'worked_example':metadata,'lengths':lengths,'frontiers':frontier,
      'explanatory_extension':explanatory,
      'generated_hashes':{str(p.relative_to(HERE)):raw_hash(p) for p in sorted(ASSETS.iterdir()) if p.is_file()}})
    print(json.dumps({'worked_programme_bits':metadata['program_bit_length'],
          'checked_bits':10240,'frontiers':frontier,'lengths':lengths},indent=2))


if __name__=='__main__':
    main()
