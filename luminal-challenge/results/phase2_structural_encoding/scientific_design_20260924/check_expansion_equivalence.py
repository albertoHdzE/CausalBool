"""Lead experiment: compare exact-cover expansion with direct Hamming neighbors."""
from pathlib import Path
import hashlib
import itertools
import json
import random
from research import structural_models as sm

def check(bits, elite):
    cover=sm.exact_cover(elite,bits,65536,10)
    assert cover.status=='COMPLETE'
    expanded=sm.expand_cubes(cover.cubes,bits)
    one=list(x for x,duplicate in sm.proposals('model_expand',bits,sorted(elite),cover.cubes,elite,None) if not duplicate)
    control=list(x for x,duplicate in sm.proposals('one_bit',bits,sorted(elite),cover.cubes,elite,None) if not duplicate)
    assert one==control,(bits,elite,one,control)
    two=set(sm.ordered_union(expanded,None))|set(sm.ordered_union(sm.expand_cubes(expanded,bits),None))
    ball={e^sum(1<<i for i in coords) for e in elite for depth in (1,2) for coords in itertools.combinations(range(bits),depth)}
    assert two-elite==ball-elite,(bits,elite)

counts={}
for bits in range(4):
    for mask in range(1<<(1<<bits)):
        check(bits,{i for i in range(1<<bits) if mask>>i&1})
    counts[str(bits)]=1<<(1<<bits)
rng=random.Random(2026092404)
for bits in range(4,9):
    for _ in range(100):
        check(bits,set(rng.sample(range(1<<bits),rng.randrange(min(64,1<<bits)+1))))
report={'status':'PASS','exhaustive_elite_sets_by_width':counts,'random_elite_sets':500,'random_seed':2026092404,'claims_checked':['depth 1 identical ascending novel proposal sequence to one_bit','depth 1+2 identical novel set to Hamming distance at most 2'],'limits':'Finite implementation checks support the separate general set-theoretic proof; no performance or learning benefit is measured.','source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['research/structural_models.py','schema_index.py']}}
out=Path(__file__).with_name('EXPANSION_EQUIVALENCE.json');out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
