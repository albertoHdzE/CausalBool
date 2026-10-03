import sys,time,resource
from hierarchy.corpus import generate_unit
from hierarchy.infer import infer, ABLATIONS
bits,_=generate_unit("development_resource",sys.argv[1],65536,0)
t=time.perf_counter(); r=infer(bits, ABLATIONS[sys.argv[2]]); 
print(sys.argv[1:], r.archive_bits, r.stop_reason, round(time.perf_counter()-t,2), "maxrss MB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20)
