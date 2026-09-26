import json, sys, time
from research import efficiency_profile as ep
from tests_direct import generate_programs as gp
out = []
for s in range(800000, 800030):
    t = time.perf_counter(); r = ep.mode_time(gp.additional_program(s)); out.append((s, round(time.perf_counter()-t, 3), r["nodes"]))
print(json.dumps(out))
