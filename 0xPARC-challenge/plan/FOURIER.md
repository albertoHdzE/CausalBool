# F00 factorization and sparse support, v1
Number stages from zero, DIF stage s has m=N>>s, h=m/2. Within every
block t in [0,h): upper=x[t]+x[t+h], lower=(x[t]-x[t+h])*w_m^t.
For fused interval [a,b), m=N>>a, d=b-a, h=N>>b. Each output row r has
exactly 2^d input columns: block*m+(r%h)+h*t, t=0..2^d-1.
Coefficients are obtained by tracing that row backwards through DIF stages.
At stage s in reverse order: row idx in lower half contributes twiddle at
idx%(m/2) with + to upper parent, - to lower parent. Upper row contributes
+1 to both parents. Choices give unique columns, hence no path cancellation.
For nonfinal transform row=r. For final transform row=bitreverse(r,log2 N).
This explicitly fuses the final permutation and changes diagonal supports.
Diagonal offset is (input_column-output_row)%N. Find union of offsets for all
rows by bounded O(N*2^d) enumeration if needed; for schedule search use exact
support set algebra: nonfinal offsets = h*t mod N for t in
[-(2^d-1),2^d-1]. Final offsets arise from r and r'=bitreverse(r):
((r'//m)*m + (r'%h) + h*t-r) mod N; use sets and residues rather than NxN.
For final block b=log2 N, h=1: offsets union over intervals of length m,
starting at ((bitreverse(r)//m)*m-r)%N. Exact interval union on cyclic N domain
via difference-array; O(N) support search, no coefficient allocation.
For each support K and baby b dividing N, use I={k%b:k in K},
G={k//b:k in K}. Explicit circuit uses one R_i(input) for i!=0 in I;
for every k one multiply with descriptor (interval,final,k, giant_offset),
then |K|-|G| inner additions, |G|-1 outer additions, and one R_(gb) for
nonzero g. Thus multiplies=|K|, adds=|K|-1, rotations=|I\{0}|+|G\{0}|.
No arithmetic/rotation/permutation other than these nodes is implicit.
For known diagonal coefficient at rotated inner position j,
R_(-gb)(d_k)[j]=d_k[(j-gb)%N]. To calculate d_k at output row r,
let r'=bitreverse(r) for final block else r; col=(r+k)%N. If col is
outside r' block or col%h!=r'%h, coefficient=0. Otherwise trace backward
stages, choosing parent half by bit of col at stage's half width, updating
current row idx and multiplying twiddle and sign as above. O(N*d) per
coefficient vector, lazy with bounded vector cache. Interpreter evaluates
explicit operations and frees references after last use; no N-by-N matrix.
All 1/2/3 group partitions and every baby size are recorded. Selection key
(cost,multiplications,rotations,partition,baby-size tuple). Counts are then
recomputed independently from emitted nodes. Targets natural output DFT.
