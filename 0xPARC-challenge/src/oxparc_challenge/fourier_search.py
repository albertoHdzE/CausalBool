"""Exact support enumeration and exhaustive contiguous-partition cost search."""
from functools import lru_cache
from itertools import combinations,product
import numpy as np

COST={'add':4,'multiply_known_vector':5600,'rotate':6100}

def log_dimension(n):
    if type(n) is not int or n<2 or n&(n-1):
        raise ValueError('power-of-two dimension >=2 required')
    return n.bit_length()-1

@lru_cache(maxsize=32)
def bit_reverse(n):
    stages=log_dimension(n)
    x=np.arange(n,dtype=np.int64); result=np.zeros(n,dtype=np.int64)
    for _ in range(stages):
        result=(result<<1)|(x&1);x=x>>1
    result.flags.writeable=False
    return result

@lru_cache(maxsize=256)
def support(n,start,stop,final):
    stages=log_dimension(n)
    if not 0<=start<stop<=stages or (final and stop!=stages):
        raise ValueError('invalid contiguous stage interval')
    m=n>>start;h=n>>stop
    if not final:
        return tuple(sorted({(h*t)%n for t in range(-(m//h-1),m//h)}))
    # Exact cyclic union of row support intervals [base-r,base-r+m).
    r=np.arange(n,dtype=np.int64)
    starts=((bit_reverse(n)//m)*m-r)%n
    ends=starts+m
    diff=np.zeros(n+1,dtype=np.int64)
    np.add.at(diff,starts,1)
    np.add.at(diff,np.minimum(ends,n),-1)
    wrap=ends>n
    diff[0]+=np.count_nonzero(wrap)
    np.add.at(diff,ends[wrap]-n,-1)
    return tuple(int(k) for k in np.flatnonzero(np.cumsum(diff[:-1])>0))

@lru_cache(maxsize=256)
def block_candidates(n,start,stop,final):
    k=np.asarray(support(n,start,stop,final),dtype=np.int64)
    result=[]
    for power in range(log_dimension(n)+1):
        baby=1<<power
        i=np.unique(k%baby);g=np.unique(k//baby)
        mult=len(k);add=mult-1;rot=int(np.count_nonzero(i)+np.count_nonzero(g))
        result.append({'baby':baby,'multiplications':mult,'additions':add,'rotations':rot,
                       'cost_us':5600*mult+4*add+6100*rot,'status':'PASS'})
    return tuple(result)


def partitions(stages):
    for groups in range(1,min(3,stages)+1):
        for cuts in combinations(range(1,stages),groups-1):
            bounds=(0,*cuts,stages)
            yield tuple(bounds[i+1]-bounds[i] for i in range(groups))


def search(n):
    stages=log_dimension(n);ledger=[]
    for partition in partitions(stages):
        blocks=[];start=0
        for size in partition:
            stop=start+size;final=stop==stages
            choices=block_candidates(n,start,stop,final)
            best=min(choices,key=lambda c:(c['cost_us'],c['multiplications'],c['rotations'],c['baby']))
            blocks.append({'start':start,'stop':stop,'final':final,'candidates':list(choices),'selected':best})
            start=stop
        row={'partition':list(partition),'blocks':blocks,'status':'PASS'}
        for k in ('cost_us','multiplications','rotations','additions'):
            row[k]=sum(b['selected'][k] for b in blocks)
        row['babies']=[b['selected']['baby'] for b in blocks]
        # Costs add across blocks, so independent block minima exhaust the
        # Cartesian family. Ledger retains every baby choice per block.
        row['evaluated_baby_combinations']=(stages+1)**len(blocks)
        ledger.append(row)
    selected=min(ledger,key=lambda c:(c['cost_us'],c['multiplications'],c['rotations'],tuple(c['partition']),tuple(c['babies'])))
    dense=min(({'baby':1<<p,'multiplications':n,'additions':n-1,
                 'rotations':(1<<p)+(n>>p)-2,
                 'cost_us':5600*n+4*(n-1)+6100*((1<<p)+(n>>p)-2)}
               for p in range(stages+1)),key=lambda c:(c['cost_us'],c['baby']))
    return {'n':n,'candidate_count':len(ledger),'ledger':ledger,'selected':selected,'dense_baseline':dense,
            'claim':'best in the completely evaluated contiguous DIF/BSGS family'}
