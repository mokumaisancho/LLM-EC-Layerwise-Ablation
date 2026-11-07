// GEN001 PoC16: two externally designated resets, unchanged actions 0/1.
// Pin to PoC7 original source blob 722e600873a547ed122b2d0c37114be5d162133c.
// No L* learning performed here. Product-state checker uses PoC15 pinned 4-state model.
function check(ok,msg){if(!ok)throw Error(msg)}

function parity(v){let p=0;while(v){p^=1;v&=v-1n}return p}

function toLatent(x){const mask=(1n<<128n)-1n;const z0=parity(x),z1=parity(x&(mask^2n))^(z0&Number((x>>2n)&1n));return [z0|(z1<<1),x>>2n]}

function fromLatent(z,h){let z0=z&1,z1=(z>>1)&1,hp=parity(h);let x0=z1^(z0&Number(h&1n))^hp,x1=z0^x0^hp;const x=(h<<2n)|(BigInt(x1)<<1n)|BigInt(x0);check(toLatent(x)[0]===z&&toLatent(x)[1]===h,"inverse");return x}

function step(x,a){let [z,h]=toLatent(x);if(a===0)z=(z+1)&3;else if(a===1)z=((z&1)^((z>>1)&1))|((z>>1)<<1);else if(a===2){z^=Number(h&1n);h=(h>>1n)|(BigInt(z&1)<<125n)}else throw Error("bad action");return fromLatent(z,h)}

function output(x){return toLatent(x)[0]&1}

function reachable(start,acts){let q=Object.values(start),seen=new Set(q.map(x=>x.toString()));for(let i=0;i<q.length;i++)for(const a of acts){let y=step(q[i],a),key=y.toString();if(!seen.has(key)){seen.add(key);q.push(y)}}return q.sort((a,b)=>a<b?-1:a>b?1:0)}

function minimal(states,acts){
 let label=new Map(states.map(x=>[x.toString(),output(x)])),counts=[new Set(label.values()).size];
 for(let it=0;it<20;it++){
  const sigs=states.map(x=>JSON.stringify([label.get(x.toString()),...acts.map(a=>label.get(step(x,a).toString()))]));
  const ids=new Map([...new Set(sigs)].sort().map((v,i)=>[v,i]));
  const next=new Map(states.map((x,i)=>[x.toString(),ids.get(sigs[i])]));
  counts.push(new Set(next.values()).size);
  let same=states.every(x=>states.every(y=>(label.get(x.toString())===label.get(y.toString()))===(next.get(x.toString())===next.get(y.toString()))));
  if(same)return {labels:next,counts};label=next
 }
 throw Error("refinement nontermination");
}

function productCheck(roots,model,acts){
 let pending=Object.entries(roots).map(([name,x])=>[name,x,model.initial,[]]);
 let seen=new Set(pending.map(p=>p[0]+"|"+p[1].toString()+"|"+p[2]));let visited=0;
 for(let i=0;i<pending.length;i++){
  const [name,x,id,w]=pending[i];visited++;
  if(output(x)!==model.outputs[id])return {status:"FAIL",reset:name,witness:w,visited};
  for(const a of acts){const y=step(x,a),lid=model.transitions[id][a],key=name+"|"+y.toString()+"|"+lid;
   if(!seen.has(key)){seen.add(key);pending.push([name,y,lid,[...w,a]])}}
 }
 return {status:"PASS_EXACT_REACHABLE_TWO_RESETS",pairs:visited,transitions:visited*acts.length};
}

function run(){
 const h=(1n<<125n)|1n,roots={original_q0_h0:0n,additional_q0_high_hidden:fromLatent(0,h)},actions=[0,1];
 check(roots.additional_q0_high_hidden===((1n<<127n)|4n),"second reset");
 const ra=reachable({a:roots.original_q0_h0},actions),rb=reachable({b:roots.additional_q0_high_hidden},actions),all=reachable(roots,actions);
 check(ra.length===4&&rb.length===4&&all.length===8&&ra.every(x=>!rb.some(y=>x===y)),"8 distinct raw");
 const partition=minimal(all,actions),groups={};
 for(const x of all){const id=partition.labels.get(x.toString());(groups[id]??=[]).push(x)}
 check(Object.keys(groups).length===4&&Object.values(groups).every(g=>g.length===2),"four classes of two");
 check(Object.values(groups).every(g=>toLatent(g[0])[0]===toLatent(g[1])[0]&&toLatent(g[0])[1]!==toLatent(g[1])[1]),"group meaning");
 const model={initial:0,outputs:{0:0,1:0,2:1,3:1},transitions:{0:{0:3,1:0},1:{0:2,1:2},2:{0:0,1:1},3:{0:1,1:3}}};
 const proof=productCheck(roots,model,actions);check(proof.status==="PASS_EXACT_REACHABLE_TWO_RESETS"&&proof.pairs===8&&proof.transitions===16,"learned model proof");
 const scopeWitness=[output(step(roots.original_q0_h0,2)),output(step(roots.additional_q0_high_hidden,2))];
 check(scopeWitness[0]===0&&scopeWitness[1]===1,"action2 scope fail");
 const misleading=fromLatent(2,h),resetWitness=[output(step(roots.original_q0_h0,1)),output(step(misleading,1))];
 check(output(misleading)===0&&resetWitness[0]===0&&resetWitness[1]===1,"false initial assignment");
 const mutant=JSON.parse(JSON.stringify(model));mutant.transitions[0][0]=0;const failed=productCheck(roots,mutant,actions);check(failed.status==="FAIL","mutant not detected");
 return {
 experiment:"GEN001_POC16_TWO_RESET_REACHABLE_QUOTIENT_V1",status:"SCOPED_PASS_SYNTHETIC",
 source_ref:"PoC7 NonlinearScrambledSUL at git blob 722e600873a547ed122b2d0c37114be5d162133c",
 contract:{reset_states:Object.fromEntries(Object.entries(roots).map(([k,v])=>[k,"0x"+v.toString(16)])),actions,output:"latent q low bit",reset_event:"separate external episode initialization, not action 2"},
 reachable_raw:all.length,reachable_from_first:ra.length,reachable_from_second:rb.length,
 raw_values:all.map(x=>"0x"+x.toString(16)),min_future_observable_classes:4,
 equivalence_classes:Object.fromEntries(Object.entries(groups).map(([k,g])=>[k,g.map(x=>"0x"+x.toString(16))])),
 refinement_history:partition.counts,raw_to_class:all.map(x=>({raw:"0x"+x.toString(16),class:partition.labels.get(x.toString()),latent_q:toLatent(x)[0]})),
 learned_poc15_model_reused_without_retraining:true,learned_check:proof,
 negatives:{action2_breaks_quotient:{same_current_output:true,witness_actions:[2],subsequent_outputs:scopeWitness},wrong_initial_learned_id:{same_current_output:true,witness_actions:[1],subsequent_outputs:resetWitness},mutated_transition:failed},
 limits:["Two resets chosen with known same q=0; learner did not discover initial mapping.","Not a learned raw state projection or multi-reset learning result.","No measured time/RAM/inference improvement.","Synthetically constructed deterministic source; no all 2^128 reachable claim."],
 next_decision:"Check whether reset identity and output/history interface can initialize the existing learned model without privileged q; no new general learner needed at this stage."
 };
}

if (typeof process !== "undefined" && process.stdout && process.argv?.[1]?.endsWith("poc16_two_reset_quotient.mjs")) process.stdout.write(JSON.stringify(run(),null,2)+"\n");
