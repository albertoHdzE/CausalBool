"""AUDIT02 control: is the CA-arm 'exact recovery' criterion informative,
or is it satisfied by construction for every ECA rule?

Same pipeline, same knobs, same seeds as index_method_comparison/run_comparison.py.
Only the rule list changes: 10 chosen -> all 256 (the common coordinate)."""
import os, sys, json, collections
HERE = "imp-causal-paper/index_method_comparison"
sys.path.insert(0, HERE)
import numpy as np
from run_comparison import (evolve_eca, deconvolve_ca, ca_global_map,
                            Network, repertoire, WIDTH, STEPS, N_ICS, RADIUS, SEED, RULES)

def run_rule(rule):
    rng = np.random.default_rng(SEED + rule)
    diagrams = [evolve_eca(rule, [int(b) for b in rng.integers(0,2,size=WIDTH)], STEPS)
                for _ in range(N_ICS)]
    net, reports = deconvolve_ca(diagrams, max_radius=RADIUS)
    truth = ca_global_map(rule, WIDTH)
    rec = repertoire(Network(n=WIDTH, C=net.C, gates=net.gates, params=net.params))
    mism = sum(1 for t,r in zip(truth,rec) for a,b in zip(t,r) if a!=b)
    fams = sorted(set(net.gates))
    return dict(rule=rule, mismatches=mism, exact=(mism==0), gates=fams)

out=[]
for r in range(256):
    try: out.append(run_rule(r))
    except Exception as e: out.append(dict(rule=r, mismatches=None, exact=False, gates=[], error=str(e)))
    if r % 32 == 0: print(f"  ...rule {r}", flush=True)

json.dump(out, open('/tmp/cb_expressivity_control.json','w'), indent=1)
ex=[o for o in out if o['exact']]
print()
print(f"ALL 256 ECA RULES, identical pipeline/knobs/seeds")
print(f"  exact global-map recovery : {len(ex)}/256")
print(f"  the 10 chosen rules       : {sum(1 for o in out if o['rule'] in RULES and o['exact'])}/10")
fam=collections.Counter(tuple(o['gates']) for o in ex)
print("  gate families used, over the exact set:")
for k,v in fam.most_common(): print(f"    {v:4d}  {list(k)}")
canon={"AND","OR","XOR","NAND","NOR","XNOR","NOT","IMPLIES","NIMPLIES","MAJORITY","KOFN","CANALISING"}
only_canon=[o for o in ex if set(o['gates'])<=canon]
print(f"  exact using ONLY the canonical twelve: {len(only_canon)}/256  -> rules {[o['rule'] for o in only_canon][:60]}")
for probe in (110,30,45,232):
    m=[o for o in out if o['rule']==probe][0]
    print(f"  probe rule {probe:3d}: exact={m['exact']} mismatches={m['mismatches']} gates={m['gates']}")
