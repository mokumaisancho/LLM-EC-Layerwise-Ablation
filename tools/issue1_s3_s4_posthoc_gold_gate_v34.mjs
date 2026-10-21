#!/usr/bin/env node
// Real source-pinned public development data post-hoc inconsistency gate; NOT independent hidden S3 gold.
import fs from "node:fs";
import crypto from "node:crypto";
export const audit=function audit(source,prior){
const stop=x=>{throw Error("REJECT:"+x)};
if(!Array.isArray(source?.data)||source.data.length!==83)stop("PUBLISHER_SHAPE");
if(prior?.schema!=="ISSUE1_MULTIRC_REAL_NATIVE_EC_LEXICAL_SOURCE_BRIDGE_V18"||prior.source?.mirror_corpus_git_blob!=="847cbabd9de66ab7f37a3e7a2a1849ef51c9b1e5"||prior.source?.native_EC_commit!=="3f435ad4365d846d96264458540efb4848ce3541")stop("SOURCE_PIN_OR_SCHEMA");
const records=prior.actual_native_execution?.raw_prediction_receipts;
if(!Array.isArray(records)||records.length!==32||prior.sample_plan?.algorithm!=="first_32_questions_in_publisher_frozen_index_order")stop("SAMPLE_SCOPE");
const qs=[];
for(let i=0;i<source.data.length;i++){
const list=source.data[i]?.paragraph?.questions;
if(!Array.isArray(list))stop("PUBLISHER_QUESTIONS");
for(let j=0;j<list.length;j++){let arr=list[j]?.answers;if(!Array.isArray(arr)||!arr.length)stop("PUBLISHER_ANSWERS");qs.push({id:i+"/"+j,options:arr.map((_,k)=>i+"/"+j+"/"+k),gold:arr.flatMap((a,k)=>a.isAnswer===true?[i+"/"+j+"/"+k]:[])});}
}
if(qs.length!==953)stop("PUBLISHER_TOTAL");
let tally={TP:0,FP:0,FN:0,TN:0},seen=new Set(),out=[];
for(let x of records){
let q=qs.slice(0,32).find(y=>y.id===x.question_id);
if(!q||seen.has(x.question_id))stop("CASE_ORDER_OR_DUPLICATE");
seen.add(x.question_id);
if(["gold","isAnswer","gold_candidate_ids"].some(k=>Object.hasOwn(x,k)))stop("GOLD_CONTAMINATION");
if(x.native_source_commit!=="3f435ad4365d846d96264458540efb4848ce3541"||!/^[a-f0-9]{64}$/.test(x.input_sha256||""))stop("SOURCE_BINDING");
if(!Array.isArray(x.selected_candidate_ids)||new Set(x.selected_candidate_ids).size!==x.selected_candidate_ids.length)stop("DUPLICATE_SELECTION");
if(x.selected_candidate_ids.some(id=>!q.options.includes(id)))stop("UNKNOWN_SELECTION");
if(!["CLOSE","BLOCKED"].includes(x.s4_formal_diagnostic))stop("UNRECOGNIZED_S4");
let gold=new Set(q.gold),got=new Set(x.selected_candidate_ids);
for(let id of q.options){let k=gold.has(id)?got.has(id)?"TP":"FN":got.has(id)?"FP":"TN";tally[k]++}
let miss=q.gold.filter(id=>!got.has(id)),extra=x.selected_candidate_ids.filter(id=>!gold.has(id));
let exact=miss.length===0&&extra.length===0;
out.push({question_id:q.id,exact_set:exact,original_formal_close:x.s4_formal_diagnostic==="CLOSE",missing_gold:miss,extraneous_selections:extra,posthoc_gold_consistency:x.s4_formal_diagnostic==="CLOSE"&&exact?"CONSISTENT_NOT_SCIENTIFIC_S4":"BLOCK",true_real_world_S4_complete:false});
}
if(seen.size!==32)stop("MISSING_RECEIPTS");
let close=out.filter(x=>x.original_formal_close).length,blockedWrong=out.filter(x=>x.original_formal_close&&!x.exact_set).length,exact=out.filter(x=>x.exact_set).length;
for(let k of ["TP","FP","FN","TN"])if(tally[k]!==prior.actual_native_execution[k])stop("HISTORICAL_COUNTER_"+k);
if(close!==prior.actual_native_execution.formal_question_close||blockedWrong!==prior.actual_native_execution.formal_close_with_wrong_published_answer_set||exact!==prior.actual_native_execution.exact_candidate_sets)stop("HISTORICAL_SUMMARY");
return {schema:"ISSUE1_MULTIRC_D04_D05_POSTHOC_GATE_V34",source:"public third-party MultiRC development labels, not genuinely blind heldout",record_count:32,counts:{...tally,exact_sets:exact,original_formal_close:close,wrong_set_formal_close_prevented:blockedWrong,source_consistent_formal_close:close-blockedWrong,preexisting_block:32-close},scientific_scope:"DIAGNOSTIC_ONLY",scientific_original_MVP:{passed:2,required:18,promoted:0},cases:out};
};
function gitBlob(bytes){return crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+bytes.length+String.fromCharCode(0)),bytes])).digest("hex");}
if(process.argv[1]?.endsWith("issue1_s3_s4_posthoc_gold_gate_v34.mjs")){
 try{
  if(process.argv.length!==4)throw Error("Usage: node gate.mjs multirc-pinned-devData.json native-v18-32-receipt.json");
  const a=fs.readFileSync(process.argv[2]),b=fs.readFileSync(process.argv[3]);
  if(gitBlob(a)!=="847cbabd9de66ab7f37a3e7a2a1849ef51c9b1e5"||gitBlob(b)!=="f0ce951cf03952dafdc949e6719c057184e31e1e")throw Error("SOURCE_BLOB_DRIFT");
  console.log(JSON.stringify(audit(JSON.parse(a),JSON.parse(b)),null,2));
  process.exitCode=2; // Scoped post-hoc check passes; scientific root 2/18 remains open
 }catch(e){console.error(String(e));process.exitCode=3;}
}
