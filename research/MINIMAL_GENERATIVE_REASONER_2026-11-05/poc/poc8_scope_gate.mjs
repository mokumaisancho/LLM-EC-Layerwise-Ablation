// GEN001 POC8: trusted-source scoped behavioral abstraction checker.
// External adapter only; native ECv4.4 unchanged.
function assert(x,msg){if(!x)throw Error(msg)}
function eq(a,b){return JSON.stringify(a)===JSON.stringify(b)}
function source(n,nonlinear=false){
 if(nonlinear){
  const mask=(1n<<BigInt(n))-1n;
  function parity(x){let v=0;while(x){v^=1;x&=x-1n}return v}
  function decode(x){const p=parity(x);return [p|((parity(x&(mask^2n))^(p&Number((x>>2n)&1n)))<<1),x>>2n]}
  function encode(z,h){const p=z&1,v=(z>>1)&1,hp=parity(h);const x0=v^(p&Number(h&1n))^hp,x1=p^x0^hp;return (h<<2n)|(BigInt(x1)<<1n)|BigInt(x0)}
  return {id:'poc7-nonlinear-128',resets:{zero:0n},actions:[0,1,2],output_id:'z0',reset:r=>({zero:0n})[r],output:x=>decode(x)[0]&1,step:(x,a)=>{let [z,h]=decode(x);if(a===0)z=(z+1)&3;else if(a===1)z=((z&1)^((z>>1)&1))|((z>>1)<<1);else if(a===2){z^=Number(h&1n);h=(h>>1n)|(BigInt(z&1)<<BigInt(n-3))}else throw Error('bad action');return encode(z,h)}}
 }
 const mask=(1<<n)-1;
 return {id:'poc8-shift-'+n,resets:{warm:4,cold:1},actions:[0,1,2],output_id:'q_zero',reset:r=>({warm:4,cold:1})[r],output:x=>+((x&3)===0),step:(x,a)=>{const q=x&3,h=x>>>2;let qn,hn;if(a===0){qn=(q+1)&3;hn=h}else if(a===1){qn=(q+2)&3;hn=h}else if(a===2){qn=(q+(h&1))&3;hn=(h>>>1)|((q&1)<<(n-3))}else throw Error('bad action');return ((hn<<2)|qn)&mask}}
}
function checkModel(model,actions){
 if(!model||!Number.isInteger(model.initial)||!Array.isArray(model.outputs)||!Array.isArray(model.transitions)||!model.outputs.length||model.outputs.length!==model.transitions.length||model.initial<0||model.initial>=model.outputs.length)return 'MALFORMED';
 const n=model.outputs.length;
 for(let i=0;i<n;i++){if(![0,1].includes(model.outputs[i]))return 'BAD_OUTPUT';if(!model.transitions[i]||Object.keys(model.transitions[i]).length!==actions.length)return 'INCOMPLETE_TRANSITIONS';for(const a of actions){const j=model.transitions[i][String(a)];if(!Number.isInteger(j)||j<0||j>=n)return 'BAD_TARGET'}}
 return null;
}
function checkExact(t,m,reset,actions,maxPairs){
 let x=t.reset(reset);if(x===undefined)return {grade:'COUNTEREXAMPLE',reason:'UNKNOWN_RESET'};
 const key=(x,s)=>String(x)+'|'+s;
 const visited=new Set([key(x,m.initial)]),queue=[[x,m.initial,[]]];let edges=0;
 for(let i=0;i<queue.length;i++){
  const [state,node,word]=queue[i];if(t.output(state)!==m.outputs[node])return {grade:'COUNTEREXAMPLE',reason:'DIFFERENT_OUTPUT',counterexample:word,pairs:visited.size};
  for(const a of actions){edges++;const ns=t.step(state,a),nn=m.transitions[node][String(a)],k=key(ns,nn);if(!visited.has(k)){if(visited.size>=maxPairs)return {grade:'BUDGET_UNKNOWN',reason:'PRODUCT_BUDGET',pairs:visited.size};visited.add(k);queue.push([ns,nn,[...word,a]])}}
 }
 return {grade:'EXACT_REACHABLE',pairs:visited.size,edges};
}
function minReference(t,reset,actions,maxStates){
 const init=t.reset(reset),queue=[init],visited=new Set([String(init)]);
 for(let i=0;i<queue.length;i++)for(const a of actions){const s=t.step(queue[i],a),k=String(s);if(!visited.has(k)){if(visited.size>=maxStates)return {grade:'BUDGET_UNKNOWN'};visited.add(k);queue.push(s)}}
 let classes=new Map(queue.map(x=>[String(x),t.output(x)]));
 for(let iter=0;iter<=maxStates;iter++){
  const signatures=queue.map(x=>JSON.stringify([t.output(x),...actions.map(a=>classes.get(String(t.step(x,a))))]));
  const uniq=[...new Set(signatures)].sort(),dict=new Map(uniq.map((s,i)=>[s,i]));
  const next=new Map(queue.map((x,i)=>[String(x),dict.get(signatures[i])]));
  if(new Set(classes.values()).size===uniq.length)return {grade:'EXACT_REACHABLE',reachable:queue.length,minimal:uniq.length,refinement_rounds:iter+1};
  classes=next;
 }
 return {grade:'BUDGET_UNKNOWN'};
}
function certify(t,c,actual,budget=20000){
 if(c.protocol!=='BEHAVIORAL_ABSTRACTION_CANDIDATE_V1')return {gate:'REJECT',reason:'BAD_PROTOCOL'};
 if(c.source_id!==t.id)return {gate:'REJECT',reason:'SOURCE_MISMATCH'};
 if(!eq(c.scope,actual))return {gate:'REJECT',reason:'SCOPE_MISMATCH'};
 if(!actual.actions.every(a=>t.actions.includes(a))||t.reset(actual.reset)===undefined||actual.output_id!==t.output_id)return {gate:'REJECT',reason:'INVALID_RUNTIME_SCOPE'};
 const err=checkModel(c.model,actual.actions);if(err)return {gate:'REJECT',reason:err};
 const exact=checkExact(t,c.model,actual.reset,actual.actions,budget);
 if(exact.grade==='BUDGET_UNKNOWN')return {gate:'HOLD',reason:'PROOF_BUDGET',proof:exact};
 if(exact.grade!=='EXACT_REACHABLE')return {gate:'REJECT',reason:'NOT_EQUIVALENT',proof:exact};
 const truth=minReference(t,actual.reset,actual.actions,budget);
 if(truth.grade!=='EXACT_REACHABLE')return {gate:'HOLD',reason:'MINIMALITY_BUDGET',proof:exact,truth};
 if(c.model.outputs.length!==truth.minimal)return {gate:'REJECT',reason:'NOT_MINIMAL',proof:exact,truth};
 return {gate:'PROPOSE_VERIFIED_REABSTRACT',authority:'EXTERNAL_PROPOSAL_ONLY',proof:exact,truth,scope:actual};
}
function membership(t,reset){const cache=new Map();let steps=0;return {query:word=>{const k=word.join(',');if(cache.has(k))return cache.get(k);let s=t.reset(reset);for(const a of word){s=t.step(s,a);steps++}const v=t.output(s);cache.set(k,v);return v},stats:()=>({distinct_queries:cache.size,source_steps:steps})}}
function learnLstar(actions,member,oracle){
 const S=[[]],E=[[]],skeys=new Set(['']),ekeys=new Set(['']);const wordKey=w=>w.join(',');const row=s=>E.map(e=>member([...s,...e])).join('');
 for(let rounds=0;rounds<200;rounds++){
  while(true){const signatures=new Set(S.map(row));let added=false;
   outer:for(const s of S)for(const a of actions){const w=[...s,a];if(!signatures.has(row(w))){if(!skeys.has(wordKey(w))){S.push(w);skeys.add(wordKey(w))}added=true;break outer}}
   if(added)continue;
   outer2:for(let i=0;i<S.length;i++)for(let j=i+1;j<S.length;j++){if(row(S[i])!==row(S[j]))continue;for(const a of actions)for(const e of E){if(member([...S[i],a,...e])!==member([...S[j],a,...e])){const w=[a,...e];if(!ekeys.has(wordKey(w))){E.push(w);ekeys.add(wordKey(w))}added=true;break outer2}}}
   if(!added)break;
  }
  const keys=[...new Set(S.map(row))].sort(),dic=new Map(keys.map((x,i)=>[x,i])),reps=new Map(S.map(s=>[dic.get(row(s)),s]));
  const outputs=[],transitions=[];
  for(const [i,s] of [...reps.entries()].sort((x,y)=>x[0]-y[0])){outputs[i]=member(s);transitions[i]={};for(const a of actions){const j=dic.get(row([...s,a]));assert(j!==undefined,'not closed');transitions[i][String(a)]=j}}
  const model={initial:dic.get(row([])),outputs,transitions};const witness=oracle(model);
  if(witness===null)return {model,rounds:rounds+1,query_table:{prefixes:S.length,suffixes:E.length}};
  for(let i=0;i<=witness.length;i++){const w=witness.slice(0,i),k=wordKey(w);if(!skeys.has(k)){S.push(w);skeys.add(k)}}
 }
 throw Error('learning round budget');
}
function testRun(){
 let assertions=0;const cases=[];function check(cond,msg){assertions++;assert(cond,msg)}
 const t=source(8),reset='warm',actions=[0,1],member=membership(t,reset);
 const learned=learnLstar(actions,member.query,m=>{const p=checkExact(t,m,reset,actions,20000);return p.grade==='EXACT_REACHABLE'?null:p.counterexample});
 const scope={reset,actions,output_id:t.output_id},candidate={protocol:'BEHAVIORAL_ABSTRACTION_CANDIDATE_V1',source_id:t.id,scope,model:learned.model,claimed_proof:'EXACT_REACHABLE'};
 const good=certify(t,candidate,scope);check(good.gate==='PROPOSE_VERIFIED_REABSTRACT','valid source');cases.push({name:'valid_reachable',grade:good.proof.grade,states:learned.model.outputs.length,minimum:good.truth.minimal,queries:member.stats().distinct_queries});
 for(const [name,scopeMutation] of [['different_reset',{...scope,reset:'cold'}],['new_probe_action',{...scope,actions:[0,1,2]}],['different_output',{...scope,output_id:'not_q_zero'}]]){const x=certify(t,candidate,scopeMutation);check(x.reason==='SCOPE_MISMATCH',name);cases.push({name,gate:x.gate})}
 let fake={...candidate,source_id:'modified_system'};let x=certify(t,fake,scope);check(x.reason==='SOURCE_MISMATCH','source');cases.push({name:'forged_source',gate:x.gate});
 let corrupt=JSON.parse(JSON.stringify(candidate));corrupt.model.outputs[corrupt.model.initial]^=1;corrupt.claimed_proof='EXACT_REACHABLE';x=certify(t,corrupt,scope);check(x.reason==='NOT_EQUIVALENT'&&x.proof.counterexample.length===0,'false output');cases.push({name:'fabricated_proof_bad_output',gate:x.gate,witness:x.proof.counterexample});
 corrupt=JSON.parse(JSON.stringify(candidate));corrupt.model.transitions[corrupt.model.initial]['0']=corrupt.model.initial;x=certify(t,corrupt,scope);check(x.reason==='NOT_EQUIVALENT','false transition');cases.push({name:'incorrect_transition',gate:x.gate,witness:x.proof.counterexample});
 x=certify(t,candidate,scope,1);check(x.gate==='HOLD'&&x.reason==='PROOF_BUDGET','budget');cases.push({name:'verification_budget',gate:x.gate});
 const bad={...candidate,model:{initial:0,outputs:[t.output(t.reset(reset))],transitions:[{'0':0,'1':0}]}};x=certify(t,bad,scope);check(x.reason==='NOT_EQUIVALENT','bad oracle');cases.push({name:'premature_learner_close',gate:x.gate,witness:x.proof.counterexample});
 corrupt=JSON.parse(JSON.stringify(candidate));corrupt.model.outputs.push(1);corrupt.model.transitions.push({'0':corrupt.model.outputs.length-1,'1':corrupt.model.outputs.length-1});x=certify(t,corrupt,scope);check(x.reason==='NOT_MINIMAL','nonminimal');cases.push({name:'extra_unreachable_state',gate:x.gate});
 const nt=source(128,true),ns={reset:'zero',actions:[0,1],output_id:'z0'},nm=membership(nt,'zero');const nl=learnLstar(ns.actions,nm.query,m=>{const p=checkExact(nt,m,ns.reset,ns.actions,20000);return p.grade==='EXACT_REACHABLE'?null:p.counterexample});const nc={protocol:'BEHAVIORAL_ABSTRACTION_CANDIDATE_V1',source_id:nt.id,scope:ns,model:nl.model};x=certify(nt,nc,ns);check(x.gate==='PROPOSE_VERIFIED_REABSTRACT'&&x.truth.minimal===4,'nonlinear128');cases.push({name:'nonlinear_128_relearned',gate:x.gate,states:nl.model.outputs.length,minimum:x.truth.minimal,queries:nm.stats().distinct_queries});
 return {experiment:'GEN001_POC8_SCOPE_CERTIFICATE_GATE_V1',status:'SCOPED_PASS',assertions,scenario_count:cases.length,cases,limitations:['Verifier must have trusted reference transition and the actual runtime action/reset contract','Finite deterministic, resettable models only; no general semantic inference','No cryptographic signature or persistent certificate validation; recomputes against live trusted source','External proposed framing only; native ECv4.4 control-plane remains unchanged'],next_blocker:'Native ECv4.4 adapter receiving verified scope-bound proposals plus regression tests; source identity integrity requires stronger authority binding'};
}
if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href)console.log(JSON.stringify(testRun(),null,2));
export {source,certify,checkExact,minReference,learnLstar,testRun};
