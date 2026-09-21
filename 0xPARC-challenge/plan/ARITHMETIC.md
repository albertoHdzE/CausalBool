# R03/R04/R05 implementation contract v1
Use constraints.py as frozen representation. Allowed module gadgets.py.
Builders build_range(), build_exclude_one(), build_factor64(),
build_factor4096()->ConstraintSystem. Witness functions witness_range(x),
witness_exclude_one(r), witness_factor64(n,u,v), witness_factor4096(n,u,v)
->dict[str,int] EXACTLY all declared signals. External u,v,n for 4096 are
nonnegative integers below 2^4096 (not field scalars), converted to canonical
64-bit limbs; all field API arguments require canonical values. Reject bool.
Range Q5: private x, auxiliary x_b0..x_b63; 64 bit rows and packing row.
Inverse Q6: private r, auxiliary s; (r-1)s=1.
Factor64 Q7: public n, private u,v; range bits n_b0..63,u_b0..63,v_b0..63;
uv=n; factor>=2 via sum bits1..63 times u_inv/v_inv =1; equivalent exclusion
0/1 stronger than inverse(r-1) alone, retain (u-1)*u_one_inv=1 and same v to
match published equation. Require integer n=u*v and 2<=u,v, n<2^64 witnesses.
Factor4096 Q8: public n_0..n_63; private u_0..u_63,v_0..v_63;
auxiliary bits for every limb named e.g. u_0_b0; q_i_j; carry_0..carry_128;
carry_k_b0..b69 for k=1..127; u_inv,v_inv for nontrivial factors.
Label partial product rows partial_i_j; carry equations column_k;
endpoint labels endpoint_0,endpoint_128; range labels signal_bit_i,signal_pack;
factor lower bound labels nontrivial_u,nontrivial_v. Preserve deterministic
insertion order. Add 4096 partials, 128 columns, endpoint zero rows; constraints
MASTER.md. Witness carry recurrence uses actual u_i*v_j and n limbs, endpoints
must zero. Every row independently constrains even if witness routine unused.
Accept R03 first (test_range,inverse,factor64), then R04 (remaining tests).
R05 allowed circom.py: export_circom(system,path)->Path writes pragma 2.2.3,
all signals are input scalars (public_inputs explicit public list; others private),
all generic A*B===C equations, no witness-generation asserts and no `<--`.
compile_circuit(source,output_dir,*,circom=None)->dict paths r1cs,wasm,sym;
use --r1cs --wasm --sym --O0 --sanity_check 0, BN128 prime; timeout 600s,
check exact Circom2.2.3. Tools default challenge/.tools/circom and
.tools/node_modules/.bin/snarkjs. run_witness(compiled,witness,output_dir)
->dict paths input,wtns,json,r1cs_json, plus command records; invoke node
<name>_js/generate_witness.js <wasm> <input.json> <witness.wtns>, snarkjs
wtns check, wtns export json, r1cs export json. Check versions, failures raise;
never skip. Decimal-string input JSON. No compile at worker scope until lead
schedules heavy check; unit export can be tested on range only.
