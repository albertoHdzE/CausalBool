"""Numerically checked operation networks for manuscript Figures 1, 4 and 5."""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from paper_network_figures import ROOT, ASSETS, TEAL, ORANGE, BLUE, GREY, PALE, INK, save
from oxparc_challenge.fourier import build_fourier, evaluate_packed


def node(ax, xy, label, *, colour=TEAL, size=850, light=False, font=11):
    ax.scatter(*xy, s=size, color=PALE if light else colour, edgecolor='white', linewidth=1.5, zorder=4)
    ax.text(*xy, label, ha='center', va='center', color=INK if light else 'white', fontsize=font,zorder=5)


def edge(ax, a, b, label=None, *, colour=GREY, radius=0, shift=(0, .15), shrink=19):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=10,
        connectionstyle=f'arc3,rad={radius}',shrinkA=shrink,shrinkB=shrink,
        color=colour,lw=1.2,zorder=2))
    if label:
        ax.text((a[0]+b[0])/2+shift[0],(a[1]+b[1])/2+shift[1],label,
                ha='center',va='center',fontsize=9,color=INK,
                bbox=dict(facecolor='white',edgecolor='none',pad=1),zorder=3)


def packing():
    values=[3,8,19];base=sum(values)+1
    contributions=[v*base**i for i,v in enumerate(values)];packed=sum(contributions)
    quotients=[packed];digits=[]
    while quotients[-1]:
        q,r=divmod(quotients[-1],base);quotients.append(q);digits.append(r)
    if digits!=values or packed!=18510:raise RuntimeError('Packing example failed')
    fig=plt.figure(figsize=(10.7,6.6))
    grid=fig.add_gridspec(2,2,height_ratios=[1.25,1],width_ratios=[.9,1.3],hspace=.5,wspace=.28)
    ax=fig.add_subplot(grid[0,0]);ax.axis('off')
    ax.set_title('A. First query: give every entry weight 1',loc='left',fontsize=11,pad=15)
    for i,v in enumerate(values):
        pos=(0,2-i)
        node(ax,pos,str(v),light=True,size=800)
        edge(ax,pos,(2.1,1),r'$\times 1$',shift=(0,.16 if i<2 else -.16))
    node(ax,(2.1,1),'30',size=1100)
    ax.text(2.1,1.62,'sum S',ha='center',fontsize=10)
    ax.text(1.1,-1.1,'Choose B = S + 1 = 31.\nEvery hidden entry is smaller than B.',ha='center',fontsize=10)
    ax.set(xlim=(-.6,3),ylim=(-1.6,2.5))
    ax=fig.add_subplot(grid[0,1]);ax.axis('off')
    ax.set_title('B. Second query: assign distinct digit weights',loc='left',fontsize=11,pad=15)
    for i,(v,c) in enumerate(zip(values,contributions)):
        y=2-i
        node(ax,(0,y),str(v),light=True,size=800)
        node(ax,(2,y),f'{c:,}',size=1850 if c>1000 else 1100,font=10)
        edge(ax,(0,y),(2,y),f'× {base**i:,}')
        edge(ax,(2,y),(4,1))
    node(ax,(4,1),f'{packed:,}',size=2000,font=10)
    ax.text(4,1.65,'sum R',ha='center',fontsize=10)
    ax.text(2,-1.1,'3 + 248 + 18,259 = 18,510\nEach entry has its own base-31 position.',ha='center',fontsize=10)
    ax.set(xlim=(-.5,4.7),ylim=(-1.6,2.5))
    ax=fig.add_subplot(grid[1,:]);ax.axis('off')
    ax.set_title('C. Divide by 31: pass the quotient onward and keep the remainder',loc='left',fontsize=11,pad=16)
    positions=[(i*2.5,1) for i in range(4)]
    for i,(pos,q) in enumerate(zip(positions,quotients)):
        node(ax,pos,f'{q:,}',size=2000 if i==0 else 900,font=10 if i==0 else 11)
        if i<3:
            edge(ax,pos,positions[i+1],'quotient',shift=(0,.25))
            node(ax,(pos[0],-.3),str(digits[i]),colour=ORANGE,size=900)
            edge(ax,pos,(pos[0],-.3),'remainder',colour=ORANGE,shift=(.58,0))
            ax.text(pos[0],-.92,f'recovered entry {i}',ha='center',fontsize=9)
    ax.text(7.5,.1,'stop',ha='center',fontsize=10)
    ax.set(xlim=(-.65,8.1),ylim=(-1.1,1.65))
    save(fig,'query_network')
    return dict(values=values,base=base,contributions=contributions,answer=packed,quotients=quotients,recovered=digits)


