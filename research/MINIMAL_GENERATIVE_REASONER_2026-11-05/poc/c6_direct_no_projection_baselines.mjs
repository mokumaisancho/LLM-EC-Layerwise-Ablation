// GEN001 C6: Direct optimized *raw* transition baselines (no phi or latent quotient).
// Original symbolic source is poc4_repro.py Git blob 706da2229bbe7a244e899729221170149bc6d014
// This is equality/baseline admission only; no runtime speedup or total cost claim.
function parity(row){let p=0;while(row){row&=row-1n;p^=1}return p}

function mulRow(row,matrix){let v=0n;while(row){const low=row&(-row);let i=0;let b=low;while(b>1n){b>>=1n;i++}v^=matrix[i];row^=low}return v}

function mul(a,b){return a.map(row=>mulRow(row,b))}

function evalRows(rows,x){let y=0n;rows.forEach((row,i)=>{if(parity(row&x))y|=1n<<BigInt(i)});return y}

function fixture(n){
 const all=(1n<<BigInt(n))-1n,A=[all,all^2n],B=[2n^(all^3n),3n];
 for(let i=2;i<n;i++){A.push(1n<<BigInt(i));B.push(1n<<BigInt(i))}
 const ident=A.map((_,i)=>1n<<BigInt(i));if(mul(A,B).some((x,i)=>x!==ident[i]))throw Error("basis inverse invalid");
 const m={};
 for(const a of [0,1]){
  let nmat=a===0?[2n,1n]:[3n,1n];
  for(let i=2;i<n;i++)nmat.push(1n<<BigInt(i));
  m[a]=mul(mul(B,nmat),A);
 }
 return {m,output:A[0]};
}

function makeColumns(m,n){return Array.from({length:n},(_,j)=>evalRows(m,1n<<BigInt(j)))}

function colStep(cols,x){let y=0n,j=0;while(x){if(x&1n)y^=cols[j];j++;x>>=1n}return y}

function makeByteLut(cols,n){const blocks=[];for(let g=0;g<n/8;g++){const v=new Array(256);v[0]=0n;for(let i=1;i<256;i++){let b=0;while(((i>>b)&1)===0)b++;v[i]=v[i^(1<<b)]^cols[g*8+b]}blocks.push(v)}return blocks}

function lutStep(blocks,x){let y=0n;for(let g=0;g<blocks.length;g++){y^=blocks[g][Number(x&255n)];x>>=8n}return y}

function check(){
 const n=128,{m,output}=fixture(n),C={},L={};
 for(const a of [0,1]){C[a]=makeColumns(m[a],n);L[a]=makeByteLut(C[a],n)}
 let basis=0,random=0;let x=0x9e3779b97f4a7c15n;
 for(const a of [0,1]){
  for(let i=-1;i<n;i++){const z=i<0?0n:1n<<BigInt(i),e=evalRows(m[a],z);if(colStep(C[a],z)!==e||lutStep(L[a],z)!==e)throw Error("basis fails");basis++}
  for(let t=0;t<512;t++){x^=(x<<13n)&((1n<<128n)-1n);x^=x>>7n;x^=(x<<17n)&((1n<<128n)-1n);x&=(1n<<128n)-1n;const e=evalRows(m[a],x);if(colStep(C[a],x)!==e||lutStep(L[a],x)!==e)throw Error("random fails");random++}
 }
 return {protocol:"GEN001_C6_DIRECT_NO_PROJECTION_BASELINE_CHECK_V1",status:"SCOPED_EQUALITY_PASS",date:"2026-11-07",original_source:"poc/poc4_repro.py@706da2229bbe7a244e899729221170149bc6d014",scope:{n,actions:[0,1],output:"one-bit observed GF(2) parity row",initial_raw_state:"arbitrary 128bit x",update:"same raw M_a*x, no phi or latent quotient"},source:"128 row parity operations/transition",alternatives:[{name:"bitset-column XOR",columns_per_action:128,worst_xor_terms:128,reference_storage_bytes:4096,notes:"Storage assumes fixed 128-bit dense masks, excludes programming-language overhead"},{name:"16-byte block LUT",blocks_per_action:16,table_entries_per_action:4096,reference_storage_bytes:131072,notes:"Per action 16 byte lookups/xors; includes precomputation, fixed mask bytes only"}],checks:{basis_zero_and_unit_states: basis,randomized_states:random,algebraic_proof:"Both mappings are linear combinations of exact row-matrix basis columns, so all GF(2)^128 inputs follow from basis equality"},timing:"NOT_RUN",cost_of_build:"NOT_MEASURED",total_cost:"NOT_MEASURED",next_atomic_decision:"Choose optimal direct no-phi baseline including preprocessing and memory before time benchmarking phi+delta"};
}

if (typeof process !== "undefined" && process.stdout) process.stdout.write(JSON.stringify(check(),null,2)+"\n");
