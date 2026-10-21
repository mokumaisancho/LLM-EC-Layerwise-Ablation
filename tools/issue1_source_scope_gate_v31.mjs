#!/usr/bin/env node
// Strict source-scope and fail-closed scientific authority preflight.
// This is NOT an independent source adjudicator.
import fs from "node:fs";
import crypto from "node:crypto";
export const audit=function audit(input,proposal){
const pins={"airline":{policy:"8098be7db3f47de943fad39d1e057ede6cc6cd04",tasks:"a18c17a1619ab1b78370ac0bc5f0e4df46cff5b9",lines:120,count:50},"retail":{policy:"d127e6b074654926f337d0d98b0e669ebe90d19e",tasks:"2c6373d7ab16cf1b9543043d31d87f0daf292d92",lines:77,count:114}};
function assert(ok,error){if(!ok)throw Error(error)}
assert(input?.schema==="ISSUE1_SOURCE_AUTHORITY_V31","BAD_SCHEMA");
assert(input?.commit==="864350a8971a8f8ee9e7b8472e2edc380a806b0c","SOURCE_COMMIT_DRIFT");
assert(Object.keys(input.domains||{}).sort().join()==="airline,retail","SOURCE_DOMAIN_DRIFT");
let lineCount=0,taskCount=0,cellCount=0;
for(const key of ["airline","retail"]){
const d=input.domains[key],p=pins[key];
assert(d.policy?.sha===p.policy && d.tasks?.sha===p.tasks,"SOURCE_BLOB_DRIFT_"+key);
assert(Array.isArray(d.policy.lines)&&d.policy.lines.length===p.lines,"SOURCE_LINE_COUNT_"+key);
let nums=new Set();
for(const l of d.policy.lines){assert(Number.isInteger(l.line)&&l.line>0&&typeof l.text==="string"&&l.text.trim().length>0&&!nums.has(l.line),"INVALID_OR_DUPLICATE_POLICY_LINE_"+key);nums.add(l.line);}
assert(Array.isArray(d.tasks.cases)&&d.tasks.cases.length===p.count,"TASK_COUNT_"+key);
let ids=new Set();
for(const row of d.tasks.cases){
assert(row.case_id?.startsWith(key+"/")&&!ids.has(row.case_id),"TASK_DUPLICATE_"+key);ids.add(row.case_id);
assert(row.publisher_source_sha===p.tasks,"TASK_UNPINNED_"+key);
assert(Number.isInteger(row.explicit_nl_count) && row.explicit_nl_count>=0,"ASSERTION_COUNT_"+key);
}
lineCount+=nums.size;taskCount+=ids.size;cellCount+=nums.size*ids.size;
}
assert(lineCount===197&&taskCount===164&&cellCount===14778,"GLOBAL_SCOPE_INCOMPLETE");
const base={science:"BLOCKED_EXTERNAL",source_scope:"COMPLETE",policy_nonempty_lines:lineCount,original_tasks:taskCount,task_line_pairs:cellCount};
if(proposal==null)return {...base,source_gate:"PASS",semantic_obligation_qualification:false};
if(proposal.certify===true){
 assert(Array.isArray(proposal.case_clause_rows)&&proposal.case_clause_rows.length===cellCount,"PER_CASE_POLICY_REVIEW_NOT_COMPLETE");
 const seen=new Set();
 for(const x of proposal.case_clause_rows){
 const d=input.domains[x.case_id?.split("/")[0]];
 assert(d && d.tasks.cases.some(c=>c.case_id===x.case_id) && d.policy.lines.some(l=>l.line===x.line),"ORPHAN_POLICY_CLAUSE");
 const id=x.case_id+"#"+x.line;assert(!seen.has(id),"DUPLICATE_REVIEW_CELL");seen.add(id);
 assert(["MANDATORY","NON_APPLICABLE","NON_NORMATIVE"].includes(x.disposition) && typeof x.reason==="string"&&x.reason.trim(),"MISSING_JUSTIFICATION");
 }
 assert(proposal.independent_witness_verified===true&&proposal.gold_hidden_from_predictor===true&&proposal.upstream_all_layers_pinned===true&&proposal.real_NL_judge_verified===true,"MISSING_SCIENTIFIC_CUSTODY");
 // No trusted independent public key has been enrolled for this evaluator version.
 // A Boolean or arbitrary signature from the same source cannot confer independent authority.
 throw Error("NO_INDEPENDENT_CRYPTOGRAPHIC_WITNESS_PINNED");
}
assert(proposal.certify!==true,"UNTRUSTED");
return {...base,source_gate:"PASS",semantic_obligation_qualification:false};
};
function blob(content){let b=Buffer.from(content,"utf8");return crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob "+b.length+String.fromCharCode(0)),b])).digest("hex");}
if(process.argv[1]?.endsWith("issue1_source_scope_gate_v31.mjs")){
  try{
    if(process.argv.length!==6)throw Error("Usage: node gate.mjs airline-policy.md airline-tasks.json retail-policy.md retail-tasks.json");
    let domains={},names=["airline","retail"],j=2;
    for(const key of names){
      const p=fs.readFileSync(process.argv[j++],"utf8"),t=fs.readFileSync(process.argv[j++],"utf8");
      domains[key]={policy:{sha:blob(p),lines:p.split("\n").map((text,i)=>({line:i+1,text})).filter(x=>x.text.trim())},
      tasks:{sha:blob(t),cases:JSON.parse(t).map(row=>({case_id:key+"/"+row.id,publisher_source_sha:blob(t),explicit_nl_count:(row.evaluation_criteria?.nl_assertions||[]).length}))}};
    }
    let r=audit({schema:"ISSUE1_SOURCE_AUTHORITY_V31",commit:"864350a8971a8f8ee9e7b8472e2edc380a806b0c",domains});
    console.log(JSON.stringify(r,null,2));process.exitCode=2; // source PASS; scientific authority BLOCKED_EXTERNAL
  }catch(e){console.error(String(e));process.exitCode=3;}
}
