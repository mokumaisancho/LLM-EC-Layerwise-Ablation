// GEN001 PoC15 direct-rule vs pinned actually learned L* model, self-contained Node.js verifier.
// The learned table was obtained by rerunning the faithful PoC7 L* port with seed 20261105.
function parity(x){let p=0;while(x){p^=1;x&=x-1n}return p}

function toLatent(x){const mask=(1n<<128n)-1n;const z0=parity(x);const z1=parity(x&(mask^2n))^(z0&Number((x>>2n)&1n));return [z0|(z1<<1),x>>2n]}

function fromLatent(z,h){const z0=z&1,z1=(z>>1)&1,hp=parity(h),x0=z1^(z0&Number(h&1n))^hp,x1=z0^x0^hp;return (h<<2n)|(BigInt(x1)<<1n)|BigInt(x0)}

function directStep(z,a){if(a===0)return (z+1)&3;if(a===1)return ((z&1)^((z>>1)&1))|((z>>1)<<1);throw Error("OUTSIDE_ACTION_SCOPE")}

function rawStep(x,a){const [z,h]=toLatent(x);return fromLatent(directStep(z,a),h)}

function verify(){
  const L={initial:0,outputs:[0,0,1,1],transitions:[{0:3,1:0},{0:2,1:2},{0:0,1:1},{0:1,1:3}]};
  const Q=[[0n,0,0,[]]];const seen=new Set();const map=new Map();const rawSet=new Set();let edges=0;
  while(Q.length){
    const [x,q,id,w]=Q.shift();const key=[x.toString(),q,id].join("|");if(seen.has(key))continue;seen.add(key);map.set(q,id);rawSet.add(x.toString());
    const [actual,h]=toLatent(x);
    if(actual!==q||L.outputs[id]!==q%2||map.size!==new Set(map.values()).size)throw Error("BAD_STATE_MAPPING_"+w);
    for(const a of [0,1]){
      const xn=rawStep(x,a),qn=directStep(q,a),learnedId=L.transitions[id][a];
      if(toLatent(xn)[0]!==qn||L.outputs[learnedId]!==qn%2)throw Error("BAD_TRANSITION_"+w+","+a);
      edges++;Q.push([xn,qn,learnedId,[...w,a]])
    }
  }
  if(seen.size!==4||rawSet.size!==4||edges!==8)throw Error("REACHABILITY_MISMATCH");
  const hs=[0n,1n,2n,3n,(1n<<56n)+123n,(1n<<125n)-1n];let probes=0;
  for(let q=0;q<4;q++)for(const h of hs)for(const a of [0,1]){
    const x=fromLatent(q,h),nx=rawStep(x,a);
    if(toLatent(x)[0]!==q||toLatent(nx)[0]!==directStep(q,a))throw Error("HIDDEN_STATE_MISMATCH");
    probes++
  }
  const mutated=JSON.parse(JSON.stringify(L));mutated.transitions[0][0]=0;
  let faultDetected=mutated.outputs[mutated.transitions[0][0]]!==directStep(0,0)%2;
  if(!faultDetected)throw Error("MUTATION_NOT_DETECTED");
  return {result:"SCOPED_PASS",scope:{reset:0,actions:[0,1],output:"latent_q_bit0"},learned_hypothesis_from_reproduced_PoC7_LStar:L,reachable_raw_states:[...rawSet].map(Number).sort((a,b)=>a-b),reachable_source_count:4,learned_state_count:4,one_step_edges_checked:edges,hidden_coordinate_sample_checks:probes,abstract_to_learned_id:Object.fromEntries([...map]),negative_control_detected:faultDetected,learned_global_raw_projection:"NOT_ESTABLISHED",note:"Exact equivalence on the 4 reachable raw states under fixed reset and actions. Arbitrary raw inputs require an independent mapping not learned by L*. Source 128-bit width is not the 4-state reachable workload."};
}

const result=verify();
if(typeof process!=="undefined" && process.stdout)process.stdout.write(JSON.stringify(result,null,2)+"\n");
