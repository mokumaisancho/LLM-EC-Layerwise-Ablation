// ROOT-GEN-001 selected shared task contract from dependency graph, PRE c58bb158422d510c2bf55c758ff464a399b77192
// Learner's task-policy sees ONLY prior L* four-state automaton and goal. Source is checker-only.
function parity(x){let p=0;for(;x;x&=x-1)p^=1;return p}

function encode(phase,noise){let m=parity(noise);return(noise<<2)|((phase&1)^m)|(((((phase>>1)&1)^m)<<1))}

function decode(z){let noise=z>>2,m=parity(noise);return[(z&1)^m|(((((z>>1)&1)^m)<<1)),noise]}

function sourceStep(z,a){const [phase,noise]=decode(z);const np=(phase+1+a)%4,highNext=(17*noise+13*phase+3*a+7)&63;return encode(np,highNext)}

function sourceOutput(z){return decode(z)[0]>>1}

function plan(model,goal,horizon){
 let queue=[{state:model.initial,actions:"",outputs:""}],count=0;
 for(let i=0;i<queue.length;i++){const cur=queue[i];count++;if(cur.outputs.endsWith(goal))return{status:"REACHABLE",witness:cur.actions,observed_trace:cur.outputs,expanded:count};if(cur.actions.length===horizon)continue;
  for(let a of [0,1]){const nxt=model.transitions[cur.state][a],obs=model.outputs[nxt];queue.push({state:nxt,actions:cur.actions+String(a),outputs:cur.outputs+String(obs)})}
 }return{status:"UNSAT_WITHIN_HORIZON",witness:null,observed_trace:null,expanded:count}
}

function gold(goal,horizon){
 let queue=[{raw:0,actions:"",outputs:""}],checked=0,sourceActions=0;
 for(let i=0;i<queue.length;i++){const st=queue[i];checked++;if(st.outputs.endsWith(goal))return{status:"REACHABLE",witness:st.actions,observed_trace:st.outputs,checked_words:checked,source_actions:sourceActions};
  if(st.actions.length===horizon)continue;
  for(const a of [0,1]){const raw=sourceStep(st.raw,a),obs=sourceOutput(raw);sourceActions++;queue.push({raw,actions:st.actions+String(a),outputs:st.outputs+String(obs)})}
 }
 return{status:"UNSAT_WITHIN_HORIZON",witness:null,observed_trace:null,checked_words:checked,source_actions:sourceActions}
}

function allGoals(){const result=[];for(let len=2;len<=4;len++)for(let mask=0;mask<1<<len;mask++)result.push(mask.toString(2).padStart(len,"0"));return result}

function evaluateSuite(){
 const model={initial:0,transitions:{"0":{"0":1,"1":3},"1":{"0":3,"1":2},"2":{"0":0,"1":1},"3":{"0":2,"1":0}},outputs:{"0":0,"1":0,"2":1,"3":1}};
 const horizon=6,goals=allGoals(),results=[],counts={REACHABLE:0,UNSAT_WITHIN_HORIZON:0},lengths={};
 let totalModelExpanded=0,totalGoldWords=0,totalSourceActions=0;
 for(const goal of goals){
 const predicted=plan(model,goal,horizon),independent=gold(goal,horizon);
 if(predicted.status!==independent.status||predicted.witness!==independent.witness||predicted.observed_trace!==independent.observed_trace)throw Error("GOAL_PLANNING_MISMATCH:"+goal+":"+JSON.stringify({predicted,independent}));
 counts[predicted.status]++;if(predicted.status==="REACHABLE")lengths[predicted.witness.length]=(lengths[predicted.witness.length]??0)+1;
 results.push({goal,predicted,independent});totalModelExpanded+=predicted.expanded;totalGoldWords+=independent.checked_words;totalSourceActions+=independent.source_actions;
 }
 const mutant=JSON.parse(JSON.stringify(model));mutant.transitions["0"]["0"]=0;const mutatedFailures=[];for(const goal of goals){const p=plan(mutant,goal,horizon),truth=results.find(x=>x.goal===goal).independent;if(p.status!==truth.status||p.witness!==truth.witness||p.observed_trace!==truth.observed_trace)mutatedFailures.push({goal,plan_status:p.status,witness:p.witness,correct_status:truth.status,correct_witness:truth.witness})}
 if(mutatedFailures.length===0)throw Error("NEGATIVE_CONTROL_DID_NOT_DETECT_MUTANT");
 const maxLen=Math.max(...Object.keys(lengths).map(Number)),hasNonTrivial=maxLen>=2&&counts.REACHABLE>0&&counts.UNSAT_WITHIN_HORIZON>0;
 return {
 protocol:"GEN001_GOAL_CONDITIONED_ACTION_SELECTION_V1",status:hasNonTrivial?"SCOPED_PASS_SYNTHETIC_PLANNING":"INCONCLUSIVE_TOO_TRIVIAL",date:"2026-11-07",
 pre_registration_commit:"c58bb158422d510c2bf55c758ff464a399b77192",
 source:"Original MGR-P1 k0 source and frozen prior four-state L* model",
 input_contract:{reset:"fixed raw0",actions:[0,1],observation:"one-bit output after each action",target:"any binary output suffix length 2..4",horizon_max:6,targets:"complete enumerated set; 28 goals",solver_sees:"only learned model, goal and horizon",checker_sees:"source-private 8bit raw system"},
 summary:{tasks:goals.length,counts,plan_lengths: lengths,all_exact_match:true,maximum_witness_length:maxLen,model_nodes_expanded:totalModelExpanded,independent_gold_words_checked:totalGoldWords,independent_gold_source_steps:totalSourceActions,mutant_detected_goal_count:mutatedFailures.length,mutant_example:mutatedFailures.slice(0,5)},
 results,negative_mutant_failures:mutatedFailures,
 limits:["Only a bounded fully-known four-state learned model; BFS is generic classical search, not newly discovered reasoning algorithm.","Outputs are simple one-bit traces in a synthetic system; no evidence of nontrivial open-ended, multi-domain or natural-language problem solving.","Independent gold uses same documented deterministic source but does not receive learned states or model.","No measured time/RAM advantage, not a total-cost conclusion.","Verifier source-aware; the model does not certify itself.","The same 28 targets are distinct desired output words, not different source domains."]
 };
}

if(typeof process!=="undefined"&&process.stdout)process.stdout.write(JSON.stringify(evaluateSuite(),null,2)+"\n");
