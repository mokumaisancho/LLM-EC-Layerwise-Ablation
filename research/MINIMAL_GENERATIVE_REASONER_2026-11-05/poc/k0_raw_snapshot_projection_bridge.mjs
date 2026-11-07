// Frozen PRE: 0a1142944afa48fe02950d76f3f453821655b84e
// Existing MGR P1 k=0 source: 9167e7e1d1326d11ecd636220b5f3a80c655bb33
// Existing source-blind L* model: 277ba261ffd5e37970b6cf40dcb5d104953505b0
// Simulation only: raw state snapshot is an ADDED capability; not available to prior output-only L*.
function parity(x){let p=0;while(x){p^=x&1;x>>=1}return p}

function encode(phase,noise){const m=parity(noise);return(noise<<2)|((phase&1)^m)|(((((phase>>1)&1)^m)<<1))}

function decode(z){const noise=z>>2,m=parity(noise);return [((z&1)^m)|(((((z>>1)&1)^m)<<1)),noise]}

function sourceStep(z,a){const [phase,noise]=decode(z);const np=(phase+1+a)%4,hw=6,hn=(17*noise+13*phase+3*a+7)&((1<<hw)-1);return encode(np,hn)}

function sourceOutput(z){return decode(z)[0]>>1}

function run(){
 const learned={initial:0,transitions:{"0":{"0":1,"1":3},"1":{"0":3,"1":2},"2":{"0":0,"1":1},"3":{"0":2,"1":0}},outputs:{"0":0,"1":0,"2":1,"3":1}};
 const BUDGET={snapshot_queries:1024,replay_actions:16000};
 function bfs(corruptWord){
   let calls=0,steps=0,maxdepth=0;const snapshotOracle=(word)=>{
     calls++;steps+=word.length;
     if(calls>BUDGET.snapshot_queries||steps>BUDGET.replay_actions)throw Error("BUDGET_EXCEEDED");
     let x=0;for(const c of word)x=sourceStep(x,Number(c));
     return {raw:word===corruptWord?0:x,output:sourceOutput(x)}
   };
   const first=snapshotOracle(""),q=[{raw:first.raw,id:learned.initial,word:""}],assigned=new Map([[first.raw,{id:learned.initial,word:""}]]);let checkedEdges=0;
   if(first.output!==learned.outputs[learned.initial])return {status:"FAIL",reason:"RESET_OUTPUT_MISMATCH"};
   for(let i=0;i<q.length;i++){
     const st=q[i];maxdepth=Math.max(maxdepth,st.word.length);
     for(const a of [0,1]){
       const word=st.word+String(a),sample=snapshotOracle(word),newId=learned.transitions[st.id][a];
       if(sample.output!==learned.outputs[newId])return{status:"FAIL",reason:"OUTPUT_MISMATCH",witness:word,raw:sample.raw};
       const old=assigned.get(sample.raw);if(old&&old.id!==newId)return{status:"FAIL",reason:"RAW_ID_CONFLICT",witness:word,raw:sample.raw,previous_word:old.word,previous_id:old.id,new_id:newId,queries:calls,replay_actions:steps};
       if(!old){assigned.set(sample.raw,{id:newId,word});q.push({raw:sample.raw,id:newId,word})}
       checkedEdges++;
     }
   }
   return{status:assigned.size===256?"PASS_COMPLETE_8BIT_DOMAIN":"UNKNOWN_PARTIAL_REACHABILITY",raw_states_mapped:assigned.size,classes:new Set([...assigned.values()].map(x=>x.id)).size,each_class_count:Object.fromEntries([0,1,2,3].map(id=>[id,[...assigned.values()].filter(v=>v.id===id).length])),queries:calls,replayed_source_actions:steps,maximum_history_depth:maxdepth,observed_edges_checked:checkedEdges,mapping_entries:Array.from({length:256},(_,raw)=>assigned.get(raw)?.id??null),witness_access_to_raw_1:assigned.get(1)?.word,witness_access_to_raw_2:assigned.get(2)?.word};
 }
 const learnedMapping=bfs("__NONE__");
 const corruption=bfs("1");
 if(learnedMapping.status!=="PASS_COMPLETE_8BIT_DOMAIN"||corruption.status!=="FAIL"||corruption.reason!=="RAW_ID_CONFLICT")throw Error("unexpected_bfs_result");
 const assigned=learnedMapping.mapping_entries;let independent=0;
 for(let raw=0;raw<256;raw++){
   const id=assigned[raw];if(id===null||learned.outputs[id]!==sourceOutput(raw))throw Error("false projection output raw="+raw);
   for(const a of [0,1]){const nr=sourceStep(raw,a),next=learned.transitions[id][a];if(assigned[nr]!==next)throw Error("false projection transition raw="+raw+",action="+a);independent++}
 }
 const p=(x)=>x===1?2:x===2?1:x;const reStep=(x,a)=>p(sourceStep(p(x),a)),reOut=(x)=>sourceOutput(p(x));
 // Output-only oracle is invariant to state relabeling fixing raw reset=0.
 const words=[""];for(let d=1;d<=8;d++){const prev=words.filter(w=>w.length===d-1);for(const w of prev){words.push(w+"0",w+"1")}}
 let queryAgreement=0;
 for(const w of words){let x=0,y=0;for(const a of w){x=sourceStep(x,Number(a));y=reStep(y,Number(a))}if(sourceOutput(x)!==reOut(y))throw Error("output-only traces not invariant for "+w);queryAgreement++}
 if(sourceOutput(1)===reOut(1)||assigned[1]===assigned[2])throw Error("insufficient permutation counterexample");
 return {
  protocol:"GEN001_K0_RAW_SNAPSHOT_INTERFACE_BRIDGE_V1",status:"SCOPED_PASS_CONDITIONAL",
  source_ref:"research/MINIMAL_GENERATIVE_REASONER_2026-11-05/poc_finite_quotient_v1/run_poc.py@9167e7e1d1326d11ecd636220b5f3a80c655bb33",
  learned_model_ref:"research/MINIMAL_GENERATIVE_REASONER_2026-11-05/poc/K0_FIXED_RESET_BLACKBOX_OBSERVED_2026-11-07.json@277ba261ffd5e37970b6cf40dcb5d104953505b0",
  pre_commit:"0a1142944afa48fe02950d76f3f453821655b84e",
  learned_input_access:"reset+action sequence -> final raw state ID and 1bit observable; original model known",
  result:learnedMapping,
  independent_source_check:{status:"PASS_EXACT_ALL_256",source_states:256,observed_edges:independent,output_matches:256,source_aware_after_learning:true},
  corrupted_snapshot_negative:corruption,
  output_only_identifiability_counterexample:{status:"UNIDENTIFIABLE_BY_OUTPUT_TRACE",permutation:"swap raw 1 and raw 2, leave reset raw0 fixed",same_reset_word_observations_verified:queryAgreement,original_raw1_output:sourceOutput(1),relabeled_raw1_output:reOut(1),original_model_state_raw1:assigned[1],original_model_state_raw2:assigned[2],proof:"Conjugate T'=p T p^-1 and O'=O p^-1 with p(0)=0. By induction, every reset-word outputs match while mapping on raw IDs 1/2 differs."},
  restrictions:["This is a complete finite 8bit lookup table of 256 raw state identifiers, not compact symbolic phi; raw IDs are a newly granted privileged input.","No guarantee of arbitrary raw-state-to-model map when the raw domain is larger or unreachable states exist.","No independent authenticity proof for raw snapshot interface; corruption rejection is a collision example only.","Not general reasoning, unknown nonlinear structure discovery, or measured end-to-end speed improvement."],
  followup_gate:"Original GEN001 does not require a raw phi for fixed-reset history prediction; do not impose it as universal P0. Require snapshot interface only when the intended consumer accepts an externally provided raw state."
 };
}

if(typeof process!=="undefined" && process.stdout)process.stdout.write(JSON.stringify(run(),null,2)+"\n");
