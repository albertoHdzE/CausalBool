import sys, time, json
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
from hierarchy.corpus import split_cases, generate_unit
def run(bits):
    from hierarchy.infer import infer
    from hierarchy.baselines import encode_baseline, BASELINE_METHODS, select_best
    t=time.perf_counter(); r=infer(bits); th=time.perf_counter()-t
    t=time.perf_counter(); arcs={m:encode_baseline(bits,m) for m in BASELINE_METHODS}; tb=time.perf_counter()-t
    best=select_best(arcs)
    return r.archive_bits, 8*len(arcs[best]), best, th, tb, r.best_source, r.stop_reason, {m:8*len(a) for m,a in arcs.items()}
if __name__=="__main__":
    mode=sys.argv[1]
    if mode=="dev":
        cases,_=split_cases("development"); items=[(c.case_id,c.family,c.base_length,c.bits) for c in cases]
    else:
        items=[]
        for fam in ("F01","F02","F04","F05","F06","F07","F08","F09"):
            for bl in (16384,65536):
                bits,_=generate_unit("development_resource",fam,bl,0); items.append((f"{fam}-{bl}",fam,bl,bits))
    with ProcessPoolExecutor(8) as ex: res=list(ex.map(run,[i[3] for i in items]))
    agg=defaultdict(list)
    for it,r in zip(items,res):
        agg[(it[1],it[2])].append((r[1]-r[0])/len(it[3]))
        if mode!="dev": print(it[0], "hid",r[0],"best",r[1],r[2],"t_hid %.1f t_base %.1f"%(r[3],r[4]), r[6], r[5][:50])
    for k in sorted(agg): print(k, "mean saving/bit %.4f"%(sum(agg[k])/len(agg[k])), [round(v,3) for v in agg[k]])
    json.dump({it[0]:r for it,r in zip(items,res)},open(f"results/hierarchy_v1/development/calibration/devcmp_{mode}_{int(time.time())}.json","w"),indent=1)
