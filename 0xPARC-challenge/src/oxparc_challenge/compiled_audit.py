"""Lead-owned audit of actual Circom R1CS rows, including malicious assignments."""
from pathlib import Path
import copy
import hashlib
import json
import resource
import sys
import time

from . import FIELD_PRIME as P
from .circom import export_circom, compile_circuit, run_witness
from .gadgets import (build_range, witness_range, build_exclude_one,
                     witness_exclude_one, build_factor64, witness_factor64,
                     build_factor4096, witness_factor4096)
from .row_evaluator import check_rows, check_compiled_rows

B = 1 << 64


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(directory, build_directory):
    directory, build_directory = Path(directory), Path(build_directory)
    directory.mkdir(parents=True, exist_ok=True)
    build_directory.mkdir(parents=True, exist_ok=True)
    command = 'python -m oxparc_challenge.compiled_audit evidence .build/compiled'
    report = {'status': 'UNKNOWN', 'command': command, 'checks': [], 'families': {},
              'source_sha256': {p.name: sha(p) for p in Path(__file__).parent.glob('*.py')}}
    previous_checkpoint = time.monotonic()

    def save():
        (directory/'compiled_audit.json').write_text(json.dumps(report, indent=2)+'\n')

    def record(test_id, ok, **detail):
        nonlocal previous_checkpoint
        current = time.monotonic()
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
        ok = bool(ok) and peak < 4*1024**3
        report['checks'].append({'test_id': test_id, 'requirement': test_id.split('-')[1],
                                 'status': 'PASS' if ok else 'FAIL', 'comparison': 'exact modular rows',
                                 'elapsed_seconds': current-previous_checkpoint,
                                 'timing_scope': 'since previous checkpoint, including setup unless explicitly timed',
                                 'peak_rss_bytes': peak, 'resource_outcome': 'within limits' if peak<4*1024**3 else 'memory exceeded',
                                 'source_hash_record': 'compiled_audit.json#/source_sha256',
                                 'artifact_hash_record': 'compiled_audit.json#/families',
                                 'command': command, 'exit_code': 0 if ok else 1, **detail})
        previous_checkpoint = current
        save()
        if not ok:
            raise AssertionError(test_id)

    def assign_bits(w, name, value, width=64):
        w[name] = value % P
        for bit in range(width):
            w[f'{name}_b{bit}'] = (value >> bit) & 1

    families = [
        ('Q5', build_range(), [witness_range(x) for x in (0, 1, B-1)]),
        ('Q6', build_exclude_one(), [witness_exclude_one(x) for x in (0, 2, P-1)]),
        ('Q7', build_factor64(), [witness_factor64(u*v, u, v) for u,v in
                                ((2,3), (3,2), (65537,65539), (2,(B-2)//2))]),
        ('Q8', build_factor4096(), [witness_factor4096(u*v,u,v) for u,v in
                                  ((2**2047+123,2**2047+321), (2,2**4094+1), (2**4094+1,2))])]
    save()
    try:
        for q, system, valid in families:
            started = time.monotonic()
            source = export_circom(system, directory/'circuits'/f'{q}.circom')
            compiled = compile_circuit(source, build_directory/q)
            symbols = {}
            for line in compiled['sym'].read_text().splitlines():
                _, index, _, name = line.split(',',3)
                if name.startswith('main.') and int(index) >= 0:
                    symbols[name[5:]] = int(index)
            record(f'A-{q}-all-signals-compiled', set(symbols) == set(system.signals))
            family = {'source_sha256': sha(source), 'system_sha256': system.structural_hash(),
                      'source_rows': len(system.constraints), 'signals': len(system.signals),
                      'compile_command': compiled['command'], 'valid_witnesses': [],
                      'compiled_artifact_sha256': {k: sha(compiled[k]) for k in ('r1cs','wasm','sym')}}
            report['families'][q] = family
            rows = None
            for index, w in enumerate(valid):
                tick = time.monotonic()
                record(f'A-{q}-source-valid-{index}', not check_rows(system.to_dict(),w))
                artifacts = run_witness(compiled,w,build_directory/q/f'case_{index}')
                rows = json.loads(artifacts['r1cs_json'].read_text())
                values = [int(x) for x in json.loads(artifacts['json'].read_text())]
                family['valid_witnesses'].append({'index': index, 'commands': artifacts['commands'],
                    'witness_sha256': sha(artifacts['json']), 'r1cs_json_sha256': sha(artifacts['r1cs_json']),
                    'elapsed_seconds': time.monotonic()-tick})
                record(f'A-{q}-compiled-valid-{index}', not check_compiled_rows(rows,values),
                       witness_sha256=sha(artifacts['json']), elapsed_seconds=time.monotonic()-tick)
                if index == 0:
                    base = dict(w)
                    # One exported compiled witness retained compactly for independent inspection.
                    import gzip
                    for name, path in (('r1cs',artifacts['r1cs_json']), ('witness',artifacts['json'])):
                        with open(directory/'circuits'/f'{q}_{name}.json.gz','wb') as stream:
                            with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as zipped:
                                zipped.write(path.read_bytes())
                    (directory/'circuits'/f'{q}_symbols.json').write_text(json.dumps(symbols,sort_keys=True)+'\n')
            family['compiled_rows'] = len(rows['constraints'])
            family['compiled_variables'] = rows['nVars']

            def compiled_values(w):
                values = [0]*rows['nVars']; values[0] = 1
                for name, value in w.items(): values[symbols[name]] = value
                return values

            def reject(name, w, omit_signals=()):
                tick = time.monotonic()
                values = compiled_values(w)
                failures = check_compiled_rows(rows, values)
                record(f'A-{q}-{name}', bool(failures), failing_compiled_rows=failures[:16],
                       failing_row_count=len(failures), elapsed_seconds=time.monotonic()-tick)
                if omit_signals:
                    indices = {str(symbols[s]) for s in omit_signals}
                    # Remove only rows involving specified auxiliary range bits.
                    # This is a deliberate weakened-circuit control, never a release artifact.
                    weakened = {**rows, 'constraints': [r for r in rows['constraints']
                                if not any(indices.intersection(lc) for lc in r)]}
                    record(f'A-{q}-{name}-omitted-range-control',
                           not check_compiled_rows(weakened,values),
                           removed_rows=len(rows['constraints'])-len(weakened['constraints']))

            def mutate(name, signal, value):
                w=dict(base); w[signal]=value%P; reject(name,w)

            if q == 'Q5':
                for value in (B,B+1,P-1): mutate(f'range-{value}', 'x', value)
                w=dict(base);w['x']=B;w['x_b63']=2
                reject('nonbinary-omitted-range',w,['x_b63'])
                for value in (-1,P,P+1):
                    w=dict(base);w['x']=value
                    try:check_rows(system.to_dict(),w)
                    except ValueError: record(f'A-Q5-canonical-api-{value}',True)
                    else:record(f'A-Q5-canonical-api-{value}',False)
            elif q == 'Q6':
                for s in (0,1,P-1):
                    w={'r':1,'s':s};reject(f'exclude-one-{s}',w)
                mutate('incorrect-inverse','s',3)
            elif q == 'Q7':
                for u,v,n in ((0,6,0),(1,6,6),(6,1,6)):
                    w=dict(base)
                    for signal,value in (('u',u),('v',v),('n',n)):assign_bits(w,signal,value)
                    for signal,value in (('u',u),('v',v)):
                        w[f'{signal}_inv']=pow((value>>1).bit_count(),P-2,P)
                        w[f'{signal}_one_inv']=pow((value-1)%P,P-2,P)
                    reject(f'trivial-{u}-{v}',w)
                mutate('changed-product','n',7)
                w=dict(base);u=2;v=(P+7)//2
                for signal,value in (('u',u),('v',v),('n',7)):assign_bits(w,signal,value)
                for signal,value in (('u',u),('v',v)):
                    w[f'{signal}_inv']=pow(sum(w[f'{signal}_b{i}'] for i in range(1,64)),P-2,P)
                    w[f'{signal}_one_inv']=pow(value-1,P-2,P)
                reject('modular-alias-factor-range',w,[f'v_b{i}' for i in range(64)])
            else:
                for signal in ('q_0_0','carry_1','carry_0','carry_128','n_63','u_63','v_63','carry_1_b69'):
                    mutate('mutate-'+signal,signal,base[signal]+1)
                for prefix in ('u','v'):
                    for value in (0,1):
                        w=witness_factor4096(6,2,3)
                        u,v=(value,3) if prefix=='u' else (2,value)
                        for name,integer in (('u',u),('v',v),('n',u*v)):
                            for limb in range(64):assign_bits(w,f'{name}_{limb}',integer if limb==0 else 0)
                        for i in range(64):
                            for j in range(64):w[f'q_{i}_{j}']=w[f'u_{i}']*w[f'v_{j}']
                        w['u_inv']=pow((u>>1).bit_count(),P-2,P)
                        w['v_inv']=pow((v>>1).bit_count(),P-2,P)
                        # All products, packing, carries, and endpoints agree;
                        # exactly the selected factor's lower-bound row fails.
                        if len(check_compiled_rows(rows,compiled_values(w)))!=1:
                            raise AssertionError('trivial-factor control must isolate one row')
                        reject(f'trivial-{prefix}-{value}',w)
                # uv=n+P. Unbounded field carries satisfy every multiplication
                # column and both endpoints; the released carry ranges reject it.
                u,v,n=2,(P+7)//2,7
                w=witness_factor4096(u*v,u,v)
                for limb in range(64):assign_bits(w,f'n_{limb}',(n>>(64*limb))%(B))
                w['carry_0']=0
                for k in range(128):
                    total=w[f'carry_{k}']+sum(w[f'q_{i}_{k-i}'] for i in range(max(0,k-63),min(63,k)+1))
                    w[f'carry_{k+1}']=((total-(w[f'n_{k}'] if k<64 else 0))*pow(B,-1,P))%P
                    if k<127:
                        for bit in range(70):w[f'carry_{k+1}_b{bit}']=(w[f'carry_{k+1}']>>bit)&1
                record('A-Q8-alias-endpoints-zero', w['carry_0']==w['carry_128']==0)
                reject('modular-alias-carry-range',w,[f'carry_{i}_b{j}' for i in range(1,128) for j in range(70)])
                # Public limb out of range while preserving its integer value
                # through an opposite adjustment to the next limb.
                w=witness_factor4096((B-1)**2,B-1,B-1)
                w['n_0']+=B;w['n_1']-=1;w['carry_1']-=1
                for name,width in (('n_0',64),('n_1',64),('carry_1',70)):
                    value=w[name]
                    for bit in range(width):w[f'{name}_b{bit}']=(value>>bit)&1
                reject('public-limb-range',w,[f'n_0_b{i}' for i in range(64)])
                # Product 2^4096 has an upper output limb and cannot equal zero.
                w=dict(base)
                for prefix,value in (('u',2**4095),('v',2),('n',0)):
                    for limb in range(64):assign_bits(w,f'{prefix}_{limb}',(value>>(64*limb))%B)
                for i in range(64):
                    for j in range(64):w[f'q_{i}_{j}']=w[f'u_{i}']*w[f'v_{j}']
                w['carry_0']=0
                for k in range(128):
                    total=w[f'carry_{k}']+sum(w[f'q_{i}_{k-i}'] for i in range(max(0,k-63),min(63,k)+1))
                    w[f'carry_{k+1}']=total//B
                    if k<127:
                        for bit in range(70):w[f'carry_{k+1}_b{bit}']=(w[f'carry_{k+1}']>>bit)&1
                w['u_inv']=w['v_inv']=1
                reject('overflow-upper-output',w)
            family['elapsed_seconds']=time.monotonic()-started
            save(); print(q, family['compiled_rows'], 'rows audited', flush=True)
        report['status']='PASS'; save(); return 0
    except Exception as exc:
        report['status']='FAIL' if isinstance(exc,AssertionError) else 'UNKNOWN'
        report['error']=repr(exc);save();raise


if __name__ == '__main__':
    raise SystemExit(run(*sys.argv[1:]))