def fourier():
    n=8;stages=[]
    for m in (8,4,2):
        mat=np.zeros((n,n),dtype=complex)
        for start in range(0,n,m):
            for t in range(m//2):
                a=start+t;b=a+m//2;w=np.exp(-2j*np.pi*t/m)
                mat[a,a]=mat[a,b]=1;mat[b,a]=w;mat[b,b]=-w
        stages.append(mat)
    permutation=[int(f'{i:03b}'[::-1],2) for i in range(n)]
    actual=(stages[2]@stages[1]@stages[0])[permutation]
    direct=np.exp(-2j*np.pi*np.outer(np.arange(n),np.arange(n))/n)
    circuit=build_fourier(8,partition=(1,1,1),babies=(2,2,2))
    errors=[float(np.max(abs(evaluate_packed(circuit,np.eye(n)[:,i])-direct[:,i]))) for i in range(n)]
    error=float(np.max(abs(actual-direct)))
    if max(error,*errors)>1e-12:raise RuntimeError('Displayed Fourier network failed')
    fig=plt.figure(figsize=(9.5,8.1))
    grid=fig.add_gridspec(3,2,height_ratios=[3.3,1.45,1.5],width_ratios=[1.8,1],hspace=.7,wspace=.28)
    ax=fig.add_subplot(grid[0,0]);ax.axis('off')
    ax.set_title('A. An eight-slot Fourier network',loc='left',fontsize=11,pad=18)
    for stage,mat in enumerate(stages):
        for row,col in zip(*np.nonzero(mat)):
            edge(ax,(stage,7-col),(stage+1,7-row),colour=BLUE if stage==0 and row in (0,4) else '#aab5bf',shrink=4)
    for row,k in enumerate(permutation):
        edge(ax,(3,7-row),(4,7-k),colour=GREY,shrink=4)
    for stage in range(5):
        for row in range(n):
            ax.scatter(stage,7-row,s=34,color=TEAL if stage<4 else ORANGE,zorder=4)
    for row in range(n):
        ax.text(-.18,7-row,f'$x_{row}$',ha='right',va='center',fontsize=9)
        ax.text(4.18,7-row,f'$F_{row}$',ha='left',va='center',fontsize=9)
    for stage in range(3):
        ax.text(stage+.5,-.65,f'stage {stage+1}',ha='center',fontsize=9)
    ax.text(3.5,-.65,'reorder',ha='center',fontsize=9)
    ax.set(xlim=(-.5,4.55),ylim=(-1,7.35))
    ax=fig.add_subplot(grid[0,1]);ax.axis('off')
    ax.set_title('B. Read one butterfly',loc='left',fontsize=11,pad=18)
    for pos,label in [((0,2),'a'),((0,0),'b'),((2.4,2),'u'),((2.4,0),'v')]:
        node(ax,pos,label,light=pos[0]==0,size=650)
    edge(ax,(0,2),(2.4,2),'+1',colour=BLUE)
    edge(ax,(0,0),(2.4,2),'+1',colour=BLUE,shift=(-.15,.25))
    edge(ax,(0,2),(2.4,0),'ω',colour=ORANGE,shift=(.32,-.15))
    edge(ax,(0,0),(2.4,0),'−ω',colour=ORANGE,shift=(0,-.25))
    ax.text(1.2,-1.25,'u = a + b\nv = ω(a − b)',ha='center',fontsize=11)
    ax.text(1.2,-2.15,r'$\omega=\exp(-2\pi\mathrm{i}t/m)$',ha='center',fontsize=10)
    ax.set(xlim=(-.4,2.9),ylim=(-2.5,2.4))
    ax=fig.add_subplot(grid[1,:]);ax.axis('off')
    ax.set_title('C. At the target sizes, fuse adjacent stages into three linear maps',loc='left',fontsize=11,pad=20)
    ledgers=[]
    for row,n in enumerate((32768,65536)):
        data=json.loads((ROOT/f'evidence/fourier_{n}_ledger.json').read_text());ledgers.append(data)
        widths=data['selected']['partition'];left=0;y=1-row
        ax.text(-.7,y,f'{n:,} slots',ha='right',va='center',fontsize=10)
        for g,width in enumerate(widths):
            xs=np.arange(left,left+width);colour=[TEAL,BLUE,ORANGE][g]
            ax.plot(xs,np.full(width,y),'-o',color=colour,lw=2,markersize=7)
            if left:ax.plot([left-1,left],[y,y],color=GREY,lw=1)
            ax.text(float(xs.mean()),y+.32,f'{width} stage'+('s' if width>1 else ''),ha='center',fontsize=9,color=colour)
            left+=width
    ax.set(xlim=(-3,16),ylim=(-.3,1.6))
    ax=fig.add_subplot(grid[2,:])
    ax.set_title('D. Estimated serial work under the same operation costs',loc='left',fontsize=11,pad=12)
    for row,data in enumerate(ledgers):
        dense=data['dense_baseline']['cost_us']/1e6;selected=data['selected']['cost_us']/1e6
        y=1-row
        ax.barh(y+.16,dense,height=.27,color='#bccdd1')
        ax.barh(y-.16,selected,height=.27,color=TEAL)
        ax.text(dense+3,y+.16,f'{dense:.3f}  dense',va='center',fontsize=9)
        ax.text(selected+3,y-.16,f'{selected:.3f}  selected',va='center',fontsize=9)
    ax.set_yticks([1,0],['32,768 slots','65,536 slots'])
    ax.set(xlim=(0,445),ylim=(-.5,1.5),xlabel='Sum of charged operation costs (seconds)')
    ax.spines[['left','right','top']].set_visible(False);ax.tick_params(axis='y',length=0)
    save(fig,'fourier_network')
    return dict(illustrative_slots=8,bit_reversal=permutation,
                direct_matrix_max_error=error,packed_basis_max_errors=errors,
                target_partitions=[d['selected']['partition'] for d in ledgers])


def carries():
    u,v,base=23,47,10
    products=[[3*7],[2*7,3*4],[2*4],[]]
    carry=0;rows=[]
    for k,terms in enumerate(products):
        total=sum(terms)+carry;next_carry,digit=divmod(total,base)
        rows.append(dict(column=k,products=terms,carry_in=carry,total=total,digit=digit,carry_out=next_carry))
        carry=next_carry
    if carry or sum(r['digit']*base**r['column'] for r in rows)!=u*v:
        raise RuntimeError('Carry-network example failed')
    fig,ax=plt.subplots(figsize=(11,5.4));ax.axis('off')
    ax.set_title('Follow the partial products and carries: 23 × 47 = 1081 (base 10)',loc='left',fontsize=12,pad=15)
    xs=[0,3,6,9]
    labels=[[(0,'3 × 7\n21')],[(-.75,'2 × 7\n14'),(.75,'3 × 4\n12')],[(0,'2 × 4\n8')],[]]
    for k,row in enumerate(rows):
        x=xs[k]
        ax.text(x,3.9,f'column {k}',ha='center',fontsize=11)
        for dx,label in labels[k]:
            node(ax,(x+dx,2.8),label,light=True,size=1550,font=11)
            edge(ax,(x+dx,2.8),(x,1.05))
        if not labels[k]:ax.text(x,2.8,'no partial\nproducts',ha='center',va='center',fontsize=10,color=GREY)
        node(ax,(x,1.05),str(row['total']),size=1500,font=13)
        node(ax,(x,-.7),str(row['digit']),colour=ORANGE,size=1000,font=13)
        edge(ax,(x,1.05),(x,-.7),'remainder',colour=ORANGE,shift=(.6,0))
        ax.text(x,-1.35,f'× {base**k:,}',ha='center',fontsize=10)
        if k<3:edge(ax,(x,1.05),(xs[k+1],1.05),f'carry {row["carry_out"]}',shift=(0,.25))
    ax.text(-1.1,1.05,'0',va='center',ha='center',fontsize=11)
    edge(ax,(-1.1,1.05),(0,1.05),shrink=12)
    ax.text(-1.1,.5,'initial\ncarry',ha='center',fontsize=9)
    edge(ax,(9,1.05),(10.2,1.05),shrink=14)
    ax.text(10.45,1.05,'0',ha='center',va='center',fontsize=11)
    ax.text(10.4,.5,'final\ncarry',ha='center',fontsize=9)
    ax.text(4.5,-2.05,'Recovered product: 1 × 1 + 8 × 10 + 0 × 100 + 1 × 1000 = 1081',ha='center',fontsize=11)
    ax.text(4.5,-2.65,r'For the 4096-bit construction: $B=2^{64}$, carries $<2^{70}$, column sides $<2^{135}<P$.',ha='center',fontsize=10)
    ax.set(xlim=(-1.5,10.9),ylim=(-2.9,4.3))
    save(fig,'carry_network')
    return dict(u=u,v=v,base=base,product=u*v,columns=rows)


def generate():
    data=dict(status='PASS',packing=packing(),fourier=fourier(),carries=carries())
    (ASSETS/'operation_examples.json').write_text(json.dumps(data,indent=2)+'\n')
    print('Operation networks: exact packing/carries and eight Fourier basis vectors checked; PASS')


if __name__=='__main__':generate()
