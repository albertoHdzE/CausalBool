import random, time, sys
from hierarchy.infer import infer, ABLATIONS
r=random.Random(7)
def tile(w,N): return (w*(N//len(w)+1))[:N]
tests={
 "ones64":"1"*64,
 "A64":"".join("1"*i+"0"+"1"*(7-i) for i in range(8)),
 "A72":("1"*8+"0")*8,
 "p13_1027":tile("".join(r.choice("01") for _ in range(13)),1027),
 "iid_1027":"".join(r.choice("01") for _ in range(1027)),
 "iid_4099":"".join(r.choice("01") for _ in range(4099)),
}
for k,x in tests.items():
  for cfgname in ("full","flat","fixed8"):
    t=time.perf_counter(); res=infer(x,ABLATIONS[cfgname]); dt=time.perf_counter()-t
    print(f"{k:10} {cfgname:7} n={len(x):5} bits={res.archive_bits:6} lit={res.literal_bits:6} mode={res.mode:7} stop={res.stop_reason:16} cand={res.candidate_counts['serialized_unique']:4} work={res.work['work_units']:>9} t={dt:.2f} src={res.best_source[:60]}")
