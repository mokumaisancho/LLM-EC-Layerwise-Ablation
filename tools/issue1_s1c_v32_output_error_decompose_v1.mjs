#!/usr/bin/env node
// Issue #1 research diagnostic. Post-hoc frozen-output sensitivity; NOT an LLM rerun,
// a permissible output repair, or an original Phase1 A-E causal experiment.
import fs from "node:fs";
import crypto from "node:crypto";
import {fileURLToPath} from "node:url";
import {resolve,dirname} from "node:path";

const EXPECTED_BLOB="c3f746dcec0a8ab150844f028e3b29a83bdffb99";
const EVAL_IDS=["Q03","Q05","Q06","Q07"];
function must(v,why){if(!v)throw Error("REJECT:"+why)}
export function permutations(xs,n){
 if(!n)return [[]];
 return xs.flatMap((x,i)=>permutations(xs.filter((_,j)=>j!==i),n-1).map(s=>[x,...s]));
}
export function analyze(data){
 must(data?.protocol==="FUNCTION_BOUNDARY_S1C_V32_PAIRED_V1","PROTOCOL");
 must(data?.raw_qwen_rows?.length===8,"FIXED_N8");
 must(data?.oracle_validation?.authority==="S1C_V31_INDEPENDENT_ORACLE_VALIDATOR_V1","ORACLE_AUTHORITY");
 must(data.oracle_validation.pass===true,"ORACLE_VALID");
 const refs=data.oracle_validation.references;
 must(Object.keys(refs).length===8,"GOLD_COUNT");
 const rows=[];const ids=new Set();
 for(const r of data.raw_qwen_rows){
  must(!ids.has(r.task_id),"DUP_CASE");ids.add(r.task_id);
  must(r.schema_core_valid===true && r.semantic_output_valid===false && r.semantic_reason==="TRAINING_MEMBER_DUPLICATED","HISTORICAL_SCORE_CHANGED");
  must(r.raw_sha256===crypto.createHash("sha256").update(r.raw).digest("hex"),"RAW_QWEN_HASH");
  must(JSON.stringify(JSON.parse(r.raw))===JSON.stringify(r.prediction),"PREDICTION_RAW_PARSE_MISMATCH");
  const gold=refs[r.task_id];must(gold&&gold.task_id===r.task_id,"GOLD_BINDING");
  const goldSlots=Object.entries(gold.slot_references).map(([code,entry])=>({code,...entry}));
  const pred=r.prediction.discovered_slots;
  must(pred.length>=goldSlots.length&&goldSlots.length===2,"SLOT_COUNT_ASSUMPTION");
  let counts={};for(const s of pred)for(const m of s.training_members)counts[m]=(counts[m]||0)+1;
  const dup=Object.values(counts).filter(n=>n>1).length;
  must(dup>0,"DUP_MEMBERS_ASSUMPTION");
  let optimistic={typed:-1,type_ignored:-1},completeVectors=0;
  for(const s of pred)for(const g of goldSlots){
   const preds=Object.fromEntries(s.evaluation_probe_predictions.map(p=>[p.probe_id,p.predicted_after]));
   let hits=g.evaluation_probe_expected.reduce((n,row)=>n+Number(JSON.stringify(preds[row.probe_id])===JSON.stringify(row.predicted_after)),0);
   if(hits===4)completeVectors++;
  }
  for(const perm of permutations(pred.map((_,i)=>i),2)){
   for(const strict of [true,false]){
    let hits=0;
    for(let j=0;j<2;j++){
     const s=pred[perm[j]],g=goldSlots[j];
     if(strict&&JSON.stringify(s.arg_types)!==JSON.stringify(g.arg_types))continue;
     const predicted=Object.fromEntries(s.evaluation_probe_predictions.map(p=>[p.probe_id,p.predicted_after]));
     hits+=g.evaluation_probe_expected.reduce((n,z)=>n+Number(JSON.stringify(predicted[z.probe_id])===JSON.stringify(z.predicted_after)),0);
    }
    const k=strict?"typed":"type_ignored";
    optimistic[k]=Math.max(optimistic[k],hits);
   }
  }
  must(optimistic.typed>=0&&optimistic.type_ignored>=optimistic.typed,"OPTIMISTIC_MONOTONICITY");
  rows.push({task_id:r.task_id,model_slot_count:pred.length,reference_slot_count:2,
     multiply_owned_training_members:dup,
     optimistic_typed_probe_matches:optimistic.typed,
     optimistic_type_ignored_probe_matches:optimistic.type_ignored,
     probe_denominator:8,exact_4_of_4_slot_ref_vectors:completeVectors});
 }
 must(ids.size===8 && rows.every(x=>x.probe_denominator===8),"EIGHT_TASKS");
 const sum=k=>rows.reduce((x,r)=>x+r[k],0);
 const typed=sum("optimistic_typed_probe_matches");
 const relaxed=sum("optimistic_type_ignored_probe_matches");
 const summary={task_count:8,original_semantically_invalid:8,
   wrong_slot_count:rows.filter(x=>x.model_slot_count!==2).length,
   gold_probe_denominator:64,optimistic_typed_probe_matches:typed,
   optimistic_type_ignored_probe_matches:relaxed,
   optimistic_typed_accuracy:typed/64,
   optimistic_type_ignored_accuracy:relaxed/64,
   exact_slot_ref_vectors:sum("exact_4_of_4_slot_ref_vectors")};
 return {schema:"ISSUE1_S1C_V32_FROZEN_OUTPUT_DIAGNOSTIC_V1",
  scope:"POSTHOC_GOLD_ALIGNED_UPPER_BOUND_ONLY_NOT_PREDICTOR_PERFORMANCE",
  corpus:"PUBLIC_FINITE_64_FUNCTION_SYNTHETIC_TYPED_INVENTORY",
  original_mvp_promoted:0,real_llm_reinference:false,raw_llm_prediction_edited:false,
  original_score_kept:"0/8 semantic validity; 0 performance by strict contract",
  source_blob:EXPECTED_BLOB,summary,rows,
  interpretation:"With all raw predictions frozen, removing duplicate-membership invalidity alone cannot supply the missing correct heldout probe vectors. Oracle-optimistic 12/64 with correct slot types, 20/64 ignoring types; not a deployable score or causal proof of LLM necessity."};
}
const pathArg=process.argv[2];
if(pathArg){
 const sourceBytes=fs.readFileSync(resolve(pathArg));
 const realBlob=crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+sourceBytes.length+"\0"),sourceBytes])).digest("hex");
 must(realBlob===EXPECTED_BLOB,"SOURCE_GIT_BLOB_DRIFT");
 const result=analyze(JSON.parse(sourceBytes));
 must(result.summary.optimistic_typed_probe_matches===12,"PINNED_TYPED_RESULT_CHANGED");
 must(result.summary.optimistic_type_ignored_probe_matches===20,"PINNED_RELAXED_RESULT_CHANGED");
 must(result.summary.exact_slot_ref_vectors===0,"PINNED_EXACT_RESULT_CHANGED");
 process.stdout.write(JSON.stringify(result,null,2)+"\n");
}
