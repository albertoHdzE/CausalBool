"""Reproduce the manuscript's bounded index-deconvolution examples."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT.parent / 'index-deconvolution/src'))
from oxparc_challenge.boolean import build_majority, evaluate_boolean
from deconvolution import essential_variables, reduce_column


def main():
    records = []
    for n in (1, 3, 5, 7, 9, 11):
        circuit = build_majority(n)
        column = [evaluate_boolean(circuit, [(x >> i) & 1 for i in range(n)])[0]
                  for x in range(1 << n)]
        connected = essential_variables(column, n)
        reduced = reduce_column(column, n, connected)
        expected = [int(x.bit_count() > n // 2) for x in range(1 << n)]
        if connected != list(range(n)) or reduced != expected:
            raise RuntimeError(f'Majority deconvolution failed at {n}')
        records.append(dict(n=n, states=len(column), gates=len(circuit.gates),
                            connected_inputs=connected, active_indices=sum(column),
                            exact_reconstruction=True,
                            column_sha256=hashlib.sha256(bytes(column)).hexdigest()))
    # Display strings use x0,x1,x2; their index weights are 1,2,4.
    schemas = [dict(pattern='11*', anchor=3, offsets=[0, 4]),
               dict(pattern='1*1', anchor=5, offsets=[0, 2]),
               dict(pattern='*11', anchor=6, offsets=[0, 1])]
    expanded = [{s['anchor'] + offset for offset in s['offsets']} for s in schemas]
    if set.union(*expanded) != {3, 5, 6, 7}:
        raise RuntimeError('Schema expansion failed')
    padded = [int((x & 7).bit_count() >= 2) for x in range(32)]
    if essential_variables(padded, 5) != [0, 1, 2]:
        raise RuntimeError('Free-coordinate control failed')
    if reduce_column(padded, 5, [0, 1, 2]) != [int(x.bit_count() >= 2) for x in range(8)]:
        raise RuntimeError('Reduced repertoire control failed')
    naive = [int(sum(int(((x >> (3*g)) & 7).bit_count() >= 2) for g in range(3)) >= 2)
             for x in range(512)]
    target = [int(x.bit_count() >= 5) for x in range(512)]
    mismatches = [x for x in range(512) if naive[x] != target[x]]
    if not mismatches or sum(naive) != sum(target) or essential_variables(naive, 9) != list(range(9)):
        raise RuntimeError('Incorrect-circuit control failed')
    sources = [Path(__file__), ROOT/'src/oxparc_challenge/boolean.py',
               ROOT.parent/'index-deconvolution/src/deconvolution.py',
               ROOT.parent/'index-deconvolution/src/causalbool.py']
    data = dict(status='PASS', majority=records, schemas=schemas,
                free_coordinate_control=dict(inputs=5, connected_inputs=[0, 1, 2], states=32),
                naive_control=dict(states=512, active_indices=sum(naive),
                                   disagreements=len(mismatches), connected_inputs=list(range(9))),
                source_sha256={str(p.relative_to(ROOT.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sources})
    (ROOT/'evidence/paper_index.json').write_text(json.dumps(data, indent=2)+'\n')
    print(f'Index deconvolution: {sum(r["states"] for r in records)} circuit states; '
          f'naive control differs on {len(mismatches)} states; PASS')


if __name__ == '__main__':
    main()
