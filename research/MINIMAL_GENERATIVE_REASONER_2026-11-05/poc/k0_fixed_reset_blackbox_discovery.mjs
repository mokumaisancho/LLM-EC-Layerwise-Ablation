// GEN001 fixed-registry source: MGR-P1 run_poc.py git blob 9167e7e1d1326d11ecd636220b5f3a80c655bb33
// Learning port from PoC7 published L* git blob 722e600873a547ed122b2d0c37114be5d162133c
// PRE commit 7982540978ff7cdd5139525a5535186e2fd7703f
// JavaScript built-ins only. Learner & black-box EQ get membership function, not raw latent states.
const ALPHABET=[0,1];
function parity(x){let p=0;while(x){p^=x&1;x>>=1}return p}

function encode(phase,noise){const m=parity(noise);return (noise<<2)|((phase&1)^m)|(((((phase>>1)^m)&1)<<1))}

function decode(z){const noise=z>>2,m=parity(noise);return [((z&1)^m)|(((((z>>1)^m)&1)<<1)),noise]}

function sourceStep(z,a,k=0){const [phase,noise]=decode(z);const np=(phase+1+a+(k?noise&1:0))%4,low=(noise&((1<<k)-1))>>1,hw=6-k,high=noise>>k,highNext=hw?((17*high+13*phase+3*a+7)&((1<<hw)-1)):0;return encode(np,low|(highNext<<k))}

function sourceOutput(z){return decode(z)[0]>>1}

function wordOrdering(a,b){return a.length-b.length||(a<b?-1:a>b?1:0)}

