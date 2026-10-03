import sys, time, json, dataclasses
from concurrent.futures import ProcessPoolExecutor
from hierarchy.corpus import split_cases
from hierarchy.infer import SearchConfig
def run(args):
    bits, cfg = args
    from hierarchy.infer import infer
    t=time.perf_counter(); r=infer(bits,cfg); return r.archive_bits, time.perf_counter()-t, r.stop_reason, r.candidate_counts["serialized_unique"]
if __name__=="__main__":
    cases,_=split_cases("development")
    variants={k:json.loads(v) for k,v in (a.split("=",1) for a in sys.argv[1:])}
    out={}
    for name,kw in variants.items():
        cfg=SearchConfig(**kw)
        with ProcessPoolExecutor(8) as ex: res=list(ex.map(run,[(c.bits,cfg) for c in cases]))
        out[name]={"kw":kw,"total_bits":sum(r[0] for r in res),"total_s":round(sum(r[1] for r in res),2),"max_s":round(max(r[1] for r in res),2),
                   "stops":{s:sum(1 for r in res if r[2]==s) for s in {r[2] for r in res}},"by_case":{c.case_id:[r[0],round(r[1],3)] for c,r in zip(cases,res)}}
        print(name, {k:v for k,v in out[name].items() if k!="by_case"}, flush=True)
    json.dump(out,open(f"results/hierarchy_v1/development/calibration/calib_{int(time.time())}.json","w"),indent=1)
