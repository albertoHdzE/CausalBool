import random, cProfile, pstats, sys
from hierarchy.infer import infer
r=random.Random(7)
def tile(w,N): return (w*(N//len(w)+1))[:N]
x=tile("".join(r.choice("01") for _ in range(13)),1027) if sys.argv[1]=="p" else "".join(r.choice("01") for _ in range(int(sys.argv[1])))
cProfile.run("infer(x)","/tmp/prof.out")
pstats.Stats("/tmp/prof.out").sort_stats("cumulative").print_stats(18)
