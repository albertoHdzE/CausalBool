"""Explicit packed-vector DAG and lazy fused DIF diagonal coefficients."""
from dataclasses import dataclass,asdict
import hashlib
import json
import numpy as np
from .fourier_search import bit_reverse,log_dimension,support,search,COST

@dataclass(frozen=True)
class Operation:
    op: str
    operands: tuple[int,...]
    offset: int = 0
    coefficient: tuple[int,int,bool,int,int] | None = None

@dataclass(frozen=True)
class PackedCircuit:
    n: int
    operations: tuple[Operation,...]
    output: int
    partition: tuple[int,...]
    babies: tuple[int,...]
    def to_dict(self):
        return {'version':'oxparc-packed-v1','n':self.n,'operations':[asdict(o) for o in self.operations],
                'output':self.output,'partition':self.partition,'babies':self.babies}
    def structural_hash(self):
        return hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def build_fourier(n,partition=None,babies=None):
    stages=log_dimension(n)
    if partition is None:
        selected=search(n)['selected'];partition=selected['partition'];babies=selected['babies']
    partition=tuple(partition);babies=tuple(babies)
    if sum(partition)!=stages or not 1<=len(partition)<=3 or len(babies)!=len(partition) or any(type(v) is not int or v<=0 for v in partition):raise ValueError('invalid partition')
    ops=[]
    def emit(op,refs,offset=0,coefficient=None):
        ops.append(Operation(op,tuple(refs),offset,coefficient));return len(ops)
    x=0;start=0
    for width,baby in zip(partition,babies):
        if type(baby) is not int or baby<1 or n%baby or baby&(baby-1):raise ValueError('invalid baby size')
        stop=start+width;final=stop==stages;kset=support(n,start,stop,final)
        rotated={i:(x if i==0 else emit('rotate',(x,),i)) for i in sorted({k%baby for k in kset})}
        groups={}
        for k in kset:groups.setdefault(k//baby,[]).append(k)
        total=None
        for g,ks in sorted(groups.items()):
            inner=None
            for k in ks:
                term=emit('multiply_known_vector',(rotated[k%baby],),coefficient=(start,stop,final,k,g*baby))
                inner=term if inner is None else emit('add',(inner,term))
            if g:inner=emit('rotate',(inner,),g*baby)
            total=inner if total is None else emit('add',(total,inner))
        x=total;start=stop
    return PackedCircuit(n,tuple(ops),x,partition,babies)

def circuit_counts(circuit):
    """Count actual DAG nodes and maximum multiplication-path depth."""
    log_dimension(circuit.n);depth=[0];counts={k:0 for k in COST}
    for ref,o in enumerate(circuit.operations,1):
        if o.op not in COST or len(o.operands)!=(2 if o.op=='add' else 1):raise ValueError('invalid operation')
        if any(type(r) is not int or r<0 or r>=ref for r in o.operands):raise ValueError('invalid DAG reference')
        counts[o.op]+=1;depth.append(max(depth[r] for r in o.operands)+(o.op=='multiply_known_vector'))
    if type(circuit.output) is not int or not 0<=circuit.output<len(depth):raise ValueError('invalid output')
    return {'multiplications':counts['multiply_known_vector'],'additions':counts['add'],'rotations':counts['rotate'],
            'depth':depth[circuit.output],'cost_us':sum(COST[k]*v for k,v in counts.items())}

def coefficient_vector(n,descriptor):
    start,stop,final,k,giant=descriptor
    if not 0<=start<stop<=log_dimension(n):raise ValueError('invalid coefficient interval')
    r=(np.arange(n,dtype=np.int64)-giant)%n
    current=bit_reverse(n)[r].copy() if final else r.copy()
    col=(r+k)%n;m=n>>start;h=n>>stop
    mask=(col//m==current//m)&(col%h==current%h)
    result=np.zeros(n,dtype=np.complex128);positions=np.flatnonzero(mask)
    if not len(positions):return result
    row=current[positions];target=col[positions];coef=np.ones(len(positions),dtype=np.complex128)
    for stage in range(stop-1,start-1,-1):
        size=n>>stage;half=size//2
        lower=(row&half)!=0;parent_lower=(target&half)!=0
        coef*=np.where(lower,np.exp((-2j*np.pi/size)*(row%half))*np.where(parent_lower,-1,1),1)
        row=(row & ~half) | (target & half)
    result[positions]=coef
    return result

def evaluate_packed(circuit,vector,*,rotation_sign=1,omit_bit_reversal=False,wrong_twiddle=False):
    """Execute emitted primitives and free every array at its last use."""
    circuit_counts(circuit);x=np.asarray(vector,dtype=np.complex128)
    if x.shape!=(circuit.n,):raise ValueError('input dimension mismatch')
    uses=[0]*(len(circuit.operations)+1)
    for o in circuit.operations:
        for r in o.operands:uses[r]+=1
    uses[circuit.output]+=1;values={0:x}
    for ref,o in enumerate(circuit.operations,1):
        if o.op=='rotate':y=np.roll(values[o.operands[0]],-rotation_sign*o.offset)
        elif o.op=='add':y=values[o.operands[0]]+values[o.operands[1]]
        else:
            descriptor=o.coefficient
            if omit_bit_reversal and descriptor[2]:descriptor=(*descriptor[:2],False,*descriptor[3:])
            coeff=coefficient_vector(circuit.n,descriptor)
            if wrong_twiddle:coeff=coeff.conjugate()
            y=values[o.operands[0]]*coeff
        values[ref]=y
        for r in o.operands:
            uses[r]-=1
            if uses[r]==0:del values[r]
    return values[circuit.output]
