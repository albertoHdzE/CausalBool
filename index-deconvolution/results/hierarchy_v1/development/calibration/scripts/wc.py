import sys,time,resource
from hierarchy.corpus import generate_unit
from hierarchy.infer import SearchConfig, infer
for fam in ("F06","F02","F05","F07"):
  bits,_=generate_unit("development_resource",fam,65536,0)
  for wc in (60_000_000,120_000_000,240_000_000):
    t=time.perf_counter(); r=infer(bits, SearchConfig(work_cap=wc))
    print(fam, wc, r.archive_bits, r.stop_reason, r.candidate_counts["serialized_unique"], round(time.perf_counter()-t,2), flush=True)