function runExperiment(){
 const fixedBudget={uniqueQueries:5000,simulatedSteps:100000,eqRounds:6,randomWordsPerEQ:400,maxDepth:20,seed:20261105};
 const memberCache=new Map();let sourceSteps=0;
 const member=(word)=>{
  if(memberCache.has(word))return memberCache.get(word);
  let x=0;for(const c of word){x=sourceStep(x,Number(c),0);sourceSteps++}
  const y=sourceOutput(x);memberCache.set(word,y);
  if(memberCache.size>fixedBudget.uniqueQueries||sourceSteps>fixedBudget.simulatedSteps)throw Error("QUERY_BUDGET_EXCEEDED");
  return y
 };
 const rand=(()=>{let s=fixedBudget.seed|0;return()=>{s^=s<<13;s^=s>>>17;s^=s<<5;return(s>>>0)/4294967296}})();
 const S=new Set([""]),E=new Set([""]);let eqCalls=0,closureAdds=0,consistencySplits=0;let cex=[],learned=null,stopped=false;
 const ordered=x=>[...x].sort(wordOrdering);
 const row=s=>ordered(E).map(e=>member(s+e));
 const rowkey=s=>JSON.stringify(row(s));
 const build=()=>{
  const keys=ordered(S),rows=new Map(keys.map(s=>[s,rowkey(s)])),uniq=[...new Set(rows.values())].sort(),toid=new Map(uniq.map((key,i)=>[key,i]));
  const reps=new Map();for(const s of keys)reps.set(toid.get(rows.get(s)),s);
  const trans={},outs={};for(const [id,s] of reps){trans[id]={};for(const a of ALPHABET){const key=rowkey(s+String(a));if(!toid.has(key))throw Error("TABLE_NOT_CLOSED");trans[id][a]=toid.get(key)}outs[id]=member(s)}
  return {initial:toid.get(rows.get("")),transitions:trans,outputs:outs,size:Object.keys(outs).length};
 };
 const runHyp=(h,word)=>{let id=h.initial;for(const c of word)id=h.transitions[id][Number(c)];return h.outputs[id]};
 const eq=(h)=>{
  eqCalls++;
  for(let k=0;k<=4;k++){const walk=(w,d)=>{if(d===0)return member(w)!==runHyp(h,w)?w:null;for(const a of ALPHABET){let c=walk(w+String(a),d-1);if(c!==null)return c}return null};const ce=walk("",k);if(ce!==null)return ce}
  for(let q=0;q<fixedBudget.randomWordsPerEQ;q++){let n=Math.floor(rand()*(fixedBudget.maxDepth+1)),w="";for(let t=0;t<n;t++)w+=String(Math.floor(rand()*2));if(member(w)!==runHyp(h,w))return w}
  return null;
 };
 try{
  for(let round=0;round<fixedBudget.eqRounds;round++){
   for(let inner=0;inner<300;inner++){
    const rows=new Map([...S].map(s=>[rowkey(s),s]));let missing=null;
    for(const s of ordered(S)){for(const a of ALPHABET){const sa=s+String(a);if(!rows.has(rowkey(sa))){missing=sa;break}}if(missing!==null)break}
    if(missing!==null){S.add(missing);closureAdds++;continue}
    const grouped=new Map();for(const s of ordered(S)){const key=rowkey(s);if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(s)}
    let inconsistent=null;
    for(const group of grouped.values()){
      for(let i=0;i<group.length;i++){for(let j=i+1;j<group.length;j++){for(const a of ALPHABET){for(const e of ordered(E)){const suffix=String(a)+e;if(member(group[i]+suffix)!==member(group[j]+suffix)){inconsistent=suffix;break}}if(inconsistent!==null)break}if(inconsistent!==null)break}if(inconsistent!==null)break}if(inconsistent!==null)break}
    if(inconsistent!==null){if(E.has(inconsistent))throw Error("DUPLICATE_SUFFIX");E.add(inconsistent);consistencySplits++;continue}
    break;
   }
   learned=build();const witness=eq(learned);if(witness===null){stopped=true;break}
   cex.push([...witness].map(Number));for(let i=0;i<=witness.length;i++)S.add(witness.slice(0,i));
  }
 }catch(err){return{status:"UNKNOWN_BUDGET_OR_RUNTIME",error:String(err),raw_reachability:"NOT_CHECKED",learning:{eqCalls,queries:memberCache.size,sourceSteps}}}
 if(!learned)throw Error("LEARNER_EMPTY");
 // Privileged verifier starts ONLY after all black-box experiments are complete.
 function exact(){
  const queue=[[0,learned.initial,""]],visited=new Set(["0|"+learned.initial]),raw=new Set([0]);let edges=0;
  for(let i=0;i<queue.length;i++){
   const [x,id,w]=queue[i];if(sourceOutput(x)!==learned.outputs[id])return {status:"FAIL",witness:[...w].map(Number),pairs:i+1,rawStates:raw.size,edges};
   for(const a of ALPHABET){const next=sourceStep(x,a,0),candidate=learned.transitions[id][a],key=next+"|"+candidate;edges++;raw.add(next);if(!visited.has(key)){visited.add(key);queue.push([next,candidate,w+String(a)])}}
  }return {status:"PASS_EXACT_REACHABLE",pairs:queue.length,rawStates:raw.size,edges};
 }
 const checked=exact();
 function fullMinimal(){
  const source=[0],s=new Set([0]);for(let i=0;i<source.length;i++)for(const a of ALPHABET){let n=sourceStep(source[i],a,0);if(!s.has(n)){s.add(n);source.push(n)}}
  let part=new Map(source.map(x=>[x,sourceOutput(x)])),rounds=0;
  while(rounds++<20){const sigs=source.map(x=>JSON.stringify([sourceOutput(x),...ALPHABET.map(a=>part.get(sourceStep(x,a,0)))])),keys=[...new Set(sigs)].sort(),ids=new Map(keys.map((v,i)=>[v,i])),next=new Map(source.map((x,i)=>[x,ids.get(sigs[i])]));
   const same=source.every(x=>source.every(y=>(part.get(x)===part.get(y))===(next.get(x)===next.get(y))));part=next;if(same)return{reachable_raw_states:source.length,minimal_future_classes:new Set(part.values()).size,partition_rounds:rounds,raw_state_min:Math.min(...source),raw_state_max:Math.max(...source)}
  }throw Error("REFINEMENT_DID_NOT_STABILIZE");
 }
 const reference=fullMinimal();
 const mutant=JSON.parse(JSON.stringify(learned));mutant.transitions[mutant.initial][0]=mutant.initial;
 function checkModel(h){
   let queue=[[0,h.initial,""]],vis=new Set(["0|"+h.initial]);
   for(let i=0;i<queue.length;i++){const [x,id,w]=queue[i];if(sourceOutput(x)!==h.outputs[id])return{status:"FAIL",witness:[...w].map(Number)};for(const a of ALPHABET){const xx=sourceStep(x,a,0),yy=h.transitions[id][a],key=xx+"|"+yy;if(!vis.has(key)){vis.add(key);queue.push([xx,yy,w+String(a)])}}}
   return {status:"PASS"};
 }
 const mutation=checkModel(mutant);
 const pass=stopped&&checked.status==="PASS_EXACT_REACHABLE"&&reference.reachable_raw_states===256&&reference.minimal_future_classes===4&&learned.size===4&&mutation.status==="FAIL";
 return {
   protocol:"GEN001_BLACKBOX_RESET0_K0_DISCOVERY_V1",status:pass?"SCOPED_PASS":"SCOPED_FAIL_OR_UNKNOWN",source_scope:{family:"MGR-P1",k:0,source_bits:8,reset_raw:0,allowed_actions:ALPHABET,observation:"decoded phase high bit"},
   pre_registered_bounds:fixedBudget,
   blackbox_learning:{implementation:"Angluin L* observation table faithful structural port of PoC7 reference; not native AALpy",source_hidden_from_learner:true,blackbox_eq_uses_only_membership:true,stopped,learned_states:learned.size,model:learned,eqCalls,unique_membership_queries:memberCache.size,simulated_source_steps:sourceSteps,closure_additions:closureAdds,consistency_splits:consistencySplits,refutation_words:cex},
   independent_checker:{...checked,minimal_reference:reference,mutated_model_negative:mutation},
   interpretation:{newly_verified:"black-box source-independent learning of reachable four-state future-observable quotient from a single reset with 256 distinct raw reachable states, checked by a separate source-aware verifier",not_verified:["the symbolic map phi(raw) was generated by learner","arbitrary new raw states can be initialized into learned model without history","runtime/memory and full learning/proof cost savings","general nonlinear law induction","all future domains / generalized intelligence"],baseline_difference:"PoC7 reset0 had only 4 raw states; PoC16's 8 raw states were achieved by intentionally paired reset states; existing MGR-P1 k0 source-aware Moore minimization had known 256->4 but did not prove black-box learner discovery"}
 };
}

const result=runExperiment();
if (typeof process!=="undefined" && process.stdout) process.stdout.write(JSON.stringify(result,null,2)+"\n");
